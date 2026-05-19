# Data Processing Boundaries

## 1. Data Residency
- All data processed by the Data Plane remains within the [Country/Region] specified by the customer.
- Control Plane telemetry data is stored in [Region].

## 2. Data Retention
- Prompt/Completion logs: [N] days (Customer configurable).
- System Telemetry: [N] days.
- Audit Logs: [N] days/years.

## 3. Privacy by Design
- The system does not require PII (Personally Identifiable Information) for core inference.
- Anonymization features are available for telemetry data.
