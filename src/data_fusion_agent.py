import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import praw
import requests
from geopy.geocoders import Nominatim
import firebase_admin  # Add this line
from firebase_admin import credentials, firestore  # Add this line
from dotenv import load_dotenv

load_dotenv('config/.env')

class SuperEfficientDataFusionAgent:
    def __init__(self):
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate('config/firebase-service-account.json')
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        
        # Initialize Gemini with rate limiting
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Smart rate limiter for efficiency
        self.last_api_call = 0
        self.api_calls_today = 0
        self.daily_limit = 250
        
        # Initialize Reddit
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        # Bengaluru intelligence keywords
        self.bengaluru_signals = {
            'traffic': ['traffic', 'jam', 'road', 'signal', 'blocked', 'accident', 'stuck'],
            'infrastructure': ['pothole', 'construction', 'metro', 'water', 'power cut', 'outage'],
            'weather': ['rain', 'flood', 'waterlogged', 'storm', 'weather'],
            'events': ['protest', 'rally', 'festival', 'event', 'crowd', 'gathering'],
            'civic': ['garbage', 'complaint', 'bbmp', 'civic', 'municipal']
        }
        
        # Location intelligence
        self.bengaluru_areas = [
            'koramangala', 'indiranagar', 'whitefield', 'electronic city',
            'hsr layout', 'jayanagar', 'malleshwaram', 'rajajinagar',
            'hebbal', 'sarjapur', 'marathahalli', 'btm layout',
            'mg road', 'brigade road', 'commercial street', 'silk board',
            'outer ring road', 'bannerghatta road', 'old airport road'
        ]
        
    def smart_rate_limiter(self):
        """Intelligent rate limiting to maximize efficiency"""
        now = time.time()
        
        # Reset daily counter at midnight
        if datetime.now().hour == 0 and datetime.now().minute == 0:
            self.api_calls_today = 0
        
        # Check if we need to wait
        if now - self.last_api_call < 6:  # 10 calls per minute max
            time.sleep(6 - (now - self.last_api_call))
        
        # Check daily limit
        if self.api_calls_today >= self.daily_limit:
            print("⚠️ Daily API limit reached. Switching to cached processing.")
            return False
        
        self.last_api_call = time.time()
        self.api_calls_today += 1
        return True
    
    def intelligent_data_ingestion(self):
        """Fetch and pre-filter high-signal data"""
        print("🔍 Intelligent data ingestion starting...")
        
        high_signal_posts = []
        
        # Target high-activity Bengaluru subreddits
        target_subreddits = ['bangalore', 'bengaluru', 'india']
        
        for subreddit_name in target_subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get both hot and new posts for comprehensive coverage
                post_sources = [
                    subreddit.hot(limit=30),
                    subreddit.new(limit=20)
                ]
                
                for post_source in post_sources:
                    for post in post_source:
                        # Pre-filter for Bengaluru relevance
                        if self._is_high_signal_content(post):
                            post_data = {
                                'id': post.id,
                                'title': post.title,
                                'content': post.selftext,
                                'score': post.score,
                                'created_utc': post.created_utc,
                                'subreddit': subreddit_name,
                                'url': post.url,
                                'num_comments': post.num_comments,
                                'category_hint': self._quick_categorize(post.title + " " + post.selftext),
                                'priority_score': self._calculate_priority(post),
                                'timestamp': datetime.now().isoformat()
                            }
                            high_signal_posts.append(post_data)
                            
            except Exception as e:
                print(f"⚠️ Error fetching r/{subreddit_name}: {e}")
        
        # Sort by priority for intelligent processing
        high_signal_posts.sort(key=lambda x: x['priority_score'], reverse=True)
        
        print(f"✅ Collected {len(high_signal_posts)} high-signal posts")
        return high_signal_posts[:50]  # Top 50 for efficiency
    
    def _is_high_signal_content(self, post) -> bool:
        """Advanced signal detection with detailed logging"""
        text = (post.title + " " + post.selftext).lower()
        
        # Check for Bengaluru mentions
        bengaluru_mentioned = any(area in text for area in self.bengaluru_areas)
        bengaluru_keywords = any(word in text for word in ['bengaluru', 'bangalore', 'blr'])
        
        # Check for actionable content categories
        actionable_content = any(
            any(keyword in text for keyword in keywords)
            for keywords in self.bengaluru_signals.values()
        )
        
        # Priority boost for recent, high-engagement posts
        is_recent = (time.time() - post.created_utc) < 86400  # Last 24 hours
        has_engagement = post.score > 5 or post.num_comments > 3
        
        # Detailed logging for selection criteria
        location_match = bengaluru_mentioned or bengaluru_keywords
        is_relevant = location_match and actionable_content and (is_recent or has_engagement)
        
        # Debug logging (uncomment to see all decision factors)
        if is_relevant:
            matched_areas = [area for area in self.bengaluru_areas if area in text]
            matched_keywords = [word for word in ['bengaluru', 'bangalore', 'blr'] if word in text]
            matched_signals = []
            for category, keywords in self.bengaluru_signals.items():
                if any(keyword in text for keyword in keywords):
                    matched_signals.append(category)
            
            print(f"      🎯 Match reasons: Areas={matched_areas} | Keywords={matched_keywords} | Signals={matched_signals}")
        
        return is_relevant

    
    def _quick_categorize(self, text: str) -> str:
        """Fast pre-categorization without API calls"""
        text = text.lower()
        
        for category, keywords in self.bengaluru_signals.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'general'
    
    def _calculate_priority(self, post) -> float:
        """Calculate processing priority for intelligent batching"""
        score = 0
        
        # Engagement score
        score += post.score * 0.1
        score += post.num_comments * 0.2
        
        # Recency score
        hours_old = (time.time() - post.created_utc) / 3600
        if hours_old < 1:
            score += 10
        elif hours_old < 6:
            score += 5
        elif hours_old < 24:
            score += 2
        
        # Urgency keywords
        urgent_keywords = ['accident', 'emergency', 'blocked', 'stuck', 'help', 'urgent']
        text = (post.title + " " + post.selftext).lower()
        score += sum(5 for keyword in urgent_keywords if keyword in text)
        
        return score
    
    def hyper_efficient_synthesis(self, posts: List[Dict]) -> List[Dict]:
        """Ultra-efficient batch processing with Gemini"""
        if not posts:
            return []
        
        print(f"🤖 Synthesizing {len(posts)} posts with Gemini...")
        
        # Group posts by category for batch processing
        categorized_batches = {}
        for post in posts:
            category = post['category_hint']
            if category not in categorized_batches:
                categorized_batches[category] = []
            categorized_batches[category].append(post)
        
        synthesized_events = []
        
        for category, category_posts in categorized_batches.items():
            # Process in smart batches of 5 for optimal token usage
            batches = [category_posts[i:i+5] for i in range(0, len(category_posts), 5)]
            
            for batch in batches:
                if not self.smart_rate_limiter():
                    break
                
                synthesized_batch = self._process_batch_with_gemini(batch, category)
                synthesized_events.extend(synthesized_batch)
        
        return synthesized_events
    
    def _process_batch_with_gemini(self, posts: List[Dict], category: str) -> List[Dict]:
        """Process a batch of posts with detailed logging"""
        print(f"\n🤖 Processing {len(posts)} {category.upper()} posts with Gemini:")
        print("-" * 40)
        
        for i, post in enumerate(posts):
            print(f"  Batch Post {i+1}: {post['title'][:60]}...")
            print(f"    📊 Score: {post['score']} | Priority: {post['priority_score']:.1f} | r/{post['subreddit']}")
        
        try:
            # Create super-efficient prompt
            prompt = f"""
            BENGALURU CITY INTELLIGENCE AGENT
            
            Category: {category.upper()}
            Analyze these {len(posts)} posts and create actionable city intelligence:
            
            """
            
            for i, post in enumerate(posts):
                prompt += f"""
            POST {i+1}:
            Title: {post['title']}
            Content: {post['content'][:300]}
            Score: {post['score']} | Comments: {post['num_comments']}
            
            """
            
            prompt += f"""
            FOR EACH POST, provide JSON output:
            {{
                "post_number": 1-{len(posts)},
                "event_id": "unique_id",
                "category": "{category}",
                "severity": "low/medium/high/critical",
                "summary": "One clear actionable sentence",
                "location": "Extracted Bengaluru area/landmark",
                "actionable_advice": "Specific citizen advice",
                "urgency_score": 1-10,
                "affects_traffic": true/false,
                "estimated_duration": "time estimate if applicable"
            }}
            
            Output as JSON array only. No other text.
            """
            
            print(f"  🧠 Sending batch to Gemini for analysis...")
            response = self.model.generate_content(prompt)
            
            # Parse and enhance the response
            try:
                gemini_analysis = json.loads(response.text.strip())
                enhanced_events = []
                
                print(f"  ✅ Gemini processed {len(gemini_analysis)} events:")
                
                for i, analysis in enumerate(gemini_analysis):
                    if i < len(posts):  # Safety check
                        enhanced_event = {
                            'id': self._generate_event_id(posts[i]),
                            'original_post_id': posts[i]['id'],
                            'original_title': posts[i]['title'],
                            'source_subreddit': posts[i]['subreddit'],
                            'category': analysis.get('category', category),
                            'severity': analysis.get('severity', 'medium'),
                            'summary': analysis.get('summary', posts[i]['title']),
                            'location': analysis.get('location', 'Bengaluru'),
                            'actionable_advice': analysis.get('actionable_advice'),
                            'urgency_score': analysis.get('urgency_score', 5),
                            'affects_traffic': analysis.get('affects_traffic', False),
                            'estimated_duration': analysis.get('estimated_duration'),
                            'source_score': posts[i]['score'],
                            'source_comments': posts[i]['num_comments'],
                            'timestamp': datetime.now().isoformat(),
                            'processed_by': 'gemini-1.5-flash'
                        }
                        
                        # Show transformation
                        print(f"    Event {i+1}: {posts[i]['title'][:40]}...")
                        print(f"    → {enhanced_event['summary']}")
                        print(f"      Severity: {enhanced_event['severity']} | Urgency: {enhanced_event['urgency_score']}/10")
                        
                        enhanced_events.append(enhanced_event)
                
                return enhanced_events
                
            except json.JSONDecodeError:
                print(f"  ⚠️ JSON parsing error for {category} batch - using fallback")
                return self._fallback_processing(posts, category)
                
        except Exception as e:
            print(f"  ⚠️ Gemini API error: {e} - using fallback")
            return self._fallback_processing(posts, category)
    
    def _fallback_processing(self, posts: List[Dict], category: str) -> List[Dict]:
        """Fallback processing when API fails"""
        fallback_events = []
        
        for post in posts:
            event = {
                'id': self._generate_event_id(post),
                'original_post_id': post['id'],
                'category': category,
                'severity': 'medium',
                'summary': post['title'][:100],
                'location': 'Bengaluru',
                'actionable_advice': 'Check local updates',
                'urgency_score': post['priority_score'] // 2,
                'affects_traffic': category == 'traffic',
                'source_score': post['score'],
                'timestamp': datetime.now().isoformat(),
                'processed_by': 'fallback'
            }
            fallback_events.append(event)
        
        return fallback_events
    
    def _generate_event_id(self, post: Dict) -> str:
        """Generate unique event ID"""
        unique_string = f"{post['id']}{post['created_utc']}{post['title'][:20]}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def real_time_storage(self, events: List[Dict]):
        """Store processed events in Firebase with intelligent indexing"""
        if not events:
            return
        
        print(f"💾 Storing {len(events)} events to Firebase...")
        
        batch = self.db.batch()
        current_time = datetime.now()
        
        for event in events:
            # Create document reference
            doc_ref = self.db.collection('live_events').document(event['id'])
            
            # Add metadata for efficient querying
            event.update({
                'created_at': current_time,
                'expires_at': current_time + timedelta(hours=24),  # Auto-cleanup
                'indexed_location': event['location'].lower(),
                'searchable_text': f"{event['summary']} {event['location']} {event['category']}".lower()
            })
            
            batch.set(doc_ref, event)
        
        # Execute batch write for efficiency
        batch.commit()
        print("✅ Batch storage completed")
    
    def run_super_efficient_cycle(self) -> List[Dict]:
        """Execute one complete hyper-efficient fusion cycle"""
        print("🚀 SUPER-EFFICIENT DATA FUSION CYCLE STARTING...")
        start_time = time.time()
        
        # Phase 1: Intelligent data ingestion
        raw_posts = self.intelligent_data_ingestion()
        
        # Phase 2: Hyper-efficient synthesis
        synthesized_events = self.hyper_efficient_synthesis(raw_posts)
        
        # Phase 3: Real-time storage
        self.real_time_storage(synthesized_events)
        
        # Phase 4: Generate city pulse summary
        pulse_summary = self.generate_city_pulse_summary(synthesized_events)
        
        execution_time = time.time() - start_time
        
        print(f"⚡ CYCLE COMPLETE in {execution_time:.2f}s")
        print(f"📊 Processed {len(raw_posts)} posts → {len(synthesized_events)} events")
        print(f"🎯 City Pulse: {pulse_summary}")
        
        return synthesized_events
    
    def generate_city_pulse_summary(self, events: List[Dict]) -> str:
        """Generate intelligent city summary"""
        if not events:
            return "City pulse: Quiet period"
        
        # Quick analysis without API calls
        categories = {}
        high_urgency = 0
        traffic_affected = 0
        
        for event in events:
            cat = event['category']
            categories[cat] = categories.get(cat, 0) + 1
            if event['urgency_score'] >= 7:
                high_urgency += 1
            if event.get('affects_traffic'):
                traffic_affected += 1
        
        top_category = max(categories.items(), key=lambda x: x[1])[0]
        
        pulse = f"{len(events)} active events. "
        pulse += f"Primary concern: {top_category}. "
        
        if high_urgency > 0:
            pulse += f"{high_urgency} urgent situations. "
        if traffic_affected > 0:
            pulse += f"{traffic_affected} traffic-affecting events."
        
        return pulse
