const STORAGE_KEY = "adminToken";
const DEFAULT_CREATE_VALUES = {
  name: "",
  description: "",
  billing_plan_id: "",
  billing_status: "active",
  rate_limit_per_minute: 1000,
  daily_token_quota: 100000000,
  weekly_token_quota: 500000000,
  monthly_token_quota: 1000000000,
  max_context_tokens: 131072,
  max_output_tokens: 32768,
  allowed_models: "",
  ip_allowlist: "",
  ip_blocklist: "",
  system_prompt: "",
  metadata_json: "",
  is_blocked: "false"
};

const state = {
  token: "",
  plans: [],
  clients: [],
  editingClientId: null
};

const els = {
  adminToken: document.getElementById("adminToken"),
  connectButton: document.getElementById("connectButton"),
  reloadButton: document.getElementById("reloadButton"),
  authStatus: document.getElementById("authStatus"),
  clientsApp: document.getElementById("clientsApp"),
  loginPrompt: document.getElementById("loginPrompt"),
  statTotalClients: document.getElementById("statTotalClients"),
  statBlockedClients: document.getElementById("statBlockedClients"),
  statSuspendedClients: document.getElementById("statSuspendedClients"),
  editorTitle: document.getElementById("editorTitle"),
  newClientButton: document.getElementById("newClientButton"),
  cancelEditButton: document.getElementById("cancelEditButton"),
  submitButton: document.getElementById("submitButton"),
  clientForm: document.getElementById("clientForm"),
  billingPlanSelect: document.getElementById("billing_plan_id"),
  clientsTableBody: document.getElementById("clientsTableBody"),
  searchInput: document.getElementById("searchInput")
};

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function shortId(value) {
  return value ? String(value).slice(0, 8) + "..." : "-";
}

function formatTimestamp(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch (error) {
    return String(value);
  }
}

function parseList(text) {
  if (!text || !String(text).trim()) return null;
  const items = String(text)
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : null;
}

function stringifyList(value) {
  if (!value) return "";
  try {
    const parsed = Array.isArray(value) ? value : JSON.parse(value);
    return Array.isArray(parsed) ? parsed.join("\n") : "";
  } catch (error) {
    return "";
  }
}

function readMetadata(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  JSON.parse(raw);
  return raw;
}

function readAdminTokenFromUrl() {
  const searchParams = new URLSearchParams(window.location.search);
  const hash = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : window.location.hash;
  const hashParams = new URLSearchParams(hash);
  return (
    searchParams.get("admin_token") ||
    searchParams.get("adminToken") ||
    searchParams.get("api_key") ||
    searchParams.get("apiKey") ||
    hashParams.get("admin_token") ||
    hashParams.get("adminToken") ||
    hashParams.get("api_key") ||
    hashParams.get("apiKey") ||
    ""
  ).trim();
}

function clearAdminTokenFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("admin_token");
  url.searchParams.delete("adminToken");
  url.searchParams.delete("api_key");
  url.searchParams.delete("apiKey");
  if (url.hash) {
    const hash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
    const hashParams = new URLSearchParams(hash);
    hashParams.delete("admin_token");
    hashParams.delete("adminToken");
    hashParams.delete("api_key");
    hashParams.delete("apiKey");
    url.hash = hashParams.toString() ? "#" + hashParams.toString() : "";
  }
  window.history.replaceState({}, document.title, url.toString());
}

function setConnected(connected) {
  els.clientsApp.classList.toggle("hidden", !connected);
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

function planNameById(planId) {
  const plan = state.plans.find((item) => String(item.id) === String(planId));
  return plan ? plan.name : "-";
}

function updateStats() {
  const clients = state.clients;
  els.statTotalClients.textContent = String(clients.length);
  els.statBlockedClients.textContent = String(clients.filter((item) => item.is_blocked).length);
  els.statSuspendedClients.textContent = String(
    clients.filter((item) => item.billing_status === "suspended" || item.billing_status === "past_due").length
  );
}

function renderPlanOptions() {
  const options = ['<option value="">Plano padrão</option>'].concat(
    state.plans.map((plan) => `<option value="${escapeHtml(plan.id)}">${escapeHtml(plan.name)} (${escapeHtml(plan.code)})</option>`)
  );
  els.billingPlanSelect.innerHTML = options.join("");
}

function filteredClients() {
  const query = els.searchInput.value.trim().toLowerCase();
  if (!query) return state.clients;
  return state.clients.filter((client) => {
    const haystack = [
      client.name,
      client.id,
      client.description,
      planNameById(client.billing_plan_id)
    ].join(" ").toLowerCase();
    return haystack.includes(query);
  });
}

function renderClients() {
  const clients = filteredClients();
  if (!clients.length) {
    els.clientsTableBody.innerHTML = '<tr><td colspan="6"><div class="empty-state">Nenhum cliente encontrado.</div></td></tr>';
    return;
  }

  els.clientsTableBody.innerHTML = clients.map((client) => {
    const statusBadge = client.is_blocked
      ? '<span class="badge danger">blocked</span>'
      : client.billing_status === "suspended"
        ? '<span class="badge warning">suspended</span>'
        : client.billing_status === "past_due"
          ? '<span class="badge warning">past_due</span>'
          : '<span class="badge success">active</span>';

    return `
      <tr>
        <td>
          <strong>${escapeHtml(client.name)}</strong><br />
          <span class="code">${escapeHtml(client.id)}</span>
        </td>
        <td>
          <div>${escapeHtml(planNameById(client.billing_plan_id))}</div>
          <div class="muted code">${escapeHtml(client.billing_plan_id || "-")}</div>
        </td>
        <td>
          ${statusBadge}
          <div class="muted" style="margin-top:6px;">billing=${escapeHtml(client.billing_status)}</div>
        </td>
        <td>
          <div class="pill-muted">rpm ${Number(client.rate_limit_per_minute).toLocaleString("pt-BR")}</div>
          <div class="muted" style="margin-top:6px;">dia ${Number(client.daily_token_quota).toLocaleString("pt-BR")}</div>
          <div class="muted">mês ${Number(client.monthly_token_quota).toLocaleString("pt-BR")}</div>
        </td>
        <td>
          <div>${formatTimestamp(client.created_at)}</div>
          <div class="muted">upd ${formatTimestamp(client.updated_at)}</div>
        </td>
        <td>
          <div class="table-actions">
            <button class="button secondary" type="button" data-action="edit" data-client-id="${escapeHtml(client.id)}">Editar</button>
            <button class="button secondary" type="button" data-action="${client.is_blocked ? "unblock" : "block"}" data-client-id="${escapeHtml(client.id)}">
              ${client.is_blocked ? "Desbloquear" : "Bloquear"}
            </button>
            <button class="button secondary" type="button" data-action="${client.billing_status === "suspended" ? "unsuspend" : "suspend"}" data-client-id="${escapeHtml(client.id)}">
              ${client.billing_status === "suspended" ? "Unsuspend" : "Suspend"}
            </button>
            <button class="button danger" type="button" data-action="delete" data-client-id="${escapeHtml(client.id)}">Remover</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function resetForm() {
  state.editingClientId = null;
  els.editorTitle.textContent = "Criar cliente";
  els.submitButton.textContent = "Criar cliente";
  els.cancelEditButton.classList.add("hidden");
  document.getElementById("name").disabled = false;
  Object.entries(DEFAULT_CREATE_VALUES).forEach(([key, value]) => {
    const input = document.getElementById(key);
    if (input) input.value = value;
  });
}

function populateForm(client) {
  state.editingClientId = String(client.id);
  els.editorTitle.textContent = "Editar cliente";
  els.submitButton.textContent = "Salvar alterações";
  els.cancelEditButton.classList.remove("hidden");
  document.getElementById("name").disabled = true;

  document.getElementById("name").value = client.name || "";
  document.getElementById("description").value = client.description || "";
  document.getElementById("billing_plan_id").value = client.billing_plan_id || "";
  document.getElementById("billing_status").value = client.billing_status || "active";
  document.getElementById("rate_limit_per_minute").value = client.rate_limit_per_minute || "";
  document.getElementById("daily_token_quota").value = client.daily_token_quota || "";
  document.getElementById("weekly_token_quota").value = client.weekly_token_quota || "";
  document.getElementById("monthly_token_quota").value = client.monthly_token_quota || "";
  document.getElementById("max_context_tokens").value = client.max_context_tokens || "";
  document.getElementById("max_output_tokens").value = client.max_output_tokens || "";
  document.getElementById("allowed_models").value = stringifyList(client.allowed_models_json);
  document.getElementById("ip_allowlist").value = stringifyList(client.ip_allowlist_json);
  document.getElementById("ip_blocklist").value = stringifyList(client.ip_blocklist_json);
  document.getElementById("system_prompt").value = client.system_prompt || "";
  document.getElementById("metadata_json").value = client.metadata_json || "";
  document.getElementById("is_blocked").value = client.is_blocked ? "true" : "false";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function buildCreatePayload(form) {
  return {
    name: form.get("name").trim(),
    description: form.get("description").trim() || null,
    billing_plan_id: form.get("billing_plan_id") || null,
    rate_limit_per_minute: Number(form.get("rate_limit_per_minute")),
    daily_token_quota: Number(form.get("daily_token_quota")),
    weekly_token_quota: Number(form.get("weekly_token_quota")),
    monthly_token_quota: Number(form.get("monthly_token_quota")),
    max_context_tokens: Number(form.get("max_context_tokens")),
    max_output_tokens: Number(form.get("max_output_tokens")),
    allowed_models: parseList(form.get("allowed_models")),
    ip_allowlist: parseList(form.get("ip_allowlist")),
    ip_blocklist: parseList(form.get("ip_blocklist")),
    system_prompt: form.get("system_prompt").trim() || null,
    metadata_json: readMetadata(form.get("metadata_json"))
  };
}

function buildPatchPayload(form) {
  return {
    description: form.get("description").trim() || null,
    billing_status: form.get("billing_status"),
    billing_plan_id: form.get("billing_plan_id") || null,
    rate_limit_per_minute: Number(form.get("rate_limit_per_minute")),
    daily_token_quota: Number(form.get("daily_token_quota")),
    weekly_token_quota: Number(form.get("weekly_token_quota")),
    monthly_token_quota: Number(form.get("monthly_token_quota")),
    max_context_tokens: Number(form.get("max_context_tokens")),
    max_output_tokens: Number(form.get("max_output_tokens")),
    allowed_models: parseList(form.get("allowed_models")),
    ip_allowlist: parseList(form.get("ip_allowlist")),
    ip_blocklist: parseList(form.get("ip_blocklist")),
    system_prompt: form.get("system_prompt").trim() || null,
    metadata_json: readMetadata(form.get("metadata_json")),
    is_blocked: form.get("is_blocked") === "true"
  };
}

async function loadData() {
  const [plans, clients] = await Promise.all([
    adminFetch("/admin/billing/plans"),
    adminFetch("/admin/clients")
  ]);
  state.plans = Array.isArray(plans) ? plans : [];
  state.clients = Array.isArray(clients) ? clients : [];
  renderPlanOptions();
  updateStats();
  renderClients();
}

async function connect() {
  const token = els.adminToken.value.trim();
  if (!token) {
    SharedNotifications.warning("Informe o X-Admin-Token.");
    return;
  }
  state.token = token;
  SharedAuth.setToken(STORAGE_KEY, token);
  try {
    await loadData();
    setConnected(true);
    clearAdminTokenFromUrl();
    SharedNotifications.success("Clientes carregados com sucesso.");
  } catch (error) {
    setConnected(false);
    SharedNotifications.error(error.message || "Falha ao autenticar.");
  }
}

async function submitForm(event) {
  event.preventDefault();
  const form = new FormData(els.clientForm);
  try {
    if (state.editingClientId) {
      const payload = buildPatchPayload(form);
      await adminFetch("/admin/clients/" + state.editingClientId, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      SharedNotifications.success("Cliente atualizado.");
    } else {
      const payload = buildCreatePayload(form);
      await adminFetch("/admin/clients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      SharedNotifications.success("Cliente criado.");
    }
    resetForm();
    await loadData();
  } catch (error) {
    SharedNotifications.error(error.message || "Falha ao salvar cliente.");
  }
}

async function performTableAction(action, clientId) {
  const client = state.clients.find((item) => String(item.id) === String(clientId));
  if (!client) return;

  try {
    if (action === "edit") {
      populateForm(client);
      return;
    }

    if (action === "delete") {
      if (!window.confirm("Remover este cliente?")) return;
      await adminFetch("/admin/clients/" + clientId, { method: "DELETE" });
      SharedNotifications.success("Cliente removido.");
    }

    if (action === "block") {
      await adminFetch("/admin/clients/" + clientId + "/block", { method: "POST" });
      SharedNotifications.success("Cliente bloqueado.");
    }

    if (action === "unblock") {
      await adminFetch("/admin/clients/" + clientId + "/unblock", { method: "POST" });
      SharedNotifications.success("Cliente desbloqueado.");
    }

    if (action === "suspend") {
      await adminFetch("/admin/security/clients/" + clientId + "/suspend", { method: "POST" });
      SharedNotifications.success("Cliente suspenso.");
    }

    if (action === "unsuspend") {
      await adminFetch("/admin/security/clients/" + clientId + "/unsuspend", { method: "POST" });
      SharedNotifications.success("Cliente reativado.");
    }

    if (action !== "edit") {
      await loadData();
    }
  } catch (error) {
    SharedNotifications.error(error.message || "Ação falhou.");
  }
}

SharedNavigation.mountTopbar("#clients-topbar", {
  brand: "Admin / Clients",
  title: "Clientes",
  actions: [
    { label: "Admin Hub", href: "/admin-dashboard" },
    { label: "Legacy", href: "/static/admin/index.legacy.html" }
  ]
});

els.connectButton.addEventListener("click", connect);
els.reloadButton.addEventListener("click", () => connect());
els.clientForm.addEventListener("submit", submitForm);
els.newClientButton.addEventListener("click", resetForm);
els.cancelEditButton.addEventListener("click", resetForm);
els.searchInput.addEventListener("input", renderClients);
els.clientsTableBody.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  performTableAction(button.dataset.action, button.dataset.clientId);
});

const urlToken = readAdminTokenFromUrl();
const savedToken = urlToken || SharedAuth.getToken(STORAGE_KEY) || SharedAuth.getToken("provider-settings-admin-token");
if (savedToken) {
  els.adminToken.value = savedToken;
  state.token = savedToken;
  connect().catch(() => {});
} else {
  resetForm();
}
resetForm();
