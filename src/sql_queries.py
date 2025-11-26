"""
SQL Queries for Transaction Monitoring System
Queries to organize, analyze, and detect anomalies in transaction data
"""

# ============================================================================
# DATA ORGANIZATION QUERIES
# ============================================================================

# Query 1: Aggregate transactions by minute with all statuses
AGGREGATE_BY_MINUTE = """
SELECT 
    timestamp,
    SUM(CASE WHEN status = 'approved' THEN count ELSE 0 END) as approved,
    SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) as failed,
    SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) as denied,
    SUM(CASE WHEN status = 'reversed' THEN count ELSE 0 END) as reversed,
    SUM(CASE WHEN status = 'backend_reversed' THEN count ELSE 0 END) as backend_reversed,
    SUM(CASE WHEN status = 'refunded' THEN count ELSE 0 END) as refunded,
    SUM(count) as total_transactions
FROM transactions
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY timestamp
ORDER BY timestamp DESC;
"""

# Query 2: Calculate failure rates by time period
FAILURE_RATES = """
SELECT 
    strftime('%Y-%m-%d %H:%M', timestamp) as minute,
    SUM(count) as total,
    SUM(CASE WHEN status IN ('failed', 'denied', 'reversed', 'backend_reversed') THEN count ELSE 0 END) as failures,
    ROUND(
        100.0 * SUM(CASE WHEN status IN ('failed', 'denied', 'reversed', 'backend_reversed') THEN count ELSE 0 END) / 
        NULLIF(SUM(count), 0), 
        2
    ) as failure_rate,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) / 
        NULLIF(SUM(count), 0), 
        2
    ) as failed_rate,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) / 
        NULLIF(SUM(count), 0), 
        2
    ) as denied_rate,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'reversed' THEN count ELSE 0 END) / 
        NULLIF(SUM(count), 0), 
        2
    ) as reversed_rate
FROM transactions
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY minute
ORDER BY minute DESC;
"""

# ============================================================================
# ANOMALY DETECTION QUERIES
# ============================================================================

# Query 3: Detect spikes in failed transactions
FAILED_TRANSACTION_SPIKES = """
WITH minute_stats AS (
    SELECT 
        strftime('%Y-%m-%d %H:%M', timestamp) as minute,
        SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) as failed_count,
        SUM(count) as total_count,
        ROUND(
            100.0 * SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) / 
            NULLIF(SUM(count), 0), 
            2
        ) as failed_rate
    FROM transactions
    WHERE timestamp >= datetime('now', '-2 hours')
    GROUP BY minute
),
baseline AS (
    SELECT 
        AVG(failed_rate) as avg_failed_rate,
        AVG(failed_rate) + 2 * STDEV(failed_rate) as upper_threshold
    FROM minute_stats
    WHERE minute < strftime('%Y-%m-%d %H:%M', datetime('now', '-15 minutes'))
)
SELECT 
    m.minute,
    m.failed_count,
    m.total_count,
    m.failed_rate,
    b.avg_failed_rate as baseline_rate,
    b.upper_threshold,
    CASE 
        WHEN m.failed_rate > b.upper_threshold THEN 'ANOMALY'
        ELSE 'NORMAL'
    END as status
FROM minute_stats m
CROSS JOIN baseline b
WHERE m.minute >= strftime('%Y-%m-%d %H:%M', datetime('now', '-15 minutes'))
ORDER BY m.minute DESC;
"""

# Query 4: Detect denied transaction anomalies
DENIED_TRANSACTION_ANOMALIES = """
WITH recent_data AS (
    SELECT 
        strftime('%Y-%m-%d %H:%M', timestamp) as minute,
        SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) as denied_count,
        SUM(count) as total_count,
        ROUND(
            100.0 * SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) / 
            NULLIF(SUM(count), 0), 
            2
        ) as denied_rate
    FROM transactions
    WHERE timestamp >= datetime('now', '-1 hour')
    GROUP BY minute
),
thresholds AS (
    SELECT 
        AVG(denied_rate) as mean_rate,
        STDEV(denied_rate) as std_rate,
        AVG(denied_rate) + 2 * STDEV(denied_rate) as warning_threshold,
        AVG(denied_rate) + 3 * STDEV(denied_rate) as critical_threshold
    FROM recent_data
)
SELECT 
    r.minute,
    r.denied_count,
    r.total_count,
    r.denied_rate,
    t.mean_rate,
    t.warning_threshold,
    t.critical_threshold,
    CASE 
        WHEN r.denied_rate > t.critical_threshold THEN 'CRITICAL'
        WHEN r.denied_rate > t.warning_threshold THEN 'WARNING'
        ELSE 'NORMAL'
    END as alert_level,
    ROUND((r.denied_rate - t.mean_rate) / NULLIF(t.std_rate, 0), 2) as z_score
FROM recent_data r
CROSS JOIN thresholds t
WHERE r.denied_rate > t.mean_rate
ORDER BY r.denied_rate DESC
LIMIT 10;
"""

# Query 5: Compare current vs historical baseline
CURRENT_VS_BASELINE = """
WITH current_stats AS (
    SELECT 
        status,
        AVG(count) as current_avg,
        SUM(count) as current_total,
        COUNT(*) as current_samples
    FROM transactions
    WHERE timestamp >= datetime('now', '-15 minutes')
    GROUP BY status
),
historical_baseline AS (
    SELECT 
        status,
        mean_count as baseline_avg,
        std_count as baseline_std,
        mean_rate as baseline_rate
    FROM baseline_stats
)
SELECT 
    c.status,
    c.current_avg,
    h.baseline_avg,
    c.current_total,
    c.current_samples,
    ROUND(
        100.0 * (c.current_avg - h.baseline_avg) / NULLIF(h.baseline_avg, 0), 
        2
    ) as percent_change,
    ROUND(
        (c.current_avg - h.baseline_avg) / NULLIF(h.baseline_std, 1), 
        2
    ) as z_score,
    CASE 
        WHEN ABS((c.current_avg - h.baseline_avg) / NULLIF(h.baseline_std, 1)) > 3 THEN 'CRITICAL'
        WHEN ABS((c.current_avg - h.baseline_avg) / NULLIF(h.baseline_std, 1)) > 2 THEN 'WARNING'
        ELSE 'NORMAL'
    END as status_flag
FROM current_stats c
LEFT JOIN historical_baseline h ON c.status = h.status
WHERE c.status IN ('failed', 'denied', 'reversed', 'backend_reversed')
ORDER BY ABS(z_score) DESC;
"""

# ============================================================================
# REPORTING QUERIES
# ============================================================================

# Query 6: Alert summary by severity
ALERT_SUMMARY = """
SELECT 
    severity,
    status,
    COUNT(*) as alert_count,
    AVG(anomaly_score) as avg_anomaly_score,
    MAX(anomaly_score) as max_anomaly_score,
    MIN(timestamp) as first_alert,
    MAX(timestamp) as last_alert
FROM alerts
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY severity, status
ORDER BY 
    CASE severity 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'WARNING' THEN 2 
        ELSE 3 
    END,
    alert_count DESC;
"""

# Query 7: Recent alerts with details
RECENT_ALERTS = """
SELECT 
    timestamp,
    alert_type,
    severity,
    status,
    metric_value,
    threshold_value,
    anomaly_score,
    message,
    created_at
FROM alerts
WHERE timestamp >= datetime('now', '-1 hour')
ORDER BY created_at DESC
LIMIT 20;
"""

# Query 8: Transaction volume trends (5-minute buckets)
TRANSACTION_TRENDS = """
SELECT 
    strftime('%Y-%m-%d %H:', timestamp) || 
    CAST((CAST(strftime('%M', timestamp) AS INTEGER) / 5) * 5 AS TEXT) as time_bucket,
    status,
    SUM(count) as total_count,
    AVG(count) as avg_count,
    MIN(count) as min_count,
    MAX(count) as max_count
FROM transactions
WHERE timestamp >= datetime('now', '-2 hours')
GROUP BY time_bucket, status
ORDER BY time_bucket DESC, status;
"""

# Query 9: Identify consecutive anomaly periods
CONSECUTIVE_ANOMALIES = """
WITH anomaly_minutes AS (
    SELECT 
        strftime('%Y-%m-%d %H:%M', timestamp) as minute,
        status,
        SUM(count) as count,
        SUM(count) * 100.0 / SUM(SUM(count)) OVER (PARTITION BY strftime('%Y-%m-%d %H:%M', timestamp)) as rate
    FROM transactions
    WHERE timestamp >= datetime('now', '-1 hour')
      AND status IN ('failed', 'denied', 'reversed')
    GROUP BY minute, status
),
anomaly_flags AS (
    SELECT 
        minute,
        status,
        count,
        rate,
        CASE 
            WHEN status = 'failed' AND rate > 2.0 THEN 1
            WHEN status = 'denied' AND rate > 15.0 THEN 1
            WHEN status = 'reversed' AND rate > 4.0 THEN 1
            ELSE 0
        END as is_anomaly
    FROM anomaly_minutes
)
SELECT 
    status,
    minute,
    count,
    ROUND(rate, 2) as rate,
    SUM(is_anomaly) OVER (
        PARTITION BY status 
        ORDER BY minute 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as consecutive_anomaly_count
FROM anomaly_flags
WHERE is_anomaly = 1
ORDER BY status, minute DESC;
"""

# Query 10: Performance summary (last hour)
PERFORMANCE_SUMMARY = """
SELECT 
    COUNT(DISTINCT strftime('%Y-%m-%d %H:%M', timestamp)) as minutes_tracked,
    SUM(count) as total_transactions,
    SUM(CASE WHEN status = 'approved' THEN count ELSE 0 END) as approved,
    SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) as failed,
    SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) as denied,
    SUM(CASE WHEN status = 'reversed' THEN count ELSE 0 END) as reversed,
    SUM(CASE WHEN status = 'backend_reversed' THEN count ELSE 0 END) as backend_reversed,
    ROUND(100.0 * SUM(CASE WHEN status = 'approved' THEN count ELSE 0 END) / SUM(count), 2) as approval_rate,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) / SUM(count), 2) as failure_rate,
    ROUND(100.0 * SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) / SUM(count), 2) as denial_rate,
    ROUND(100.0 * SUM(CASE WHEN status = 'reversed' THEN count ELSE 0 END) / SUM(count), 2) as reversal_rate
FROM transactions
WHERE timestamp >= datetime('now', '-1 hour');
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_query_map():
    """Return dictionary of all queries"""
    return {
        'aggregate_by_minute': AGGREGATE_BY_MINUTE,
        'failure_rates': FAILURE_RATES,
        'failed_spikes': FAILED_TRANSACTION_SPIKES,
        'denied_anomalies': DENIED_TRANSACTION_ANOMALIES,
        'current_vs_baseline': CURRENT_VS_BASELINE,
        'alert_summary': ALERT_SUMMARY,
        'recent_alerts': RECENT_ALERTS,
        'transaction_trends': TRANSACTION_TRENDS,
        'consecutive_anomalies': CONSECUTIVE_ANOMALIES,
        'performance_summary': PERFORMANCE_SUMMARY
    }
