# Local Production Runbook

This document describes the steps to set up, validate, and maintain the local production environment.

## 1. Setup
... (rest of the file) ...

## Validation Steps

### 1. Health Check
```bash
make health
```

### 2. Standard Validation
```bash
make validate
```

### 3. Security Report
```bash
make security
```

### 4. Commercial Plans Validation
Initialize and verify the plan matrix:
```bash
./scripts/seed-commercial-plans-local.sh
./scripts/validate-commercial-plans-local.sh
```

### 5. System Control Center Validation
```bash
make validate-control-center
```

### 6. Capability Matrix Validation
Verify the feature matrix and backend readiness:
```bash
./scripts/validate-capability-matrix-local.sh
```

### 7. Validate Abuse Protection
Before finalizing the production environment, ensure it can handle abuse without crashing:
```bash
make validate-abuse
```
Check the generated report in `artifacts/abuse-protection/<timestamp>/abuse-report.md`.

## Maintenance
...
