import sys
import os

# Add src to path so we can import our modules
sys.path.append('src')

from data_fusion_agent import SuperEfficientDataFusionAgent

def run_single_cycle():
    """Run one complete data fusion cycle"""
    print("🚀 Starting Namma Navigator Test Run...")
    
    try:
        # Initialize the agent
        agent = SuperEfficientDataFusionAgent()
        
        # Run one complete cycle
        events = agent.run_super_efficient_cycle()
        
        # Display results
        print(f"\n🎯 SUCCESS! Processed {len(events)} events")
        print("="*50)
        
        # Show first few events
        for i, event in enumerate(events[:3]):
            print(f"\nEvent {i+1}:")
            print(f"📍 {event['summary']}")
            print(f"📊 Category: {event['category']} | Severity: {event['severity']}")
            print(f"🎯 Location: {event['location']}")
            if event.get('actionable_advice'):
                print(f"💡 Advice: {event['actionable_advice']}")
        
        print(f"\n✅ All {len(events)} events stored in Firebase!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_single_cycle()
