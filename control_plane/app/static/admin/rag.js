      const STORAGE_KEY = "adminToken";
      const state = {
        token: "",
        hybridRag: null,
        vaults: [],
        receipts: [],
        violations: [],
        usage: []
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        authStatus: document.getElementById("authStatus"),
        ragApp: document.getElementById("ragApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statDocuments: document.getElementById("statDocuments"),
        statChunks: document.getElementById("statChunks"),
        statCollections: document.getElementById("statCollections"),
        statViolations: document.getElementById("statViolations"),
        hybridRagStats: document.getElementById("hybridRagStats"),
        ragDocStatus: document.getElementById("ragDocStatus"),
        hybridRagDebug: document.getElementById("hybridRagDebug"),
        vaultsTable: document.getElementById("vaultsTable"),
        vaultsDebug: document.getElementById("vaultsDebug"),
        receiptsTable: document.getElementById("receiptsTable"),
        receiptsDebug: document.getElementById("receiptsDebug"),
        violationsTable: document.getElementById("violationsTable"),
        violationsDebug: document.getElementById("violationsDebug"),
        usageTable: document.getElementById("usageTable"),
        usageDebug: document.getElementById("usageDebug")
      };

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }

      function shortId(value) {
        return typeof value === "string" ? value.substring(0, 8) : "N/A";
      }

      function num(value, fallback = 0) {
        return typeof value === "number" ? value : fallback;
      }

      function formatTimestamp(value) {
        if (!value) return "indisponivel";
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return "indisponivel";
        return parsed.toLocaleString("pt-BR");
      }

      function setConnected(connected) {
        els.ragApp.classList.toggle("hidden", !connected);
        els.loginPrompt.classList.toggle("hidden", connected);
        els.authStatus.textContent = connected ? "Conectado" : "Desconectado";
        els.authStatus.className = connected ? "badge success" : "badge warning";
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
        ["admin_token", "adminToken", "api_key", "apiKey"].forEach((key) => url.searchParams.delete(key));
        if (url.hash) {
          const hash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
          const hashParams = new URLSearchParams(hash);
          ["admin_token", "adminToken", "api_key", "apiKey"].forEach((key) => hashParams.delete(key));
          url.hash = hashParams.toString() ? "#" + hashParams.toString() : "";
        }
        window.history.replaceState({}, document.title, url.toString());
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

      function toggleDebug(id) {
        document.getElementById(id).classList.toggle("hidden");
      }

      function updateStats() {
        const data = state.hybridRag || {};
        els.statDocuments.textContent = num(data.total_documents).toLocaleString("pt-BR");
        els.statChunks.textContent = num(data.total_chunks).toLocaleString("pt-BR");
        els.statCollections.textContent = num(data.total_collections).toLocaleString("pt-BR");
        els.statViolations.textContent = String(state.violations.length);
      }

      function renderHybridRag() {
        const data = state.hybridRag;
        if (!data) {
          els.hybridRagStats.innerHTML = '<div class="empty-state">Sem dados de Enterprise RAG.</div>';
          els.ragDocStatus.textContent = "";
          return;
        }

        const storageMb = data.total_storage_bytes ? (data.total_storage_bytes / (1024 * 1024)).toFixed(2) : "0";
        els.hybridRagStats.innerHTML = `
          <div class="stat">
            <strong>RAG Enabled</strong>
            <span>${data.rag_enabled ? "YES" : "NO"}</span>
          </div>
          <div class="stat">
            <strong>Embedding Provider</strong>
            <span>${escapeHtml(data.embedding_provider || "N/A")}</span>
          </div>
          <div class="stat">
            <strong>Documents</strong>
            <span>${num(data.total_documents).toLocaleString("pt-BR")}</span>
          </div>
          <div class="stat">
            <strong>Chunks</strong>
            <span>${num(data.total_chunks).toLocaleString("pt-BR")}</span>
          </div>
          <div class="stat">
            <strong>Collections</strong>
            <span>${num(data.total_collections).toLocaleString("pt-BR")}</span>
          </div>
          <div class="stat">
            <strong>Clients with RAG</strong>
            <span>${num(data.clients_with_rag).toLocaleString("pt-BR")}</span>
          </div>
          <div class="stat">
            <strong>Storage</strong>
            <span>${storageMb} MB</span>
          </div>
        `;

        const status = data.documents_by_status || {};
        const statusHtml = Object.entries(status).map(([key, count]) => (
          `<span class="pill" style="margin-right: 6px;">${escapeHtml(key)}: ${escapeHtml(String(count))}</span>`
        )).join("");
        els.ragDocStatus.innerHTML = statusHtml ? "<strong>Docs by status:</strong> " + statusHtml : "";
      }

      function renderVaults() {
        const rows = Array.isArray(state.vaults) ? state.vaults : [];
        if (!rows.length) {
          els.vaultsTable.innerHTML = '<div class="empty-state">No vaults found.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Vault Name</th><th>Tenant</th><th>Retention</th></tr></thead><tbody>";
        rows.forEach((row) => {
          html += `
            <tr>
              <td>${escapeHtml(row.vault_name || "-")}</td>
              <td><code>${escapeHtml(row.tenant_id || "-")}</code></td>
              <td>${escapeHtml(String(row.retention_policy_days || 0))} days</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.vaultsTable.innerHTML = html;
      }

      function renderReceipts() {
        const rows = Array.isArray(state.receipts) ? state.receipts : [];
        if (!rows.length) {
          els.receiptsTable.innerHTML = '<div class="empty-state">No receipts found.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Session ID</th><th>Receipt Hash</th><th>Time</th></tr></thead><tbody>";
        rows.forEach((row) => {
          html += `
            <tr>
              <td><code>${escapeHtml(shortId(row.session_id))}</code></td>
              <td><code>${escapeHtml(String(row.receipt_hash || "").substring(0, 12))}...</code></td>
              <td>${formatTimestamp(row.created_at)}</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.receiptsTable.innerHTML = html;
      }

      function renderViolations() {
        const rows = Array.isArray(state.violations) ? state.violations : [];
        if (!rows.length) {
          els.violationsTable.innerHTML = '<div class="empty-state">No violations found.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Session ID</th><th>Violation</th><th>Action</th><th>Time</th></tr></thead><tbody>";
        rows.forEach((row) => {
          html += `
            <tr>
              <td><code>${escapeHtml(shortId(row.session_id))}</code></td>
              <td><span class="pill pill-danger">${escapeHtml(row.violation_type || "-")}</span></td>
              <td>${escapeHtml(row.action_taken || "-")}</td>
              <td>${formatTimestamp(row.created_at)}</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.violationsTable.innerHTML = html;
      }

      function renderUsage() {
        const rows = Array.isArray(state.usage) ? state.usage : [];
        if (!rows.length) {
          els.usageTable.innerHTML = '<div class="empty-state">Nenhum uso de RAG encontrado.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Cliente</th><th>ID</th><th>Docs</th><th>Storage (MB)</th><th>Consultas (Mes)</th><th>Paginas (Mes)</th></tr></thead><tbody>";
        rows.forEach((row) => {
          html += `
            <tr>
              <td><strong>${escapeHtml(row.client_name || "-")}</strong></td>
              <td><code>${escapeHtml(shortId(row.client_id))}</code></td>
              <td>${num(row.documents_count)}</td>
              <td>${num(row.storage_mb).toFixed(2)}</td>
              <td>${num(row.queries_month)}</td>
              <td>${num(row.pages_month)}</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.usageTable.innerHTML = html;
      }

      async function loadData() {
        const [hybridRag, vaults, receipts, violations, usage] = await Promise.all([
          adminFetch("/admin/hybrid/rag"),
          adminFetch("/admin/rag/vaults"),
          adminFetch("/admin/rag/receipts"),
          adminFetch("/admin/rag/violations"),
          adminFetch("/admin/rag/usage")
        ]);

        state.hybridRag = hybridRag || null;
        state.vaults = Array.isArray(vaults) ? vaults : [];
        state.receipts = Array.isArray(receipts) ? receipts : [];
        state.violations = Array.isArray(violations) ? violations : [];
        state.usage = Array.isArray(usage) ? usage : [];

        updateStats();
        renderHybridRag();
        renderVaults();
        renderReceipts();
        renderViolations();
        renderUsage();

        els.hybridRagDebug.textContent = JSON.stringify(state.hybridRag, null, 2);
        els.vaultsDebug.textContent = JSON.stringify(state.vaults, null, 2);
        els.receiptsDebug.textContent = JSON.stringify(state.receipts, null, 2);
        els.violationsDebug.textContent = JSON.stringify(state.violations, null, 2);
        els.usageDebug.textContent = JSON.stringify(state.usage, null, 2);
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
          SharedNotifications.success("RAG carregado com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      SharedNavigation.mountTopbar("#rag-topbar", {
        brand: "Admin",
        title: "RAG",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Portal", href: "/static/portal/index.html" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      document.getElementById("connectButton").addEventListener("click", connect);
      document.getElementById("reloadButton").addEventListener("click", () => loadData().catch((error) => SharedNotifications.error(error.message || "Falha ao recarregar.")));
      document.getElementById("hybridRagDebugToggle").addEventListener("click", () => toggleDebug("hybridRagDebug"));
      document.getElementById("vaultsDebugToggle").addEventListener("click", () => toggleDebug("vaultsDebug"));
      document.getElementById("receiptsDebugToggle").addEventListener("click", () => toggleDebug("receiptsDebug"));
      document.getElementById("violationsDebugToggle").addEventListener("click", () => toggleDebug("violationsDebug"));
      document.getElementById("usageDebugToggle").addEventListener("click", () => toggleDebug("usageDebug"));

      (function bootstrap() {
        const token = readAdminTokenFromUrl() || SharedAuth.getToken(STORAGE_KEY) || "";
        if (!token) return;
        els.adminToken.value = token;
        state.token = token;
        connect();
      })();
