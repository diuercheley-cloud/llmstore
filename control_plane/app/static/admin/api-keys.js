const STORAGE_KEY = "adminToken";

const state = {
  token: "",
  clients: [],
  keys: []
};

const els = {
  adminToken: document.getElementById("adminToken"),
  connectButton: document.getElementById("connectButton"),
  reloadButton: document.getElementById("reloadButton"),
  authStatus: document.getElementById("authStatus"),
  apiKeysApp: document.getElementById("apiKeysApp"),
  loginPrompt: document.getElementById("loginPrompt"),
  statTotalKeys: document.getElementById("statTotalKeys"),
  statActiveKeys: document.getElementById("statActiveKeys"),
  keyForm: document.getElementById("keyForm"),
  clientSelect: document.getElementById("client_id"),
  keysTableBody: document.getElementById("keysTableBody"),
  newKeyPanel: document.getElementById("newKeyPanel"),
  newKeyValue: document.getElementById("newKeyValue")
};

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatTimestamp(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch (error) {
    return String(value);
  }
}

function readAdminTokenFromUrl() {
  const searchParams = new URLSearchParams(window.location.search);
  return (searchParams.get("admin_token") || searchParams.get("api_key") || "").trim();
}

function setConnected(connected) {
  els.apiKeysApp.classList.toggle("hidden", !connected);
  els.loginPrompt.classList.toggle("hidden", connected);
  els.authStatus.textContent = connected ? "Conectado" : "Desconectado";
  els.authStatus.className = connected ? "badge success" : "badge warning";
}

function adminHeaders() {
  const token = state.token || els.adminToken.value.trim();
  if (!token) throw new Error("Informe o X-Admin-Token.");
  return SharedAuth.headerForAdminToken(token);
}

function adminFetch(path, options) {
  const init = Object.assign({}, options || {});
  init.headers = Object.assign({}, adminHeaders(), init.headers || {});
  return SharedAPI.request(path, init);
}

function updateStats() {
  const keys = state.keys;
  els.statTotalKeys.textContent = String(keys.length);
  els.statActiveKeys.textContent = String(keys.filter((k) => !k.revoked_at).length);
}

function renderClientOptions() {
  const options = ['<option value="">Selecione um cliente...</option>'].concat(
    state.clients.map((c) => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${escapeHtml(c.id).slice(0,8)})</option>`)
  );
  els.clientSelect.innerHTML = options.join("");
}

function renderKeys() {
  if (!state.keys.length) {
    els.keysTableBody.innerHTML = '<tr><td colspan="5"><div class="empty-state">Nenhuma API Key encontrada.</div></td></tr>';
    return;
  }

  els.keysTableBody.innerHTML = state.keys.map((key) => {
    const client = state.clients.find(c => c.id === key.client_id);
    const clientName = client ? client.name : "Unknown";

    return `
      <tr>
        <td>
          <strong>${escapeHtml(key.name || "Sem nome")}</strong><br />
          <span class="code">${escapeHtml(key.key_prefix)}***</span>
        </td>
        <td>
          <strong>${escapeHtml(clientName)}</strong><br />
          <span class="code">${escapeHtml(key.client_id)}</span>
        </td>
        <td>${formatTimestamp(key.created_at)}</td>
        <td>${formatTimestamp(key.last_used_at)}</td>
        <td>
          <div class="table-actions">
            <button class="button secondary" type="button" data-action="rotate" data-key-id="${escapeHtml(key.id)}">Rotacionar</button>
            <button class="button danger" type="button" data-action="delete" data-key-id="${escapeHtml(key.id)}">Revogar</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

async function loadData() {
  const [clients, keys] = await Promise.all([
    adminFetch("/admin/clients"),
    adminFetch("/admin/api-keys")
  ]);
  state.clients = Array.isArray(clients) ? clients : [];
  state.keys = Array.isArray(keys) ? keys : [];
  renderClientOptions();
  updateStats();
  renderKeys();
}

async function connect() {
  const token = els.adminToken.value.trim();
  if (!token) return;
  state.token = token;
  SharedAuth.setToken(STORAGE_KEY, token);
  try {
    await loadData();
    setConnected(true);
    SharedNotifications.success("Dados carregados.");
  } catch (error) {
    setConnected(false);
    SharedNotifications.error(error.message || "Falha ao conectar.");
  }
}

async function submitForm(event) {
  event.preventDefault();
  const formData = new FormData(els.keyForm);
  const payload = {
    client_id: formData.get("client_id"),
    name: formData.get("name") || null
  };

  try {
    const result = await adminFetch("/admin/api-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    els.newKeyValue.textContent = result.plaintext_key;
    els.newKeyPanel.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
    
    await loadData();
    els.keyForm.reset();
  } catch (error) {
    SharedNotifications.error(error.message || "Falha ao gerar chave.");
  }
}

async function performAction(action, keyId) {
  try {
    if (action === "delete") {
      if (!confirm("Revogar esta chave permanentemente?")) return;
      await adminFetch(`/admin/api-keys/${keyId}`, { method: "DELETE" });
      SharedNotifications.success("Chave revogada.");
    } else if (action === "rotate") {
      if (!confirm("Rotacionar esta chave? A chave antiga será revogada imediatamente.")) return;
      const result = await adminFetch(`/admin/api-keys/${keyId}/rotate`, { method: "POST" });
      els.newKeyValue.textContent = result.api_key.plaintext_key;
      els.newKeyPanel.classList.remove("hidden");
      SharedNotifications.success("Chave rotacionada.");
    }
    await loadData();
  } catch (error) {
    SharedNotifications.error(error.message || "Ação falhou.");
  }
}

els.connectButton.addEventListener("click", connect);
els.reloadButton.addEventListener("click", () => connect());
els.keyForm.addEventListener("submit", submitForm);
els.keysTableBody.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (btn) performAction(btn.dataset.action, btn.dataset.keyId);
});

SharedNavigation.mountTopbar("#api-keys-topbar", {
  brand: "Admin / API Keys",
  title: "API Keys",
  actions: [
    { label: "Admin Hub", href: "/admin-dashboard" }
  ]
});

const urlToken = readAdminTokenFromUrl();
if (urlToken || SharedAuth.getToken(STORAGE_KEY)) {
  els.adminToken.value = urlToken || SharedAuth.getToken(STORAGE_KEY);
  connect();
}
