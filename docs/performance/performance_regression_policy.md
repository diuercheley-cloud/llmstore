# Performance Regression Policy

## Principles
1. **Zero Degradation**: Any PR that increases critical path latency by >10% without justification will be blocked.
2. **Mandatory Benchmarking**: New features in the inference or governance path must include a local benchmark.
3. **Continuous Monitoring**: Performance baselines are updated with every release baseline.

## Regression Handling
- **Minor (<5%)**: Documented and monitored.
- **Moderate (5-15%)**: Requires architectural review.
- **Critical (>15%)**: Blocked unless explicitly waived by the Performance Lead.
