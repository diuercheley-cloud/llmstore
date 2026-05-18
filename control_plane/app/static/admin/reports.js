      const STORAGE_KEY = "adminToken";
      const state = {
        token: "",
        schedules: [],
        deliveries: null,
        federationClusters: null,
        federationOverview: null,
        federationCompare: null,
        previewLoaded: false
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        authStatus: document.getElementById("authStatus"),
        reportsApp: document.getElementById("reportsApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statSchedules: document.getElementById("statSchedules"),
        statDeliveries: document.getElementById("statDeliveries"),
        statClusters: document.getElementById("statClusters"),
        statPreview: document.getElementById("statPreview")
      };

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }

      function num(value, fallback = 0) {
        return typeof value === "number" ? value : fallback;
      }

      function setConnected(connected) {
        els.reportsApp.classList.toggle("hidden", !connected);
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

      function getExecutiveReportQuery() {
        return "?hours=24";
      }

      function updateStats() {
        const counts = (state.deliveries && state.deliveries.counts) || {};
        const overview = state.federationOverview || {};
        els.statSchedules.textContent = String(state.schedules.length);
        els.statDeliveries.textContent = String(num(counts.sent) + num(counts.dry_run) + num(counts.failed));
        els.statClusters.textContent = String(num(overview.cluster_count || overview.total_clusters || 0));
        els.statPreview.textContent = state.previewLoaded ? "ready" : "pending";
      }

      async function refreshExecutiveReportPreview() {
        const status = document.getElementById("commReportStatus");
        const preview = document.getElementById("commReportPreview");
        status.textContent = "Loading preview...";
        try {
          const res = await fetch("/admin/routing/executive-dashboard/export/preview" + getExecutiveReportQuery(), {
            headers: adminHeaders()
          });
          const body = await res.text();
          if (!res.ok) throw new Error(body || res.statusText);
          preview.srcdoc = body;
          status.textContent = "Preview updated at " + new Date().toLocaleTimeString() + ".";
          state.previewLoaded = true;
          updateStats();
        } catch (error) {
          status.textContent = "Preview error: " + error.message;
        }
      }

      async function downloadExecutiveReport(format) {
        const url = "/admin/routing/executive-dashboard/export?format=" + encodeURIComponent(format) + "&hours=24";
        const res = await fetch(url, { headers: adminHeaders() });
        if (format === "pdf" && res.status === 501) {
          const data = await res.json();
          alert((data.detail && data.detail.message) || "PDF export unsupported. Use HTML export.");
          return;
        }
        if (!res.ok) throw new Error(res.statusText);
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = "executive-report." + format;
        link.click();
        URL.revokeObjectURL(objectUrl);
      }

      function renderReportSchedules(schedules) {
        const host = document.getElementById("reportSchedulesList");
        if (!schedules || schedules.length === 0) {
          host.innerHTML = '<p class="muted">No schedules configured.</p>';
          document.getElementById("commReportDebug").textContent = "[]";
          return;
        }
        let html = '<table><thead><tr><th>Name</th><th>Frequency</th><th>Format</th><th>Recipients</th><th>Next Run</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
        schedules.forEach((schedule) => {
          html += `<tr>
            <td>${escapeHtml(schedule.name)}</td>
            <td>${escapeHtml(schedule.frequency)}</td>
            <td>${escapeHtml(schedule.format)}</td>
            <td>${escapeHtml((schedule.recipients_json || []).join(", ") || "-")}</td>
            <td>${escapeHtml(schedule.next_run_at || "-")}</td>
            <td>${schedule.enabled ? '<span class="pill pill-success">enabled</span>' : '<span class="pill">disabled</span>'}</td>
            <td style="display:flex;gap:4px;flex-wrap:wrap;">
              <button class="button secondary" type="button" data-action="run-now" data-id="${escapeHtml(schedule.id)}">Run now</button>
              <button class="button secondary" type="button" data-action="send-test" data-id="${escapeHtml(schedule.id)}">Send test email</button>
              <button class="button secondary" type="button" data-action="${schedule.enabled ? "disable" : "enable"}" data-id="${escapeHtml(schedule.id)}">${schedule.enabled ? "Disable" : "Enable"}</button>
            </td>
          </tr>`;
        });
        html += "</tbody></table>";
        host.innerHTML = html;
        document.getElementById("commReportDebug").textContent = JSON.stringify(schedules, null, 2);
      }

      async function fetchReportSchedules() {
        const schedules = await adminFetch("/admin/routing/executive-dashboard/report-schedules");
        state.schedules = Array.isArray(schedules) ? schedules : [];
        renderReportSchedules(state.schedules);
        updateStats();
      }

      async function createReportSchedule() {
        const body = {
          name: document.getElementById("reportScheduleName").value.trim() || "Monthly executive report",
          frequency: document.getElementById("reportScheduleFrequency").value,
          day_of_month: document.getElementById("reportScheduleDayOfMonth").value ? parseInt(document.getElementById("reportScheduleDayOfMonth").value, 10) : null,
          day_of_week: document.getElementById("reportScheduleDayOfWeek").value ? parseInt(document.getElementById("reportScheduleDayOfWeek").value, 10) : null,
          hour_utc: parseInt(document.getElementById("reportScheduleHourUtc").value || "8", 10),
          recipients_json: (document.getElementById("reportScheduleRecipients").value || "").split(",").map((value) => value.trim()).filter(Boolean),
          format: document.getElementById("reportScheduleFormat").value,
          filters_json: { hours: 24 }
        };
        await adminFetch("/admin/routing/executive-dashboard/report-schedules", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        await fetchReportSchedules();
        await fetchReportDeliveries();
      }

      async function runReportScheduleNow(id) {
        const data = await adminFetch("/admin/routing/executive-dashboard/report-schedules/" + id + "/run-now", {
          method: "POST"
        });
        document.getElementById("commReportDebug").textContent = JSON.stringify(data, null, 2);
        if (data.preview_html) document.getElementById("commReportPreview").srcdoc = data.preview_html;
        await fetchReportSchedules();
        await fetchReportDeliveries();
      }

      async function sendTestReportEmail(id) {
        const data = await adminFetch("/admin/routing/executive-dashboard/report-schedules/" + id + "/send-test-email", {
          method: "POST"
        });
        document.getElementById("commReportDebug").textContent = JSON.stringify(data, null, 2);
        await fetchReportDeliveries();
      }

      async function disableReportSchedule(id) {
        await adminFetch("/admin/routing/executive-dashboard/report-schedules/" + id + "/disable", {
          method: "POST"
        });
        await fetchReportSchedules();
      }

      async function enableReportSchedule(id) {
        await adminFetch("/admin/routing/executive-dashboard/report-schedules/" + id + "/enable", {
          method: "POST"
        });
        await fetchReportSchedules();
      }

      function renderReportDeliveries(payload) {
        const summary = document.getElementById("reportDeliverySummary");
        const host = document.getElementById("reportDeliveriesList");
        const counts = payload.counts || {};
        summary.textContent = "Mode=" + payload.smtp_mode +
          " | enabled=" + payload.smtp_enabled +
          " | send_real=" + payload.send_real_email +
          " | allowlist=" + (payload.allowlist_configured ? "configured" : "missing") +
          " | sent=" + num(counts.sent) +
          " | dry_run=" + num(counts.dry_run) +
          " | blocked=" + num(counts.blocked) +
          " | failed=" + num(counts.failed) +
          " | retries=" + num(counts.retries);
        const deliveries = payload.deliveries || [];
        if (!deliveries.length) {
          host.innerHTML = '<p class="muted">No deliveries recorded.</p>';
          return;
        }
        let html = '<table><thead><tr><th>Status</th><th>Mode</th><th>Recipients</th><th>Subject</th><th>Retries</th><th>Error</th><th>Created</th></tr></thead><tbody>';
        deliveries.forEach((item) => {
          html += `<tr>
            <td>${escapeHtml(String(item.delivery_status || "").toUpperCase())}</td>
            <td>${escapeHtml(item.delivery_mode || "-")}</td>
            <td>${escapeHtml((item.recipients_json || []).join(", ") || "-")}</td>
            <td>${escapeHtml(item.subject || "-")}</td>
            <td>${num(item.retries)}</td>
            <td>${escapeHtml(item.error_message || "-")}</td>
            <td>${escapeHtml(item.created_at || "-")}</td>
          </tr>`;
        });
        html += "</tbody></table>";
        host.innerHTML = html;
      }

      async function fetchReportDeliveries() {
        const payload = await adminFetch("/admin/routing/executive-dashboard/report-deliveries?limit=10");
        state.deliveries = payload || {};
        renderReportDeliveries(state.deliveries);
        updateStats();
      }

      function renderFederation() {
        const overview = state.federationOverview || {};
        const compare = Array.isArray(state.federationCompare) ? state.federationCompare : [];
        const clustersPayload = state.federationClusters || {};
        const clusterRows = Array.isArray(clustersPayload.clusters) ? clustersPayload.clusters : (Array.isArray(clustersPayload) ? clustersPayload : []);

        document.getElementById("federationStats").innerHTML = `
          <div class="stat"><strong>Mode</strong><span>${escapeHtml(overview.mode || "-")}</span></div>
          <div class="stat"><strong>Clusters</strong><span>${num(overview.cluster_count || clusterRows.length)}</span></div>
          <div class="stat"><strong>Requests</strong><span>${num(overview.requests_count).toLocaleString("pt-BR")}</span></div>
          <div class="stat"><strong>Margin</strong><span>R$ ${num(overview.actual_margin_brl).toFixed(2)}</span></div>
          <div class="stat"><strong>Latency</strong><span>${num(overview.avg_latency_ms).toFixed(2)} ms</span></div>
        `;

        if (!clusterRows.length) {
          document.getElementById("federationClustersTable").innerHTML = '<div class="empty-state">Nenhum cluster encontrado.</div>';
        } else {
          let html = '<table><thead><tr><th>Cluster</th><th>Status</th><th>Region</th><th>Env</th><th>Requests</th><th>Margin</th><th>Providers</th></tr></thead><tbody>';
          clusterRows.slice(0, 15).forEach((row) => {
            html += `<tr><td>${escapeHtml(row.cluster_id || row.peer_cluster_id || "-")}</td><td>${escapeHtml(row.status || "-")}</td><td>${escapeHtml(row.region || "-")}</td><td>${escapeHtml(row.environment || "-")}</td><td>${num(row.requests_count)}</td><td>R$ ${num(row.actual_margin_brl).toFixed(2)}</td><td>${escapeHtml(Array.isArray(row.providers) ? row.providers.join(", ") : "-")}</td></tr>`;
          });
          html += "</tbody></table>";
          document.getElementById("federationClustersTable").innerHTML = html;
        }

        if (!compare.length) {
          document.getElementById("federationCompareTable").innerHTML = '<div class="empty-state">Sem comparacao cross-cluster.</div>';
        } else {
          let html = '<table><thead><tr><th>Cluster</th><th>Rank</th><th>Margin</th><th>Cost</th><th>Latency</th><th>Requests</th></tr></thead><tbody>';
          compare.slice(0, 15).forEach((row) => {
            html += `<tr><td>${escapeHtml(row.cluster_id || "-")}</td><td>${escapeHtml(String(row.margin_rank || "-"))}</td><td>R$ ${num(row.actual_margin_brl).toFixed(2)}</td><td>R$ ${num(row.actual_cost_brl).toFixed(2)}</td><td>${num(row.avg_latency_ms).toFixed(2)} ms</td><td>${num(row.requests_count)}</td></tr>`;
          });
          html += "</tbody></table>";
          document.getElementById("federationCompareTable").innerHTML = html;
        }
      }

      async function downloadFederationExport(format) {
        const url = "/admin/routing/federation/export?format=" + encodeURIComponent(format) + "&hours=24";
        const res = await fetch(url, { headers: adminHeaders() });
        if (!res.ok) throw new Error("federation export failed");
        const text = await res.text();
        const win = window.open("", "_blank");
        if (win) {
          win.document.write(format === "html" ? text : "<pre>" + text.replace(/[<>&]/g, (value) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[value])) + "</pre>");
          win.document.close();
        }
      }

      async function loadData() {
        const [clusters, overview, compare, schedules, deliveries] = await Promise.all([
          adminFetch("/admin/routing/federation/clusters"),
          adminFetch("/admin/routing/federation/overview"),
          adminFetch("/admin/routing/federation/compare"),
          adminFetch("/admin/routing/executive-dashboard/report-schedules"),
          adminFetch("/admin/routing/executive-dashboard/report-deliveries?limit=10")
        ]);

        state.federationClusters = clusters || null;
        state.federationOverview = overview || null;
        state.federationCompare = compare || [];
        state.schedules = Array.isArray(schedules) ? schedules : [];
        state.deliveries = deliveries || {};

        renderFederation();
        renderReportSchedules(state.schedules);
        renderReportDeliveries(state.deliveries);
        updateStats();

        document.getElementById("federationDebug").textContent = JSON.stringify({
          clusters: state.federationClusters,
          overview: state.federationOverview,
          compare: state.federationCompare
        }, null, 2);
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
          SharedNotifications.success("Reports carregado com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      SharedNavigation.mountTopbar("#reports-topbar", {
        brand: "Admin",
        title: "Reports",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Portal", href: "/static/portal/index.html" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      document.getElementById("connectButton").addEventListener("click", connect);
      document.getElementById("reloadButton").addEventListener("click", () => loadData().catch((error) => SharedNotifications.error(error.message || "Falha ao recarregar.")));
      document.getElementById("reportDebugToggle").addEventListener("click", () => toggleDebug("commReportDebug"));
      document.getElementById("federationDebugToggle").addEventListener("click", () => toggleDebug("federationDebug"));
      document.getElementById("refreshPreviewButton").addEventListener("click", () => refreshExecutiveReportPreview().catch((error) => SharedNotifications.error(error.message || "Falha ao atualizar preview.")));
      document.getElementById("exportJsonButton").addEventListener("click", () => downloadExecutiveReport("json").catch((error) => SharedNotifications.error(error.message || "Export failed.")));
      document.getElementById("exportCsvButton").addEventListener("click", () => downloadExecutiveReport("csv").catch((error) => SharedNotifications.error(error.message || "Export failed.")));
      document.getElementById("exportHtmlButton").addEventListener("click", () => downloadExecutiveReport("html").catch((error) => SharedNotifications.error(error.message || "Export failed.")));
      document.getElementById("exportPdfButton").addEventListener("click", () => downloadExecutiveReport("pdf").catch((error) => SharedNotifications.error(error.message || "Export failed.")));
      document.getElementById("createScheduleButton").addEventListener("click", () => createReportSchedule().catch((error) => SharedNotifications.error(error.message || "Falha ao criar schedule.")));
      document.getElementById("refreshSchedulesButton").addEventListener("click", () => fetchReportSchedules().catch((error) => SharedNotifications.error(error.message || "Falha ao carregar schedules.")));
      document.getElementById("refreshDeliveriesButton").addEventListener("click", () => fetchReportDeliveries().catch((error) => SharedNotifications.error(error.message || "Falha ao carregar deliveries.")));
      document.getElementById("federationJsonButton").addEventListener("click", () => downloadFederationExport("json").catch((error) => SharedNotifications.error(error.message || "Federation export failed.")));
      document.getElementById("federationCsvButton").addEventListener("click", () => downloadFederationExport("csv").catch((error) => SharedNotifications.error(error.message || "Federation export failed.")));
      document.getElementById("federationHtmlButton").addEventListener("click", () => downloadFederationExport("html").catch((error) => SharedNotifications.error(error.message || "Federation export failed.")));
      document.getElementById("reportSchedulesList").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const id = button.getAttribute("data-id");
        const action = button.getAttribute("data-action");
        const map = {
          "run-now": runReportScheduleNow,
          "send-test": sendTestReportEmail,
          "disable": disableReportSchedule,
          "enable": enableReportSchedule
        };
        const handler = map[action];
        if (!handler) return;
        handler(id).catch((error) => SharedNotifications.error(error.message || "Falha na acao do schedule."));
      });

      (function bootstrap() {
        const token = readAdminTokenFromUrl() || SharedAuth.getToken(STORAGE_KEY) || "";
        if (!token) return;
        els.adminToken.value = token;
        state.token = token;
        connect();
      })();
