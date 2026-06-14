# Chaos Engineering Experiment Report

## 1. Experiment Overview
- **Name**: 
- **Type**: (data_plane_latency | redis_failure | db_outage | provider_timeout)
- **Environment**: 
- **Date**: 
- **Operator**: 

## 2. Hypothesis
(Describe what you expected to happen when the fault was injected. E.g., "The circuit breaker should open and requests should fail-over to the backup model.")

## 3. Injection Configuration
```json
{
  "injection_type": "...",
  "parameters": { ... }
}
```

## 4. Observed Impact
- **Service Availability**: 
- **Error Rate**: 
- **Latency (P95/P99)**: 
- **Logs / Trace Analysis**: 

## 5. Resilience Validation
- [ ] **Circuit Breaker**: (Opened / Closed / Not Triggered)
- [ ] **Retries**: (Successful / Exhausted)
- [ ] **Fallback**: (Triggered / Not Triggered)
- [ ] **Auto-Recovery**: (Yes / No / Manual Intervention Required)

## 6. Conclusions & Recommendations
- **Resilience Score**: (0.0 - 1.0)
- **Summary**: 
- **Action Items**: 
  - [ ] ...
