# POS Checkout Data - Anomaly Analysis Report
## CloudWalk Monitoring Analyst Assessment

**Analyst:** Candidate Assessment  
**Date:** November 25, 2025  
**Data Period:** 24-hour checkout data from two POS systems  

---

## Executive Summary

Analysis of two POS systems revealed **critical operational anomalies** requiring immediate attention:

- **POS_1**: 2 hours with zero sales during peak/operational hours (4h, 8h)
- **POS_2**: 5 hours with zero sales, including 3 consecutive hours (15h-17h) during peak business hours
- Both systems show significant deviations from historical patterns
- POS_2 exhibits signs of potential system outage or connectivity issues during afternoon peak hours

**Risk Level:** 🔴 **HIGH** - Revenue loss and potential system failure

---

## 1. Data Analysis & Methodology

### 1.1 Dataset Overview

**POS_1 Statistics:**
- Total sales today: 526 transactions
- Total sales yesterday: 523 transactions
- Average per hour: 21.92 transactions
- Historical weekly average: 15.48 transactions/hour
- Zero sales hours: 2
- Anomaly hours (>50% deviation): 14 out of 24 hours

**POS_2 Statistics:**
- Total sales today: 427 transactions
- Total sales yesterday: 526 transactions
- Average per hour: 17.79 transactions
- Historical weekly average: 11.94 transactions/hour
- Zero sales hours: 5
- Anomaly hours (>50% deviation): 20 out of 24 hours

### 1.2 Analysis Approach

1. **Comparative Analysis**: Compared today's performance against:
   - Yesterday's data
   - Same day last week
   - Weekly average
   - Monthly average

2. **Statistical Deviation**: Calculated percentage deviation from historical averages

3. **Pattern Recognition**: Identified temporal patterns and anomalies

4. **SQL Queries**: Deep-dive analysis using structured queries (see Section 4)

---

## 2. Key Findings & Anomalies

### 2.1 Critical Anomalies - POS_1

#### Zero Sales Events
| Hour | Today | Yesterday | Avg Week | Avg Month | Issue |
|------|-------|-----------|----------|-----------|-------|
| 04h  | 0     | 0         | 0.42     | 0.21      | Low-traffic hour |
| **08h** | **0** | **1** | **8.71** | **10.42** | **CRITICAL - Morning peak** |

**Analysis:**
- 08h typically sees 8-10 transactions but recorded ZERO today
- This represents a -100% deviation during morning business hours
- Previous day had normal activity (1 sale)
- Potential system failure or connectivity issue

#### Severe Underperformance
| Hour | Today | Avg Week | Deviation | Issue |
|------|-------|----------|-----------|-------|
| 09h  | 2     | 20.00    | -90%      | Major drop during peak |
| 06h  | 1     | 2.85     | -63%      | Morning startup issue |
| 07h  | 2     | 5.57     | -63%      | Pre-peak slowdown |

#### Exceptional Overperformance
| Hour | Today | Avg Week | Deviation | Note |
|------|-------|----------|-----------|------|
| 10h  | 55    | 29.42    | +87%      | Compensating for 08h-09h? |
| 12h  | 51    | 27.57    | +85%      | Lunch rush spike |
| 17h  | 45    | 20.42    | +120%     | Evening spike |

### 2.2 Critical Anomalies - POS_2

#### Zero Sales Events - SYSTEM OUTAGE SUSPECTED
| Hour | Today | Yesterday | Avg Week | Avg Month | Issue |
|------|-------|-----------|----------|-----------|-------|
| 03h  | 0     | 1         | 0.42     | 0.46      | Low-traffic |
| 04h  | 0     | 0         | 0.14     | 0.21      | Low-traffic |
| **15h** | **0** | **51** | **22.43** | **27.78** | **CRITICAL OUTAGE** |
| **16h** | **0** | **41** | **21.57** | **25.53** | **CRITICAL OUTAGE** |
| **17h** | **0** | **45** | **17.71** | **22.67** | **CRITICAL OUTAGE** |

**Analysis - SYSTEM OUTAGE:**
- **3 consecutive hours** (15h-17h) with ZERO sales during peak afternoon hours
- Yesterday same hours: 51, 41, 45 transactions
- Historical average: 20-28 transactions per hour
- **Total revenue loss: ~60-70 transactions (~$XXX estimated loss)**
- Strong evidence of system failure, network outage, or power failure

#### Severe Morning Spikes (Compensation Pattern?)
| Hour | Today | Avg Week | Deviation | Note |
|------|-------|----------|-----------|------|
| 08h  | 25    | 3.71     | +574%     | Extreme spike |
| 09h  | 36    | 10.14    | +255%     | Continued spike |
| 07h  | 10    | 3.00     | +233%     | Pre-spike buildup |

**Pattern Observation:** Morning hours show extreme overperformance, possibly due to:
- Pent-up demand from previous issues
- Special promotion or event
- Data collection anomaly

---

## 3. Business Impact Analysis

### 3.1 Revenue Impact

**POS_1:**
- Lost opportunity during 08h-09h: ~28 transactions
- Overcompensated in 10h-12h: +40 transactions
- Net impact: Likely neutral to positive for the day
- **Risk:** System instability could worsen

**POS_2:**
- Lost sales during 15h-17h: ~60-70 transactions
- No compensation pattern observed
- **Estimated revenue loss:** 14-16% of daily revenue
- **Risk:** HIGH - System appears to have failed completely for 3 hours

### 3.2 Operational Concerns

1. **System Reliability**: Both POS systems showing zero-sale events during operational hours
2. **Data Integrity**: Need to verify if zeros represent actual no-sales or data collection failures
3. **Customer Impact**: Potential customer dissatisfaction if unable to complete purchases
4. **Pattern Persistence**: POS_2 shows more severe and prolonged issues

---

## 4. SQL Analysis Results

### Query 1: Zero Sales During High-Traffic Periods
```sql
SELECT dataset, time, today as current_sales, yesterday, avg_last_week,
       ROUND(((today - avg_last_week) / NULLIF(avg_last_week, 0)) * 100, 2) as deviation_pct
FROM pos_sales
WHERE today = 0 AND avg_last_week > 5
ORDER BY dataset, time;
```

**Results:**
- POS_1: 1 critical hour (08h) with -100% deviation
- POS_2: 3 critical hours (15h-17h) with -100% deviation

### Query 2: Extreme Deviations (>100%)
```sql
SELECT dataset, time, today, avg_last_week, deviation_pct,
       CASE 
           WHEN today = 0 THEN 'CRITICAL: Zero Sales'
           WHEN deviation_pct > 100 THEN 'ALERT: High Spike'
           WHEN deviation_pct < -80 THEN 'ALERT: Major Drop'
       END as alert_type
FROM pos_sales
WHERE ABS(deviation_pct) > 100 OR today = 0
```

**Findings:**
- 5 CRITICAL zero-sales alerts
- 13 HIGH SPIKE alerts (mostly POS_2 morning hours)
- Total 18 extreme anomalies detected

### Query 3: Peak Hours Performance (10h-18h)
**Key Insight:** POS_2's afternoon collapse is clearly visible:
- 14h: 19 sales (-3% vs avg) - Starting to decline
- 15h-17h: 0 sales (-100%) - Complete failure
- 18h: 13 sales (-23%) - Partial recovery

---

## 5. Root Cause Hypotheses

### POS_1 - Morning Slowdown (08h-09h)
**Possible Causes:**
1. Network connectivity issue (8-9 AM)
2. System restart or maintenance
3. Staff scheduling gap
4. Payment processor timeout
5. Power interruption

**Evidence:** Single hour zero + subsequent severe drop suggests technical issue

### POS_2 - Afternoon Outage (15h-17h)
**Possible Causes:**
1. **System crash** (most likely - 3 consecutive hours)
2. **Network outage** (internet/connectivity failure)
3. **Power failure** (no backup power)
4. **Software failure** (application crash)
5. Payment gateway outage

**Evidence:** 
- Perfect zero for 3 consecutive hours
- Normal operation before and partial recovery after
- Strongest indicator of complete system failure

---

## 6. Recommendations

### Immediate Actions (Within 24 hours)

1. **POS_2 System Investigation** 🔴 URGENT
   - Check system logs for 15h-17h period
   - Verify network connectivity history
   - Review error logs and crash reports
   - Test payment processor connectivity
   - Verify power supply and UPS functionality

2. **POS_1 Morning Analysis** 🟡 HIGH PRIORITY
   - Review 08h-09h system logs
   - Check network stability metrics
   - Verify staff presence and system access logs

3. **Data Validation**
   - Confirm zeros represent actual no-sales vs. data collection failures
   - Cross-reference with:
     - Server logs
     - Network monitoring tools
     - Security cameras (staff presence)
     - Customer complaint logs

### Short-term Actions (This Week)

4. **Implement Real-time Monitoring**
   - Set up alerts for zero-sale periods >30 minutes during business hours (9h-22h)
   - Alert threshold: Any hour with <50% of historical average
   - Dashboard showing current vs. expected sales by hour

5. **System Health Checks**
   - Daily automated system health reports
   - Network connectivity monitoring
   - Payment gateway response time tracking

6. **Redundancy Planning**
   - Backup payment processing methods
   - Offline transaction capability
   - UPS/backup power verification

### Long-term Actions (This Month)

7. **Pattern Analysis**
   - Continue monitoring for recurring issues
   - Establish baseline performance metrics
   - Create predictive anomaly detection models

8. **Business Continuity**
   - Document incident response procedures
   - Create escalation protocols
   - Train staff on system failure procedures

9. **Infrastructure Assessment**
   - Review hardware age and reliability
   - Assess network infrastructure quality
   - Consider system redundancy/failover solutions

---

## 7. Monitoring Framework Proposal

### KPIs to Track

1. **Sales per Hour**: Compare to rolling 7-day and 30-day averages
2. **Zero-Sale Incidents**: Any hour with 0 sales during business hours (6h-22h)
3. **Deviation Threshold**: Alert when >50% deviation from expected
4. **System Uptime**: Track POS availability percentage
5. **Recovery Time**: Measure time to restore after incidents

### Alert Rules

```
CRITICAL: Zero sales for >1 hour during peak hours (9h-18h)
HIGH: Sales <25% of expected for >30 minutes
MEDIUM: Sales 25-50% of expected for >1 hour
INFO: Sales >150% of expected (potential spike or data error)
```

### Dashboard Metrics

- Real-time sales vs. expected (hourly)
- 24-hour rolling comparison
- Week-over-week trends
- System health status
- Alert history and response times

---

## 8. Conclusion

The analysis reveals **significant operational risks** requiring immediate attention:

**POS_1**: Moderate concern with isolated morning performance issues. Likely recoverable and may represent temporary technical glitch.

**POS_2**: **CRITICAL FAILURE** - Evidence strongly suggests complete system outage for 3 consecutive peak hours (15h-17h). This resulted in substantial revenue loss and represents a serious reliability issue.

### Key Takeaways

1. **Data smoke = Business fire** is validated: Small anomalies (08h zero) preceded larger issues
2. Both systems require enhanced monitoring and alerting
3. POS_2 needs immediate investigation and potentially hardware/software intervention
4. Historical comparison is essential for identifying anomalies
5. Real-time monitoring could have caught and mitigated these issues earlier

### Success Metrics for Resolution

- Zero critical incidents (0 sales during peak) in next 30 days
- <5% deviation from historical averages
- <15 minute incident detection time
- <30 minute incident response time
- System uptime >99.5%

---

## Appendix: Technical Details

### Data Sources
- checkout_1.csv: POS System 1, 24-hour transaction data
- checkout_2.csv: POS System 2, 24-hour transaction data

### Analysis Tools
- Python (pandas, matplotlib, numpy)
- SQLite (in-memory database for complex queries)
- Statistical analysis and visualization

### Methodology
- Deviation analysis: ((today - average) / average) × 100
- Anomaly threshold: ±50% from historical average
- Critical threshold: Zero sales during hours with historical average >5 transactions

---

**Report prepared by:** Monitoring Analyst Candidate  
**For:** CloudWalk Assessment  
**Next Review:** Daily until systems stabilize, then weekly
