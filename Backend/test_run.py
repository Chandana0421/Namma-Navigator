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
        # Updated to use the new interface
        inputs = {'preferences': user_preferences}
        result = agent.run(inputs)

        # Handle different result formats
        if isinstance(result, dict):
            if 'events_created' in result:
                # New format - summary result
                print(f"🎯 SUCCESS! Processing Summary:")
                print(f"📊 Posts fetched: {result.get('posts_fetched', 0)}")
                print(f"🔍 Posts filtered: {result.get('posts_filtered', 0)}")
                print(f"🎯 Events created: {result.get('events_created', 0)}")
                print(
                    f"💾 Storage status: {result.get('storage_status', 'unknown')}")

                if result.get('events_created', 0) == 0:
                    print(
                        "No events were created that matched the specified preferences.")
                else:
                    print(
                        f"✅ {result.get('events_created', 0)} relevant events stored in Firebase!")

            elif 'result' in result:
                # Error result format
                print(f"⚠️ Processing result: {result['result']}")
                if result['result'] == 'no posts found':
                    print("No Reddit posts were found matching the criteria.")
                elif result['result'] == 'no posts matched preferences':
                    print("Posts were found but none matched your preferences.")
                elif result['result'] == 'no events synthesized':
                    print("Posts were filtered but no events could be synthesized.")
            else:
                print("🎯 Processing completed with unknown result format")
                print(result)
        elif isinstance(result, list):
            # Legacy format - list of events
            events = result
            print(
                f"🎯 SUCCESS! Processed {len(events)} events based on preferences")
            print("="*50)

            if not events:
                print("No events matched the specified user preferences in this cycle.")
            else:
                # Show first few events
                for i, event in enumerate(events[:3]):
                    print(f"Event {i+1}:")
                    print(f"📍 {event.get('summary', 'No summary')}")
                    print(
                        f"📊 Category: {event.get('category', 'unknown')} | Severity: {event.get('severity', 'unknown')}")
                    print(f"🎯 Location: {event.get('location', 'unknown')}")
                    if event.get('actionable_advice'):
                        print(f"💡 Advice: {event['actionable_advice']}")
                    print("-" * 30)

                print(f"✅ All {len(events)} relevant events processed!")
        else:
            print("🎯 Processing completed with unexpected result format")
            print(result)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def run_traffic_test():
    """Run a test focused on traffic information"""
    print("🚦 Starting Traffic-Focused Test Run...")

    try:
        traffic_preferences = {
            "categories": ["traffic", "infrastructure"],
            "keywords": ["jam", "accident", "blocked", "signal", "road"],
            "min_urgency": 3,
            "relevant_areas": ["koramangala", "indiranagar", "silk board", "marathahalli", "whitefield"]
        }

        print("📋 Using Traffic Preferences:")
        print(traffic_preferences)

        agent = SuperEfficientDataFusionAgent()
        inputs = {'preferences': traffic_preferences}
        result = agent.run(inputs)

        print("🚦 Traffic Test Results:")
        print(result)

    except Exception as e:
        print(f"❌ Traffic Test Error: {e}")
        import traceback
        traceback.print_exc()


def run_general_test():
    """Run a test with general Bengaluru preferences"""
    print("🏙️ Starting General Bengaluru Test Run...")

    try:
        general_preferences = {
            "categories": ["traffic", "infrastructure", "weather", "events", "civic"],
            "keywords": ["bengaluru", "bangalore", "metro", "rain", "power"],
            "min_urgency": 2,
            "relevant_areas": ["all"]
        }

        print("📋 Using General Preferences:")
        print(general_preferences)

        agent = SuperEfficientDataFusionAgent()
        inputs = {'preferences': general_preferences}
        result = agent.run(inputs)

        print("🏙️ General Test Results:")
        print(result)

    except Exception as e:
        print(f"❌ General Test Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # To avoid exceeding the API quota during development,
    # we will only run the primary test cycle.
    # The other tests can be un-commented for more comprehensive testing
    # when you have a higher API quota.
    run_single_cycle()

    print("Choose test to run:")
    print("1. Original economy test")
    print("2. Traffic-focused test")
    print("3. General Bengaluru test")
    print("4. All tests")

    choice = input("Enter choice (1-4) or press Enter for default: ").strip()

    if choice == "1" or choice == "":
        run_single_cycle()
    elif choice == "2":
        run_traffic_test()
    elif choice == "3":
        run_general_test()
    elif choice == "4":
        print("" + "="*60)
        run_single_cycle()
        print("" + "="*60)
        run_traffic_test()
        print("" + "="*60)
        run_general_test()
    else:
        print("Invalid choice, running default test...")
        run_single_cycle()
