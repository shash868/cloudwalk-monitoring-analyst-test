"""
CloudWalk Transaction Monitoring & Alert System
Real-time anomaly detection for transaction failures, denials, and reversals
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import sqlite3
import json
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ============================================================================
# CONFIGURATION
# ============================================================================

class MonitoringConfig:
    """Configuration for monitoring thresholds and parameters"""
    
    # Time windows for analysis (minutes)
    WINDOW_SHORT = 5    # 5-minute window for immediate alerts
    WINDOW_MEDIUM = 15  # 15-minute window for trend detection
    WINDOW_LONG = 60    # 1-hour window for baseline calculation
    
    # Statistical thresholds (standard deviations from mean)
    SIGMA_WARNING = 2.0   # Warning threshold
    SIGMA_CRITICAL = 3.0  # Critical threshold
    
    # Rule-based thresholds (absolute percentages)
    FAILED_RATE_WARNING = 1.0      # 1% failed transactions
    FAILED_RATE_CRITICAL = 2.0     # 2% failed transactions
    
    DENIED_RATE_WARNING = 10.0     # 10% denied transactions
    DENIED_RATE_CRITICAL = 15.0    # 15% denied transactions
    
    REVERSED_RATE_WARNING = 2.0    # 2% reversed transactions
    REVERSED_RATE_CRITICAL = 4.0   # 4% reversed transactions
    
    BACKEND_REVERSED_RATE_WARNING = 0.5   # 0.5% backend reversed
    BACKEND_REVERSED_RATE_CRITICAL = 1.0  # 1% backend reversed
    
    # Anomaly score thresholds
    ANOMALY_SCORE_WARNING = 50
    ANOMALY_SCORE_CRITICAL = 75

# ============================================================================
# DATA STORAGE & MANAGEMENT
# ============================================================================

class TransactionDataStore:
    """In-memory storage with SQLite persistence"""
    
    def __init__(self, db_path='transactions_monitor.db'):
        self.db_path = db_path
        self.recent_data = deque(maxlen=10000)  # Keep last 10k records in memory
        self._init_database()
        self._load_historical_baseline()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                metric_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                anomaly_score REAL NOT NULL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create baseline statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline_stats (
                status TEXT PRIMARY KEY,
                mean_count REAL,
                std_count REAL,
                mean_rate REAL,
                std_rate REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _load_historical_baseline(self):
        """Load baseline statistics from historical data"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM baseline_stats",
            conn
        )
        conn.close()
        
        if df.empty:
            # Load from CSV files to establish baseline
            self._calculate_baseline_from_files()
        
        self.baseline = df.set_index('status').to_dict('index')
        logger.info(f"Loaded baseline statistics for {len(self.baseline)} status types")
    
    def _calculate_baseline_from_files(self):
        """Calculate baseline from historical CSV data"""
        try:
            df = pd.read_csv('/mnt/user-data/uploads/transactions.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate statistics per status
            baseline_stats = []
            for status in df['status'].unique():
                status_data = df[df['status'] == status]
                
                # Group by minute to get rates
                minute_groups = df.groupby(pd.Grouper(key='timestamp', freq='1min'))
                total_per_minute = minute_groups['count'].sum()
                status_per_minute = status_data.set_index('timestamp').resample('1min')['count'].sum()
                
                rate_per_minute = (status_per_minute / total_per_minute * 100).dropna()
                
                baseline_stats.append({
                    'status': status,
                    'mean_count': status_data['count'].mean(),
                    'std_count': status_data['count'].std(),
                    'mean_rate': rate_per_minute.mean(),
                    'std_rate': rate_per_minute.std()
                })
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            pd.DataFrame(baseline_stats).to_sql(
                'baseline_stats',
                conn,
                if_exists='replace',
                index=False
            )
            conn.commit()
            conn.close()
            
            logger.info("Baseline statistics calculated from historical data")
            
        except Exception as e:
            logger.warning(f"Could not load baseline from files: {e}")
    
    def add_transaction(self, timestamp: str, status: str, count: int):
        """Add transaction data"""
        # Add to in-memory storage
        self.recent_data.append({
            'timestamp': pd.to_datetime(timestamp),
            'status': status,
            'count': count
        })
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (timestamp, status, count) VALUES (?, ?, ?)",
            (timestamp, status, count)
        )
        conn.commit()
        conn.close()
    
    def get_recent_data(self, minutes: int) -> pd.DataFrame:
        """Get recent transaction data"""
        if not self.recent_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(self.recent_data))
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return df[df['timestamp'] >= cutoff_time]
    
    def save_alert(self, alert_data: dict):
        """Save alert to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts 
            (timestamp, alert_type, severity, status, metric_value, threshold_value, anomaly_score, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data['timestamp'],
            alert_data['alert_type'],
            alert_data['severity'],
            alert_data['status'],
            alert_data['metric_value'],
            alert_data['threshold_value'],
            alert_data['anomaly_score'],
            alert_data['message']
        ))
        conn.commit()
        conn.close()

# ============================================================================
# ANOMALY DETECTION ENGINE
# ============================================================================

class AnomalyDetector:
    """Hybrid anomaly detection using rule-based and statistical methods"""
    
    def __init__(self, data_store: TransactionDataStore, config: MonitoringConfig):
        self.data_store = data_store
        self.config = config
    
    def analyze_transaction(self, timestamp: str, status: str, count: int) -> Dict:
        """
        Analyze a single transaction data point
        Returns alert recommendation with anomaly score
        """
        # Add to data store
        self.data_store.add_transaction(timestamp, status, count)
        
        # Get recent data for analysis
        recent_data = self.data_store.get_recent_data(self.config.WINDOW_MEDIUM)
        
        if recent_data.empty or len(recent_data) < 5:
            return {
                'should_alert': False,
                'alerts': [],
                'anomaly_score': 0,
                'message': 'Insufficient data for analysis'
            }
        
        # Calculate current metrics
        current_metrics = self._calculate_metrics(recent_data)
        
        # Detect anomalies
        alerts = []
        max_anomaly_score = 0
        
        # Check each problem status type
        for problem_status in ['failed', 'denied', 'reversed', 'backend_reversed']:
            if problem_status in current_metrics:
                alert = self._check_status_anomaly(
                    problem_status,
                    current_metrics[problem_status]
                )
                if alert:
                    alerts.append(alert)
                    max_anomaly_score = max(max_anomaly_score, alert['anomaly_score'])
        
        return {
            'should_alert': len(alerts) > 0,
            'alerts': alerts,
            'anomaly_score': max_anomaly_score,
            'current_metrics': current_metrics,
            'timestamp': timestamp
        }
    
    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate current metrics from recent data"""
        metrics = {}
        
        # Get total transactions
        total = df['count'].sum()
        
        # Calculate metrics for each status
        for status in df['status'].unique():
            status_data = df[df['status'] == status]
            count = status_data['count'].sum()
            rate = (count / total * 100) if total > 0 else 0
            
            metrics[status] = {
                'count': count,
                'rate': rate,
                'avg_per_minute': status_data['count'].mean(),
                'std_per_minute': status_data['count'].std()
            }
        
        metrics['total'] = total
        return metrics
    
    def _check_status_anomaly(self, status: str, metrics: Dict) -> Dict:
        """Check if a status shows anomalous behavior"""
        rate = metrics['rate']
        count = metrics['count']
        
        # Get baseline if available
        baseline = self.data_store.baseline.get(status, {})
        
        # Rule-based detection
        rule_alert = self._rule_based_check(status, rate)
        
        # Statistical detection
        stat_alert = self._statistical_check(status, rate, baseline)
        
        # Combine scores
        if rule_alert or stat_alert:
            # Calculate combined anomaly score (0-100)
            anomaly_score = 0
            severity = 'INFO'
            
            if rule_alert:
                anomaly_score += rule_alert['score']
                severity = rule_alert['severity']
            
            if stat_alert:
                anomaly_score += stat_alert['score']
                if stat_alert['severity'] == 'CRITICAL':
                    severity = 'CRITICAL'
                elif stat_alert['severity'] == 'WARNING' and severity != 'CRITICAL':
                    severity = 'WARNING'
            
            anomaly_score = min(100, anomaly_score)
            
            return {
                'status': status,
                'alert_type': f'{status}_anomaly',
                'severity': severity,
                'metric_value': rate,
                'threshold_value': self._get_threshold(status, severity),
                'anomaly_score': anomaly_score,
                'message': f'{status.upper()} transactions at {rate:.2f}% (count: {count})',
                'timestamp': datetime.now().isoformat()
            }
        
        return None
    
    def _rule_based_check(self, status: str, rate: float) -> Dict:
        """Rule-based threshold checking"""
        thresholds = {
            'failed': (self.config.FAILED_RATE_WARNING, self.config.FAILED_RATE_CRITICAL),
            'denied': (self.config.DENIED_RATE_WARNING, self.config.DENIED_RATE_CRITICAL),
            'reversed': (self.config.REVERSED_RATE_WARNING, self.config.REVERSED_RATE_CRITICAL),
            'backend_reversed': (self.config.BACKEND_REVERSED_RATE_WARNING, 
                               self.config.BACKEND_REVERSED_RATE_CRITICAL)
        }
        
        if status not in thresholds:
            return None
        
        warning_threshold, critical_threshold = thresholds[status]
        
        if rate >= critical_threshold:
            return {
                'severity': 'CRITICAL',
                'score': 50,
                'threshold': critical_threshold
            }
        elif rate >= warning_threshold:
            return {
                'severity': 'WARNING',
                'score': 30,
                'threshold': warning_threshold
            }
        
        return None
    
    def _statistical_check(self, status: str, rate: float, baseline: Dict) -> Dict:
        """Statistical anomaly detection using Z-score"""
        if not baseline or 'mean_rate' not in baseline:
            return None
        
        mean = baseline['mean_rate']
        std = baseline.get('std_rate', 1.0)
        
        if std == 0:
            std = 1.0  # Avoid division by zero
        
        # Calculate Z-score
        z_score = abs((rate - mean) / std)
        
        if z_score >= self.config.SIGMA_CRITICAL:
            return {
                'severity': 'CRITICAL',
                'score': 40,
                'z_score': z_score
            }
        elif z_score >= self.config.SIGMA_WARNING:
            return {
                'severity': 'WARNING',
                'score': 25,
                'z_score': z_score
            }
        
        return None
    
    def _get_threshold(self, status: str, severity: str) -> float:
        """Get the threshold value that was breached"""
        thresholds = {
            'failed': (self.config.FAILED_RATE_WARNING, self.config.FAILED_RATE_CRITICAL),
            'denied': (self.config.DENIED_RATE_WARNING, self.config.DENIED_RATE_CRITICAL),
            'reversed': (self.config.REVERSED_RATE_WARNING, self.config.REVERSED_RATE_CRITICAL),
            'backend_reversed': (self.config.BACKEND_REVERSED_RATE_WARNING, 
                               self.config.BACKEND_REVERSED_RATE_CRITICAL)
        }
        
        if status in thresholds:
            warning, critical = thresholds[status]
            return critical if severity == 'CRITICAL' else warning
        
        return 0.0

# ============================================================================
# ALERT NOTIFICATION SYSTEM
# ============================================================================

class AlertNotificationSystem:
    """System to send alerts to monitoring teams"""
    
    def __init__(self, data_store: TransactionDataStore):
        self.data_store = data_store
        self.alert_history = deque(maxlen=100)
    
    def send_alert(self, alert: Dict):
        """Send alert notification"""
        # Save to database
        self.data_store.save_alert(alert)
        
        # Add to history
        self.alert_history.append(alert)
        
        # Log alert
        severity_emoji = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'CRITICAL': '🔴'
        }
        
        emoji = severity_emoji.get(alert['severity'], '📊')
        logger.warning(
            f"{emoji} {alert['severity']} ALERT: {alert['message']} "
            f"(Anomaly Score: {alert['anomaly_score']:.1f})"
        )
        
        # In production, send to:
        # - Slack/Teams webhook
        # - PagerDuty
        # - Email
        # - SMS for critical alerts
        
        return True
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        return list(self.alert_history)[-limit:]

# ============================================================================
# INITIALIZE GLOBAL INSTANCES
# ============================================================================

data_store = TransactionDataStore()
config = MonitoringConfig()
detector = AnomalyDetector(data_store, config)
alert_system = AlertNotificationSystem(data_store)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/transaction', methods=['POST'])
def receive_transaction():
    """
    Main endpoint to receive transaction data and return alert recommendation
    
    Expected payload:
    {
        "timestamp": "2025-07-12 13:45:00",
        "status": "failed",
        "count": 5
    }
    """
    try:
        data = request.json
        
        # Validate input
        required_fields = ['timestamp', 'status', 'count']
        if not all(field in data for field in required_fields):
            return jsonify({
                'error': 'Missing required fields',
                'required': required_fields
            }), 400
        
        # Analyze transaction
        result = detector.analyze_transaction(
            data['timestamp'],
            data['status'],
            data['count']
        )
        
        # Send alerts if needed
        if result['should_alert']:
            for alert in result['alerts']:
                alert_system.send_alert(alert)
        
        # Return recommendation
        response = {
            'should_alert': result['should_alert'],
            'anomaly_score': result['anomaly_score'],
            'alerts': result['alerts'],
            'timestamp': result['timestamp'],
            'recommendation': 'ALERT' if result['should_alert'] else 'OK'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing transaction: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/metrics', methods=['GET'])
def get_current_metrics():
    """Get current transaction metrics"""
    try:
        window = int(request.args.get('window', 15))  # minutes
        recent_data = data_store.get_recent_data(window)
        
        if recent_data.empty:
            return jsonify({
                'metrics': {},
                'message': 'No recent data available'
            })
        
        metrics = detector._calculate_metrics(recent_data)
        
        return jsonify({
            'window_minutes': window,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    try:
        limit = int(request.args.get('limit', 10))
        alerts = alert_system.get_recent_alerts(limit)
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/baseline', methods=['GET'])
def get_baseline():
    """Get baseline statistics"""
    return jsonify({
        'baseline': data_store.baseline,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("Starting Transaction Monitoring API...")
    logger.info(f"Configuration: {config.__dict__}")
    app.run(host='0.0.0.0', port=5000, debug=True)
