from data_fusion_agent import SuperEfficientDataFusionAgent
import sys
import os

# Add src to path so we can import our modules
sys.path.append('src')


def run_single_cycle():
    """Run one complete data fusion cycle"""
    print("🚀 Starting Namma Navigator Test Run...")

    try:
        # Define sample user preferences for the test run
        # user_preferences = {
        #     "categories": ["traffic", "events", "infrastructure"],
        #     "keywords": ["jam", "accident", "protest", "metro", "power cut"],
        #     "min_urgency": 4,
        #     "relevant_areas": ["koramangala", "indiranagar", "silk board", "marathahalli"]
        # }
        user_preferences = {
            "categories": ["economy"],
            "keywords": ['dance', 'tax', 'capgemini'],
            "min_urgency": 8,
            "relevant_areas": ["bengaluru", "bengalore"]
        }

        print("📋 Using Sample User Preferences:")
        print(user_preferences)

        # Initialize the agent
        agent = SuperEfficientDataFusionAgent()

        # Run one complete cycle with the preferences
        events = agent.run_super_efficient_cycle(user_preferences)

        # Display results
        print(
            f"🎯 SUCCESS! Processed {len(events)} events based on preferences")
        print("="*50)

        if not events:
            print("No events matched the specified user preferences in this cycle.")
        else:
            # Show first few events
            for i, event in enumerate(events[:3]):
                print(f"Event {i+1}:")
                print(f"📍 {event['summary']}")
                print(
                    f"📊 Category: {event['category']} | Severity: {event['severity']}")
                print(f"🎯 Location: {event['location']}")
                if event.get('actionable_advice'):
                    print(f"💡 Advice: {event['actionable_advice']}")

            print(f"✅ All {len(events)} relevant events stored in Firebase!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_single_cycle()
