# src/continuous_intelligence.py
import time
import schedule
from data_fusion_agent import SuperEfficientDataFusionAgent

class ContinuousIntelligence:
    def __init__(self):
        self.agent = SuperEfficientDataFusionAgent()
        self.running = False
    
    def start_intelligent_monitoring(self):
        """Start continuous city intelligence monitoring"""
        print("🌟 Starting Bengaluru Live Intelligence System...")
        
        # Schedule intelligent runs
        schedule.every(5).minutes.do(self._quick_pulse_check)
        schedule.every(15).minutes.do(self._full_intelligence_cycle)
        schedule.every(1).hours.do(self._cleanup_old_events)
        
        self.running = True
        
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def _quick_pulse_check(self):
        """Quick 5-minute pulse check"""
        print("⚡ Quick pulse check...")
        # Run with limited posts for speed
        events = self.agent.run_super_efficient_cycle()
        return len(events)
    
    def _full_intelligence_cycle(self):
        """Full 15-minute intelligence cycle"""
        print("🧠 Full intelligence cycle...")
        events = self.agent.run_super_efficient_cycle()
        
        # Generate predictive insights
        self._generate_predictions(events)
        
        return events
    
    def _cleanup_old_events(self):
        """Clean up expired events"""
        print("🧹 Cleaning up old events...")
        # Query expired events and delete
        expired_query = self.agent.db.collection('live_events').where(
            'expires_at', '<', datetime.now()
        )
        
        batch = self.agent.db.batch()
        for doc in expired_query.stream():
            batch.delete(doc.reference)
        batch.commit()
    
    def _generate_predictions(self, events: List[Dict]):
        """Generate predictive insights for proactive alerts"""
        # Pattern detection without API calls
        traffic_events = [e for e in events if e['category'] == 'traffic']
        infrastructure_events = [e for e in events if e['category'] == 'infrastructure']
        
        if len(traffic_events) >= 3:
            print("🚨 PREDICTION: High traffic congestion expected")
        
        if len(infrastructure_events) >= 2:
            print("🚨 PREDICTION: Infrastructure issues may cascade")

if __name__ == "__main__":
    intelligence = ContinuousIntelligence()
    intelligence.start_intelligent_monitoring()
