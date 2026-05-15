# Commercial Revenue Forecasting & Financial Anomaly Detection

Phase 28 implements statistical tools to predict future financial performance and detect anomalies in real-time.

## 1. Revenue Forecasting

The forecasting service provides predictions for:
- **Revenue**: Total billable amount for customers.
- **Cost**: Total provider costs (USD/BRL).
- **Margin**: Gross profit (Revenue - Cost).
- **QoS Billing**: Revenue specifically from priority queues and QoS tiers.

### Forecasting Methods

| Method | Description | Best For |
|--------|-------------|----------|
| `moving_average` | Simple average of the last N days. | Stable, non-seasonal traffic. |
| `ewma` | Exponentially Weighted Moving Average. | Adapting quickly to recent trends. |
| `linear_trend` | Linear regression on historical data. | Growing or shrinking workloads. |

### Confidence Levels
- **High**: Stable data with low variance and many samples.
- **Medium**: Moderate variance or fewer samples.
- **Low**: Highly volatile data or insufficient history (< 7 days).

## 2. Financial Anomaly Detection

Detects unusual spikes or drops in financial metrics using:
- **Z-Score**: Number of standard deviations from the mean.
- **Percentage Threshold**: Absolute deviation from the baseline.

### Detected Anomalies
- `revenue_spike` / `revenue_drop`
- `cost_spike`
- `margin_drop`
- `wallet_debit_spike`
- `qos_billing_spike`
- `dispute_spike`

### Severity Levels
- **Critical**: Deviation > 100% or Z-Score > 5.
- **High**: Deviation > 50% or Z-Score > 3.
- **Medium**: Significant deviation within thresholds.
- **Low**: Noticed but within expected variance.

## 3. Configuration

```bash
COMMERCIAL_REVENUE_FORECASTING_ENABLED=true
COMMERCIAL_REVENUE_FORECAST_METHOD=ewma
COMMERCIAL_REVENUE_FORECAST_WINDOW_DAYS=30

COMMERCIAL_FINANCIAL_ANOMALY_DETECTION_ENABLED=true
COMMERCIAL_FINANCIAL_ANOMALY_ZSCORE_THRESHOLD=3.0
COMMERCIAL_FINANCIAL_ANOMALY_PERCENT_THRESHOLD=30
```

## 4. Admin API

- `GET /admin/billing/forecast/overview`: Executive summary of next 30 days.
- `POST /admin/billing/forecast/run`: Trigger manual forecast recalculation.
- `GET /admin/billing/anomalies`: List detected anomalies.
- `POST /admin/billing/anomalies/{id}/ack`: Acknowledge an anomaly.
- `POST /admin/billing/anomalies/{id}/resolve`: Mark anomaly as resolved.

## 5. Dashboard Integration

The **Executive Dashboard** now includes:
- **Next 30 Days Forecast**: Revenue and Margin predictions.
- **Financial Anomaly Badge**: SAFE (Green), WARNING (Yellow), CRITICAL (Red).
- **Top Risk Clients**: Clients with recent anomalous spend or dispute spikes.

## 6. Limitations

- This system uses **statistical methods**, not Deep Learning. It does not account for complex seasonality or external market events.
- Accuracy depends on having at least 7-14 days of historical data.
- Forecasts are re-calculated on demand or via scheduled jobs (if configured).
