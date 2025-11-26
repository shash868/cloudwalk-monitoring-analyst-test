"""
Test Simulation for Transaction Monitoring System
Simulates real-time transaction data and demonstrates anomaly detection
"""

import requests
import pandas as pd
import time
import json
from datetime import datetime

class MonitoringSystemSimulator:
    """Simulate transaction data and test the monitoring system"""
    
    def __init__(self, api_url='http://localhost:5000'):
        self.api_url = api_url
        self.transaction_data = None
        self.load_historical_data()
    
    def load_historical_data(self):
        """Load historical transaction data"""
        self.transaction_data = pd.read_csv('/mnt/user-data/uploads/transactions.csv')
        self.transaction_data['timestamp'] = pd.to_datetime(self.transaction_data['timestamp'])
        print(f"✓ Loaded {len(self.transaction_data)} historical transaction records")
    
    def simulate_realtime_stream(self, num_records=100, delay=0.1):
        """Simulate real-time transaction stream"""
        print(f"\n{'='*80}")
        print("SIMULATING REAL-TIME TRANSACTION STREAM")
        print(f"{'='*80}\n")
        
        # Take a sample of records
        sample_data = self.transaction_data.sample(n=min(num_records, len(self.transaction_data)))
        
        alerts_triggered = 0
        
        for idx, row in sample_data.iterrows():
            # Prepare transaction data
            transaction = {
                'timestamp': row['timestamp'].isoformat(),
                'status': row['status'],
                'count': int(row['count'])
            }
            
            # Send to API
            try:
                response = requests.post(
                    f'{self.api_url}/api/transaction',
                    json=transaction,
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Print status
                    status_emoji = {
                        'approved': '✓',
                        'failed': '✗',
                        'denied': '⊘',
                        'reversed': '↶',
                        'backend_reversed': '⇄',
                        'refunded': '↩'
                    }
                    
                    emoji = status_emoji.get(row['status'], '•')
                    print(f"{emoji} [{row['timestamp']}] {row['status']:20} Count: {row['count']:3} ", end='')
                    
                    if result['should_alert']:
                        alerts_triggered += 1
                        print(f"🚨 ALERT! Score: {result['anomaly_score']:.1f}")
                        for alert in result['alerts']:
                            print(f"   → {alert['severity']}: {alert['message']}")
                    else:
                        print("OK")
                
                else:
                    print(f"✗ API Error: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print("✗ API not running. Start with: python transaction_monitor.py")
                return
            except Exception as e:
                print(f"✗ Error: {e}")
            
            # Delay to simulate real-time
            time.sleep(delay)
        
        print(f"\n{'='*80}")
        print(f"SIMULATION COMPLETE")
        print(f"Total Records Sent: {num_records}")
        print(f"Alerts Triggered: {alerts_triggered}")
        print(f"Alert Rate: {alerts_triggered/num_records*100:.1f}%")
        print(f"{'='*80}\n")
    
    def test_api_endpoints(self):
        """Test all API endpoints"""
        print(f"\n{'='*80}")
        print("TESTING API ENDPOINTS")
        print(f"{'='*80}\n")
        
        endpoints = [
            ('GET', '/health', None),
            ('GET', '/api/metrics?window=15', None),
            ('GET', '/api/alerts?limit=5', None),
            ('GET', '/api/baseline', None)
        ]
        
        for method, endpoint, data in endpoints:
            print(f"\nTesting {method} {endpoint}")
            print("-" * 60)
            
            try:
                if method == 'GET':
                    response = requests.get(f'{self.api_url}{endpoint}', timeout=5)
                else:
                    response = requests.post(
                        f'{self.api_url}{endpoint}',
                        json=data,
                        timeout=5
                    )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")
                    print("✓ SUCCESS")
                else:
                    print(f"✗ FAILED: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                print("✗ API not running")
                return
            except Exception as e:
                print(f"✗ Error: {e}")
    
    def analyze_anomaly_patterns(self):
        """Analyze patterns in the data that would trigger alerts"""
        print(f"\n{'='*80}")
        print("ANALYZING ANOMALY PATTERNS IN HISTORICAL DATA")
        print(f"{'='*80}\n")
        
        # Calculate rates by minute
        df = self.transaction_data.copy()
        df['minute'] = df['timestamp'].dt.floor('min')
        
        # Aggregate by minute
        minute_totals = df.groupby('minute')['count'].sum()
        
        for status in ['failed', 'denied', 'reversed', 'backend_reversed']:
            status_data = df[df['status'] == status]
            status_by_minute = status_data.groupby('minute')['count'].sum()
            
            rates = (status_by_minute / minute_totals * 100).dropna()
            
            print(f"\n{status.upper()} Transactions:")
            print(f"  Mean Rate: {rates.mean():.2f}%")
            print(f"  Std Dev: {rates.std():.2f}%")
            print(f"  Max Rate: {rates.max():.2f}%")
            print(f"  Min Rate: {rates.min():.2f}%")
            
            # Identify anomaly minutes
            threshold_warning = 2.0 if status == 'failed' else (10.0 if status == 'denied' else 2.0)
            threshold_critical = 4.0 if status == 'failed' else (15.0 if status == 'denied' else 4.0)
            
            warning_minutes = rates[rates > threshold_warning]
            critical_minutes = rates[rates > threshold_critical]
            
            print(f"  Warning Minutes (>{threshold_warning}%): {len(warning_minutes)}")
            print(f"  Critical Minutes (>{threshold_critical}%): {len(critical_minutes)}")
            
            if len(critical_minutes) > 0:
                print(f"  Sample Critical Events:")
                for timestamp, rate in critical_minutes.head(3).items():
                    count = status_by_minute.get(timestamp, 0)
                    total = minute_totals.get(timestamp, 1)
                    print(f"    [{timestamp}] Rate: {rate:.2f}% ({count}/{total})")

def main():
    """Main test function"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            CloudWalk Transaction Monitoring System - Test Suite             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    simulator = MonitoringSystemSimulator()
    
    # Analyze patterns first
    simulator.analyze_anomaly_patterns()
    
    print("\n\nTo test the real-time API:")
    print("1. Start the API server: python transaction_monitor.py")
    print("2. In another terminal, run: python test_simulation.py --simulate")
    print("\nOr test individual endpoints with: python test_simulation.py --test-api")

if __name__ == '__main__':
    import sys
    
    if '--simulate' in sys.argv:
        simulator = MonitoringSystemSimulator()
        num_records = 50
        if '--num' in sys.argv:
            idx = sys.argv.index('--num')
            num_records = int(sys.argv[idx + 1])
        simulator.simulate_realtime_stream(num_records=num_records, delay=0.5)
    
    elif '--test-api' in sys.argv:
        simulator = MonitoringSystemSimulator()
        simulator.test_api_endpoints()
    
    else:
        main()
