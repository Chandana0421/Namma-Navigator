# tests/test_super_system.py
import time
from src.data_fusion_agent import SuperEfficientDataFusionAgent

def test_complete_system():
    """Test the complete super-efficient system"""
    print("🧪 TESTING SUPER-EFFICIENT NAMMA NAVIGATOR...")
    
    agent = SuperEfficientDataFusionAgent()
    
    # Test 1: Data ingestion efficiency
    print("\n📡 Testing intelligent data ingestion...")
    start = time.time()
    posts = agent.intelligent_data_ingestion()
    ingestion_time = time.time() - start
    print(f"✅ Ingested {len(posts)} posts in {ingestion_time:.2f}s")
    
    # Test 2: Synthesis efficiency
    print("\n🤖 Testing hyper-efficient synthesis...")
    start = time.time()
    events = agent.hyper_efficient_synthesis(posts[:10])  # Test with 10 posts
    synthesis_time = time.time() - start
    print(f"✅ Synthesized {len(events)} events in {synthesis_time:.2f}s")
    
    # Test 3: Storage efficiency
    print("\n💾 Testing real-time storage...")
    start = time.time()
    agent.real_time_storage(events)
    storage_time = time.time() - start
    print(f"✅ Stored {len(events)} events in {storage_time:.2f}s")
    
    # Test 4: Full cycle performance
    print("\n⚡ Testing complete cycle performance...")
    start = time.time()
    cycle_events = agent.run_super_efficient_cycle()
    cycle_time = time.time() - start
    
    print(f"\n🏆 SYSTEM PERFORMANCE SUMMARY:")
    print(f"📊 Total events processed: {len(cycle_events)}")
    print(f"⚡ Complete cycle time: {cycle_time:.2f}s")
    print(f"🚀 Processing rate: {len(cycle_events)/cycle_time:.1f} events/second")
    
    # Display sample results
    print(f"\n📋 SAMPLE PROCESSED EVENTS:")
    for i, event in enumerate(cycle_events[:3]):
        print(f"{i+1}. {event['summary']}")
        print(f"   Category: {event['category']} | Severity: {event['severity']}")
        print(f"   Location: {event['location']} | Urgency: {event['urgency_score']}/10")

if __name__ == "__main__":
    test_complete_system()
