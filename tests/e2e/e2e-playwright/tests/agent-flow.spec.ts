import { test, expect } from '@playwright/test';

test.describe('Agent Lifecycle E2E', () => {
  const BASE = process.env.BASE_URL || 'http://localhost:18080';

  test('health endpoint returns ok', async ({ request }) => {
    const resp = await request.get(`${BASE}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('create and run a simple agent', async ({ request }) => {
    const adminToken = process.env.ADMIN_TOKEN || 'default-admin-token';
    const headers = { 'X-Admin-Token': adminToken };

    // Create a client
    const clientResp = await request.post(`${BASE}/admin/clients`, {
      headers,
      data: { name: 'e2e-test-client', email: 'e2e@test.com' },
    });
    expect(clientResp.ok()).toBeTruthy();
    const client = await clientResp.json();
    expect(client.name).toBe('e2e-test-client');
    const clientId = client.id || client.client_id;

    // Create API key for the client
    const keyResp = await request.post(`${BASE}/admin/api-keys`, {
      headers,
      data: { client_id: clientId, name: 'e2e-key' },
    });
    expect(keyResp.ok()).toBeTruthy();
    const keyData = await keyResp.json();
    const apiKey = keyData.api_key || keyData.key;

    // Create an agent
    const agentResp = await request.post(`${BASE}/v1/agents`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      data: {
        name: 'e2e-agent',
        system_prompt: 'You are a helpful assistant.',
      },
    });
    expect(agentResp.ok()).toBeTruthy();
    const agent = await agentResp.json();
    expect(agent.name).toBe('e2e-agent');
    const agentId = agent.id || agent.agent_id;

    // Run the agent
    const runResp = await request.post(`${BASE}/v1/agents/${agentId}/run`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      data: { input: 'Hello, agent!' },
    });
    expect(runResp.ok()).toBeTruthy();
    const run = await runResp.json();
    expect(run).toBeDefined();

    // Cleanup: delete agent and client
    await request.delete(`${BASE}/v1/agents/${agentId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
  });

  test('list models endpoint returns data', async ({ request }) => {
    const adminToken = process.env.ADMIN_TOKEN || 'default-admin-token';
    const resp = await request.get(`${BASE}/admin/models`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    expect(resp.ok()).toBeTruthy();
  });

  test('ready endpoint passes', async ({ request }) => {
    const resp = await request.get(`${BASE}/ready`);
    expect(resp.ok()).toBeTruthy();
  });
});
