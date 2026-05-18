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
    playground: 'playground.html'
  };

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
    viewInvoicesBtn: document.getElementById('viewInvoicesBtn'),
    overviewQuickStats: document.getElementById('overviewQuickStats'),
    demoModeNotice: document.getElementById('demoModeNotice'),
    apiKeysList: document.getElementById('apiKeysList'),
    createNewKey: document.getElementById('createNewKey'),
    newKeyModal: document.getElementById('newKeyModal'),
    newKeyName: document.getElementById('newKeyName'),
    confirmNewKey: document.getElementById('confirmNewKey'),
    cancelNewKey: document.getElementById('cancelNewKey'),
    keyDisplayArea: document.getElementById('keyDisplayArea'),
    newKeySecret: document.getElementById('newKeySecret'),
    usageRequestsTodayMonth: document.getElementById('usageRequestsTodayMonth'),
    usageTokensTodayMonth: document.getElementById('usageTokensTodayMonth'),
    usageMonthlyTokens: document.getElementById('usageMonthlyTokens'),
    usageMonthlyLimit: document.getElementById('usageMonthlyLimit'),
    usageMonthlyProgress: document.getElementById('usageMonthlyProgress'),
    usageQuotaRemaining: document.getElementById('usageQuotaRemaining'),
    usagePricingSummary: document.getElementById('usagePricingSummary'),
    usageRateLimit: document.getElementById('usageRateLimit'),
    dailyUsageChart: document.getElementById('dailyUsageChart'),
    modelUsageList: document.getElementById('modelUsageList'),
    qosUsageTableBody: document.getElementById('qosUsageTableBody'),
    invoicesSummary: document.getElementById('invoicesSummary'),
    invoicesList: document.getElementById('invoicesList'),
    walletWarning: document.getElementById('walletWarning'),
    walletBalance: document.getElementById('walletBalance'),
    walletAvailable: document.getElementById('walletAvailable'),
    walletReserved: document.getElementById('walletReserved'),
    walletConsumptionEstimate: document.getElementById('walletConsumptionEstimate'),
    walletRechargeAmount: document.getElementById('walletRechargeAmount'),
    walletRequestRecharge: document.getElementById('walletRequestRecharge'),
    walletTransactions: document.getElementById('walletTransactions'),
    pgModelSelect: document.getElementById('pgModelSelect'),
    pgMaxTokens: document.getElementById('pgMaxTokens'),
    pgPrompt: document.getElementById('pgPrompt'),
    pgEstimate: document.getElementById('pgEstimate'),
    pgRun: document.getElementById('pgRun'),
    pgResponse: document.getElementById('pgResponse'),
    pgStats: document.getElementById('pgStats'),
    btnRagUpload: document.getElementById('btnRagUpload'),
    ragFileUpload: document.getElementById('ragFileUpload'),
    ragFilesList: document.getElementById('ragFilesList'),
    ragStatsDocs: document.getElementById('ragStatsDocs'),
    ragProgressDocsFill: document.getElementById('ragProgressDocsFill'),
    ragStatsStorage: document.getElementById('ragStatsStorage'),
    ragProgressStorageFill: document.getElementById('ragProgressStorageFill'),
    ragStatsQueries: document.getElementById('ragStatsQueries'),
    ragProgressQueriesFill: document.getElementById('ragProgressQueriesFill'),
    ragQueryInput: document.getElementById('ragQueryInput'),
    btnRagQuery: document.getElementById('btnRagQuery'),
    ragQueryResponse: document.getElementById('ragQueryResponse'),
    ragQuerySources: document.getElementById('ragQuerySources'),
    toast: document.getElementById('toast')
  };

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

  function goToPage(pageKey) {
    const next = pageRoutes[pageKey];
    if (next) window.location.href = next;
  }

  window.switchTab = goToPage;
  window.copyToClipboard = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent).then(() => showToast('Copiado!'));
  };

  function activateNav() {
    document.querySelectorAll('[data-page-link]').forEach((item) => {
      item.classList.toggle('active', item.dataset.pageLink === page);
    });
  }

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
    const [me, usage, models] = await Promise.all([
      apiFetch('/portal/me'),
      apiFetch('/portal/usage'),
      apiFetch('/portal/models')
    ]);
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
    await loadPageData();
  }

  function renderOverview(me, usage) {
    if (els.overviewAccountDetails) {
      els.overviewAccountDetails.innerHTML = `
        <div class="field"><div class="field-label">ID do Cliente</div><div class="field-value"><code>${esc(me.id)}</code></div></div>
        <div class="field"><div class="field-label">Plano Atual</div><div class="field-value"><strong>${esc(me.plan.name)}</strong></div></div>
        <div class="field"><div class="field-label">Status da Conta</div><div class="field-value">${esc(me.billing_status.toUpperCase())}</div></div>
      `;
    }
    if (els.overviewBillingDetails) {
      els.overviewBillingDetails.innerHTML = `
        <div class="field"><div class="field-label">Preço Mensal</div><div class="field-value">${esc(me.plan.currency)} ${Number(me.plan.monthly_price).toFixed(2)}</div></div>
        <div class="field"><div class="field-label">Próxima Fatura (Est.)</div><div class="field-value">${esc(usage.invoice_preview.currency)} ${Number(usage.invoice_preview.total_estimated).toFixed(2)}</div></div>
      `;
    }
    if (els.overviewUsageSnapshot) {
      const m = usage.monthly_usage;
      const pct = Math.min(100, (m.used_tokens / m.quota) * 100);
      els.overviewUsageSnapshot.innerHTML = `
        <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">
          <span>${m.used_tokens.toLocaleString()} / ${m.quota.toLocaleString()} tokens</span>
          <span>${pct.toFixed(1)}%</span>
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
          <div class="field-label">Tokens no Mês</div>
          <div class="usage-num">${usage.tokens_month.toLocaleString()}</div>
        </div>
        <div class="summary-card">
          <div class="field-label">Quota Restante</div>
          <div class="usage-num">${usage.quota_remaining.monthly_tokens.toLocaleString()}</div>
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
  }

  async function loadApiKeys() {
    if (!els.apiKeysList) return;
    const keys = await apiFetch('/portal/api-keys');
    els.apiKeysList.innerHTML = keys.map((k) => `
      <tr>
        <td><strong>${esc(k.name)}</strong></td>
        <td><code>${esc(k.masked_key)}</code></td>
        <td>${new Date(k.created_at).toLocaleDateString()}</td>
        <td>${k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'Nunca'}</td>
        <td>
          <button class="secondary" onclick="copyApiExample()">Copiar Exemplo</button>
          ${k.revoked_at ? '<span class="badge badge-blocked">Revogada</span>' : `<button class="danger" onclick="revokeKey('${k.id}')">Revogar</button>`}
        </td>
      </tr>
    `).join('');
  }

  async function loadUsageStats() {
    if (!els.usageRequestsTodayMonth) return;
    const [usage, stats] = await Promise.all([
      apiFetch('/portal/usage'),
      apiFetch('/portal/usage-stats')
    ]);
    const m = usage.monthly_usage;
    els.usageRequestsTodayMonth.textContent = `${usage.requests_today.toLocaleString()} / ${usage.requests_month.toLocaleString()}`;
    els.usageTokensTodayMonth.textContent = `${usage.tokens_today.toLocaleString()} / ${usage.tokens_month.toLocaleString()}`;
    els.usageMonthlyTokens.textContent = m.used_tokens.toLocaleString();
    els.usageMonthlyLimit.textContent = `limite: ${m.quota.toLocaleString()}`;
    els.usageMonthlyProgress.style.width = `${Math.min(100, (m.used_tokens / m.quota) * 100)}%`;
    els.usageQuotaRemaining.textContent = usage.quota_remaining.monthly_tokens.toLocaleString();
    els.usagePricingSummary.innerHTML = `
      <div class="field"><div class="field-label">Hoje</div><div class="field-value">${usage.customer_pricing.today_amount === null ? 'indisponível' : `${usage.customer_pricing.currency} ${usage.customer_pricing.today_amount.toFixed(2)}`}</div></div>
      <div class="field"><div class="field-label">Mês</div><div class="field-value">${usage.customer_pricing.currency} ${usage.customer_pricing.month_amount.toFixed(2)}</div></div>
      <div class="field"><div class="field-label">Origem</div><div class="field-value">${esc(usage.customer_pricing.source)}</div></div>
    `;
    els.usageRateLimit.innerHTML = `
      <div class="field"><div class="field-label">RPM</div><div class="field-value">${usage.rate_limit.requests_per_minute}</div></div>
      <div class="field"><div class="field-label">RPD</div><div class="field-value">${usage.rate_limit.requests_per_day || 'sem limite específico'}</div></div>
    `;
    renderChart(stats.daily_usage || []);
    els.modelUsageList.innerHTML = (stats.model_usage || []).map((r) => `
      <tr>
        <td><code>${esc(r.model)}</code></td>
        <td>${r.requests.toLocaleString()}</td>
        <td>${r.tokens.toLocaleString()}</td>
      </tr>
    `).join('');
  }

  function renderChart(data) {
    if (!els.dailyUsageChart) return;
    if (!data.length) {
      els.dailyUsageChart.innerHTML = '<div class="muted">Sem uso recente.</div>';
      return;
    }
    const maxTokens = Math.max(...data.map((d) => d.tokens), 1);
    els.dailyUsageChart.innerHTML = data.map((d) => {
      const height = (d.tokens / maxTokens) * 100;
      return `
        <div class="chart-bar" style="height:${height}%" data-label="${esc(d.day.substring(5))}">
          <div class="chart-tooltip">${esc(d.day)}: ${d.tokens.toLocaleString()} tokens</div>
        </div>
      `;
    }).join('');
  }

  async function loadQosUsage() {
    if (!els.qosUsageTableBody) return;
    const records = await apiFetch('/portal/qos-billing');
    if (!records || !records.length) {
      els.qosUsageTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);">Nenhum consumo de QoS registrado no período.</td></tr>';
      return;
    }
    els.qosUsageTableBody.innerHTML = records.map((r) => `
      <tr>
        <td>${new Date(r.period_start).toLocaleDateString()}</td>
        <td>${esc(r.qos_tier)}</td>
        <td>${r.compute_seconds.toFixed(2)}s</td>
        <td>${r.priority_slots_consumed.toFixed(2)}</td>
        <td><strong>R$ ${r.billable_amount_brl.toFixed(4)}</strong></td>
        <td>${esc(r.status)}</td>
      </tr>
    `).join('');
  }

  async function loadInvoices() {
    if (!els.invoicesList) return;
    const data = await apiFetch('/portal/invoices');
    const invoices = data.invoices || [];
    els.invoicesSummary.textContent = data.local_billing_message
      ? `Modo de cobrança: ${data.local_billing_message}.`
      : 'Sem mensagem adicional de cobrança.';
    els.invoicesList.innerHTML = invoices.length ? invoices.map((invoice) => `
      <tr>
        <td><code>${esc(invoice.id.slice(0, 8))}</code></td>
        <td><span class="badge ${invoice.status === 'paid' ? 'badge-active' : invoice.status === 'pending' ? 'badge-warning' : 'badge-blocked'}">${esc(invoice.status)}</span></td>
        <td>${esc(invoice.period_start)} a ${esc(invoice.period_end)}</td>
        <td>${esc(invoice.currency)} ${Number(invoice.total_amount).toFixed(2)}</td>
        <td>${invoice.due_at ? new Date(invoice.due_at).toLocaleDateString() : '-'}</td>
        <td>
          <button class="secondary" onclick="downloadInvoice('${invoice.id}', 'json')">JSON</button>
          <button class="secondary" onclick="downloadInvoice('${invoice.id}', 'html')">HTML</button>
        </td>
      </tr>
    `).join('') : '<tr><td colspan="6">Nenhuma fatura encontrada.</td></tr>';
  }

  async function loadWallet() {
    if (!els.walletBalance) return;
    const wallet = await apiFetch('/portal/wallet');
    els.walletBalance.textContent = `BRL ${wallet.balance_brl.toFixed(2)}`;
    els.walletAvailable.textContent = `disponível: BRL ${wallet.available_brl.toFixed(2)}`;
    els.walletReserved.textContent = `BRL ${wallet.reserved_brl.toFixed(2)}`;
    els.walletConsumptionEstimate.textContent = `consumo estimado: BRL ${wallet.consumption_estimate_brl.toFixed(2)}`;
    els.walletWarning.style.display = wallet.low_balance ? 'block' : 'none';
    els.walletWarning.textContent = wallet.low_balance_message || '';
    els.walletTransactions.innerHTML = (wallet.transactions || []).length ? wallet.transactions.map((tx) => `
      <tr>
        <td>${tx.created_at ? new Date(tx.created_at).toLocaleString() : '-'}</td>
        <td>${esc(tx.type)}</td>
        <td>BRL ${Number(tx.amount_brl).toFixed(2)}</td>
        <td>BRL ${Number(tx.balance_after_brl).toFixed(2)}</td>
        <td>${tx.reference_type ? `${esc(tx.reference_type)}:${esc(tx.reference_id || '-')}` : '-'}</td>
      </tr>
    `).join('') : '<tr><td colspan="5">Nenhuma transação registrada.</td></tr>';
  }

  function estimateTokensFromPrompt(prompt) {
    return Math.max(1, Math.ceil((prompt || '').length / 4));
  }

  async function refreshPlaygroundEstimate() {
    if (!els.pgEstimate || !els.pgPrompt || !els.pgMaxTokens) return;
    const promptTokens = estimateTokensFromPrompt(els.pgPrompt.value);
    els.pgEstimate.textContent = `Estimativa: ~${promptTokens} tokens de prompt + até ${Number(els.pgMaxTokens.value || 0)} de saída`;
  }

  async function loadRagFiles() {
    if (!els.ragFilesList) return;
    const [files, usage] = await Promise.all([
      apiFetch('/client/rag/documents'),
      apiFetch('/client/rag/usage')
    ]);
    els.ragFilesList.innerHTML = (files.data || []).map((f) => `
      <tr>
        <td><strong>${esc(f.original_filename)}</strong><br><small>${(f.file_size_bytes / 1024).toFixed(1)}KB</small></td>
        <td><span class="badge ${f.status === 'indexed' ? 'badge-active' : (f.status === 'failed' ? 'badge-blocked' : 'badge-warning')}">${esc(f.status)}</span></td>
        <td>${f.page_count || '-'}</td>
        <td><button class="danger" onclick="deleteFile('${f.id}')">Excluir</button></td>
      </tr>
    `).join('') || '<tr><td colspan="4">Nenhum documento enviado.</td></tr>';
    const u = usage.usage;
    const l = usage.limits;
    els.ragStatsDocs.textContent = `${u.documents_count} / ${l.max_documents || '∞'}`;
    els.ragProgressDocsFill.style.width = l.max_documents ? `${Math.min(100, (u.documents_count / l.max_documents) * 100)}%` : '0%';
    els.ragStatsStorage.textContent = `${u.storage_mb.toFixed(1)} / ${l.max_storage_mb || '∞'}`;
    els.ragProgressStorageFill.style.width = l.max_storage_mb ? `${Math.min(100, (u.storage_mb / l.max_storage_mb) * 100)}%` : '0%';
    els.ragStatsQueries.textContent = `${u.queries_month} / ${l.max_queries_per_month || '∞'}`;
    els.ragProgressQueriesFill.style.width = l.max_queries_per_month ? `${Math.min(100, (u.queries_month / l.max_queries_per_month) * 100)}%` : '0%';
  }

  window.revokeKey = async (id) => {
    if (!confirm('Tem certeza que deseja revogar esta chave? Esta ação é irreversível.')) return;
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

  window.deleteFile = async (id) => {
    if (!confirm('Excluir documento?')) return;
    await apiFetch(`/client/rag/documents/${id}`, { method: 'DELETE' });
    await loadRagFiles();
  };

  if (els.doLogin) {
    els.doLogin.addEventListener('click', async () => {
      const key = els.loginKey.value.trim();
      if (!key) return;
      try {
        await attemptLogin(key, { persist: Boolean(els.rememberMe && els.rememberMe.checked) });
      } catch (err) {
        alert('Chave inválida ou erro de conexão: ' + err.message);
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

  if (els.walletRequestRecharge) {
    els.walletRequestRecharge.addEventListener('click', async () => {
      await apiFetch('/portal/wallet/recharge-request', {
        method: 'POST',
        body: JSON.stringify({
          amount_brl: els.walletRechargeAmount.value ? Number(els.walletRechargeAmount.value) : null,
          note: 'Solicitação iniciada pelo portal do cliente'
        })
      });
      showToast('Solicitação de recarga registrada.');
      els.walletRechargeAmount.value = '';
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
        els.pgStats.textContent = `Latência: ${latency}ms | Modelo: ${result.model} | Tokens: ${usage.total_tokens || 0}`;
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
        showToast('Upload concluído!');
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
          els.ragQuerySources.innerHTML = '<strong>Fontes:</strong><br>' + result.sources.map((s) => `${esc(s.filename)} (pág ${s.page}) - Score: ${s.score.toFixed(2)}`).join('<br>');
        }
      } catch (err) {
        els.ragQueryResponse.innerHTML = `<span style="color: var(--danger);">Erro: ${esc(err.message)}</span>`;
      } finally {
        els.btnRagQuery.disabled = false;
      }
    });
  }

  activateNav();

  const urlKey = readApiKeyFromUrl();
  const savedKey = localStorage.getItem('portalApiKey');
  const bootKey = urlKey || savedKey;
  if (bootKey) {
    attemptLogin(bootKey, { persist: Boolean(urlKey) || Boolean(savedKey) }).catch(() => {
      if (urlKey) alert('A API key fornecida na URL e invalida ou nao conseguiu autenticar no portal.');
    });
  }
})();
