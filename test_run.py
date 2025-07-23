# test_run.py (create in root directory)
import sys
import os
from datetime import datetime

# Add src to path so we can import our modules
sys.path.append('src')

from data_fusion_agent import SuperEfficientDataFusionAgent

def run_debug_cycle():
    """Run one complete data fusion cycle with detailed debug logging"""
    print("🚀 NAMMA NAVIGATOR - DEBUG TEST RUN")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    try:
        # Initialize the agent
        print("🔧 Initializing Data Fusion Agent...")
        agent = SuperEfficientDataFusionAgent()
        print("✅ Agent initialized successfully")
        print()
        
        # Phase 1: Show what posts are being collected
        print("📡 PHASE 1: DATA COLLECTION FROM REDDIT")
        print("="*50)
        
        # Get raw posts with detailed logging
        raw_posts = agent.intelligent_data_ingestion()
        
        if not raw_posts:
            print("⚠️ No posts collected! Check your Reddit API credentials.")
            return
        
        print(f"\n📊 COLLECTION SUMMARY:")
        print(f"  Total high-signal posts: {len(raw_posts)}")
        
        # Show breakdown by subreddit and category
        subreddit_breakdown = {}
        category_breakdown = {}
        
        for post in raw_posts:
            # Count by subreddit
            subreddit = post['subreddit']
            subreddit_breakdown[subreddit] = subreddit_breakdown.get(subreddit, 0) + 1
            
            # Count by category
            category = post['category_hint']
            category_breakdown[category] = category_breakdown.get(category, 0) + 1
        
        print(f"\n📋 POSTS BY SUBREDDIT:")
        for subreddit, count in subreddit_breakdown.items():
            print(f"  r/{subreddit}: {count} posts")
        
        print(f"\n🏷️ POSTS BY CATEGORY:")
        for category, count in category_breakdown.items():
            print(f"  {category.capitalize()}: {count} posts")
        
        print(f"\n🎯 TOP 10 COLLECTED POSTS:")
        for i, post in enumerate(raw_posts[:10]):
            print(f"\n  {i+1}. [{post['category_hint'].upper()}] r/{post['subreddit']}")
            print(f"     📝 Title: {post['title'][:60]}...")
            print(f"     📊 Score: {post['score']} | Comments: {post['num_comments']} | Priority: {post['priority_score']:.1f}")
            if post['content']:
                print(f"     💬 Content: {post['content'][:80]}...")
        
        # Phase 2: Show AI processing
        print(f"\n🤖 PHASE 2: AI SYNTHESIS WITH GEMINI")
        print("="*50)
        
        # Process with Gemini (limit to 15 for testing)
        test_posts = raw_posts[:15]
        print(f"Processing top {len(test_posts)} posts with Gemini AI...")
        
        events = agent.hyper_efficient_synthesis(test_posts)
        
        if not events:
            print("⚠️ No events synthesized! Check your Gemini API key.")
            return
        
        # Phase 3: Show results
        print(f"\n💾 PHASE 3: PROCESSED RESULTS")
        print("="*50)
        
        # Store to Firebase
        agent.real_time_storage(events)
        
        print(f"\n🎯 SYNTHESIS RESULTS:")
        print(f"  Input posts: {len(test_posts)}")
        print(f"  Output events: {len(events)}")
        print(f"  Compression ratio: {len(test_posts)/len(events):.1f}:1")
        
        # Show detailed transformation
        print(f"\n📋 DETAILED POST → EVENT TRANSFORMATIONS:")
        for i, event in enumerate(events):
            print(f"\n  Event {i+1}:")
            print(f"    🔍 Original Post: {event.get('original_title', 'N/A')[:50]}...")
            print(f"    📡 Source: r/{event.get('source_subreddit', 'unknown')}")
            print(f"    ✨ AI Summary: {event['summary']}")
            print(f"    📊 Category: {event['category']} | Severity: {event['severity']}")
            print(f"    📍 Location: {event['location']}")
            print(f"    🚨 Urgency: {event['urgency_score']}/10")
            if event.get('actionable_advice'):
                print(f"    💡 Advice: {event['actionable_advice']}")
            if event.get('affects_traffic'):
                print(f"    🚦 Traffic Impact: Yes")
        
        # Summary statistics
        print(f"\n📈 FINAL STATISTICS:")
        print(f"  🔍 Posts scanned from Reddit: {len(raw_posts)}")
        print(f"  🤖 Events created by AI: {len(events)}")
        print(f"  💾 Events stored in Firebase: {len(events)}")
        
        # Show category distribution of final events
        final_categories = {}
        severity_levels = {}
        
        for event in events:
            cat = event['category']
            final_categories[cat] = final_categories.get(cat, 0) + 1
            
            sev = event['severity']
            severity_levels[sev] = severity_levels.get(sev, 0) + 1
        
        print(f"\n🏷️ FINAL EVENT CATEGORIES:")
        for category, count in final_categories.items():
            print(f"  {category.capitalize()}: {count} events")
        
        print(f"\n⚠️ SEVERITY BREAKDOWN:")
        for severity, count in severity_levels.items():
            print(f"  {severity.capitalize()}: {count} events")
        
        print(f"\n✅ DEBUG TEST RUN COMPLETED SUCCESSFULLY!")
        print(f"🎯 Your Namma Navigator system is processing Bengaluru data effectively!")
        
    except Exception as e:
        print(f"\n❌ ERROR DURING EXECUTION:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"\n🔍 FULL TRACEBACK:")
        import traceback
        traceback.print_exc()
        
        # Helpful debugging suggestions
        print(f"\n💡 DEBUGGING SUGGESTIONS:")
        if "reddit" in str(e).lower():
            print("  - Check your Reddit API credentials in config/.env")
            print("  - Verify your Reddit app is set to 'script' type")
        elif "gemini" in str(e).lower() or "generative" in str(e).lower():
            print("  - Check your Gemini API key in config/.env")
            print("  - Verify you have quota remaining")
        elif "firebase" in str(e).lower():
            print("  - Check your Firebase service account key path")
            print("  - Verify your Firebase project ID is correct")
        else:
            print("  - Check all API keys in config/.env")
            print("  - Ensure all dependencies are installed")

def show_config_status():
    """Show current configuration status"""
    print(f"\n🔧 CONFIGURATION STATUS:")
    
    # Check .env file
    env_path = 'config/.env'
    if os.path.exists(env_path):
        print(f"  ✅ .env file found")
        from dotenv import load_dotenv
        load_dotenv(env_path)
        
        required_keys = ['FIREBASE_PROJECT_ID', 'GEMINI_API_KEY', 'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET']
        for key in required_keys:
            if os.getenv(key):
                print(f"  ✅ {key}: Set")
            else:
                print(f"  ❌ {key}: Missing")
    else:
        print(f"  ❌ .env file not found at {env_path}")
    
    # Check Firebase service account
    firebase_key_path = 'config/firebase-service-account.json'
    if os.path.exists(firebase_key_path):
        print(f"  ✅ Firebase service account key found")
    else:
        print(f"  ❌ Firebase service account key not found at {firebase_key_path}")

if __name__ == "__main__":
    print("🚀 Starting Namma Navigator Debug Test...")
    show_config_status()
    print()
    
    # Ask user if they want to proceed
    try:
        response = input("Do you want to run the debug cycle? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            run_debug_cycle()
        else:
            print("Debug run cancelled.")
    except KeyboardInterrupt:
        print("\n\n⏹️ Debug run interrupted by user.")
