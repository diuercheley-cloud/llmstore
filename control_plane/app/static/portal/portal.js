(function () {
  const page = document.body.dataset.page || 'home';
  const pageRoutes = {
    overview: 'index.html',
    home: 'index.html',
    'api-keys': 'keys.html',
    usage: 'usage.html',
    invoices: 'invoices.html',
    wallet: 'wallet.html',
    rag: 'rag.html',
    playground: 'playground.html',
    models: 'models.html',
    plans: 'plans.html',
    trust: 'trust.html',
    audit: 'audit.html',
    disputes: 'disputes.html',
    examples: 'examples.html'
  };

  const navEntries = [
    ['home', 'Hub'],
    ['keys', 'API Keys'],
    ['usage', 'Uso'],
    ['invoices', 'Faturas'],
    ['wallet', 'Wallet'],
    ['rag', 'RAG'],
    ['playground', 'Playground'],
    ['models', 'Modelos'],
    ['plans', 'Planos'],
    ['trust', 'Trust'],
    ['audit', 'Audit'],
    ['disputes', 'Disputas'],
    ['examples', 'Examples']
  ];

  const state = {
    apiKey: '',
    client: null,
    models: [],
    demoMode: false
  };

  const els = {
    loginOverlay: document.getElementById('loginOverlay'),
    loginKey: document.getElementById('loginKey'),
    doLogin: document.getElementById('doLogin'),
    rememberMe: document.getElementById('rememberMe'),
    logout: document.getElementById('logout'),
    sidebarClientName: document.getElementById('sidebarClientName'),
    welcomeName: document.getElementById('welcomeName'),
    headerStatusBadge: document.getElementById('headerStatusBadge'),
    headerPlanName: document.getElementById('headerPlanName'),
    overviewAccountDetails: document.getElementById('overviewAccountDetails'),
    overviewBillingDetails: document.getElementById('overviewBillingDetails'),
    overviewUsageSnapshot: document.getElementById('overviewUsageSnapshot'),
    overviewQuickStats: document.getElementById('overviewQuickStats'),
    viewInvoicesBtn: document.getElementById('viewInvoicesBtn'),
    demoModeNotice: document.getElementById('demoModeNotice'),
    createNewKey: document.getElementById('createNewKey'),
    newKeyModal: document.getElementById('newKeyModal'),
    newKeyName: document.getElementById('newKeyName'),
    confirmNewKey: document.getElementById('confirmNewKey'),
    cancelNewKey: document.getElementById('cancelNewKey'),
    keyDisplayArea: document.getElementById('keyDisplayArea'),
    newKeySecret: document.getElementById('newKeySecret'),
    pgModelSelect: document.getElementById('pgModelSelect'),
    pgMaxTokens: document.getElementById('pgMaxTokens'),
    pgPrompt: document.getElementById('pgPrompt'),
    pgEstimate: document.getElementById('pgEstimate'),
    pgRun: document.getElementById('pgRun'),
    pgResponse: document.getElementById('pgResponse'),
    pgStats: document.getElementById('pgStats'),
    btnRagUpload: document.getElementById('btnRagUpload'),
    ragFileUpload: document.getElementById('ragFileUpload'),
    btnRagQuery: document.getElementById('btnRagQuery'),
    ragQueryInput: document.getElementById('ragQueryInput'),
    ragQueryResponse: document.getElementById('ragQueryResponse'),
    ragQuerySources: document.getElementById('ragQuerySources'),
    toast: document.getElementById('toast')
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function showToast(msg) {
    if (!els.toast) return;
    els.toast.textContent = msg;
    els.toast.style.display = 'block';
    setTimeout(() => {
      if (els.toast) els.toast.style.display = 'none';
    }, 2000);
  }

  function formatDateTime(value) {
    if (!value) return '-';
    return new Date(value).toLocaleString();
  }

  function formatDate(value) {
    if (!value) return '-';
    return new Date(value).toLocaleDateString();
  }

  function formatMoney(currency, amount) {
    const numeric = Number(amount || 0);
    return `${esc(currency || 'BRL')} ${numeric.toFixed(2)}`;
  }

  function toNumber(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
  }

  function percent(part, total) {
    if (!total) return 0;
    return Math.min(100, (part / total) * 100);
  }

  function formatTokenLimit(value) {
    return value == null ? 'Ilimitado' : Number(value).toLocaleString();
  }

  function formatTokenUsage(used, quota) {
    return quota == null
      ? `${Number(used || 0).toLocaleString()} / Ilimitado`
      : `${Number(used || 0).toLocaleString()} / ${Number(quota).toLocaleString()} tokens`;
  }

  function renderEmpty(message, colSpan) {
    if (colSpan) {
      return `<tr><td colspan="${colSpan}" class="muted-cell">${esc(message)}</td></tr>`;
    }
    return `<div class="empty-state">${esc(message)}</div>`;
  }

  function goToPage(pageKey) {
    const next = pageRoutes[pageKey];
    if (next) window.location.href = next;
  }

  function activateNav() {
    document.querySelectorAll('[data-page-link]').forEach((item) => {
      item.classList.toggle('active', item.dataset.pageLink === page);
    });
  }

  function enhanceNavigation() {
    const nav = document.querySelector('aside nav');
    if (!nav) return;
    const seen = new Set(Array.from(nav.querySelectorAll('[data-page-link]')).map((item) => item.dataset.pageLink));
    navEntries.forEach(([key, label]) => {
      if (seen.has(key)) return;
      const link = document.createElement('a');
      link.className = 'nav-item';
      link.dataset.pageLink = key;
      link.href = pageRoutes[key];
      link.textContent = label;
      nav.appendChild(link);
    });
  }

  window.switchTab = goToPage;
  window.copyToClipboard = (id) => {
    const el = byId(id);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent).then(() => showToast('Copiado!'));
  };

  function extractErrorMessage(payload, fallbackText) {
    if (!payload) return fallbackText;
    if (typeof payload === 'string') return payload;
    if (payload.error && payload.error.message) return payload.error.message;
    if (payload.detail && typeof payload.detail === 'string') return payload.detail;
    if (payload.detail && payload.detail.message) return payload.detail.message;
    return fallbackText;
  }

  function portalFriendlyError(status, payload, fallbackText) {
    const message = extractErrorMessage(payload, fallbackText);
    const normalized = (message || '').toLowerCase();
    if (status === 403 && normalized.includes('not allowed for this api key')) {
      return `Esta API key esta restrita por IP. O backend recusou o acesso do IP atual. Detalhe: ${message}`;
    }
    if (status === 402 || normalized.includes('billing_suspended')) {
      return 'Seu acesso foi bloqueado por faturamento pendente. Regularize as faturas para voltar a usar a API.';
    }
    if (status === 429 && normalized.includes('quota')) {
      return 'A quota do cliente foi atingida. Revise o consumo ou solicite recarga/upgrade.';
    }
    if (status === 429 && normalized.includes('rate')) {
      return 'O rate limit atual foi atingido. Aguarde alguns instantes e tente novamente.';
    }
    if (status === 413) {
      return 'O prompt excede o limite de contexto permitido para este cliente.';
    }
    return message || fallbackText || 'Falha na requisição.';
  }

  async function apiFetch(path, options = {}) {
    const headers = { ...options.headers };
    if (state.apiKey) headers.Authorization = `Bearer ${state.apiKey}`;
    if (headers['Content-Type'] === undefined && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    if (options.body instanceof FormData) delete headers['Content-Type'];
    const response = await fetch(path, { ...options, headers });
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) throw new Error(portalFriendlyError(response.status, payload, response.statusText));
    return payload;
  }

  async function apiFetchBlob(path, options = {}) {
    const headers = { ...options.headers };
    if (state.apiKey) headers.Authorization = `Bearer ${state.apiKey}`;
    const response = await fetch(path, { ...options, headers });
    if (!response.ok) {
      const contentType = response.headers.get('content-type') || '';
      const payload = contentType.includes('application/json') ? await response.json() : await response.text();
      throw new Error(portalFriendlyError(response.status, payload, response.statusText));
    }
    return {
      blob: await response.blob(),
      filename: (response.headers.get('content-disposition') || '').match(/filename=\"([^\"]+)\"/)?.[1] || 'download'
    };
  }

  function readApiKeyFromUrl() {
    const searchParams = new URLSearchParams(window.location.search);
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
    const hashParams = new URLSearchParams(hash);
    return (
      searchParams.get('api_key') ||
      searchParams.get('apiKey') ||
      hashParams.get('api_key') ||
      hashParams.get('apiKey') ||
      ''
    ).trim();
  }

  function clearApiKeyFromUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete('api_key');
    url.searchParams.delete('apiKey');
    if (url.hash) {
      const hash = url.hash.startsWith('#') ? url.hash.slice(1) : url.hash;
      const hashParams = new URLSearchParams(hash);
      hashParams.delete('api_key');
      hashParams.delete('apiKey');
      const nextHash = hashParams.toString();
      url.hash = nextHash ? `#${nextHash}` : '';
    }
    window.history.replaceState({}, document.title, url.toString());
  }

  async function attemptLogin(key, { persist = false } = {}) {
    if (!key) return;
    state.apiKey = key.trim();
    if (els.loginKey) els.loginKey.value = state.apiKey;
    try {
      await initPortal();
      if (persist) localStorage.setItem('portalApiKey', state.apiKey);
      if (els.loginOverlay) els.loginOverlay.style.display = 'none';
      clearApiKeyFromUrl();
    } catch (err) {
      state.apiKey = '';
      if (persist) localStorage.removeItem('portalApiKey');
      throw err;
    }
  }

  async function initPortal() {
    // Authentication must depend only on the identity endpoint. Optional portal
    // modules can be temporarily unavailable without rejecting a valid API key.
    const me = await apiFetch('/portal/me');
    const [usageResult, modelsResult] = await Promise.allSettled([
      apiFetch('/portal/usage'),
      apiFetch('/portal/models')
    ]);
    const usage = usageResult.status === 'fulfilled' ? usageResult.value : {
      requests_today: 0,
      tokens_month: 0,
      wallet_balance_brl: 0,
      monthly_usage: { used_tokens: 0, quota: null },
      quota_remaining: { monthly_tokens: null },
      invoice_preview: { currency: 'BRL', total_estimated: 0 }
    };
    const models = modelsResult.status === 'fulfilled' ? modelsResult.value : [];
    state.client = me;
    state.models = models;
    state.demoMode = me.demo_mode === true;

    if (els.sidebarClientName) els.sidebarClientName.textContent = me.name;
    if (els.welcomeName) els.welcomeName.textContent = me.name;
    if (els.headerPlanName) els.headerPlanName.textContent = me.plan.name;
    if (els.headerStatusBadge) {
      els.headerStatusBadge.textContent = me.billing_status;
      els.headerStatusBadge.className = `badge ${me.is_blocked ? 'badge-blocked' : (me.billing_status === 'active' ? 'badge-active' : 'badge-warning')}`;
    }
    if (els.demoModeNotice) {
      els.demoModeNotice.style.display = state.demoMode ? 'block' : 'none';
    }

    renderOverview(me, usage);
    renderModelSelects();
    try {
      await loadPageData();
    } catch (error) {
      showToast(`Login concluído, mas um módulo do portal está indisponível: ${error.message}`);
    }
    if (usageResult.status === 'rejected' || modelsResult.status === 'rejected') {
      showToast('Login concluído. Alguns dados do portal estão temporariamente indisponíveis.');
    }
  }

  function renderOverview(me, usage) {
    if (els.overviewAccountDetails) {
      els.overviewAccountDetails.innerHTML = `
        <div class="field"><div class="field-label">ID do Cliente</div><div class="field-value"><code>${esc(me.id)}</code></div></div>
        <div class="field"><div class="field-label">Plano Atual</div><div class="field-value"><strong>${esc(me.plan.name)}</strong></div></div>
        <div class="field"><div class="field-label">Status da Conta</div><div class="field-value">${esc(me.billing_status.toUpperCase())}</div></div>
        <div class="field"><div class="field-label">Modelos Habilitados</div><div class="field-value">${state.models.length}</div></div>
      `;
    }
    if (els.overviewBillingDetails) {
      els.overviewBillingDetails.innerHTML = `
        <div class="field"><div class="field-label">Preco Mensal</div><div class="field-value">${formatMoney(me.plan.currency, me.plan.monthly_price)}</div></div>
        <div class="field"><div class="field-label">Proxima Fatura (Est.)</div><div class="field-value">${formatMoney(usage.invoice_preview.currency, usage.invoice_preview.total_estimated)}</div></div>
        <div class="field"><div class="field-label">Wallet</div><div class="field-value">${formatMoney('BRL', usage.wallet_balance_brl || 0)}</div></div>
      `;
    }
    if (els.overviewUsageSnapshot) {
      const m = usage.monthly_usage;
      const pct = percent(m.used_tokens, m.quota);
      els.overviewUsageSnapshot.innerHTML = `
        <div class="split-row">
          <span>${formatTokenUsage(m.used_tokens, m.quota)}</span>
          <span>${m.quota == null ? 'sem teto' : `${pct.toFixed(1)}%`}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      `;
    }
    if (els.overviewQuickStats) {
      els.overviewQuickStats.innerHTML = `
        <div class="summary-card">
          <div class="field-label">Requests Hoje</div>
          <div class="usage-num">${usage.requests_today.toLocaleString()}</div>
        </div>
        <div class="summary-card">
          <div class="field-label">Tokens no Mes</div>
          <div class="usage-num">${usage.tokens_month.toLocaleString()}</div>
        </div>
        <div class="summary-card">
          <div class="field-label">Quota Restante</div>
          <div class="usage-num">${usage.quota_remaining.monthly_tokens == null ? 'Ilimitado' : usage.quota_remaining.monthly_tokens.toLocaleString()}</div>
        </div>
        <div class="summary-card">
          <div class="field-label">Modelos</div>
          <div class="usage-num">${state.models.length}</div>
        </div>
      `;
    }
  }

  function renderModelSelects() {
    if (!els.pgModelSelect) return;
    els.pgModelSelect.innerHTML = state.models.map((m) => `<option value="${esc(m.id)}">${esc(m.display_name)} (${esc(m.id)})</option>`).join('');
  }

  async function loadPageData() {
    if (page === 'keys') return loadApiKeys();
    if (page === 'usage') {
      await loadUsageStats();
      return loadQosUsage();
    }
    if (page === 'invoices') return loadInvoices();
    if (page === 'wallet') return loadWallet();
    if (page === 'rag') return loadRagFiles();
    if (page === 'playground') return refreshPlaygroundEstimate();
    if (page === 'models') return loadModelsPage();
    if (page === 'plans') return loadPlansPage();
    if (page === 'trust') return loadTrustPage();
    if (page === 'audit') return loadAuditPage();
    if (page === 'disputes') return loadDisputesPage();
    if (page === 'examples') return loadExamplesPage();
  }

  async function loadApiKeys() {
    const tbody = byId('apiKeysList');
    if (!tbody) return;
    const keys = await apiFetch('/portal/api-keys');
    tbody.innerHTML = keys.length ? keys.map((k) => `
      <tr>
        <td><strong>${esc(k.name)}</strong></td>
        <td><code>${esc(k.masked_key)}</code></td>
        <td>${formatDate(k.created_at)}</td>
        <td>${k.last_used_at ? formatDateTime(k.last_used_at) : 'Nunca'}</td>
        <td>
          <button class="secondary" onclick="copyApiExample()">Copiar Exemplo</button>
          ${k.revoked_at ? '<span class="badge badge-blocked">Revogada</span>' : `<button class="danger" onclick="revokeKey('${k.id}')">Revogar</button>`}
        </td>
      </tr>
    `).join('') : renderEmpty('Nenhuma chave criada.', 5);
  }

  async function loadUsageStats() {
    const usageRequests = byId('usageRequestsTodayMonth');
    if (!usageRequests) return;
    const [usage, stats] = await Promise.all([
      apiFetch('/portal/usage'),
      apiFetch('/portal/usage-stats')
    ]);
    const m = usage.monthly_usage;
    byId('usageRequestsTodayMonth').textContent = `${usage.requests_today.toLocaleString()} / ${usage.requests_month.toLocaleString()}`;
    byId('usageTokensTodayMonth').textContent = `${usage.tokens_today.toLocaleString()} / ${usage.tokens_month.toLocaleString()}`;
    byId('usageMonthlyTokens').textContent = m.used_tokens.toLocaleString();
    byId('usageMonthlyLimit').textContent = `limite: ${formatTokenLimit(m.quota)}`;
    byId('usageMonthlyProgress').style.width = `${percent(m.used_tokens, m.quota)}%`;
    byId('usageQuotaRemaining').textContent = usage.quota_remaining.monthly_tokens == null ? 'Ilimitado' : usage.quota_remaining.monthly_tokens.toLocaleString();
    byId('usagePricingSummary').innerHTML = `
      <div class="field"><div class="field-label">Hoje</div><div class="field-value">${usage.customer_pricing.today_amount === null ? 'indisponivel' : `${usage.customer_pricing.currency} ${usage.customer_pricing.today_amount.toFixed(2)}`}</div></div>
      <div class="field"><div class="field-label">Mes</div><div class="field-value">${usage.customer_pricing.currency} ${usage.customer_pricing.month_amount.toFixed(2)}</div></div>
      <div class="field"><div class="field-label">Origem</div><div class="field-value">${esc(usage.customer_pricing.source)}</div></div>
    `;
    byId('usageRateLimit').innerHTML = `
      <div class="field"><div class="field-label">RPM</div><div class="field-value">${usage.rate_limit.requests_per_minute}</div></div>
      <div class="field"><div class="field-label">RPD</div><div class="field-value">${usage.rate_limit.requests_per_day || 'sem limite especifico'}</div></div>
    `;
    renderChart(stats.daily_usage || []);
    const modelUsageList = byId('modelUsageList');
    modelUsageList.innerHTML = (stats.model_usage || []).length ? (stats.model_usage || []).map((r) => `
      <tr>
        <td><code>${esc(r.model)}</code></td>
        <td>${r.requests.toLocaleString()}</td>
        <td>${r.tokens.toLocaleString()}</td>
      </tr>
    `).join('') : renderEmpty('Nenhum consumo por modelo encontrado.', 3);
  }

  function renderChart(data) {
    const chart = byId('dailyUsageChart');
    if (!chart) return;
    if (!data.length) {
      chart.innerHTML = '<div class="muted">Sem uso recente.</div>';
      return;
    }
    const maxTokens = Math.max(...data.map((d) => d.tokens), 1);
    chart.innerHTML = data.map((d) => {
      const height = (d.tokens / maxTokens) * 100;
      return `
        <div class="chart-bar" style="height:${height}%" data-label="${esc(d.day.substring(5))}">
          <div class="chart-tooltip">${esc(d.day)}: ${d.tokens.toLocaleString()} tokens</div>
        </div>
      `;
    }).join('');
  }

  async function loadQosUsage() {
    const tbody = byId('qosUsageTableBody');
    if (!tbody) return [];
    const records = await apiFetch('/portal/qos-billing');
    tbody.innerHTML = records.length ? records.map((r) => `
      <tr>
        <td>${formatDate(r.period_start)}</td>
        <td>${esc(r.qos_tier)}</td>
        <td>${toNumber(r.compute_seconds).toFixed(2)}s</td>
        <td>${toNumber(r.priority_slots_consumed).toFixed(2)}</td>
        <td><strong>R$ ${toNumber(r.billable_amount_brl).toFixed(4)}</strong></td>
        <td>${esc(r.status)}</td>
      </tr>
    `).join('') : renderEmpty('Nenhum consumo de QoS registrado no periodo.', 6);
    return records;
  }

  async function loadInvoices() {
    const invoicesList = byId('invoicesList');
    if (!invoicesList) return;
    const data = await apiFetch('/portal/invoices');
    const invoices = data.invoices || [];
    const payments = data.payments || [];
    const summary = byId('invoicesSummary');
    if (summary) {
      summary.textContent = data.local_billing_message
        ? `Modo de cobranca: ${data.local_billing_message}.`
        : 'Sem mensagem adicional de cobranca.';
    }
    invoicesList.innerHTML = invoices.length ? invoices.map((invoice) => `
      <tr>
        <td><code>${esc(invoice.id.slice(0, 8))}</code></td>
        <td><span class="badge ${invoice.status === 'paid' ? 'badge-active' : invoice.status === 'pending' ? 'badge-warning' : 'badge-blocked'}">${esc(invoice.status)}</span></td>
        <td>${esc(invoice.period_start)} a ${esc(invoice.period_end)}</td>
        <td>${esc(invoice.currency)} ${Number(invoice.total_amount).toFixed(2)}</td>
        <td>${invoice.due_at ? formatDate(invoice.due_at) : '-'}</td>
        <td class="inline-actions">
          <button class="secondary" onclick="downloadInvoice('${invoice.id}', 'json')">JSON</button>
          <button class="secondary" onclick="downloadInvoice('${invoice.id}', 'html')">HTML</button>
          ${invoice.status !== 'paid' ? `<button class="secondary" onclick="simulateInvoicePayment('${invoice.id}')">Simular Pagto</button>` : ''}
        </td>
      </tr>
    `).join('') : renderEmpty('Nenhuma fatura encontrada.', 6);

    const paymentsTable = byId('invoicePaymentsList');
    if (paymentsTable) {
      paymentsTable.innerHTML = payments.length ? payments.map((payment) => `
        <tr>
          <td><code>${esc(payment.id.slice(0, 8))}</code></td>
          <td>${payment.invoice_id ? `<code>${esc(payment.invoice_id.slice(0, 8))}</code>` : '-'}</td>
          <td>${esc(payment.status)}</td>
          <td>${formatMoney(payment.currency, payment.amount)}</td>
          <td>${esc(payment.payment_method || '-')}</td>
          <td>${payment.paid_at ? formatDateTime(payment.paid_at) : '-'}</td>
        </tr>
      `).join('') : renderEmpty('Nenhum pagamento registrado.', 6);
    }
  }

  async function loadWallet() {
    const balance = byId('walletBalance');
    if (!balance) return;
    const [wallet, topups] = await Promise.all([
      apiFetch('/portal/wallet'),
      apiFetch('/portal/wallet/topups')
    ]);
    balance.textContent = `BRL ${toNumber(wallet.balance_brl).toFixed(2)}`;
    byId('walletAvailable').textContent = `disponivel: BRL ${toNumber(wallet.available_brl).toFixed(2)}`;
    byId('walletReserved').textContent = `BRL ${toNumber(wallet.reserved_brl).toFixed(2)}`;
    byId('walletConsumptionEstimate').textContent = `consumo estimado: BRL ${toNumber(wallet.consumption_estimate_brl).toFixed(2)}`;
    const warning = byId('walletWarning');
    warning.style.display = wallet.low_balance ? 'block' : 'none';
    warning.textContent = wallet.low_balance_message || '';
    byId('walletTransactions').innerHTML = (wallet.transactions || []).length ? wallet.transactions.map((tx) => `
      <tr>
        <td>${tx.created_at ? formatDateTime(tx.created_at) : '-'}</td>
        <td>${esc(tx.type)}</td>
        <td>BRL ${Number(tx.amount_brl).toFixed(2)}</td>
        <td>BRL ${Number(tx.balance_after_brl).toFixed(2)}</td>
        <td>${tx.reference_type ? `${esc(tx.reference_type)}:${esc(tx.reference_id || '-')}` : '-'}</td>
      </tr>
    `).join('') : renderEmpty('Nenhuma transacao registrada.', 5);

    const topupTable = byId('walletTopups');
    if (topupTable) {
      topupTable.innerHTML = topups.length ? topups.map((item) => `
        <tr>
          <td><code>${esc(String(item.id || '').slice(0, 8))}</code></td>
          <td>BRL ${toNumber(item.amount_brl).toFixed(2)}</td>
          <td>${esc(item.status || '-')}</td>
          <td>${esc(item.idempotency_key || '-')}</td>
          <td>${formatDateTime(item.created_at)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhuma recarga estruturada encontrada.', 5);
    }
  }

  function estimateTokensFromPrompt(prompt) {
    return Math.max(1, Math.ceil((prompt || '').length / 4));
  }

  async function refreshPlaygroundEstimate() {
    if (!els.pgEstimate || !els.pgPrompt || !els.pgMaxTokens) return;
    const promptTokens = estimateTokensFromPrompt(els.pgPrompt.value);
    els.pgEstimate.textContent = `Estimativa: ~${promptTokens} tokens de prompt + ate ${Number(els.pgMaxTokens.value || 0)} de saida`;
  }

  async function loadRagFiles() {
    const table = byId('ragFilesList');
    if (!table) return;
    const [files, usage, vault, history, holds, trust] = await Promise.all([
      apiFetch('/client/rag/documents'),
      apiFetch('/client/rag/usage'),
      apiFetch('/portal/rag/vault'),
      apiFetch('/portal/rag/retrieval-history'),
      apiFetch('/portal/rag/legal-holds'),
      apiFetch('/portal/rag/trust-status')
    ]);
    table.innerHTML = (files.data || []).length ? (files.data || []).map((f) => `
      <tr>
        <td><strong>${esc(f.original_filename)}</strong><br><small>${(f.file_size_bytes / 1024).toFixed(1)}KB</small></td>
        <td><span class="badge ${f.status === 'indexed' ? 'badge-active' : (f.status === 'failed' ? 'badge-blocked' : 'badge-warning')}">${esc(f.status)}</span></td>
        <td>${f.page_count || '-'}</td>
        <td><button class="danger" onclick="deleteFile('${f.id}')">Excluir</button></td>
      </tr>
    `).join('') : renderEmpty('Nenhum documento enviado.', 4);
    const u = usage.usage;
    const l = usage.limits;
    byId('ragStatsDocs').textContent = `${u.documents_count} / ${l.max_documents || '∞'}`;
    byId('ragProgressDocsFill').style.width = l.max_documents ? `${percent(u.documents_count, l.max_documents)}%` : '0%';
    byId('ragStatsStorage').textContent = `${u.storage_mb.toFixed(1)} / ${l.max_storage_mb || '∞'}`;
    byId('ragProgressStorageFill').style.width = l.max_storage_mb ? `${percent(u.storage_mb, l.max_storage_mb)}%` : '0%';
    byId('ragStatsQueries').textContent = `${u.queries_month} / ${l.max_queries_per_month || '∞'}`;
    byId('ragProgressQueriesFill').style.width = l.max_queries_per_month ? `${percent(u.queries_month, l.max_queries_per_month)}%` : '0%';

    const vaultSummary = byId('ragVaultSummary');
    if (vaultSummary) {
      vaultSummary.innerHTML = `
        <div class="field"><div class="field-label">Vault</div><div class="field-value">${esc(vault.vault_name || 'nao provisionado')}</div></div>
        <div class="field"><div class="field-label">Documentos Assinados</div><div class="field-value">${vault.signed_documents || 0}</div></div>
        <div class="field"><div class="field-label">Legal Holds Ativos</div><div class="field-value">${vault.active_legal_holds || 0}</div></div>
      `;
    }
    const historyTable = byId('ragRetrievalHistory');
    if (historyTable) {
      historyTable.innerHTML = history.length ? history.map((item) => `
        <tr>
          <td>${formatDateTime(item.created_at)}</td>
          <td>${esc(item.query_text || '-')}</td>
          <td>${esc(item.retrieval_mode || '-')}</td>
          <td>${esc(item.retrieved_documents_count || 0)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhum retrieval audit encontrado.', 4);
    }
    const holdsTable = byId('ragLegalHolds');
    if (holdsTable) {
      holdsTable.innerHTML = holds.length ? holds.map((item) => `
        <tr>
          <td>${esc(item.document_id || 'vault')}</td>
          <td>${esc(item.reason || '-')}</td>
          <td>${item.active ? 'ativo' : 'inativo'}</td>
          <td>${formatDateTime(item.created_at)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhum legal hold ativo.', 4);
    }
    const trustTable = byId('ragTrustStatus');
    if (trustTable) {
      trustTable.innerHTML = trust.length ? trust.map((item) => `
        <tr>
          <td>${esc(item.document_title || '-')}</td>
          <td>${item.signed_document ? 'assinado' : 'sem assinatura'}</td>
          <td>${esc(item.trust_state || 'unknown')}</td>
          <td>${formatDateTime(item.created_at)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhum documento com trust-status retornado.', 4);
    }
  }

  async function loadModelsPage() {
    const table = byId('modelsTableBody');
    if (!table) return;
    const models = state.models.length ? state.models : await apiFetch('/portal/models');
    const summary = byId('modelsSummary');
    if (summary) {
      const attested = models.filter((model) => model.attestation_summary).length;
      summary.innerHTML = `
        <div class="summary-card"><div class="field-label">Modelos Visiveis</div><div class="usage-num">${models.length}</div></div>
        <div class="summary-card"><div class="field-label">Com Attestation</div><div class="usage-num">${attested}</div></div>
        <div class="summary-card"><div class="field-label">Plano</div><div class="usage-num">${esc(state.client.plan.name)}</div></div>
      `;
    }
    table.innerHTML = models.length ? models.map((model) => `
      <tr>
        <td><strong>${esc(model.display_name)}</strong><br><code>${esc(model.id)}</code></td>
        <td>${esc(model.provider || '-')}</td>
        <td>${esc(model.context_length || '-')}</td>
        <td>${esc(model.trust_state_runtime || 'unknown')}</td>
        <td>${model.attestation_summary ? esc(model.attestation_summary.attestation_status || 'available') : '-'}</td>
      </tr>
    `).join('') : renderEmpty('Nenhum modelo habilitado para este cliente.', 5);
  }

  async function loadPlansPage({ publicCatalog = false } = {}) {
    const payload = await apiFetch(publicCatalog ? '/public/plans' : '/portal/plans');
    const plans = Array.isArray(payload) ? payload : (payload.plans || []);
    const table = byId('plansTableBody');
    if (!table) return;
    const currentPlan = state.client ? state.client.plan : null;
    table.innerHTML = plans.length ? plans.map((plan) => `
      <tr>
        <td><strong>${esc(plan.name)}</strong><br><code>${esc(plan.code)}</code></td>
        <td>${formatMoney(plan.currency, plan.monthly_price)}</td>
        <td>${plan.rate_limit_rpm || plan.rate_limit_per_minute || '-'}</td>
        <td>${formatTokenLimit(plan.monthly_token_quota)}</td>
        <td>${currentPlan && currentPlan.code === plan.code
          ? '<span class="badge badge-active">Atual</span>'
          : (state.apiKey ? `<button onclick="upgradePlan('${plan.code}')">Migrar</button>` : '<span class="badge">Entre para migrar</span>')}</td>
      </tr>
    `).join('') : renderEmpty('Nenhum plano ativo encontrado.', 5);
  }

  async function loadTrustPage() {
    const [
      reproducibility,
      receipts,
      proofs,
      correlations,
      trustGraph,
      workflowExecutions,
      replaySessions
    ] = await Promise.all([
      apiFetch('/portal/inference/reproducibility'),
      apiFetch('/portal/inference/receipts'),
      apiFetch('/portal/inference/proofs/proofs'),
      apiFetch('/portal/operations/correlations/'),
      apiFetch('/portal/operations/correlations/trust-graph'),
      apiFetch('/portal/workflows/governance/executions'),
      apiFetch('/portal/workflows/replay/sessions')
    ]);

    const summary = byId('trustSummary');
    if (summary) {
      summary.innerHTML = `
        <div class="summary-card"><div class="field-label">Receipts</div><div class="usage-num">${(receipts.items || []).length}</div></div>
        <div class="summary-card"><div class="field-label">Proofs</div><div class="usage-num">${proofs.count || 0}</div></div>
        <div class="summary-card"><div class="field-label">Correlations</div><div class="usage-num">${correlations.length}</div></div>
        <div class="summary-card"><div class="field-label">Replay Sessions</div><div class="usage-num">${(replaySessions.items || []).length}</div></div>
      `;
    }

    const reproTable = byId('reproducibilityTableBody');
    if (reproTable) {
      reproTable.innerHTML = reproducibility.items?.length ? reproducibility.items.map((item) => `
        <tr>
          <td>${formatDateTime(item.created_at)}</td>
          <td>${esc(item.model_name || '-')}</td>
          <td>${esc(item.backend_name || '-')}</td>
          <td>${item.replay_supported ? 'sim' : 'nao'}</td>
          <td>${esc(item.runtime_provenance_summary?.runtime_engine || '-')}</td>
        </tr>
      `).join('') : renderEmpty('Nenhum registro de reproducibility encontrado.', 5);
    }

    const receiptsTable = byId('receiptsTableBody');
    if (receiptsTable) {
      receiptsTable.innerHTML = receipts.items?.length ? receipts.items.map((item) => `
        <tr>
          <td><code>${esc(item.id.slice(0, 8))}</code></td>
          <td>${formatDateTime(item.created_at)}</td>
          <td>${esc(item.model_name || '-')}</td>
          <td>${esc(item.backend_name || '-')}</td>
          <td>${esc(item.verification_status || '-')}</td>
          <td><button class="secondary" onclick="verifyReceipt('${item.id}')">Verificar</button></td>
        </tr>
      `).join('') : renderEmpty('Nenhum receipt encontrado.', 6);
    }

    const proofsTable = byId('proofsTableBody');
    if (proofsTable) {
      proofsTable.innerHTML = proofs.items?.length ? proofs.items.map((item) => `
        <tr>
          <td><code>${esc(item.id.slice(0, 8))}</code></td>
          <td>${esc(item.proof_type)}</td>
          <td><code>${esc((item.proof_hash || '').slice(0, 16))}</code></td>
          <td>${esc(item.verification_status || '-')}</td>
          <td>${formatDateTime(item.created_at)}</td>
          <td><button class="secondary" onclick="verifyProof('${item.id}')">Verificar</button></td>
        </tr>
      `).join('') : renderEmpty('Nenhuma proof encontrada.', 6);
    }

    const correlationsTable = byId('correlationsTableBody');
    if (correlationsTable) {
      correlationsTable.innerHTML = correlations.length ? correlations.map((item) => `
        <tr>
          <td>${formatDateTime(item.created_at)}</td>
          <td>${esc(item.correlation_type || '-')}</td>
          <td>${esc((item.involved_domains || []).join(', ') || '-')}</td>
          <td>${toNumber(item.correlation_score).toFixed(2)}</td>
          <td>${toNumber(item.confidence).toFixed(2)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhuma correlation disponivel.', 5);
    }

    const graph = byId('trustGraphSummary');
    if (graph) {
      graph.innerHTML = `<pre class="code-block">${esc(JSON.stringify(trustGraph, null, 2))}</pre>`;
    }

    const workflowsTable = byId('workflowGovernanceTableBody');
    if (workflowsTable) {
      workflowsTable.innerHTML = workflowExecutions.items?.length ? workflowExecutions.items.map((item) => `
        <tr>
          <td><code>${esc(item.id.slice(0, 8))}</code></td>
          <td>${esc(item.status || '-')}</td>
          <td>${esc(item.governance_status || '-')}</td>
          <td>${esc(item.replay_status || '-')}</td>
          <td><code>${esc((item.governance_ledger_hash || '').slice(0, 16) || '-')}</code></td>
        </tr>
      `).join('') : renderEmpty('Nenhuma execucao de workflow encontrada.', 5);
    }

    const replayTable = byId('replaySessionsTableBody');
    if (replayTable) {
      replayTable.innerHTML = replaySessions.items?.length ? replaySessions.items.map((item) => `
        <tr>
          <td><code>${esc(item.id.slice(0, 8))}</code></td>
          <td><code>${esc(item.original_execution_id.slice(0, 8))}</code></td>
          <td>${esc(item.session_status || '-')}</td>
          <td>${item.mismatch_detected || item.policy_mismatch_detected ? 'sim' : 'nao'}</td>
          <td><code>${esc((item.report_hash || '').slice(0, 16) || '-')}</code></td>
        </tr>
      `).join('') : renderEmpty('Nenhuma replay session encontrada.', 5);
    }
  }

  async function loadAuditPage() {
    const [
      chains,
      evidence,
      attestations,
      exceptions,
      reports,
      logs,
      federation
    ] = await Promise.all([
      apiFetch('/portal/audit/approval-chains'),
      apiFetch('/portal/audit/evidence-packages'),
      apiFetch('/portal/audit/attestations'),
      apiFetch('/portal/audit/exceptions'),
      apiFetch('/portal/audit/reports'),
      apiFetch('/portal/audit/access-logs'),
      apiFetch('/portal/governance-federation-summary')
    ]);

    const summary = byId('auditSummary');
    if (summary) {
      summary.innerHTML = `
        <div class="summary-card"><div class="field-label">Approval Chains</div><div class="usage-num">${(chains.items || []).length}</div></div>
        <div class="summary-card"><div class="field-label">Evidence</div><div class="usage-num">${(evidence.items || []).length}</div></div>
        <div class="summary-card"><div class="field-label">Attestations</div><div class="usage-num">${(attestations.items || []).length}</div></div>
        <div class="summary-card"><div class="field-label">Exceptions</div><div class="usage-num">${(exceptions.items || []).length}</div></div>
      `;
    }

    const federationBox = byId('federationSummary');
    if (federationBox) {
      federationBox.innerHTML = `
        <div class="field"><div class="field-label">Policies Replicadas</div><div class="field-value">${federation.policies_replicated || 0}</div></div>
        <div class="field"><div class="field-label">Eventos Federados</div><div class="field-value">${federation.audit_events_federated || 0}</div></div>
        <div class="field"><div class="field-label">Consistency</div><div class="field-value">${esc(federation.consistency_status || '-')}</div></div>
        <div class="field"><div class="field-label">Regions</div><div class="field-value">${federation.region_coverage || 0}</div></div>
      `;
    }

    renderAuditTable('approvalChainsTableBody', chains.items, (item) => `
      <tr>
        <td>${esc(item.control_area || '-')}</td>
        <td>${esc(item.status || '-')}</td>
        <td>${esc(item.actor_email || item.actor_name || '-')}</td>
        <td>${formatDateTime(item.created_at)}</td>
      </tr>
    `, 4, 'Nenhuma approval chain encontrada.');
    renderAuditTable('evidencePackagesTableBody', evidence.items, (item) => `
      <tr>
        <td>${esc(item.evidence_type || '-')}</td>
        <td>${esc(item.control_area || '-')}</td>
        <td>${esc(item.status || '-')}</td>
        <td>${formatDateTime(item.created_at)}</td>
      </tr>
    `, 4, 'Nenhum evidence package encontrado.');
    renderAuditTable('attestationsTableBody', attestations.items, (item) => `
      <tr>
        <td>${esc(item.attestation_type || '-')}</td>
        <td>${esc(item.status || '-')}</td>
        <td>${esc(item.control_area || '-')}</td>
        <td>${formatDateTime(item.created_at)}</td>
      </tr>
    `, 4, 'Nenhuma attestation encontrada.');
    renderAuditTable('exceptionsTableBody', exceptions.items, (item) => `
      <tr>
        <td>${esc(item.exception_type || '-')}</td>
        <td>${esc(item.severity || '-')}</td>
        <td>${esc(item.status || '-')}</td>
        <td>${formatDateTime(item.created_at)}</td>
      </tr>
    `, 4, 'Nenhuma exception encontrada.');
    renderAuditTable('reportsTableBody', reports.items, (item) => `
      <tr>
        <td>${esc(item.report_type || '-')}</td>
        <td>${esc(item.export_format || '-')}</td>
        <td><code>${esc((item.immutable_hash || '').slice(0, 16) || '-')}</code></td>
        <td>${formatDateTime(item.created_at)}</td>
        <td><button class="secondary" onclick="downloadAuditReport('${item.id}')">Download</button></td>
      </tr>
    `, 5, 'Nenhum report gerado.');
    renderAuditTable('accessLogsTableBody', logs.items, (item) => `
      <tr>
        <td>${formatDateTime(item.created_at)}</td>
        <td>${esc(item.actor_email || item.actor_name || '-')}</td>
        <td>${esc(item.action || '-')}</td>
        <td>${esc(item.resource_type || '-')}</td>
      </tr>
    `, 4, 'Nenhum access-log disponivel.');
  }

  function renderAuditTable(id, items, renderRow, colSpan, emptyMessage) {
    const table = byId(id);
    if (!table) return;
    table.innerHTML = items?.length ? items.map(renderRow).join('') : renderEmpty(emptyMessage, colSpan);
  }

  async function loadDisputesPage() {
    const [disputes, invoiceData, qosRecords, wallet] = await Promise.all([
      apiFetch('/portal/billing/disputes'),
      apiFetch('/portal/invoices'),
      apiFetch('/portal/qos-billing'),
      apiFetch('/portal/wallet')
    ]);

    const table = byId('disputesTableBody');
    if (table) {
      table.innerHTML = disputes.length ? disputes.map((item) => `
        <tr>
          <td><code>${esc(item.id.slice(0, 8))}</code></td>
          <td>${esc(item.dispute_type)}</td>
          <td>${formatMoney('BRL', item.claimed_amount_brl)}</td>
          <td>${esc(item.status)}</td>
          <td>${formatDateTime(item.created_at)}</td>
        </tr>
      `).join('') : renderEmpty('Nenhuma disputa aberta.', 5);
    }

    const invoiceSelect = byId('disputeInvoiceId');
    if (invoiceSelect) {
      invoiceSelect.innerHTML = '<option value="">Nenhuma</option>' + (invoiceData.invoices || []).map((invoice) => `<option value="${invoice.id}">${invoice.id.slice(0, 8)} · ${invoice.status} · ${invoice.currency} ${Number(invoice.total_amount).toFixed(2)}</option>`).join('');
    }
    const qosSelect = byId('disputeQosRecordId');
    if (qosSelect) {
      qosSelect.innerHTML = '<option value="">Nenhuma</option>' + qosRecords.map((record) => `<option value="${record.id || ''}">${record.qos_tier} · R$ ${toNumber(record.billable_amount_brl).toFixed(4)}</option>`).join('');
    }
    const walletSelect = byId('disputeWalletTransactionId');
    if (walletSelect) {
      walletSelect.innerHTML = '<option value="">Nenhuma</option>' + (wallet.transactions || []).map((tx) => `<option value="${tx.id}">${tx.type} · BRL ${Number(tx.amount_brl).toFixed(2)} · ${formatDateTime(tx.created_at)}</option>`).join('');
    }
  }

  async function loadExamplesPage() {
    const container = byId('examplesContent');
    if (!container) return;
    const examples = await apiFetch('/portal/examples');
    const entries = Object.entries(examples.snippets || {});
    container.innerHTML = `
      <section>
        <h3>Base URL</h3>
        <pre class="code-block">${esc(examples.base_url || '/v1')}</pre>
      </section>
      ${entries.map(([name, snippet]) => `
        <section>
          <h3>${esc(name)}</h3>
          <pre class="code-block">${esc(snippet)}</pre>
        </section>
      `).join('')}
    `;
  }

  window.revokeKey = async (id) => {
    if (!confirm('Tem certeza que deseja revogar esta chave? Esta acao e irreversivel.')) return;
    await apiFetch(`/portal/api-keys/${id}`, { method: 'DELETE' });
    showToast('Chave revogada.');
    await loadApiKeys();
  };

  window.copyApiExample = async () => {
    const example = `curl -X POST /v1/chat/completions -H "Authorization: Bearer ${state.apiKey}" -H "Content-Type: application/json" -d '{"model":"default","messages":[{"role":"user","content":"Teste da chave"}]}'`;
    await navigator.clipboard.writeText(example);
    showToast('Exemplo copiado.');
  };

  window.downloadInvoice = async (invoiceId, format) => {
    const result = await apiFetchBlob(`/portal/invoices/${invoiceId}/download?format=${format}`);
    const url = URL.createObjectURL(result.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  window.simulateInvoicePayment = async (invoiceId) => {
    await apiFetch(`/portal/simulate-payment/${invoiceId}`, { method: 'POST' });
    showToast('Pagamento simulado com sucesso.');
    await loadInvoices();
  };

  window.deleteFile = async (id) => {
    if (!confirm('Excluir documento?')) return;
    await apiFetch(`/client/rag/documents/${id}`, { method: 'DELETE' });
    await loadRagFiles();
  };

  window.upgradePlan = async (planCode) => {
    await apiFetch('/portal/upgrade', {
      method: 'POST',
      body: JSON.stringify({ plan_code: planCode })
    });
    showToast('Plano atualizado.');
    await initPortal();
  };

  window.verifyReceipt = async (receiptId) => {
    const result = await apiFetch(`/portal/inference/receipts/${receiptId}/verify`, { method: 'POST' });
    showToast(`Receipt ${result.valid ? 'valido' : 'invalido'}.`);
    await loadTrustPage();
  };

  window.verifyProof = async (proofId) => {
    const result = await apiFetch(`/portal/inference/proofs/proofs/${proofId}/verify`, { method: 'POST' });
    showToast(`Proof ${result.valid ? 'valida' : 'invalida'}.`);
    await loadTrustPage();
  };

  window.downloadAuditReport = async (reportId) => {
    const result = await apiFetchBlob(`/portal/audit/reports/${reportId}/download`);
    const url = URL.createObjectURL(result.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  if (els.doLogin) {
    els.doLogin.addEventListener('click', async () => {
      const key = els.loginKey.value.trim();
      if (!key) return;
      try {
        await attemptLogin(key, { persist: Boolean(els.rememberMe && els.rememberMe.checked) });
      } catch (err) {
        alert('Falha ao autenticar no portal: ' + err.message);
      }
    });
  }

  if (els.loginKey) {
    els.loginKey.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && els.doLogin) {
        e.preventDefault();
        els.doLogin.click();
      }
    });
  }

  if (els.logout) {
    els.logout.addEventListener('click', () => {
      localStorage.removeItem('portalApiKey');
      window.location.reload();
    });
  }

  if (els.viewInvoicesBtn) {
    els.viewInvoicesBtn.addEventListener('click', () => goToPage('invoices'));
  }

  if (els.createNewKey && els.newKeyModal) {
    els.createNewKey.addEventListener('click', () => {
      els.newKeyModal.classList.add('open');
      els.newKeyName.value = '';
      els.keyDisplayArea.style.display = 'none';
      els.confirmNewKey.style.display = 'inline-flex';
    });
  }

  if (els.cancelNewKey && els.newKeyModal) {
    els.cancelNewKey.addEventListener('click', () => {
      els.newKeyModal.classList.remove('open');
      loadApiKeys();
    });
  }

  if (els.confirmNewKey) {
    els.confirmNewKey.addEventListener('click', async () => {
      const name = els.newKeyName.value.trim() || 'Nova Chave';
      const result = await apiFetch('/portal/api-keys', {
        method: 'POST',
        body: JSON.stringify({ client_id: state.client.id, name })
      });
      els.newKeySecret.textContent = result.api_key;
      els.keyDisplayArea.style.display = 'block';
      els.confirmNewKey.style.display = 'none';
      showToast('Chave gerada com sucesso!');
    });
  }

  const walletRequestRecharge = byId('walletRequestRecharge');
  if (walletRequestRecharge) {
    walletRequestRecharge.addEventListener('click', async () => {
      await apiFetch('/portal/wallet/recharge-request', {
        method: 'POST',
        body: JSON.stringify({
          amount_brl: byId('walletRechargeAmount').value ? Number(byId('walletRechargeAmount').value) : null,
          note: 'Solicitacao iniciada pelo portal do cliente'
        })
      });
      showToast('Solicitacao de recarga registrada.');
      byId('walletRechargeAmount').value = '';
    });
  }

  const walletCreateTopup = byId('walletCreateTopup');
  if (walletCreateTopup) {
    walletCreateTopup.addEventListener('click', async () => {
      const amount = Number(byId('walletTopupAmount').value || 0);
      if (!amount) return;
      await apiFetch('/portal/wallet/topups', {
        method: 'POST',
        body: JSON.stringify({
          amount_brl: amount,
          idempotency_key: `portal-${Date.now()}`
        })
      });
      showToast('Intent de top-up criada.');
      byId('walletTopupAmount').value = '';
      await loadWallet();
    });
  }

  if (els.pgPrompt) els.pgPrompt.addEventListener('input', refreshPlaygroundEstimate);
  if (els.pgMaxTokens) els.pgMaxTokens.addEventListener('input', refreshPlaygroundEstimate);

  if (els.pgRun) {
    els.pgRun.addEventListener('click', async () => {
      const prompt = els.pgPrompt.value.trim();
      if (!prompt) return;
      els.pgRun.disabled = true;
      els.pgResponse.textContent = 'Processando...';
      const start = performance.now();
      try {
        const result = await apiFetch('/portal/test-chat', {
          method: 'POST',
          body: JSON.stringify({
            prompt,
            model: els.pgModelSelect.value,
            max_tokens: Number(els.pgMaxTokens.value || 512)
          })
        });
        const latency = (performance.now() - start).toFixed(0);
        const usage = result.usage || {};
        els.pgResponse.textContent = result.text;
        els.pgStats.textContent = `Latencia: ${latency}ms | Modelo: ${result.model} | Tokens: ${usage.total_tokens || 0}`;
      } catch (err) {
        els.pgResponse.innerHTML = `<span style="color: var(--danger);">Erro: ${esc(err.message)}</span>`;
      } finally {
        els.pgRun.disabled = false;
      }
    });
  }

  if (els.btnRagUpload && els.ragFileUpload) {
    els.btnRagUpload.addEventListener('click', () => els.ragFileUpload.click());
    els.ragFileUpload.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      els.btnRagUpload.disabled = true;
      try {
        await apiFetch('/client/rag/documents', { method: 'POST', body: fd });
        showToast('Upload concluido!');
        await loadRagFiles();
      } finally {
        els.btnRagUpload.disabled = false;
        els.ragFileUpload.value = '';
      }
    });
  }

  if (els.btnRagQuery) {
    els.btnRagQuery.addEventListener('click', async () => {
      const question = els.ragQueryInput.value.trim();
      if (!question) return;
      els.btnRagQuery.disabled = true;
      els.ragQueryResponse.textContent = 'Consultando...';
      els.ragQuerySources.textContent = '';
      try {
        const result = await apiFetch('/client/rag/query', {
          method: 'POST',
          body: JSON.stringify({ question, top_k: 3 })
        });
        els.ragQueryResponse.textContent = result.answer;
        if (result.sources && result.sources.length) {
          els.ragQuerySources.innerHTML = '<strong>Fontes:</strong><br>' + result.sources.map((s) => `${esc(s.filename)} (pag ${s.page}) - Score: ${s.score.toFixed(2)}`).join('<br>');
        }
      } catch (err) {
        els.ragQueryResponse.innerHTML = `<span style="color: var(--danger);">Erro: ${esc(err.message)}</span>`;
      } finally {
        els.btnRagQuery.disabled = false;
      }
    });
  }

  const auditGenerate = byId('generateAuditReport');
  if (auditGenerate) {
    auditGenerate.addEventListener('click', async () => {
      const payload = {
        report_type: byId('auditReportType').value,
        period_start: byId('auditPeriodStart').value,
        period_end: byId('auditPeriodEnd').value,
        export_format: byId('auditExportFormat').value
      };
      await apiFetch('/portal/audit/reports/generate', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast('Relatorio solicitado.');
      await loadAuditPage();
    });
  }

  const disputeCreate = byId('createDispute');
  if (disputeCreate) {
    disputeCreate.addEventListener('click', async () => {
      const payload = {
        dispute_type: byId('disputeType').value,
        claimed_amount_brl: Number(byId('disputeAmount').value || 0),
        disputed_reason: byId('disputeReason').value.trim(),
        invoice_id: byId('disputeInvoiceId').value || null,
        qos_billing_record_id: byId('disputeQosRecordId').value || null,
        wallet_transaction_id: byId('disputeWalletTransactionId').value || null
      };
      if (!payload.claimed_amount_brl || !payload.disputed_reason) return;
      await apiFetch('/portal/billing/disputes', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast('Disputa registrada.');
      byId('disputeReason').value = '';
      byId('disputeAmount').value = '';
      await loadDisputesPage();
    });
  }

  enhanceNavigation();
  activateNav();

  const urlKey = readApiKeyFromUrl();
  const savedKey = localStorage.getItem('portalApiKey');
  const bootKey = urlKey || savedKey;
  if (bootKey) {
    attemptLogin(bootKey, { persist: Boolean(urlKey) || Boolean(savedKey) }).catch(() => {
      if (urlKey) alert('A API key fornecida na URL e invalida ou nao conseguiu autenticar no portal.');
    });
  } else if (page === 'plans') {
    if (els.loginOverlay) els.loginOverlay.style.display = 'none';
    loadPlansPage({ publicCatalog: true }).catch((error) => {
      showToast(`Não foi possível carregar os planos: ${error.message}`);
    });
  }
})();
