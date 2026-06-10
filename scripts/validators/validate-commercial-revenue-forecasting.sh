#!/bin/bash
set -e

echo "=== Validating Commercial Revenue Forecasting & Anomaly Detection ==="

# 1. Run Forecast
echo "Running forecast..."
curl -s -X POST "http://localhost:8080/admin/billing/forecast/run" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq .

# 2. List Forecasts
echo "Listing forecasts..."
curl -s -X GET "http://localhost:8080/admin/billing/forecast/records" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq .

# 3. Run Anomaly Detection
echo "Running anomaly detection..."
curl -s -X POST "http://localhost:8080/admin/billing/anomalies/run" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq .

# 4. List Anomalies
echo "Listing anomalies..."
ANOMALIES=$(curl -s -X GET "http://localhost:8080/admin/billing/anomalies" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}")
echo "${ANOMALIES}" | jq .

ANOMALY_ID=$(echo "${ANOMALIES}" | jq -r '.[0].id')

if [ "${ANOMALY_ID}" != "null" ]; then
    # 5. Ack Anomaly
    echo "Acknowledging anomaly ${ANOMALY_ID}..."
    curl -s -X POST "http://localhost:8080/admin/billing/anomalies/${ANOMALY_ID}/ack" \
         -H "Authorization: Bearer ${ADMIN_TOKEN}" \
         -H "Content-Type: application/json" \
         -d '{"explanation": "Investigating"}' | jq .

    # 6. Resolve Anomaly
    echo "Resolving anomaly ${ANOMALY_ID}..."
    curl -s -X POST "http://localhost:8080/admin/billing/anomalies/${ANOMALY_ID}/resolve" \
         -H "Authorization: Bearer ${ADMIN_TOKEN}" \
         -H "Content-Type: application/json" \
         -d '{"explanation": "Fixed issue"}' | jq .
else
    echo "No anomalies found to test actions."
fi

echo "=== Validation Complete ==="
