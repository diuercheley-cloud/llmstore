      const STORAGE_KEY = "adminToken";
      const DEFAULT_FORM = {
        display_name: "",
        model_id: "",
        model_alias: "",
        inference_backend_id: "",
        provider: "llama.cpp",
        model_file: "",
        context_length: 4096,
        status: "configured",
        is_active: "true",
        is_default: "false",
        prompt_template: "",
        allow_reasoning: "",
        include_reasoning_default: "",
        allowed_plan_codes: "",
        metadata_json: ""
      };

      const state = {
        token: "",
        modelsPayload: null,
        models: [],
        backends: [],
        planAccess: [],
        filesPayload: null,
        editingModelId: null,
        selectedModel: null
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        connectButton: document.getElementById("connectButton"),
        reloadButton: document.getElementById("reloadButton"),
        authStatus: document.getElementById("authStatus"),
        modelsApp: document.getElementById("modelsApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statActive: document.getElementById("statActive"),
        statTotal: document.getElementById("statTotal"),
        statBackends: document.getElementById("statBackends"),
        statDefault: document.getElementById("statDefault"),
        editorTitle: document.getElementById("editorTitle"),
        submitButton: document.getElementById("submitButton"),
        cancelEditButton: document.getElementById("cancelEditButton"),
        modelForm: document.getElementById("modelForm"),
        newModelButton: document.getElementById("newModelButton"),
        inferenceBackendSelect: document.getElementById("inference_backend_id"),
        modelFilesList: document.getElementById("modelFilesList"),
        modelFilesInfo: document.getElementById("modelFilesInfo"),
        supplyChainSummary: document.getElementById("supplyChainSummary"),
        integritySummary: document.getElementById("integritySummary"),
        searchInput: document.getElementById("searchInput"),
        modelsTableBody: document.getElementById("modelsTableBody"),
        routeEmpty: document.getElementById("routeEmpty"),
        routeSection: document.getElementById("routeSection"),
        routeForm: document.getElementById("routeForm"),
        routeBackendSelect: document.getElementById("route_backend_id"),
        routesTableBody: document.getElementById("routesTableBody")
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
        try { return new Date(value).toLocaleString("pt-BR"); } catch (error) { return String(value); }
      }

      function parseList(text) {
        if (!text || !String(text).trim()) return null;
        const items = String(text).split(/\n|,/).map((item) => item.trim()).filter(Boolean);
        return items.length ? items : null;
      }

      function parseOptionalBoolean(value) {
        if (value === "") return null;
        return value === "true";
      }

      function parseJsonSafe(raw) {
        if (!raw || !String(raw).trim()) return null;
        JSON.parse(raw);
        return String(raw).trim();
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
        els.modelsApp.classList.toggle("hidden", !connected);
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
        const models = state.models;
        const activeCount = models.filter((item) => item.is_active).length;
        const defaultModel = models.find((item) => item.is_default);
        els.statActive.textContent = String(activeCount);
        els.statTotal.textContent = String(models.length);
        els.statBackends.textContent = String(state.backends.length);
        els.statDefault.textContent = defaultModel ? (defaultModel.model_alias || defaultModel.model_id) : "-";
      }

      function renderBackendOptions() {
        const options = ['<option value="">Nenhum</option>'].concat(
          state.backends.map((backend) => `<option value="${escapeHtml(backend.id)}">${escapeHtml(backend.name)} (${escapeHtml(backend.provider)})</option>`)
        );
        els.inferenceBackendSelect.innerHTML = options.join("");
        els.routeBackendSelect.innerHTML = options.join("");
      }

      function renderModelFiles() {
        const filesPayload = state.filesPayload || {};
        const files = Array.isArray(filesPayload.files) ? filesPayload.files : [];
        els.modelFilesList.innerHTML = files.map((file) => `<option value="${escapeHtml(file.name || file.path || file)}"></option>`).join("");
        if (!files.length) {
          els.modelFilesInfo.innerHTML = `<div class="subtle">${escapeHtml(filesPayload.warning || "Nenhum arquivo de modelo disponível.")}</div>`;
          return;
        }
        els.modelFilesInfo.innerHTML =
          `<div class="subtle">Diretório: <code>${escapeHtml(filesPayload.models_dir || "-")}</code></div>` +
          `<div class="subtle" style="margin-top:8px;">${files.slice(0, 12).map((file) => `<code>${escapeHtml(file.name || file.path || file)}</code>`).join(" · ")}</div>`;
      }

      function inferAllowedPlanCodes(model) {
        const keys = [model.model_alias, model.model_id].filter(Boolean);
        return state.planAccess
          .filter((plan) => {
            try {
              const parsed = JSON.parse(plan.allowed_models_json || "[]");
              return Array.isArray(parsed) && parsed.some((item) => keys.includes(item));
            } catch (error) {
              return false;
            }
          })
          .map((plan) => plan.billing_plan_code);
      }

      function filteredModels() {
        const query = els.searchInput.value.trim().toLowerCase();
        if (!query) return state.models;
        return state.models.filter((model) => {
          const haystack = [
            model.display_name,
            model.model_id,
            model.model_alias,
            model.provider,
            model.backend_name,
            model.backend_url
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        });
      }

      function renderModelsTable() {
        const models = filteredModels();
        if (!models.length) {
          els.modelsTableBody.innerHTML = '<tr><td colspan="6"><div class="empty-state">Nenhum modelo encontrado.</div></td></tr>';
          return;
        }
        els.modelsTableBody.innerHTML = models.map((model) => {
          const activeBadge = model.is_active ? '<span class="badge success">active</span>' : '<span class="badge warning">disabled</span>';
          const defaultBadge = model.is_default ? ' <span class="badge info">default</span>' : '';
          return `
            <tr>
              <td>
                <strong>${escapeHtml(model.display_name || model.model_alias || model.model_id)}</strong>${defaultBadge}<br />
                <span class="code">${escapeHtml(model.model_id)}</span><br />
                <span class="subtle">${escapeHtml(model.model_alias || "-")}</span>
              </td>
              <td>
                <div>${escapeHtml(model.backend_name || "-")}</div>
                <div class="subtle">${escapeHtml(model.provider || "-")}</div>
              </td>
              <td>
                ${activeBadge}
                <div class="subtle" style="margin-top:6px;">${escapeHtml(model.status || "-")}</div>
              </td>
              <td>
                <div>${Number(model.context_length || 0).toLocaleString("pt-BR")}</div>
                <div class="subtle">${escapeHtml(model.model_file || "-")}</div>
              </td>
              <td>
                <div>${Array.isArray(model.routes) ? model.routes.length : 0}</div>
                <div class="subtle">${Array.isArray(model.routes) ? model.routes.map((route) => escapeHtml(route.backend_name || shortId(route.backend_id))).join(", ") : "-"}</div>
              </td>
              <td>
                <div class="table-actions">
                  <button class="button secondary" type="button" data-action="edit" data-model-id="${escapeHtml(model.id)}">Editar</button>
                  <button class="button secondary" type="button" data-action="default" data-model-id="${escapeHtml(model.id)}">Default</button>
                  <button class="button secondary" type="button" data-action="${model.is_active ? "disable" : "enable"}" data-model-id="${escapeHtml(model.id)}">
                    ${model.is_active ? "Desativar" : "Ativar"}
                  </button>
                  <button class="button danger" type="button" data-action="delete" data-model-id="${escapeHtml(model.id)}">Remover</button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }

      function resetForm() {
        state.editingModelId = null;
        state.selectedModel = null;
        els.editorTitle.textContent = "Criar modelo";
        els.submitButton.textContent = "Criar modelo";
        els.cancelEditButton.classList.add("hidden");
        document.getElementById("model_id").disabled = false;
        Object.entries(DEFAULT_FORM).forEach(([key, value]) => {
          document.getElementById(key).value = value;
        });
        renderRoutesSection();
      }

      function populateForm(model) {
        state.editingModelId = String(model.id);
        state.selectedModel = model;
        els.editorTitle.textContent = "Editar modelo";
        els.submitButton.textContent = "Salvar alterações";
        els.cancelEditButton.classList.remove("hidden");
        document.getElementById("model_id").disabled = true;
        document.getElementById("display_name").value = model.display_name || "";
        document.getElementById("model_id").value = model.model_id || "";
        document.getElementById("model_alias").value = model.model_alias || "";
        document.getElementById("inference_backend_id").value = model.inference_backend_id || "";
        document.getElementById("provider").value = model.provider || "llama.cpp";
        document.getElementById("model_file").value = model.model_file || "";
        document.getElementById("context_length").value = model.context_length || 4096;
        document.getElementById("status").value = model.status || "configured";
        document.getElementById("is_active").value = model.is_active ? "true" : "false";
        document.getElementById("is_default").value = model.is_default ? "true" : "false";
        document.getElementById("prompt_template").value = model.prompt_template || "";
        document.getElementById("allow_reasoning").value = model.allow_reasoning == null ? "" : String(model.allow_reasoning);
        document.getElementById("include_reasoning_default").value = model.include_reasoning_default == null ? "" : String(model.include_reasoning_default);
        document.getElementById("allowed_plan_codes").value = inferAllowedPlanCodes(model).join("\n");
        document.getElementById("metadata_json").value = model.metadata_json || "";
        renderRoutesSection();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }

      function buildCreatePayload() {
        return {
          display_name: document.getElementById("display_name").value.trim() || null,
          model_id: document.getElementById("model_id").value.trim(),
          model_alias: document.getElementById("model_alias").value.trim() || null,
          inference_backend_id: document.getElementById("inference_backend_id").value || null,
          provider: document.getElementById("provider").value,
          model_file: document.getElementById("model_file").value.trim(),
          context_length: Number(document.getElementById("context_length").value),
          is_active: document.getElementById("is_active").value === "true",
          is_default: document.getElementById("is_default").value === "true",
          status: document.getElementById("status").value.trim() || "configured",
          prompt_template: document.getElementById("prompt_template").value || null,
          allow_reasoning: parseOptionalBoolean(document.getElementById("allow_reasoning").value),
          include_reasoning_default: parseOptionalBoolean(document.getElementById("include_reasoning_default").value),
          allowed_plan_codes: parseList(document.getElementById("allowed_plan_codes").value),
          metadata_json: parseJsonSafe(document.getElementById("metadata_json").value),
          backend_routes: []
        };
      }

      function buildPatchPayload() {
        return {
          display_name: document.getElementById("display_name").value.trim() || null,
          model_alias: document.getElementById("model_alias").value.trim() || null,
          inference_backend_id: document.getElementById("inference_backend_id").value || null,
          provider: document.getElementById("provider").value,
          model_file: document.getElementById("model_file").value.trim(),
          context_length: Number(document.getElementById("context_length").value),
          is_active: document.getElementById("is_active").value === "true",
          is_default: document.getElementById("is_default").value === "true",
          status: document.getElementById("status").value.trim() || "configured",
          prompt_template: document.getElementById("prompt_template").value || null,
          allow_reasoning: parseOptionalBoolean(document.getElementById("allow_reasoning").value),
          include_reasoning_default: parseOptionalBoolean(document.getElementById("include_reasoning_default").value),
          allowed_plan_codes: parseList(document.getElementById("allowed_plan_codes").value),
          metadata_json: parseJsonSafe(document.getElementById("metadata_json").value)
        };
      }

      function renderRoutesSection() {
        const model = state.selectedModel;
        if (!model) {
          els.routeEmpty.classList.remove("hidden");
          els.routeSection.classList.add("hidden");
          els.routesTableBody.innerHTML = "";
          return;
        }
        els.routeEmpty.classList.add("hidden");
        els.routeSection.classList.remove("hidden");
        const routes = Array.isArray(model.routes) ? model.routes : [];
        if (!routes.length) {
          els.routesTableBody.innerHTML = '<tr><td colspan="6">Nenhuma rota configurada.</td></tr>';
          return;
        }
        els.routesTableBody.innerHTML = routes.map((route) => `
          <tr>
            <td>${escapeHtml(route.backend_name || "-")}<br /><span class="code">${escapeHtml(route.backend_id)}</span></td>
            <td>${escapeHtml(route.provider || "-")}</td>
            <td>${route.priority}</td>
            <td>${route.weight}</td>
            <td><span class="badge ${route.state === "healthy" ? "success" : route.state === "disabled" ? "warning" : "info"}">${escapeHtml(route.state)}</span></td>
            <td>
              <div class="table-actions">
                <button class="button secondary" type="button" data-route-action="edit" data-backend-id="${escapeHtml(route.backend_id)}">Editar</button>
                <button class="button danger" type="button" data-route-action="delete" data-backend-id="${escapeHtml(route.backend_id)}">Remover</button>
              </div>
            </td>
          </tr>
        `).join("");
      }

      function renderSupplyChain(status, registry) {
        const items = Array.isArray(registry?.items) ? registry.items : [];
        const risk = status?.model_risk_summary || {};
        els.supplyChainSummary.innerHTML =
          `<div>registry_total=${status?.registry_total || items.length || 0}</div>` +
          `<div>trusted=${status?.trust_states?.trusted || 0} pending=${status?.trust_states?.pending || 0} blocked=${risk.blocked || 0}</div>` +
          `<div>mode=${String(status?.enforcement_mode || "report_only").toUpperCase()} bundles=${status?.bundle_total || 0}</div>`;
      }

      function renderIntegrity(status) {
        if (!status) {
          els.integritySummary.textContent = "Sem dados de integridade.";
          return;
        }
        els.integritySummary.innerHTML =
          `quarantined=${(status.quarantined_models || []).length} · ` +
          `missing=${(status.missing_models || []).length} · ` +
          `drift=${(status.drift_models || []).length} · ` +
          `alias_drift=${(status.alias_drift_models || []).length} · ` +
          `peers=${status.federated_integrity?.peer_count || 0}`;
      }

      async function loadData() {
        const [modelsPayload, filesPayload, supplyChainStatus, supplyChainRegistry, integrityStatus] = await Promise.all([
          adminFetch("/admin/models"),
          adminFetch("/admin/models/files"),
          adminFetch("/admin/models/supply-chain/status"),
          adminFetch("/admin/models/supply-chain/registry"),
          adminFetch("/admin/models/integrity/status")
        ]);
        state.modelsPayload = modelsPayload;
        state.models = Array.isArray(modelsPayload.registry) ? modelsPayload.registry : [];
        state.backends = Array.isArray(modelsPayload.backends) ? modelsPayload.backends : [];
        state.planAccess = Array.isArray(modelsPayload.plan_access) ? modelsPayload.plan_access : [];
        state.filesPayload = filesPayload;
        renderBackendOptions();
        renderModelFiles();
        renderSupplyChain(supplyChainStatus, supplyChainRegistry);
        renderIntegrity(integrityStatus);
        updateStats();
        renderModelsTable();
        if (state.editingModelId) {
          state.selectedModel = state.models.find((item) => item.id === state.editingModelId) || null;
          if (state.selectedModel) populateForm(state.selectedModel);
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
          SharedNotifications.success("Modelos carregados com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      async function submitModel(event) {
        event.preventDefault();
        try {
          if (state.editingModelId) {
            await adminFetch("/admin/models/" + state.editingModelId, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(buildPatchPayload())
            });
            SharedNotifications.success("Modelo atualizado.");
          } else {
            await adminFetch("/admin/models", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(buildCreatePayload())
            });
            SharedNotifications.success("Modelo criado.");
          }
          resetForm();
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao salvar modelo.");
        }
      }

      async function handleModelAction(action, modelId) {
        const model = state.models.find((item) => item.id === modelId);
        if (!model) return;
        try {
          if (action === "edit") {
            populateForm(model);
            return;
          }
          if (action === "default") {
            await adminFetch("/admin/models/" + modelId + "/set-default", { method: "POST" });
            SharedNotifications.success("Modelo default atualizado.");
          }
          if (action === "enable") {
            await adminFetch("/admin/models/" + modelId + "/enable", { method: "POST" });
            SharedNotifications.success("Modelo ativado.");
          }
          if (action === "disable") {
            await adminFetch("/admin/models/" + modelId + "/disable", { method: "POST" });
            SharedNotifications.success("Modelo desativado.");
          }
          if (action === "delete") {
            if (!window.confirm("Remover este modelo?")) return;
            await adminFetch("/admin/models/" + modelId, {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ confirm_route_removal: true, mode: "auto" })
            });
            SharedNotifications.success("Modelo removido.");
            if (state.editingModelId === modelId) resetForm();
          }
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Ação de modelo falhou.");
        }
      }

      async function submitRoute(event) {
        event.preventDefault();
        if (!state.selectedModel) return;
        try {
          await adminFetch("/admin/models/" + state.selectedModel.id + "/routes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              inference_backend_id: document.getElementById("route_backend_id").value,
              priority: Number(document.getElementById("route_priority").value),
              weight: Number(document.getElementById("route_weight").value),
              state: document.getElementById("route_state").value
            })
          });
          SharedNotifications.success("Rota adicionada.");
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao adicionar rota.");
        }
      }

      async function handleRouteAction(action, backendId) {
        if (!state.selectedModel) return;
        const route = (state.selectedModel.routes || []).find((item) => item.backend_id === backendId);
        if (!route) return;
        try {
          if (action === "delete") {
            if (!window.confirm("Remover esta rota?")) return;
            await adminFetch("/admin/models/" + state.selectedModel.id + "/routes/" + backendId, { method: "DELETE" });
            SharedNotifications.success("Rota removida.");
          }
          if (action === "edit") {
            const priority = Number(window.prompt("Priority", String(route.priority)));
            if (!priority) return;
            const weight = Number(window.prompt("Weight", String(route.weight)));
            if (!weight) return;
            const stateValue = window.prompt("State (healthy|degraded|unhealthy|disabled)", route.state);
            if (!stateValue) return;
            await adminFetch("/admin/models/" + state.selectedModel.id + "/routes/" + backendId, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ priority: priority, weight: weight, state: stateValue })
            });
            SharedNotifications.success("Rota atualizada.");
          }
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao atualizar rota.");
        }
      }

      SharedNavigation.mountTopbar("#models-topbar", {
        brand: "Admin / Models",
        title: "Modelos",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Backends", href: "/static/admin/backends.html" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      els.connectButton.addEventListener("click", connect);
      els.reloadButton.addEventListener("click", connect);
      els.modelForm.addEventListener("submit", submitModel);
      els.routeForm.addEventListener("submit", submitRoute);
      els.newModelButton.addEventListener("click", resetForm);
      els.cancelEditButton.addEventListener("click", resetForm);
      els.searchInput.addEventListener("input", renderModelsTable);
      els.modelsTableBody.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        handleModelAction(button.dataset.action, button.dataset.modelId);
      });
      els.routesTableBody.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-route-action]");
        if (!button) return;
        handleRouteAction(button.dataset.routeAction, button.dataset.backendId);
      });

      resetForm();
      const urlToken = readAdminTokenFromUrl();
      const savedToken = urlToken || SharedAuth.getToken(STORAGE_KEY) || SharedAuth.getToken("provider-settings-admin-token");
      if (savedToken) {
        els.adminToken.value = savedToken;
        state.token = savedToken;
        connect().catch(() => {});
      }
