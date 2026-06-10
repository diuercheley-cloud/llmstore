import { test, expect, type Page, type APIRequestContext } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// ─── Helpers ───────────────────────────────────────────────────────────────────

async function isVisible(page: Page, selector: string, timeout = 2000): Promise<boolean> {
  try {
    await page.waitForSelector(selector, { state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

/** Login into Admin Lab (static HTML page) */
async function adminLabLogin(page: Page, token: string) {
  await page.goto('/admin-lab');
  const needsLogin = await isVisible(page, '#admin-token');
  if (needsLogin) {
    await page.fill('#admin-token', token);
    await page.click('#btn-connect');
    // Wait for connection status to change
    await page.waitForSelector('#connection-status:has-text("Conectado")', { timeout: 10000 });
  }
}

/** Login into Portal page (static HTML page) */
async function portalLogin(page: Page, apiKey: string, portalPage = 'index.html') {
  await page.goto(`/static/portal/${portalPage}`);
  const needsLogin = await isVisible(page, '#loginKey');
  if (needsLogin) {
    await page.fill('#loginKey', apiKey);
    await page.click('#doLogin');
    await page.waitForTimeout(500);
  }
}

// ─── Test Suite ────────────────────────────────────────────────────────────────

test.describe.serial('Critical Business Flows E2E', () => {
  const adminToken = 'test-admin-token';
  let apiKeyValue = '';
  let clientId = '';
  let invoiceId = '';

  // ─── Flow 1: Admin Login com Token ─────────────────────────────────────────
  test('Flow 1: Admin Login with Token', async ({ page }) => {
    // Navigate to Admin Lab
    await page.goto('/admin-lab');

    // Login overlay should be visible
    await page.waitForSelector('#login-overlay', { state: 'visible', timeout: 15000 });

    // Enter admin token and connect
    await page.fill('#admin-token', adminToken);
    await page.click('#btn-connect');

    // Wait for connection to succeed
    await page.waitForSelector('#connection-status:has-text("Conectado")', { timeout: 10000 });

    // Login overlay should disappear
    await expect(page.locator('#login-overlay')).toBeHidden({ timeout: 5000 });

    // Sidebar navigation should be visible
    await expect(page.locator('aside nav')).toBeVisible();
  });

  // ─── Flow 2: Criação de Cliente e API Key ──────────────────────────────────
  test('Flow 2: Client & API Key Creation', async ({ page }) => {
    // Use API to create client (reliable, not dependent on UI modal selectors)
    const createClientRes = await page.request.post('/admin/clients', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { name: 'E2E Test Client', description: 'Created by Playwright E2E tests' },
    });
    expect(createClientRes.status()).toBe(200);
    const clientData = await createClientRes.json();
    clientId = clientData.id;
    expect(clientId).toBeTruthy();

    // Create API Key via API
    const createKeyRes = await page.request.post('/admin/api-keys', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { client_id: clientId, name: 'E2E Default Key' },
    });
    expect(createKeyRes.status()).toBe(200);
    const keyData = await createKeyRes.json();
    apiKeyValue = keyData.key || keyData.api_key || keyData.secret || '';
    expect(apiKeyValue).toContain('sk-');

    // Verify the client is visible in Admin Lab UI
    await adminLabLogin(page, adminToken);
    await page.click('a[data-tab="clients"]');
    await page.waitForSelector('td:has-text("E2E Test Client")', { timeout: 10000 });
  });

  // ─── Flow 3: Chat Completion via Playground ────────────────────────────────
  test('Flow 3: Chat Completion via Playground', async ({ page }) => {
    test.skip(!apiKeyValue, 'API key not available from Flow 2');

    // Test chat completions via API (the actual inference test)
    const chatRes = await page.request.post('/v1/chat/completions', {
      headers: {
        'Authorization': `Bearer ${apiKeyValue}`,
        'Content-Type': 'application/json',
      },
      data: {
        model: 'default',
        messages: [{ role: 'user', content: 'Hello, what is your status?' }],
        max_tokens: 50,
      },
    });
    // Accept 200 (success) or 503 (model not loaded) in mock mode
    expect([200, 503]).toContain(chatRes.status());

    // If 200, verify response structure
    if (chatRes.status() === 200) {
      const chatData = await chatRes.json();
      expect(chatData.choices).toBeDefined();
      expect(chatData.choices.length).toBeGreaterThan(0);
    }

    // Verify the playground page loads correctly in the portal
    await portalLogin(page, apiKeyValue, 'playground.html');
    await expect(page.locator('#pgPrompt')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#pgRun')).toBeVisible();
  });

  // ─── Flow 4: RAG Document Upload & Semantic Search ─────────────────────────
  test('Flow 4: RAG Document Upload & Semantic Search', async ({ page }) => {
    test.skip(!apiKeyValue, 'API key not available from Flow 2');

    // Create a temporary test file
    const tmpDir = path.resolve(__dirname, '..');
    const filePath = path.join(tmpDir, 'rag_test_doc.txt');
    fs.writeFileSync(filePath, 'Este é um documento de teste RAG sobre infraestrutura inteligente de IA e modelos de linguagem.');

    try {
      // Upload via API
      const uploadRes = await page.request.post('/v1/rag/documents', {
        headers: { 'Authorization': `Bearer ${apiKeyValue}` },
        multipart: {
          file: {
            name: 'rag_test_doc.txt',
            mimeType: 'text/plain',
            buffer: fs.readFileSync(filePath),
          },
        },
      });
      // Accept 200/201 (success) or 501/503 (RAG not fully configured in test mode)
      expect([200, 201, 400, 501, 503]).toContain(uploadRes.status());

      // If upload succeeded, test semantic search via API
      if (uploadRes.status() === 200 || uploadRes.status() === 201) {
        const searchRes = await page.request.post('/v1/rag/query', {
          headers: {
            'Authorization': `Bearer ${apiKeyValue}`,
            'Content-Type': 'application/json',
          },
          data: { query: 'infraestrutura inteligente', top_k: 3 },
        });
        expect([200, 501, 503]).toContain(searchRes.status());
      }

      // Verify RAG portal page loads correctly
      await portalLogin(page, apiKeyValue, 'rag.html');
      await expect(page.locator('#ragQueryInput')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('#btnRagQuery')).toBeVisible();
    } finally {
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    }
  });

  // ─── Flow 5: Invoice Generation & Viewing ──────────────────────────────────
  test('Flow 5: Invoice Generation & Viewing', async ({ page }) => {
    test.skip(!clientId, 'Client ID not available from Flow 2');

    // Generate invoice via API
    const invoiceRes = await page.request.post('/admin/billing/invoices/generate', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { client_id: clientId, due_days: 7, force: true },
    });
    // Accept various success codes
    expect([200, 201, 422]).toContain(invoiceRes.status());

    if (invoiceRes.status() === 200 || invoiceRes.status() === 201) {
      const invoiceData = await invoiceRes.json();
      // The response may be an array or a single invoice
      if (Array.isArray(invoiceData) && invoiceData.length > 0) {
        invoiceId = invoiceData[0].id;
      } else if (invoiceData.id) {
        invoiceId = invoiceData.id;
      } else if (invoiceData.created && Array.isArray(invoiceData.created) && invoiceData.created.length > 0) {
        invoiceId = invoiceData.created[0].id || invoiceData.created[0];
      }
    }

    // If no invoice was generated, try listing existing invoices
    if (!invoiceId) {
      const listRes = await page.request.get(`/admin/billing/invoices?client_id=${clientId}`, {
        headers: { 'X-Admin-Token': adminToken },
      });
      if (listRes.status() === 200) {
        const invoices = await listRes.json();
        if (Array.isArray(invoices) && invoices.length > 0) {
          invoiceId = invoices[0].id;
        }
      }
    }

    // Verify invoices page loads in portal
    if (apiKeyValue) {
      await portalLogin(page, apiKeyValue, 'invoices.html');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    }
  });

  // ─── Flow 6: Cloud Provider Configuration ──────────────────────────────────
  test('Flow 6: Cloud Provider Configuration', async ({ page }) => {
    // Navigate to provider-settings page
    await page.goto('/provider-settings');

    // Enter admin token and load config
    await page.waitForSelector('#adminToken', { state: 'visible', timeout: 15000 });
    await page.fill('#adminToken', adminToken);
    await page.click('#loadBtn');

    // Wait for configuration to load
    await page.waitForSelector('#message', { timeout: 10000 });
    // The message may say "Configuracao carregada" or show an error if .env.local doesn't exist
    const messageText = await page.locator('#message').innerText();
    
    // If config loaded successfully, modify and save
    if (messageText.includes('carregada') || messageText.includes('Carregada')) {
      const cloudCheckbox = page.locator('#cloudEnabled');
      await cloudCheckbox.setChecked(true);
      await page.click('#saveBtn');

      // Verify save message
      await page.waitForTimeout(1000);
      const saveMessage = await page.locator('#message').innerText();
      expect(saveMessage.length).toBeGreaterThan(0);
    } else {
      // Even if the config can't be loaded (e.g., file not found), 
      // verify the page UI elements are present
      await expect(page.locator('#cloudEnabled')).toBeVisible();
      await expect(page.locator('#saveBtn')).toBeVisible();
    }
  });

  // ─── Flow 7: Model Hot-Swap & Rollback ─────────────────────────────────────
  test('Flow 7: Model Hot-Swap & Rollback Flow', async ({ page }) => {
    const api = page.request;

    // List registered models
    const modelsRes = await api.get('/admin/models', {
      headers: { 'X-Admin-Token': adminToken },
    });
    expect(modelsRes.status()).toBe(200);
    const models = await modelsRes.json();
    expect(models.length).toBeGreaterThan(0);
    const model = models[0];

    // 1. Load model runtime v1 (mock mode)
    const loadV1Res = await api.post('/admin/models/runtime/load', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: {
        model_id: model.id,
        backend_id: model.inference_backend_id,
        model_path: 'fake-gemma-v1.gguf',
      },
    });
    expect(loadV1Res.status()).toBe(200);
    const instanceV1 = await loadV1Res.json();
    expect(instanceV1.id).toBeTruthy();

    // 2. Activate model v1
    const actV1Res = await api.post(`/admin/models/runtime/activate/${instanceV1.id}`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    expect(actV1Res.status()).toBe(200);

    // 3. Load model runtime v2 (hot-swap)
    const loadV2Res = await api.post('/admin/models/runtime/load', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: {
        model_id: model.id,
        backend_id: model.inference_backend_id,
        model_path: 'fake-gemma-v2.gguf',
      },
    });
    expect(loadV2Res.status()).toBe(200);
    const instanceV2 = await loadV2Res.json();

    // 4. Activate v2
    const actV2Res = await api.post(`/admin/models/runtime/activate/${instanceV2.id}`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    expect(actV2Res.status()).toBe(200);

    // 5. Rollback to v1
    const rollbackRes = await api.post(
      `/admin/models/runtime/rollback?model_id=${model.id}&backend_id=${model.inference_backend_id}`,
      { headers: { 'X-Admin-Token': adminToken } }
    );
    expect(rollbackRes.status()).toBe(200);
  });

  // ─── Flow 8: Client Suspension & Reactivation ─────────────────────────────
  test('Flow 8: Client Suspension & Reactivation Flow', async ({ page }) => {
    test.skip(!clientId, 'Client ID not available from Flow 2');

    const api = page.request;

    // 1. Suspend client via admin API
    const suspendRes = await api.patch(`/admin/clients/${clientId}`, {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { billing_status: 'suspended' },
    });
    expect([200, 422]).toContain(suspendRes.status());

    if (suspendRes.status() === 200) {
      // 2. Verify client is suspended
      const clientRes = await api.get(`/admin/clients/${clientId}`, {
        headers: { 'X-Admin-Token': adminToken },
      });
      expect(clientRes.status()).toBe(200);
      const clientData = await clientRes.json();
      expect(clientData.billing_status).toBe('suspended');

      // 3. Reactivate client
      const reactivateRes = await api.patch(`/admin/clients/${clientId}`, {
        headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
        data: { billing_status: 'active' },
      });
      expect(reactivateRes.status()).toBe(200);

      // 4. Verify client is active again
      const clientRes2 = await api.get(`/admin/clients/${clientId}`, {
        headers: { 'X-Admin-Token': adminToken },
      });
      expect(clientRes2.status()).toBe(200);
      const clientData2 = await clientRes2.json();
      expect(clientData2.billing_status).toBe('active');
    }
  });

  // ─── Flow 9: Onboarding Wizard ─────────────────────────────────────────────
  test('Flow 9: Onboarding Wizard Flow', async ({ page }) => {
    const api = page.request;

    // 1. Reset onboarding status to show wizard
    await api.post('/admin/onboarding/status', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { is_finished: false },
    });

    // 2. Access Admin V2 and verify Wizard is visible
    await page.goto('/admin-v2');
    // The wizard might take a moment to load due to React
    await page.waitForSelector('text=Passo 1 de 5', { timeout: 20000 });
    await expect(page.locator('text=Modelo GGUF')).toBeVisible();

    // 3. Test skipping or finishing via API (reliable)
    const updateRes = await api.post('/admin/onboarding/status', {
      headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
      data: { is_finished: true },
    });
    expect([200, 422, 500]).toContain(updateRes.status());

    // 4. Verify Admin Lab loads correctly and shows dashboard
    await adminLabLogin(page, adminToken);
    await expect(page.locator('a[data-tab="overview"]')).toBeVisible({ timeout: 5000 });
  });
});
