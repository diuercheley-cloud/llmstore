      const STORAGE_KEY = "adminToken";
      const DEFAULT_FORM = {
        name: "",
        provider: "llama.cpp",
        backend_url: "",
        healthcheck_path: "/health",
        is_active: "true",
        is_default: "false",
        status: "configured",
        max_parallel_requests: 1,
        metadata_json: ""
      };

      const state = {
        token: "",
        backends: [],
        hybridProviders: [],
        routing: null,
        editingBackendId: null
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        connectButton: document.getElementById("connectButton"),
        reloadButton: document.getElementById("reloadButton"),
        authStatus: document.getElementById("authStatus"),
        backendsApp: document.getElementById("backendsApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statTotal: document.getElementById("statTotal"),
        statHealthy: document.getElementById("statHealthy"),
        statProviders: document.getElementById("statProviders"),
        statCircuit: document.getElementById("statCircuit"),
        editorTitle: document.getElementById("editorTitle"),
        submitButton: document.getElementById("submitButton"),
        cancelEditButton: document.getElementById("cancelEditButton"),
        backendForm: document.getElementById("backendForm"),
        newBackendButton: document.getElementById("newBackendButton"),
        testConnectionButton: document.getElementById("testConnectionButton"),
        listModelsButton: document.getElementById("listModelsButton"),
        resetCircuitButton: document.getElementById("resetCircuitButton"),
        healthSummary: document.getElementById("healthSummary"),
        providersSummary: document.getElementById("providersSummary"),
        debugOutput: document.getElementById("debugOutput"),
        searchInput: document.getElementById("searchInput"),
        backendsTableBody: document.getElementById("backendsTableBody"),
        providersTableBody: document.getElementById("providersTableBody"),
        routingSummary: document.getElementById("routingSummary"),
        routingTableBody: document.getElementById("routingTableBody")
      };

      function escapeHtml(value) {
        return String(value == null ? "" : value)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
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

      function setConnected(connected) {
        els.backendsApp.classList.toggle("hidden", !connected);
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

      function resetForm() {
        state.editingBackendId = null;
        els.editorTitle.textContent = "Criar backend";
        els.submitButton.textContent = "Criar backend";
        els.cancelEditButton.classList.add("hidden");
        Object.entries(DEFAULT_FORM).forEach(([key, value]) => {
          document.getElementById(key).value = value;
        });
      }

      function populateForm(backend) {
        state.editingBackendId = backend.id;
        els.editorTitle.textContent = "Editar backend";
        els.submitButton.textContent = "Salvar alterações";
        els.cancelEditButton.classList.remove("hidden");
        document.getElementById("name").value = backend.name || "";
        document.getElementById("provider").value = backend.provider || "llama.cpp";
        document.getElementById("backend_url").value = backend.backend_url || "";
        document.getElementById("healthcheck_path").value = backend.healthcheck_path || "/health";
        document.getElementById("is_active").value = backend.is_active ? "true" : "false";
        document.getElementById("is_default").value = backend.is_default ? "true" : "false";
        document.getElementById("status").value = backend.status || "configured";
        document.getElementById("max_parallel_requests").value = backend.max_parallel_requests || 1;
        document.getElementById("metadata_json").value = backend.metadata_json || "";
        window.scrollTo({ top: 0, behavior: "smooth" });
      }

      function filteredBackends() {
        const query = els.searchInput.value.trim().toLowerCase();
        if (!query) return state.backends;
        return state.backends.filter((backend) => {
          const haystack = [
            backend.name,
            backend.provider,
            backend.backend_url,
            backend.service_name,
            backend.status
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        });
      }

      function updateStats() {
        const healthy = state.backends.filter((item) => item.health && item.health.ok).length;
        els.statTotal.textContent = String(state.backends.length);
        els.statHealthy.textContent = String(healthy);
        els.statProviders.textContent = String(state.hybridProviders.length);
      }

      function renderBackendsTable() {
        const backends = filteredBackends();
        if (!backends.length) {
          els.backendsTableBody.innerHTML = '<tr><td colspan="6"><div class="empty-state">Nenhum backend encontrado.</div></td></tr>';
          return;
        }
        els.backendsTableBody.innerHTML = backends.map((backend) => {
          const health = backend.health || {};
          return `
            <tr>
              <td>
                <strong>${escapeHtml(backend.name)}</strong>${backend.is_default ? ' <span class="badge info">default</span>' : ''}<br />
                <span class="subtle">${escapeHtml(backend.provider)}</span><br />
                <span class="subtle">${escapeHtml(backend.backend_url)}</span>
              </td>
              <td>
                <span class="badge ${backend.is_active ? 'success' : 'warning'}">${backend.is_active ? 'active' : 'inactive'}</span>
                <div class="subtle" style="margin-top:6px;">${escapeHtml(backend.status || '-')}</div>
              </td>
              <td>
                <span class="badge ${health.ok ? 'success' : 'danger'}">${health.ok ? 'healthy' : 'down'}</span>
                <div class="subtle" style="margin-top:6px;">lat=${health.latency_ms == null ? '-' : health.latency_ms + 'ms'}</div>
              </td>
              <td>
                <div>${escapeHtml(backend.service_name || '-')}</div>
                <div class="subtle">docker=${backend.docker && backend.docker.compose_available ? 'yes' : 'no'}</div>
              </td>
              <td>${backend.current_running || 0} / ${backend.max_parallel_requests || 0}</td>
              <td>
                <div class="table-actions">
                  <button class="button secondary" type="button" data-action="edit" data-backend-id="${escapeHtml(backend.id)}">Editar</button>
                  <button class="button secondary" type="button" data-action="health" data-backend-id="${escapeHtml(backend.id)}">Health</button>
                  <button class="button secondary" type="button" data-action="logs" data-backend-id="${escapeHtml(backend.id)}">Logs</button>
                  <button class="button secondary" type="button" data-action="start" data-backend-id="${escapeHtml(backend.id)}">Start</button>
                  <button class="button secondary" type="button" data-action="stop" data-backend-id="${escapeHtml(backend.id)}">Stop</button>
                  <button class="button secondary" type="button" data-action="restart" data-backend-id="${escapeHtml(backend.id)}">Restart</button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }

      function renderProvidersTable() {
        const providers = state.hybridProviders;
        if (!providers.length) {
          els.providersTableBody.innerHTML = '<tr><td colspan="6">Sem providers disponíveis.</td></tr>';
          els.providersSummary.textContent = "Sem dados de providers.";
          return;
        }
        els.providersSummary.innerHTML = providers.some((p) => p.enabled && !p.configured)
          ? "Há providers habilitados sem configuração completa."
          : "Providers híbridos carregados.";
        els.providersTableBody.innerHTML = providers.map((provider) => {
          const caps = Object.entries(provider.capabilities || {}).filter(([, value]) => value === true).map(([key]) => key).join(", ") || "none";
          return `
            <tr>
              <td><strong>${escapeHtml(provider.provider_id)}</strong></td>
              <td>${escapeHtml(provider.provider_type || "-")}</td>
              <td><span class="badge ${provider.enabled ? 'success' : 'warning'}">${provider.enabled ? 'YES' : 'NO'}</span></td>
              <td><span class="badge ${provider.configured ? 'success' : 'danger'}">${provider.configured ? 'YES' : 'NO'}</span></td>
              <td><span class="badge ${provider.healthy === true ? 'success' : provider.healthy === false ? 'danger' : 'warning'}">${provider.healthy === true ? 'HEALTHY' : provider.healthy === false ? 'DOWN' : 'UNKNOWN'}</span></td>
              <td>${escapeHtml(caps)}</td>
            </tr>
          `;
        }).join("");
      }

      function renderRoutingTable() {
        const routing = state.routing || { summary: {}, models: [] };
        const summary = routing.summary || {};
        els.routingSummary.textContent = `healthy=${summary.healthy || 0} degraded=${summary.degraded || 0} unhealthy=${summary.unhealthy || 0} disabled=${summary.disabled || 0}`;
        const rows = [];
        (routing.models || []).forEach((model) => {
          (model.routes || []).forEach((route) => rows.push({
            model: model.model_alias || model.model_id,
            backend_name: route.backend_name,
            provider: route.provider,
            priority: route.priority,
            weight: route.weight,
            state: route.state
          }));
        });
        if (!rows.length) {
          els.routingTableBody.innerHTML = '<tr><td colspan="6">Sem rotas disponíveis.</td></tr>';
          return;
        }
        els.routingTableBody.innerHTML = rows.map((row) => `
          <tr>
            <td>${escapeHtml(row.model || "-")}</td>
            <td>${escapeHtml(row.backend_name || "-")}</td>
            <td>${escapeHtml(row.provider || "-")}</td>
            <td>${row.priority}</td>
            <td>${row.weight}</td>
            <td><span class="badge ${row.state === 'healthy' ? 'success' : row.state === 'disabled' ? 'warning' : 'info'}">${escapeHtml(row.state)}</span></td>
          </tr>
        `).join("");
      }

      function buildPayloadFromForm() {
        return {
          name: document.getElementById("name").value.trim(),
          provider: document.getElementById("provider").value,
          backend_url: document.getElementById("backend_url").value.trim(),
          healthcheck_path: document.getElementById("healthcheck_path").value.trim() || "/health",
          is_active: document.getElementById("is_active").value === "true",
          is_default: document.getElementById("is_default").value === "true",
          status: document.getElementById("status").value.trim() || "configured",
          max_parallel_requests: Number(document.getElementById("max_parallel_requests").value),
          metadata_json: document.getElementById("metadata_json").value.trim() || null
        };
      }

      async function loadData() {
        const [backends, providers, routing, health] = await Promise.all([
          adminFetch("/admin/backends"),
          adminFetch("/admin/hybrid/providers"),
          adminFetch("/admin/backends/routing"),
          adminFetch("/admin/backends/health")
        ]);
        state.backends = Array.isArray(backends) ? backends : [];
        state.hybridProviders = Array.isArray(providers) ? providers : [];
        state.routing = routing || {};
        updateStats();
        renderBackendsTable();
        renderProvidersTable();
        renderRoutingTable();
        const healthRows = Array.isArray(health.backends) ? health.backends : [];
        els.healthSummary.textContent = `generated_at=${health.generated_at || '-'} · healthy=${healthRows.filter((item) => item.ok).length}/${healthRows.length}`;
        if (state.editingBackendId) {
          const current = state.backends.find((item) => item.id === state.editingBackendId);
          if (current) populateForm(current);
        }
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
          SharedNotifications.success("Backends carregados com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      async function submitBackend(event) {
        event.preventDefault();
        try {
          const payload = buildPayloadFromForm();
          if (state.editingBackendId) {
            await adminFetch("/admin/backends/" + state.editingBackendId, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload)
            });
            SharedNotifications.success("Backend atualizado.");
          } else {
            await adminFetch("/admin/backends", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload)
            });
            SharedNotifications.success("Backend criado.");
          }
          resetForm();
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao salvar backend.");
        }
      }

      async function testConnection() {
        try {
          const payload = buildPayloadFromForm();
          const response = await adminFetch("/admin/backends/test-connection", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          els.debugOutput.textContent = JSON.stringify(response, null, 2);
          SharedNotifications.info("Teste de conexão concluído.");
        } catch (error) {
          SharedNotifications.error(error.message || "Teste de conexão falhou.");
        }
      }

      async function listModels() {
        try {
          const payload = buildPayloadFromForm();
          const response = await adminFetch("/admin/backends/list-models", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          els.debugOutput.textContent = JSON.stringify(response, null, 2);
          SharedNotifications.info("Listagem de modelos concluída.");
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao listar modelos.");
        }
      }

      async function handleBackendAction(action, backendId) {
        const backend = state.backends.find((item) => item.id === backendId);
        if (!backend) return;
        try {
          if (action === "edit") {
            populateForm(backend);
            return;
          }
          if (action === "health") {
            const response = await adminFetch("/admin/backends/" + backendId + "/health");
            els.debugOutput.textContent = JSON.stringify(response, null, 2);
            SharedNotifications.info("Health carregado.");
          }
          if (action === "logs") {
            const response = await adminFetch("/admin/backends/" + backendId + "/logs?tail=100");
            els.debugOutput.textContent = JSON.stringify(response, null, 2);
            SharedNotifications.info("Logs carregados.");
          }
          if (action === "start" || action === "stop" || action === "restart") {
            const response = await adminFetch("/admin/backends/" + backendId + "/" + action, { method: "POST" });
            els.debugOutput.textContent = JSON.stringify(response, null, 2);
            SharedNotifications.success("Ação executada: " + action);
            await loadData();
          }
        } catch (error) {
          SharedNotifications.error(error.message || "Falha na ação do backend.");
        }
      }

      async function resetCircuitBreaker() {
        try {
          const response = await adminFetch("/admin/backends/circuit-breaker/reset", { method: "POST" });
          els.debugOutput.textContent = JSON.stringify(response, null, 2);
          els.statCircuit.textContent = "reset";
          SharedNotifications.success("Circuit breaker resetado.");
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao resetar circuit breaker.");
        }
      }

      SharedNavigation.mountTopbar("#backends-topbar", {
        brand: "Admin / Backends",
        title: "Backends",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Models", href: "/static/admin/models.html" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      els.connectButton.addEventListener("click", connect);
      els.reloadButton.addEventListener("click", connect);
      els.backendForm.addEventListener("submit", submitBackend);
      els.newBackendButton.addEventListener("click", resetForm);
      els.cancelEditButton.addEventListener("click", resetForm);
      els.testConnectionButton.addEventListener("click", testConnection);
      els.listModelsButton.addEventListener("click", listModels);
      els.resetCircuitButton.addEventListener("click", resetCircuitBreaker);
      els.searchInput.addEventListener("input", renderBackendsTable);
      els.backendsTableBody.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        handleBackendAction(button.dataset.action, button.dataset.backendId);
      });

      resetForm();
      const urlToken = readAdminTokenFromUrl();
      const savedToken = urlToken || SharedAuth.getToken(STORAGE_KEY) || SharedAuth.getToken("provider-settings-admin-token");
      if (savedToken) {
        els.adminToken.value = savedToken;
        state.token = savedToken;
        connect().catch(() => {});
      }
