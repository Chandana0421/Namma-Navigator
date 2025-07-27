import logging
import warnings
from google.adk import Agent
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

warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")
load_dotenv('config/.env')

logger = logging.getLogger(__name__)


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
    """Decorator for retrying a function with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    if i == max_retries - 1:
                        logger.error(
                            f"Final attempt for {func.__name__} failed after {max_retries} retries.")
                        raise e

                    jitter = random.uniform(0, delay * 0.1)
                    wait_time = min(delay + jitter, max_delay)

                    logger.warning(
                        f"{func.__name__} failed ({type(e).__name__}). Retrying in {wait_time:.2f}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(wait_time)
                    delay *= 2
        return wrapper
    return decorator


def _extract_json_from_response(text: str) -> Optional[str]:
    match = re.search(r'```json(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'(\[.*?\]|\{.*?\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None


class FirebaseClient:
    def __init__(self):
        if not firebase_admin._apps:
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            cert_path = os.path.join(
                project_root, 'config', 'firebase-service-account.json')

            if not os.path.exists(cert_path):
                raise FileNotFoundError(
                    f"Could not find the Firebase service account key. Expected at: {cert_path}")

            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()


def fetch_reddit_posts() -> dict:
    """Fetches high-signal Reddit posts about Bengaluru."""
    try:
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )

        bengaluru_signals = {
            'traffic': ['traffic', 'jam', 'road', 'signal', 'blocked', 'accident', 'stuck'],
            'infrastructure': ['pothole', 'construction', 'metro', 'water', 'power cut', 'outage'],
            'weather': ['rain', 'flood', 'waterlogged', 'storm', 'weather'],
            'events': ['protest', 'rally', 'festival', 'event', 'crowd', 'gathering'],
            'civic': ['garbage', 'complaint', 'bbmp', 'civic', 'municipal']
        }

        bengaluru_areas = [
            'koramangala', 'indiranagar', 'whitefield', 'electronic city', 'hsr layout',
            'jayanagar', 'malleshwaram', 'rajajinagar', 'hebbal', 'sarjapur',
            'marathahalli', 'btm layout', 'mg road', 'brigade road', 'commercial street',
            'silk board', 'outer ring road', 'bannerghatta road', 'old airport road'
        ]

        def _is_high_signal_content(post) -> bool:
            text = (post.title + " " + post.selftext).lower()
            bengaluru_mentioned = any(area in text for area in bengaluru_areas)
            bengaluru_keywords = any(word in text for word in [
                                     'bengaluru', 'bangalore', 'blr'])
            actionable_content = any(
                any(keyword in text for keyword in keywords) for keywords in bengaluru_signals.values()
            )
            is_recent = (time.time() - post.created_utc) < 86400
            has_engagement = post.score > 5 or post.num_comments > 3
            return (bengaluru_mentioned or bengaluru_keywords) and actionable_content and (is_recent or has_engagement)

        def _quick_categorize(text: str) -> str:
            text = text.lower()
            for category, keywords in bengaluru_signals.items():
                if any(keyword in text for keyword in keywords):
                    return category
            return 'general'

        def _calculate_priority(post) -> float:
            score = post.score * 0.1 + post.num_comments * 0.2
            hours_old = (time.time() - post.created_utc) / 3600
            if hours_old < 1:
                score += 10
            elif hours_old < 6:
                score += 5
            elif hours_old < 24:
                score += 2
            urgent_keywords = ['accident', 'emergency',
                               'blocked', 'stuck', 'help', 'urgent']
            text = (post.title + " " + post.selftext).lower()
            score += sum(5 for keyword in urgent_keywords if keyword in text)
            return score

        logger.info("Fetching Reddit posts...")
        high_signal_posts = []
        target_subreddits = ['bangalore', 'bengaluru', 'india']

        for subreddit_name in target_subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            post_sources = [("HOT", subreddit.hot(limit=30)),
                            ("NEW", subreddit.new(limit=20))]

            for source_type, post_source in post_sources:
                for post in post_source:
                    if _is_high_signal_content(post):
                        post_data = {
                            'id': post.id, 'title': post.title, 'content': post.selftext,
                            'score': post.score, 'created_utc': post.created_utc,
                            'subreddit': subreddit_name, 'url': post.url, 'num_comments': post.num_comments,
                            'category_hint': _quick_categorize(f"{post.title} {post.selftext}"),
                            'priority_score': _calculate_priority(post), 'source_type': source_type,
                            'timestamp': datetime.now().isoformat(),
                        }
                        high_signal_posts.append(post_data)

        high_signal_posts.sort(key=lambda x: x['priority_score'], reverse=True)
        logger.info(
            f"Fetched {len(high_signal_posts[:50])} high-signal Reddit posts")
        return {'posts': high_signal_posts[:50]}
    except Exception as e:
        logger.warning(f"Exception in fetch_reddit_posts: {e}")
        return {'posts': []}


@retry_with_exponential_backoff()
def filter_posts_with_gemini(posts: list, preferences: dict = None) -> dict:
    """Filters posts using Gemini based on preferences."""
    if not posts:
        return {'filtered_posts': []}

    logger.info(f"Filtering {len(posts)} posts with Gemini...")
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    filter_model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are a JSON filtering agent. Your task is to filter a list of Reddit posts based on user preferences.
    Analyze the user preferences and the list of posts provided.
    Return a valid JSON array containing only the post objects that match the user's preferences.
    The structure of the returned post objects must be identical to the input post objects.

    USER PREFERENCES:
    {json.dumps(preferences or {}, indent=2)}

    REDDIT POSTS:
    {json.dumps(posts, indent=2)}

    IMPORTANT:
    - Your entire response must be ONLY the JSON array.
    - Do not include any explanatory text, markdown, or any characters before or after the JSON array.
    - If no posts match the preferences, you MUST return an empty JSON array: [].
    """

    response = filter_model.generate_content(prompt)
    json_text = _extract_json_from_response(response.text)
    if not json_text:
        logger.warning("No valid JSON found in the model's response.")
        return {'filtered_posts': []}

    filtered_posts = json.loads(json_text)
    logger.info(f"Gemini filter selected {len(filtered_posts)} posts")
    return {'filtered_posts': filtered_posts}


@retry_with_exponential_backoff()
def synthesize_events_with_gemini(filtered_posts: list, preferences: dict = None) -> dict:
    """Synthesizes posts into actionable events using Gemini."""
    if not filtered_posts:
        return {'events': []}

    logger.info(
        f"Synthesizing {len(filtered_posts)} posts into events with Gemini...")
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    inference_model = genai.GenerativeModel('gemini-1.5-flash')

    preferred_category = (preferences or {}).get('categories', ['general'])[0]
    all_events = []

    batches = [filtered_posts[i:i+5] for i in range(0, len(filtered_posts), 5)]
    for batch in batches:
        try:
            prompt = f"""
            BENGALURU CITY INTELLIGENCE AGENT - INFERENCE
            Category: {preferred_category.upper()}
            Analyze these {len(batch)} posts and create actionable city intelligence in a JSON array.
            """

            for i, post in enumerate(batch):
                prompt += f"POST {i+1}: Title: {post['title']}, Content: {post['content'][:300]}"

            prompt += """
            FOR EACH POST, provide JSON output:
            {"post_number": int, "event_id": "unique_id", "category": "category", "severity": "low/medium/high/critical", "summary": "actionable sentence", "location": "Bengaluru area", "actionable_advice": "citizen advice", "urgency_score": 1-10, "affects_traffic": bool, "estimated_duration": "time estimate"}
            """

            response = inference_model.generate_content(prompt)
            json_text = _extract_json_from_response(response.text)

            if not json_text:
                logger.warning(
                    "No valid JSON found in synthesis response, using fallback.")
                for post in batch:
                    all_events.append({
                        'id': hashlib.md5(post['id'].encode()).hexdigest()[:12],
                        'summary': post['title'],
                        'category': preferred_category,
                        'severity': 'medium',
                        'location': 'Bengaluru',
                        'actionable_advice': 'Check local updates',
                        'urgency_score': 5,
                        'affects_traffic': preferred_category == 'traffic',
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
                        'category': analysis.get('category', preferred_category),
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
            logger.warning(f"Synthesis error on batch: {e}, falling back.")
            for post in batch:
                all_events.append({
                    'id': hashlib.md5(post['id'].encode()).hexdigest()[:12],
                    'summary': post['title'],
                    'category': preferred_category,
                    'severity': 'medium',
                    'location': 'Bengaluru',
                    'actionable_advice': 'Check local updates',
                    'urgency_score': 4,
                    'affects_traffic': preferred_category == 'traffic',
                    'timestamp': datetime.now().isoformat(),
                    'processed_by': 'fallback',
                })

    logger.info(f"Synthesized {len(all_events)} events")
    return {'events': all_events}


def store_events_to_firestore(events: list) -> dict:
    """Stores events to Firestore and prints inference details."""
    if not events:
        logger.warning("No events to store")
        return {'result': 'no events'}

    print("💾 Storing Events to Firestore with Agent Inference:")
    print("=" * 60)

    firebase_client = FirebaseClient()
    batch = firebase_client.db.batch()
    current_time = datetime.now()

    for i, event in enumerate(events):
        print(f"  Event {i+1}:")
        print(f"    📝 Summary: {event.get('summary', 'N/A')}")
        print(
            f"    🏷️ Category: {event.get('category', 'general')} | Severity: {event.get('severity', 'medium')}")
        print(f"    📍 Location: {event.get('location', 'Bengaluru')}")
        print(f"    💡 Advice: {event.get('actionable_advice', 'N/A')}")
        print("-" * 40)

        doc_ref = firebase_client.db.collection(
            'live_events').document(event['id'])
        event.update({
            'created_at': current_time,
            'expires_at': current_time + timedelta(hours=24),
            'indexed_location': event.get('location', 'bengaluru').lower(),
            'searchable_text': f"{event.get('summary', '')} {event.get('location', '')} {event.get('category', '')}".lower()
        })
        batch.set(doc_ref, event)

    batch.commit()
    print(f"✅ Batch storage of {len(events)} events completed")
    print("=" * 60)
    return {'result': 'success'}


def process_bengaluru_intelligence(preferences: dict = None) -> dict:
    """Main function to process Bengaluru city intelligence."""
    if preferences is None:
        preferences = {
            'categories': ['traffic', 'infrastructure', 'weather', 'events', 'civic']
        }

    reddit_result = fetch_reddit_posts()
    posts = reddit_result.get('posts', [])

    if not posts:
        return {'result': 'no posts found'}

    filter_result = filter_posts_with_gemini(posts, preferences)
    filtered_posts = filter_result.get('filtered_posts', [])

    if not filtered_posts:
        return {'result': 'no posts matched preferences'}

    synthesis_result = synthesize_events_with_gemini(
        filtered_posts, preferences)
    events = synthesis_result.get('events', [])

    if not events:
        return {'result': 'no events synthesized'}

    storage_result = store_events_to_firestore(events)

    return {
        'posts_fetched': len(posts),
        'posts_filtered': len(filtered_posts),
        'events_created': len(events),
        'storage_status': storage_result['result']
    }


def rate_limit_callback():
    """Rate limiting callback for ADK agent."""
    if not hasattr(rate_limit_callback, '_last_api_call'):
        rate_limit_callback._last_api_call = 0
        rate_limit_callback._api_calls_today = 0
        rate_limit_callback._daily_limit = 250

    now = time.time()
    if datetime.now().hour == 0 and datetime.now().minute == 0:
        rate_limit_callback._api_calls_today = 0

    if now - rate_limit_callback._last_api_call < 6:
        time.sleep(6 - (now - rate_limit_callback._last_api_call))

    if rate_limit_callback._api_calls_today >= rate_limit_callback._daily_limit:
        logger.warning("Daily API limit reached.")
        return False

    rate_limit_callback._last_api_call = time.time()
    rate_limit_callback._api_calls_today += 1
    return True


def before_agent():
    """Callback before agent execution."""
    logger.info("Starting Bengaluru city intelligence processing...")


def before_tool(tool_name: str):
    """Callback before tool execution."""
    logger.info(f"Executing tool: {tool_name}")


def after_tool(tool_name: str, result: any):
    """Callback after tool execution."""
    logger.info(f"Tool {tool_name} completed")


GLOBAL_INSTRUCTION = """
You are the Bengaluru City Pulse Agent, specialized in monitoring and analyzing real-time city intelligence 
from Reddit posts about Bengaluru/Bangalore. Your role is to fetch, filter, synthesize, and store actionable 
city events that help citizens stay informed about traffic, infrastructure, weather, events, and civic issues.
"""

INSTRUCTION = """
Process Bengaluru city intelligence by:
1. Fetching high-signal Reddit posts from relevant subreddits
2. Filtering posts based on user preferences  
3. Synthesizing posts into actionable city events
4. Storing events in Firestore for citizen access

Focus on traffic updates, infrastructure issues, weather alerts, civic events, and municipal concerns.
Prioritize recent, high-engagement posts with location-specific information.
"""

city_pulse_agent = Agent(
    model="gemini-1.5-flash",
    global_instruction=GLOBAL_INSTRUCTION,
    instruction=INSTRUCTION,
    name="BengaluruCityPulseAgent",
    tools=[
        fetch_reddit_posts,
        filter_posts_with_gemini,
        synthesize_events_with_gemini,
        store_events_to_firestore,
        process_bengaluru_intelligence,
    ],
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_agent_callback=before_agent,
    before_model_callback=rate_limit_callback,
)


class SuperEfficientDataFusionAgent:
    """Wrapper class to maintain compatibility with existing imports."""

    def __init__(self):
        self.agent = city_pulse_agent

    def run(self, inputs: dict):
        """Run the agent with given inputs."""
        preferences = inputs.get('preferences', {
            'categories': ['traffic', 'infrastructure', 'weather', 'events', 'civic']
        })
        return process_bengaluru_intelligence(preferences)

    def smart_rate_limiter(self):
        """Legacy rate limiter method."""
        return rate_limit_callback()


CityPulseAgent = SuperEfficientDataFusionAgent

if __name__ == "__main__":
    agent = SuperEfficientDataFusionAgent()
    inputs = {
        'preferences': {
            'categories': ['traffic', 'infrastructure', 'weather', 'events', 'civic']
        }
    }
    result = agent.run(inputs)
    logger.info("Agent run result:")
    logger.info(json.dumps(result, indent=2))
