// k6 load test: multi-tenant agent runtime
// Usage: k6 run tests/load/test_agent_multi_tenant_k6.js
// Optional: k6 run -e BASE_URL=http://localhost:8000 -e AGENT_ID=<id> -e TENANTS=5 tests/load/test_agent_multi_tenant_k6.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'k6/crypto';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AGENT_ID = __ENV.AGENT_ID || 'test-agent-id';
const NUM_TENANTS = parseInt(__ENV.TENANTS || '5');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

function getTenantId(index) {
  return `load-tenant-${index}`;
}

export default function () {
  const tenantIndex = Math.floor(Math.random() * NUM_TENANTS);
  const tenantId = getTenantId(tenantIndex);
  const headers = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': tenantId,
  };

  // POST /v1/agents/{agent_id}/runs
  const payload = JSON.stringify({
    input_text: `Load test message from tenant ${tenantId} at ${Date.now()}`,
  });

  const createRes = http.post(
    `${BASE_URL}/v1/agents/${AGENT_ID}/runs`,
    payload,
    { headers },
  );

  check(createRes, {
    'agent run created': (r) => r.status === 200 || r.status === 201 || r.status === 202,
  });

  if (createRes.status === 200 || createRes.status === 201) {
    const runId = createRes.json('id');
    if (runId) {
      // Poll for completion
      for (let i = 0; i < 5; i++) {
        sleep(2);
        const pollRes = http.get(
          `${BASE_URL}/v1/agents/runs/${runId}`,
          { headers },
        );
        if (pollRes.status === 200) {
          const status = pollRes.json('status');
          if (status === 'completed' || status === 'failed') {
            break;
          }
        }
      }
    }
  }

  // GET /v1/models
  const modelsRes = http.get(`${BASE_URL}/v1/models`, { headers });
  check(modelsRes, {
    'models listed': (r) => r.status === 200,
  });
}
