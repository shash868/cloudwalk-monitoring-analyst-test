"""
Real-Time Transaction Monitoring Dashboard
Interactive visualization with live updates
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
import seaborn as sns
import sqlite3

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.facecolor'] = '#1a1a1a'
plt.rcParams['axes.facecolor'] = '#2d2d2d'
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
plt.rcParams['grid.color'] = '#3d3d3d'

class TransactionMonitorDashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self, db_path='transactions_monitor.db'):
        self.db_path = db_path
        self.fig = None
        self.axes = None
        
    def create_static_dashboard(self, output_path='dashboard.png'):
        """Create static dashboard snapshot"""
        # Create figure with subplots
        self.fig = plt.figure(figsize=(20, 12))
        gs = self.fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
        
        # Define subplots
        ax1 = self.fig.add_subplot(gs[0, :])    # Transaction volume timeline
        ax2 = self.fig.add_subplot(gs[1, 0])    # Status distribution pie
        ax3 = self.fig.add_subplot(gs[1, 1])    # Failure rate timeline
        ax4 = self.fig.add_subplot(gs[1, 2])    # Alert severity distribution
        ax5 = self.fig.add_subplot(gs[2, :2])   # Status comparison heatmap
        ax6 = self.fig.add_subplot(gs[2, 2])    # Current metrics gauge
        ax7 = self.fig.add_subplot(gs[3, :])    # Anomaly score timeline
        
        self.axes = {
            'volume': ax1,
            'distribution': ax2,
            'failure_rate': ax3,
            'alerts': ax4,
            'heatmap': ax5,
            'gauge': ax6,
            'anomaly': ax7
        }
        
        # Load data and create visualizations
        self._plot_transaction_volume()
        self._plot_status_distribution()
        self._plot_failure_rates()
        self._plot_alert_distribution()
        self._plot_status_heatmap()
        self._plot_current_metrics()
        self._plot_anomaly_scores()
        
        # Add title
        self.fig.suptitle(
            'CloudWalk Transaction Monitoring Dashboard - Real-Time View',
            fontsize=20,
            fontweight='bold',
            color='white',
            y=0.98
        )
        
        # Add timestamp
        timestamp_text = f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.fig.text(0.99, 0.01, timestamp_text, ha='right', va='bottom', 
                     fontsize=10, color='gray')
        
        # Save
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
        print(f"✓ Dashboard saved to {output_path}")
        
        return output_path
    
    def _get_transaction_data(self, hours=2):
        """Load transaction data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT timestamp, status, count
                FROM transactions
                WHERE timestamp >= datetime('now', '-{hours} hours')
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            conn.close()
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            # Load from CSV for demo
            return self._load_from_csv()
    
    def _load_from_csv(self):
        """Load from CSV files for demo"""
        df = pd.read_csv('/mnt/user-data/uploads/transactions.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def _get_alert_data(self):
        """Load alert data"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT timestamp, severity, status, anomaly_score
                FROM alerts
                WHERE timestamp >= datetime('now', '-2 hours')
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except:
            return pd.DataFrame()
    
    def _plot_transaction_volume(self):
        """Plot transaction volume over time"""
        ax = self.axes['volume']
        df = self._get_transaction_data()
        
        if df.empty:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   fontsize=14, color='gray')
            return
        
        # Aggregate by minute
        df_pivot = df.pivot_table(
            index='timestamp',
            columns='status',
            values='count',
            aggfunc='sum',
            fill_value=0
        )
        
        # Plot stacked area chart
        colors = {
            'approved': '#2ecc71',
            'denied': '#e74c3c',
            'failed': '#e67e22',
            'reversed': '#f39c12',
            'backend_reversed': '#c0392b',
            'refunded': '#9b59b6'
        }
        
        for status in df_pivot.columns:
            color = colors.get(status, '#95a5a6')
            ax.plot(df_pivot.index, df_pivot[status], label=status, 
                   color=color, linewidth=2, alpha=0.8)
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Transaction Count', fontsize=12, fontweight='bold')
        ax.set_title('Transaction Volume by Status (Real-Time)', 
                    fontsize=14, fontweight='bold', pad=10)
        ax.legend(loc='upper left', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def _plot_status_distribution(self):
        """Plot status distribution pie chart"""
        ax = self.axes['distribution']
        df = self._get_transaction_data()
        
        if df.empty:
            return
        
        # Calculate totals
        status_totals = df.groupby('status')['count'].sum()
        
        colors = ['#2ecc71', '#e74c3c', '#e67e22', '#f39c12', '#c0392b', '#9b59b6']
        
        wedges, texts, autotexts = ax.pie(
            status_totals.values,
            labels=status_totals.index,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            textprops={'color': 'white', 'fontweight': 'bold'}
        )
        
        ax.set_title('Transaction Status Distribution', 
                    fontsize=14, fontweight='bold', pad=10)
    
    def _plot_failure_rates(self):
        """Plot failure rates over time"""
        ax = self.axes['failure_rate']
        df = self._get_transaction_data()
        
        if df.empty:
            return
        
        # Calculate rates per minute
        minute_groups = df.groupby([pd.Grouper(key='timestamp', freq='5min'), 'status'])['count'].sum().unstack(fill_value=0)
        
        if 'failed' in minute_groups.columns:
            total = minute_groups.sum(axis=1)
            failed_rate = (minute_groups['failed'] / total * 100)
            
            ax.plot(failed_rate.index, failed_rate.values, 
                   color='#e67e22', linewidth=2.5, marker='o', markersize=4)
            
            # Add threshold lines
            ax.axhline(y=1.0, color='yellow', linestyle='--', linewidth=1.5, 
                      label='Warning (1%)', alpha=0.7)
            ax.axhline(y=2.0, color='red', linestyle='--', linewidth=1.5, 
                      label='Critical (2%)', alpha=0.7)
            
            ax.fill_between(failed_rate.index, 0, failed_rate.values, 
                          alpha=0.3, color='#e67e22')
        
        ax.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax.set_ylabel('Failed Rate (%)', fontsize=11, fontweight='bold')
        ax.set_title('Failed Transaction Rate', fontsize=13, fontweight='bold', pad=10)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def _plot_alert_distribution(self):
        """Plot alert severity distribution"""
        ax = self.axes['alerts']
        alert_df = self._get_alert_data()
        
        if alert_df.empty:
            ax.text(0.5, 0.5, 'No Alerts', ha='center', va='center',
                   fontsize=16, color='#2ecc71', fontweight='bold')
            ax.set_title('Alert Status', fontsize=13, fontweight='bold', pad=10)
            ax.axis('off')
            return
        
        severity_counts = alert_df['severity'].value_counts()
        
        colors = {
            'CRITICAL': '#e74c3c',
            'WARNING': '#f39c12',
            'INFO': '#3498db'
        }
        
        bars = ax.bar(
            range(len(severity_counts)),
            severity_counts.values,
            color=[colors.get(s, '#95a5a6') for s in severity_counts.index]
        )
        
        ax.set_xticks(range(len(severity_counts)))
        ax.set_xticklabels(severity_counts.index, fontweight='bold')
        ax.set_ylabel('Count', fontsize=11, fontweight='bold')
        ax.set_title('Alerts by Severity (Last 2 Hours)', 
                    fontsize=13, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    def _plot_status_heatmap(self):
        """Plot status comparison heatmap"""
        ax = self.axes['heatmap']
        df = self._get_transaction_data()
        
        if df.empty:
            return
        
        # Create pivot table with 10-minute buckets
        df['time_bucket'] = df['timestamp'].dt.floor('10min')
        pivot = df.pivot_table(
            index='time_bucket',
            columns='status',
            values='count',
            aggfunc='sum',
            fill_value=0
        )
        
        # Select last 12 time buckets (2 hours)
        pivot = pivot.tail(12)
        
        # Create heatmap
        sns.heatmap(
            pivot.T,
            cmap='YlOrRd',
            annot=True,
            fmt='.0f',
            cbar_kws={'label': 'Transaction Count'},
            ax=ax,
            linewidths=0.5,
            linecolor='gray'
        )
        
        ax.set_xlabel('Time (10-min buckets)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Status', fontsize=11, fontweight='bold')
        ax.set_title('Transaction Status Heatmap', fontsize=13, fontweight='bold', pad=10)
        
        # Format x-axis labels
        labels = [t.strftime('%H:%M') for t in pivot.index]
        ax.set_xticklabels(labels, rotation=45, ha='right')
    
    def _plot_current_metrics(self):
        """Plot current metrics as gauge/cards"""
        ax = self.axes['gauge']
        ax.axis('off')
        
        df = self._get_transaction_data(hours=1)
        
        if df.empty:
            return
        
        # Calculate current metrics
        total = df['count'].sum()
        approved = df[df['status'] == 'approved']['count'].sum()
        failed = df[df['status'] == 'failed']['count'].sum()
        denied = df[df['status'] == 'denied']['count'].sum()
        
        approval_rate = (approved / total * 100) if total > 0 else 0
        failure_rate = (failed / total * 100) if total > 0 else 0
        denial_rate = (denied / total * 100) if total > 0 else 0
        
        # Create metric cards
        metrics = [
            ('Total Trans.', f'{total:,.0f}', '#3498db'),
            ('Approval Rate', f'{approval_rate:.1f}%', '#2ecc71'),
            ('Failure Rate', f'{failure_rate:.2f}%', '#e67e22'),
            ('Denial Rate', f'{denial_rate:.1f}%', '#e74c3c')
        ]
        
        y_pos = 0.85
        for label, value, color in metrics:
            ax.text(0.5, y_pos, label, ha='center', va='top', 
                   fontsize=11, fontweight='bold', color='white')
            ax.text(0.5, y_pos - 0.12, value, ha='center', va='top',
                   fontsize=18, fontweight='bold', color=color)
            y_pos -= 0.25
        
        ax.set_title('Current Metrics (1 Hour)', fontsize=13, fontweight='bold', pad=10)
    
    def _plot_anomaly_scores(self):
        """Plot anomaly scores timeline"""
        ax = self.axes['anomaly']
        alert_df = self._get_alert_data()
        
        if alert_df.empty:
            ax.text(0.5, 0.5, 'No anomalies detected ✓', ha='center', va='center',
                   fontsize=16, color='#2ecc71', fontweight='bold')
            ax.set_title('Anomaly Detection Timeline', fontsize=14, fontweight='bold', pad=10)
            ax.axis('off')
            return
        
        alert_df['timestamp'] = pd.to_datetime(alert_df['timestamp'])
        
        # Plot anomaly scores
        severity_colors = {
            'CRITICAL': '#e74c3c',
            'WARNING': '#f39c12',
            'INFO': '#3498db'
        }
        
        for severity in alert_df['severity'].unique():
            data = alert_df[alert_df['severity'] == severity]
            ax.scatter(
                data['timestamp'],
                data['anomaly_score'],
                label=severity,
                color=severity_colors.get(severity, '#95a5a6'),
                s=100,
                alpha=0.7,
                edgecolors='white',
                linewidth=1.5
            )
        
        # Add threshold lines
        ax.axhline(y=50, color='yellow', linestyle='--', linewidth=1, 
                  label='Warning Threshold', alpha=0.5)
        ax.axhline(y=75, color='red', linestyle='--', linewidth=1, 
                  label='Critical Threshold', alpha=0.5)
        
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Anomaly Score', fontsize=12, fontweight='bold')
        ax.set_title('Anomaly Score Timeline', fontsize=14, fontweight='bold', pad=10)
        ax.legend(loc='upper left', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

def create_dashboard_from_csv():
    """Create dashboard directly from CSV files"""
    dashboard = TransactionMonitorDashboard()
    output_path = '/home/claude/transaction_monitoring_dashboard.png'
    dashboard.create_static_dashboard(output_path)
    return output_path

if __name__ == '__main__':
    create_dashboard_from_csv()
