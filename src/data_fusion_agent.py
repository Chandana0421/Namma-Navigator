from google.agent import Agent, Tool, Workflow, Context
import os
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import google.api_core.exceptions as google_exceptions
import praw
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import functools
import random

load_dotenv('config/.env')


def retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=5,
    max_delay=60,
    allowed_exceptions=(
        google_exceptions.ResourceExhausted,
        google_exceptions.ServiceUnavailable,
        google_exceptions.DeadlineExceeded,
        json.JSONDecodeError,
    )
):
    """
    Decorator for retrying a function with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if i == max_retries - 1:
                        print(
                            f"❌ Final attempt for {func.__name__} failed after {max_retries} retries.")
                        raise e

                    jitter = random.uniform(0, delay * 0.1)
                    wait_time = min(delay + jitter, max_delay)

                    print(
                        f"⚠️ {func.__name__} failed ({type(e).__name__}). Retrying in {wait_time:.2f}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(wait_time)
                    delay *= 2
        return wrapper
    return decorator


def _extract_json_from_response(text: str) -> Optional[str]:
    match = re.search(r'``````', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'(\[.*?\]|\{.*?\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None


class FirebaseClient:

         def __init__(self):
                 if not firebase_admin._apps:


                        cred = credentials.Certificate('config/firebase-service-account.json')
                        firebase_admin.initialize_app(cred)
                self.db = firestore.client()


class FetchRedditPosts(Tool):

         def __init__(self, name="FetchRedditPosts"):


                super().__init__(name=name)
                # Initialize PRAW Reddit client
                self.reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
                        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                        user_agent=os.getenv('REDDIT_USER_AGENT')
               )
                self.bengaluru_signals = {
    'traffic': ['traffic', 'jam', 'road', 'signal', 'blocked', 'accident', 'stuck'],
                        'infrastructure': ['pothole', 'construction', 'metro', 'water', 'power cut', 'outage'],
                        'weather': ['rain', 'flood', 'waterlogged', 'storm', 'weather'],
                        'events': ['protest', 'rally', 'festival', 'event', 'crowd', 'gathering'],
                        'civic': ['garbage', 'complaint', 'bbmp', 'civic', 'municipal']
               }


                self.bengaluru_areas = [
    'koramangala', 'indiranagar', 'whitefield', 'electronic city', 'hsr layout',
    'jayanagar', 'malleshwaram', 'rajajinagar', 'hebbal', 'sarjapur',
    'marathahalli', 'btm layout', 'mg road', 'brigade road', 'commercial street',
    'silk board', 'outer ring road', 'bannerghatta road', 'old airport road'
]

         def _is_high_signal_content(self, post) -> bool:
                text = (post.title + " " + post.selftext).lower()
                bengaluru_mentioned = any(area in text for area in self.bengaluru_areas)
                bengaluru_keywords = any(word in text for word in ['bengaluru', 'bangalore', 'blr'])
                actionable_content = any(
    any(keyword in text for keyword in keywords) for keywords in self.bengaluru_signals.values()
               )
                is_recent = (time.time() - post.created_utc) < 86400
                has_engagement = post.score > 5 or post.num_comments > 3
                 return (bengaluru_mentioned or bengaluru_keywords) and actionable_content and (is_recent or has_engagement)

         def _quick_categorize(self, text: str) -> str:
                text = text.lower()
                 for category, keywords in self.bengaluru_signals.items():
                         if any(keyword in text for keyword in keywords):
                                 return category
                 return 'general'

         def _calculate_priority(self, post) -> float:
                score = post.score * 0.1 + post.num_comments * 0.2
                hours_old = (time.time() - post.created_utc) / 3600
                 if hours_old < 1:
                        score += 10
                 elif hours_old < 6:
                        score += 5
                 elif hours_old < 24:
                        score += 2
                urgent_keywords = ['accident', 'emergency', 'blocked', 'stuck', 'help', 'urgent']
                text = (post.title + " " + post.selftext).lower()
                score += sum(5 for keyword in urgent_keywords if keyword in text)
                 return score

         def invoke(self, context: Context, inputs: dict) -> dict:
                 try:
                         print("🔍 Fetching Reddit posts...")
                        high_signal_posts = []
                        target_subreddits = ['bangalore', 'bengaluru', 'india']
                         for subreddit_name in target_subreddits:
                                subreddit = self.reddit.subreddit(subreddit_name)
                                post_sources = [("HOT", subreddit.hot(limit=30)), ("NEW", subreddit.new(limit=20))]
                                 for source_type, post_source in post_sources:
                                         for post in post_source:
                                                 if self._is_high_signal_content(post):
                                                        post_data = {
    'id': post.id, 'title': post.title, 'content': post.selftext,
    'score': post.score, 'created_utc': post.created_utc,
    'subreddit': subreddit_name, 'url': post.url, 'num_comments': post.num_comments,
    'category_hint': self._quick_categorize(f"{post.title} {post.selftext}"),
                                                                'priority_score': self._calculate_priority(post), 'source_type': source_type,
                                                                'timestamp': datetime.now().isoformat(),
                                                       }
                                                        high_signal_posts.append(post_data)


                        # Sort descending priority and limit
                        high_signal_posts.sort(key=lambda x: x['priority_score'], reverse=True)
                         print(f"✅ Fetched {len(high_signal_posts[:50])} high-signal Reddit posts")
                         return {'posts': high_signal_posts[:50]}
                 except Exception as e:
                         print(f"⚠️ Exception in FetchRedditPosts: {e}")
                         return {'posts': []}


class FilterPostsWithGemini(Tool):

         def __init__(self, name="FilterPostsWithGemini"):


                super().__init__(name=name)
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                self.filter_model = genai.GenerativeModel('gemini-1.5-flash')


        @retry_with_exponential_backoff()
         def invoke(self, context: Context, inputs: dict) -> dict:
                posts = inputs.get('posts', [])
                preferences = inputs.get('preferences', {})
                 if not posts:
                         return {'filtered_posts': []}
                 print(f"🤖 Filtering {len(posts)} posts with Gemini...")


                prompt = f"""
        You are a JSON filtering agent. Your task is to filter a list of Reddit posts based on user preferences.
        Analyze the user preferences and the list of posts provided.
        Return a valid JSON array containing only the post objects that match the user's preferences.
        The structure of the returned post objects must be identical to the input post objects.


        USER PREFERENCES:
        {json.dumps(preferences, indent=2)}


        REDDIT POSTS:
        {json.dumps(posts, indent=2)}


        IMPORTANT:
        - Your entire response must be ONLY the JSON array.
        - Do not include any explanatory text, markdown, or any characters before or after the JSON array.
        - If no posts match the preferences, you MUST return an empty JSON array: [].
        """
                 if not context.agent.smart_rate_limiter():
                         raise Exception("Rate limit hit")
                response = self.filter_model.generate_content(prompt)
                json_text = _extract_json_from_response(response.text)
                 if not json_text:
                         print("⚠️ No valid JSON found in the model's response.")
                         return {'filtered_posts': []}
                filtered_posts = json.loads(json_text)
                 print(f"✅ Gemini filter selected {len(filtered_posts)} posts")
                 return {'filtered_posts': filtered_posts}


class SynthesizeEventsWithGemini(Tool):

         def __init__(self, name="SynthesizeEventsWithGemini"):


                super().__init__(name=name)
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                self.inference_model = genai.GenerativeModel('gemini-1.5-flash')


        @retry_with_exponential_backoff()
         def invoke(self, context: Context, inputs: dict) -> dict:
                posts = inputs.get('filtered_posts', [])
                preferences = inputs.get('preferences', {})
                 if not posts:
                         return {'events': []}
                 print(f"🤖 Synthesizing {len(posts)} posts into events with Gemini...")
                preferred_category = preferences.get('categories', ['general'])[0]
                categorized_batches = {preferred_category: posts} if posts else {}


                all_events = []
                 for category, category_posts in categorized_batches.items():
                        batches = [category_posts[i:i+5] for i in range(0, len(category_posts), 5)]
                         for batch in batches:
                                 try:
                                        prompt = f"""
                    BENGALURU CITY INTELLIGENCE AGENT - INFERENCE
                    Category: {category.upper()}
                    Analyze these {len(batch)} posts and create actionable city intelligence in a JSON array.
                    """
                                         for i, post in enumerate(batch):
                                                prompt += f"POST {i+1}: Title: {post['title']}, Content: {post['content'][:300]}"
                                        prompt += """
                    FOR EACH POST, provide JSON output:
                    {"post_number": int, "event_id": "unique_id", "category": "category", "severity": "low/medium/high/critical", "summary": "actionable sentence", "location": "Bengaluru area", "actionable_advice": "citizen advice", "urgency_score": 1-10, "affects_traffic": bool, "estimated_duration": "time estimate"}
                    """
                                         if not context.agent.smart_rate_limiter():
                                                 raise Exception("Rate limit hit")
                                        response = self.inference_model.generate_content(prompt)
                                        json_text = _extract_json_from_response(response.text)
                                         if not json_text:
                                                 print("⚠️ No valid JSON found in the model's response for synthesis.")
                                                # Fallback to simple titles as events
                                                 for post in batch:
                                                        all_events.append({
    'id': hashlib.md5(post['id'].encode()).hexdigest()[:12],
                                                                'summary': post['title'],
                                                                'category': category,
                                                                'severity': 'medium',
                                                                'location': 'Bengaluru',
                                                                'actionable_advice': 'Check local updates',
                                                                'urgency_score': 5,
                                                                'affects_traffic': category == 'traffic',
                                                                'timestamp': datetime.now().isoformat(),
                                                       })
                                                 continue
                                        gemini_analysis = json.loads(json_text)
                                         for i, analysis in enumerate(gemini_analysis):
                                                 if i < len(batch):
                                                        event = {
    'id': hashlib.md5(batch[i]['id'].encode()).hexdigest()[:12],
                                                                'original_post_id': batch[i]['id'],
                                                                'original_title': batch[i]['title'],
                                                                'source_subreddit': batch[i]['subreddit'],
                                                                'category': analysis.get('category', category),
                                                                'severity': analysis.get('severity', 'medium'),
                                                                'summary': analysis.get('summary', batch[i]['title']),
                                                                'location': analysis.get('location', 'Bengaluru'),
                                                                'actionable_advice': analysis.get('actionable_advice'),
                                                                'urgency_score': analysis.get('urgency_score', 5),
                                                                'affects_traffic': analysis.get('affects_traffic', False),
                                                                'estimated_duration': analysis.get('estimated_duration'),
                                                                'timestamp': datetime.now().isoformat(),
                                                                'processed_by': 'inference-model',
                                                       }
                                                        all_events.append(event)
                                 except Exception as e:
                                         print(f"⚠️ Synthesis error on batch: {e}, falling back.")
                                         for post in batch:
                                                all_events.append({
    'id': hashlib.md5(post['id'].encode()).hexdigest()[:12],
                                                        'summary': post['title'],
                                                        'category': category,
                                                        'severity': 'medium',
                                                        'location': 'Bengaluru',
                                                        'actionable_advice': 'Check local updates',
                                                        'urgency_score': 4,
                                                        'affects_traffic': category == 'traffic',
                                                        'timestamp': datetime.now().isoformat(),
                                                        'processed_by': 'fallback',
                                               })
                 print(f"✅ Synthesized {len(all_events)} events")
                 return {'events': all_events}


class StoreEventsToFirestore(Tool):

         def __init__(self, name="StoreEventsToFirestore"):


                super().__init__(name=name)
                self.firebase_client = FirebaseClient()

         def invoke(self, context: Context, inputs: dict) -> dict:
                events = inputs.get('events', [])
                 if not events:
                         print("⚠️ No events to store")
                         return {'result': 'no events'}
                 print(f"💾 Storing {len(events)} events to Firestore...")
                batch = self.firebase_client.db.batch()
                current_time = datetime.now()
                 for event in events:
                        doc_ref = self.firebase_client.db.collection('live_events').document(event['id'])
                        event.update({
    'created_at': current_time,
    'expires_at': current_time + timedelta(hours=24),
                                'indexed_location': event['location'].lower(),
                                'searchable_text': f"{event['summary']} {event['location']} {event['category']}".lower()
                       })
                        batch.set(doc_ref, event)
                batch.commit()
                 print("✅ Batch storage completed")
                 return {'result': 'success'}


# Compose all tools into the workflow
fusion_workflow = Workflow(
    steps=[
        FetchRedditPosts(),
                FilterPostsWithGemini(),
                SynthesizeEventsWithGemini(),
                StoreEventsToFirestore()
    ]
)


# Define your Agent which runs the workflow
class CityPulseAgent(Agent):

         def __init__(self):


                super().__init__(workflow=fusion_workflow, name="BengaluruLivePulseAgent")

         def smart_rate_limiter(self):
                    # Provide rate limiter support to tools (copied from your agent)
                 if not hasattr(self, '_last_api_call'):
                        self._last_api_call = 0
                        self._api_calls_today = 0
                        self._daily_limit = 250
                now = time.time()
                 if datetime.now().hour == 0 and datetime.now().minute == 0:
                        self._api_calls_today = 0
                 if now - self._last_api_call < 6:
                        time.sleep(6 - (now - self._last_api_call))
                 if self._api_calls_today >= self._daily_limit:
                         print("⚠️ Daily API limit reached.")
                         return False
                self._last_api_call = time.time()
                self._api_calls_today += 1
                 return True


if __name__ == "__main__":
        agent = CityPulseAgent()
        inputs = {
    'preferences': {
        'categories': ['traffic', 'infrastructure', 'weather', 'events', 'civic']
    }
       }
        # Add the agent reference to context for smart_rate_limiter calls
        Context.agent = agent
        result = agent.run(inputs)
         print("🏆 Agent run result:")
        print(json.dumps(result, indent=2))
