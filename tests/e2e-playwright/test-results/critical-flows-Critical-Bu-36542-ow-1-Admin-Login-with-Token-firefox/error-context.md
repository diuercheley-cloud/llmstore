# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: critical-flows.spec.ts >> Critical Business Flows E2E >> Flow 1: Admin Login with Token
- Location: tests/critical-flows.spec.ts:48:7

# Error details

```
Error: expect(locator).toBeHidden() failed

Locator:  locator('#login-overlay')
Expected: hidden
Received: visible
Timeout:  5000ms

Call log:
  - Expect "toBeHidden" with timeout 5000ms
  - waiting for locator('#login-overlay')
    14 × locator resolved to <div id="login-overlay">…</div>
       - unexpected value "visible"

```

```yaml
- heading "Bem-vindo ao Admin Lab" [level=1]
- paragraph: Insira o token administrativo para validar o sistema.
- checkbox "Lembrar neste navegador"
- text: Lembrar neste navegador
```

# Test source

```ts
  1   | import { test, expect, type Page, type APIRequestContext } from '@playwright/test';
  2   | import * as path from 'path';
  3   | import * as fs from 'fs';
  4   | 
  5   | // ─── Helpers ───────────────────────────────────────────────────────────────────
  6   | 
  7   | async function isVisible(page: Page, selector: string, timeout = 2000): Promise<boolean> {
  8   |   try {
  9   |     await page.waitForSelector(selector, { state: 'visible', timeout });
  10  |     return true;
  11  |   } catch {
  12  |     return false;
  13  |   }
  14  | }
  15  | 
  16  | /** Login into Admin Lab (static HTML page) */
  17  | async function adminLabLogin(page: Page, token: string) {
  18  |   await page.goto('/admin-lab');
  19  |   const needsLogin = await isVisible(page, '#admin-token');
  20  |   if (needsLogin) {
  21  |     await page.fill('#admin-token', token);
  22  |     await page.click('#btn-connect');
  23  |     // Wait for connection status to change
  24  |     await page.waitForSelector('#connection-status:has-text("Conectado")', { timeout: 10000 });
  25  |   }
  26  | }
  27  | 
  28  | /** Login into Portal page (static HTML page) */
  29  | async function portalLogin(page: Page, apiKey: string, portalPage = 'index.html') {
  30  |   await page.goto(`/static/portal/${portalPage}`);
  31  |   const needsLogin = await isVisible(page, '#loginKey');
  32  |   if (needsLogin) {
  33  |     await page.fill('#loginKey', apiKey);
  34  |     await page.click('#doLogin');
  35  |     await page.waitForTimeout(500);
  36  |   }
  37  | }
  38  | 
  39  | // ─── Test Suite ────────────────────────────────────────────────────────────────
  40  | 
  41  | test.describe.serial('Critical Business Flows E2E', () => {
  42  |   const adminToken = 'test-admin-token';
  43  |   let apiKeyValue = '';
  44  |   let clientId = '';
  45  |   let invoiceId = '';
  46  | 
  47  |   // ─── Flow 1: Admin Login com Token ─────────────────────────────────────────
  48  |   test('Flow 1: Admin Login with Token', async ({ page }) => {
  49  |     // Navigate to Admin Lab
  50  |     await page.goto('/admin-lab');
  51  | 
  52  |     // Login overlay should be visible
  53  |     await page.waitForSelector('#login-overlay', { state: 'visible', timeout: 15000 });
  54  | 
  55  |     // Enter admin token and connect
  56  |     await page.fill('#admin-token', adminToken);
  57  |     await page.click('#btn-connect');
  58  | 
  59  |     // Wait for connection to succeed
  60  |     await page.waitForSelector('#connection-status:has-text("Conectado")', { timeout: 10000 });
  61  | 
  62  |     // Login overlay should disappear
> 63  |     await expect(page.locator('#login-overlay')).toBeHidden({ timeout: 5000 });
      |                                                  ^ Error: expect(locator).toBeHidden() failed
  64  | 
  65  |     // Sidebar navigation should be visible
  66  |     await expect(page.locator('aside nav')).toBeVisible();
  67  |   });
  68  | 
  69  |   // ─── Flow 2: Criação de Cliente e API Key ──────────────────────────────────
  70  |   test('Flow 2: Client & API Key Creation', async ({ page }) => {
  71  |     // Use API to create client (reliable, not dependent on UI modal selectors)
  72  |     const createClientRes = await page.request.post('/admin/clients', {
  73  |       headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
  74  |       data: { name: 'E2E Test Client', description: 'Created by Playwright E2E tests' },
  75  |     });
  76  |     expect(createClientRes.status()).toBe(200);
  77  |     const clientData = await createClientRes.json();
  78  |     clientId = clientData.id;
  79  |     expect(clientId).toBeTruthy();
  80  | 
  81  |     // Create API Key via API
  82  |     const createKeyRes = await page.request.post('/admin/api-keys', {
  83  |       headers: { 'X-Admin-Token': adminToken, 'Content-Type': 'application/json' },
  84  |       data: { client_id: clientId, name: 'E2E Default Key' },
  85  |     });
  86  |     expect(createKeyRes.status()).toBe(200);
  87  |     const keyData = await createKeyRes.json();
  88  |     apiKeyValue = keyData.key || keyData.api_key || keyData.secret || '';
  89  |     expect(apiKeyValue).toContain('sk-');
  90  | 
  91  |     // Verify the client is visible in Admin Lab UI
  92  |     await adminLabLogin(page, adminToken);
  93  |     await page.click('a[data-tab="clients"]');
  94  |     await page.waitForSelector('td:has-text("E2E Test Client")', { timeout: 10000 });
  95  |   });
  96  | 
  97  |   // ─── Flow 3: Chat Completion via Playground ────────────────────────────────
  98  |   test('Flow 3: Chat Completion via Playground', async ({ page }) => {
  99  |     test.skip(!apiKeyValue, 'API key not available from Flow 2');
  100 | 
  101 |     // Test chat completions via API (the actual inference test)
  102 |     const chatRes = await page.request.post('/v1/chat/completions', {
  103 |       headers: {
  104 |         'Authorization': `Bearer ${apiKeyValue}`,
  105 |         'Content-Type': 'application/json',
  106 |       },
  107 |       data: {
  108 |         model: 'default',
  109 |         messages: [{ role: 'user', content: 'Hello, what is your status?' }],
  110 |         max_tokens: 50,
  111 |       },
  112 |     });
  113 |     // Accept 200 (success) or 503 (model not loaded) in mock mode
  114 |     expect([200, 503]).toContain(chatRes.status());
  115 | 
  116 |     // If 200, verify response structure
  117 |     if (chatRes.status() === 200) {
  118 |       const chatData = await chatRes.json();
  119 |       expect(chatData.choices).toBeDefined();
  120 |       expect(chatData.choices.length).toBeGreaterThan(0);
  121 |     }
  122 | 
  123 |     // Verify the playground page loads correctly in the portal
  124 |     await portalLogin(page, apiKeyValue, 'playground.html');
  125 |     await expect(page.locator('#pgPrompt')).toBeVisible({ timeout: 10000 });
  126 |     await expect(page.locator('#pgRun')).toBeVisible();
  127 |   });
  128 | 
  129 |   // ─── Flow 4: RAG Document Upload & Semantic Search ─────────────────────────
  130 |   test('Flow 4: RAG Document Upload & Semantic Search', async ({ page }) => {
  131 |     test.skip(!apiKeyValue, 'API key not available from Flow 2');
  132 | 
  133 |     // Create a temporary test file
  134 |     const tmpDir = path.resolve(__dirname, '..');
  135 |     const filePath = path.join(tmpDir, 'rag_test_doc.txt');
  136 |     fs.writeFileSync(filePath, 'Este é um documento de teste RAG sobre infraestrutura inteligente de IA e modelos de linguagem.');
  137 | 
  138 |     try {
  139 |       // Upload via API
  140 |       const uploadRes = await page.request.post('/v1/rag/documents', {
  141 |         headers: { 'Authorization': `Bearer ${apiKeyValue}` },
  142 |         multipart: {
  143 |           file: {
  144 |             name: 'rag_test_doc.txt',
  145 |             mimeType: 'text/plain',
  146 |             buffer: fs.readFileSync(filePath),
  147 |           },
  148 |         },
  149 |       });
  150 |       // Accept 200/201 (success) or 501/503 (RAG not fully configured in test mode)
  151 |       expect([200, 201, 400, 501, 503]).toContain(uploadRes.status());
  152 | 
  153 |       // If upload succeeded, test semantic search via API
  154 |       if (uploadRes.status() === 200 || uploadRes.status() === 201) {
  155 |         const searchRes = await page.request.post('/v1/rag/query', {
  156 |           headers: {
  157 |             'Authorization': `Bearer ${apiKeyValue}`,
  158 |             'Content-Type': 'application/json',
  159 |           },
  160 |           data: { query: 'infraestrutura inteligente', top_k: 3 },
  161 |         });
  162 |         expect([200, 501, 503]).toContain(searchRes.status());
  163 |       }
```