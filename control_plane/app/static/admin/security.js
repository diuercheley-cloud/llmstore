      const STORAGE_KEY = "adminToken";
      const state = {
        token: "",
        securityLatest: null,
        securityEvents: [],
        requests: [],
        complianceControls: {},
        complianceApprovals: [],
        complianceEvidence: [],
        complianceExceptions: [],
        operationalControls: {},
        operationalEvidence: {},
        operationalReviews: {},
        federationStatus: {},
        federationConsistency: {},
        federationAudit: {}
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        authStatus: document.getElementById("authStatus"),
        securityApp: document.getElementById("securityApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statSecurityEvents: document.getElementById("statSecurityEvents"),
        statAuditEvents: document.getElementById("statAuditEvents"),
        statComplianceIssues: document.getElementById("statComplianceIssues"),
        statRequests: document.getElementById("statRequests")
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

      function setConnected(connected) {
        els.securityApp.classList.toggle("hidden", !connected);
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

      function updateTopStats() {
        const controlsSummary = state.complianceControls.summary || {};
        const federationEvents = state.federationAudit.total_events || 0;
        els.statSecurityEvents.textContent = String(state.securityEvents.length);
        els.statAuditEvents.textContent = String(federationEvents);
        els.statComplianceIssues.textContent = String(num(controlsSummary.open_exceptions) + num(controlsSummary.pending_approval_chains));
        els.statRequests.textContent = String(state.requests.length);
      }

      function renderSecurityLatest() {
        const data = state.securityLatest || {};
        const value = document.getElementById("securityValue");
        const details = document.getElementById("securityDetails");
        const materials = document.getElementById("securityMaterials");
        if (data.status === "not_generated") {
          value.textContent = "NOT GENERATED";
          details.textContent = "Run security-report-local.sh";
          materials.textContent = "Latest report indisponivel.";
          return;
        }

        value.textContent = data.score || "N/A";
        const totals = data.totals || {};
        details.innerHTML = `Score: ${escapeHtml(String(data.score || "N/A"))} | PASS: ${num(totals.pass)} | WARN: ${num(totals.warn)} | FAIL: ${num(totals.fail)}<br /><small>Generated: ${escapeHtml(data.generated_at || "N/A")}</small>`;
        materials.textContent = `offline_crl=${state.federationStatus.mode || "-"} | hardware_attestation=${escapeHtml(String((data.attestations && data.attestations.pending) || 0))} pending`;
      }

      function renderSecurity() {
        const events = Array.isArray(state.securityEvents) ? state.securityEvents : [];
        if (!events.length) {
          document.getElementById("securityTable").innerHTML = '<div class="empty-state">Nenhum evento de seguranca encontrado.</div>';
          return;
        }
        let html = '<table><thead><tr><th>Time</th><th>Type</th><th>Severity</th><th>Client</th><th>Message</th></tr></thead><tbody>';
        events.slice(0, 25).forEach((event) => {
          html += `
            <tr>
              <td><small>${escapeHtml(event.created_at || "-")}</small></td>
              <td>${escapeHtml(event.event_type || "-")}</td>
              <td><span class="pill ${event.severity === "high" ? "pill-danger" : "pill-warning"}">${escapeHtml(event.severity || "unknown")}</span></td>
              <td><small>${escapeHtml(shortId(event.client_id))}</small></td>
              <td>${escapeHtml(event.title || "-")}</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        document.getElementById("securityTable").innerHTML = html;
      }

      function renderRequests() {
        const requests = Array.isArray(state.requests) ? state.requests : [];
        if (!requests.length) {
          document.getElementById("requestTable").innerHTML = '<div class="empty-state">Nenhum request recente encontrado.</div>';
          return;
        }
        let html = '<table><thead><tr><th>Time</th><th>Method</th><th>Status</th><th>Latency</th><th>Cache</th></tr></thead><tbody>';
        requests.slice(0, 25).forEach((request) => {
          html += `
            <tr>
              <td><small>${escapeHtml(request.created_at || "-")}</small></td>
              <td>${escapeHtml(request.method || "POST")}</td>
              <td><span class="pill ${num(request.status) < 400 ? "pill-success" : "pill-danger"}">${escapeHtml(String(request.status || "-"))}</span></td>
              <td>${num(request.latency_ms)}ms</td>
              <td><span class="pill">${request.cache_hit ? "HIT" : "MISS"}</span></td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        document.getElementById("requestTable").innerHTML = html;
      }

      function renderComplianceControls() {
        const controlsEnvelope = state.complianceControls || {};
        const approvalChains = state.complianceApprovals || [];
        const evidencePackages = state.complianceEvidence || [];
        const exceptions = state.complianceExceptions || [];
        const summary = controlsEnvelope.summary || {};
        const controls = Array.isArray(controlsEnvelope.controls) ? controlsEnvelope.controls : [];

        document.getElementById("complianceStats").innerHTML = `
          <div class="stat"><strong>Controles Ativos</strong><span>${num(summary.active_controls)}</span></div>
          <div class="stat"><strong>Approvals Pendentes</strong><span>${num(summary.pending_approval_chains)}</span></div>
          <div class="stat"><strong>Evidence Recentes</strong><span>${num(summary.recent_evidence_packages)}</span></div>
          <div class="stat"><strong>Attestations Pendentes</strong><span>${num(summary.pending_attestations)}</span></div>
          <div class="stat"><strong>Exceptions Abertas</strong><span>${num(summary.open_exceptions)}</span></div>
        `;

        const badges = (summary.badges || []).filter(Boolean).map((badge) => `<span class="pill pill-warning" style="margin-right:8px;">${escapeHtml(badge)}</span>`).join("");
        document.getElementById("complianceBadges").innerHTML = badges || '<span class="pill pill-success">EVIDENCE_READY</span>';

        document.getElementById("complianceControlsTable").innerHTML = '<table><thead><tr><th>Controle</th><th>Area</th><th>Acao</th><th>Badges</th></tr></thead><tbody>' +
          controls.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.control_area)}</td><td>${escapeHtml(item.action_type)}</td><td>${[
            item.requires_approval ? "APPROVAL_REQUIRED" : null,
            item.segregation_required ? "SEGREGATION_REQUIRED" : null,
            item.evidence_required ? "EVIDENCE_READY" : null
          ].filter(Boolean).join(", ")}</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("complianceApprovalsTable").innerHTML = '<table><thead><tr><th>Approval Chain</th><th>Status</th><th>Requester</th></tr></thead><tbody>' +
          approvalChains.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.target_type)}:${escapeHtml(item.target_id)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.requested_by)}</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("complianceEvidenceTable").innerHTML = '<table><thead><tr><th>Evidence</th><th>Target</th><th>Hash</th></tr></thead><tbody>' +
          evidencePackages.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.package_type)}</td><td>${escapeHtml(item.target_type)}:${escapeHtml(item.target_id)}</td><td>${escapeHtml(String(item.immutable_hash || "").slice(0, 12))}...</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("complianceExceptionsTable").innerHTML = '<table><thead><tr><th>Exception</th><th>Severity</th><th>Status</th></tr></thead><tbody>' +
          exceptions.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.exception_type)}</td><td>${escapeHtml(item.severity)}</td><td>${escapeHtml(item.status)}</td></tr>`).join("") +
          "</tbody></table>";
      }

      function renderOperationalControls() {
        const controlsEnvelope = state.operationalControls || {};
        const evidenceEnvelope = state.operationalEvidence || {};
        const reviewsEnvelope = state.operationalReviews || {};
        const summary = controlsEnvelope.summary || {};
        const controls = Array.isArray(controlsEnvelope.controls) ? controlsEnvelope.controls : [];
        const reviewCalendar = controlsEnvelope.review_calendar || [];
        const escalations = controlsEnvelope.escalation_status || [];
        const evidenceItems = evidenceEnvelope.items || [];
        const reviewItems = reviewsEnvelope.items || [];

        document.getElementById("operationalStats").innerHTML = `
          <div class="stat"><strong>Controls</strong><span>${num(summary.controls)}</span></div>
          <div class="stat"><strong>Stale Evidence</strong><span>${num(summary.stale_evidence)}</span></div>
          <div class="stat"><strong>Overdue Reviews</strong><span>${num(summary.overdue_reviews)}</span></div>
          <div class="stat"><strong>Ineffective</strong><span>${num(summary.ineffective_controls)}</span></div>
          <div class="stat"><strong>Linked Exceptions</strong><span>${num(summary.linked_exceptions)}</span></div>
        `;

        const badges = [
          summary.ineffective_controls ? "INEFFECTIVE" : null,
          summary.overdue_reviews ? "OVERDUE" : null,
          summary.stale_evidence ? "STALE" : null,
          summary.linked_exceptions ? "EXCEPTION_LINKED" : null
        ].filter(Boolean).map((badge) => `<span class="pill pill-warning" style="margin-right:8px;">${badge}</span>`).join("");
        document.getElementById("operationalBadges").innerHTML = badges || '<span class="pill pill-success">EFFECTIVE</span>';

        document.getElementById("operationalControlsTable").innerHTML = '<table><thead><tr><th>Control</th><th>Score</th><th>Owner</th><th>Badges</th></tr></thead><tbody>' +
          controls.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.control_code)} · ${escapeHtml(item.name)}</td><td>${escapeHtml(String(item.effectiveness_score ?? "n/a"))} (${escapeHtml(item.effectiveness_status || "unknown")})</td><td>${escapeHtml(item.owner_email || "-")}</td><td>${escapeHtml(((item.badges || []).filter(Boolean)).join(", "))}</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("operationalEvidenceTable").innerHTML = '<table><thead><tr><th>Evidence</th><th>Status</th><th>Hash</th></tr></thead><tbody>' +
          evidenceItems.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.freshness_status)}</td><td>${escapeHtml(String(item.immutable_hash || "").slice(0, 12))}...</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("operationalReviewsTable").innerHTML = '<table><thead><tr><th>Review Calendar</th><th>Status</th><th>Reviewer</th></tr></thead><tbody>' +
          (reviewCalendar.length ? reviewCalendar : reviewItems).slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.control_code || item.control_id)}<br />${escapeHtml(item.review_period_start || "-")} → ${escapeHtml(item.review_period_end || "-")}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.reviewed_by || "-")}</td></tr>`).join("") +
          "</tbody></table>";

        document.getElementById("operationalEscalationsTable").innerHTML = '<table><thead><tr><th>Escalation</th><th>Severity</th><th>Status</th></tr></thead><tbody>' +
          escalations.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.control_code)}<br />${escapeHtml(item.trigger_type)}</td><td>${escapeHtml(item.severity)}</td><td>${item.internal_escalation ? "internal+dry-run" : "none"}</td></tr>`).join("") +
          "</tbody></table>";
      }

      function renderGovernanceFederation() {
        const statusData = state.federationStatus || {};
        const consistencyData = state.federationConsistency || {};
        const auditData = state.federationAudit || {};
        const cc = consistencyData.compliance_consistency || {};

        document.getElementById("federationStats").innerHTML = `
          <div class="stat"><strong>Total Peers</strong><span>${num(statusData.total_peers)}</span></div>
          <div class="stat"><strong>Online</strong><span>${num(statusData.online_peers)}</span></div>
          <div class="stat"><strong>Offline</strong><span>${num(statusData.offline_peers)}</span></div>
          <div class="stat"><strong>Conflicts</strong><span>${num(cc.drift)}</span></div>
          <div class="stat"><strong>Audit Events</strong><span>${num(auditData.total_events)}</span></div>
        `;

        const badges = [];
        if (statusData.offline_peers > 0) badges.push('<span class="pill pill-danger">OFFLINE</span>');
        if (cc.drift > 0) badges.push('<span class="pill pill-warning">DRIFT</span>');
        if (statusData.mode !== "disabled") badges.push('<span class="pill pill-success">SYNCED</span>');
        document.getElementById("federationBadges").innerHTML = badges.length ? badges.join(" ") : '<span class="pill">NO_DATA</span>';

        const peers = statusData.peers || [];
        document.getElementById("federationPeersTable").innerHTML = '<table><thead><tr><th>Cluster</th><th>Region</th><th>Env</th><th>Status</th><th>Sync</th><th>Trust</th><th>Last Policy Sync</th></tr></thead><tbody>' +
          peers.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.peer_cluster_id)}</td><td>${escapeHtml(item.region || "-")}</td><td>${escapeHtml(item.environment || "-")}</td><td>${escapeHtml(item.status || "-")}</td><td>${escapeHtml(item.sync_mode || "-")}</td><td>${escapeHtml(item.trust_level || "-")}</td><td>${escapeHtml(item.last_policy_sync_at || "-")}</td></tr>`).join("") +
          "</tbody></table>";

        const issues = cc.issues || [];
        document.getElementById("federationConsistencyTable").innerHTML = '<table><thead><tr><th>Peer</th><th>Issue</th><th>Severity</th><th>Detail</th></tr></thead><tbody>' +
          issues.slice(0, 12).map((item) => `<tr><td>${escapeHtml(item.peer)}</td><td>${escapeHtml(item.issue)}</td><td>${escapeHtml(item.severity)}</td><td>${escapeHtml(item.detail || "")}</td></tr>`).join("") +
          "</tbody></table>";

        const events = auditData.recent_events || [];
        document.getElementById("federationAuditTable").innerHTML = '<table><thead><tr><th>Source Cluster</th><th>Event Type</th><th>Received</th></tr></thead><tbody>' +
          events.slice(0, 15).map((item) => `<tr><td>${escapeHtml(item.source_cluster_id)}</td><td>${escapeHtml(item.event_type)}</td><td>${escapeHtml(item.received_at)}</td></tr>`).join("") +
          "</tbody></table>";
      }

      async function exportComplianceAuditReport(format) {
        const token = els.adminToken.value.trim();
        const res = await fetch("/admin/compliance/audit-report?format=" + encodeURIComponent(format), {
          headers: { "X-Admin-Token": token }
        });
        const text = await res.text();
        const popup = window.open("", "_blank");
        if (popup) popup.document.write("<pre>" + text.replace(/</g, "&lt;") + "</pre>");
      }

      async function loadData() {
        const results = await Promise.all([
          adminFetch("/admin/security/latest"),
          adminFetch("/admin/security/events"),
          adminFetch("/admin/requests"),
          adminFetch("/admin/compliance/controls"),
          adminFetch("/admin/compliance/approval-chains?limit=10"),
          adminFetch("/admin/compliance/evidence-packages?limit=10"),
          adminFetch("/admin/compliance/exceptions"),
          adminFetch("/admin/compliance/operational-controls"),
          adminFetch("/admin/compliance/operational-controls/evidence"),
          adminFetch("/admin/compliance/operational-controls/reviews"),
          adminFetch("/admin/governance/federation/status"),
          adminFetch("/admin/governance/federation/consistency"),
          adminFetch("/admin/governance/federation/audit-trail")
        ]);

        state.securityLatest = results[0] || null;
        state.securityEvents = Array.isArray(results[1]) ? results[1] : [];
        state.requests = Array.isArray(results[2]) ? results[2] : [];
        state.complianceControls = results[3] || {};
        state.complianceApprovals = Array.isArray(results[4]) ? results[4] : [];
        state.complianceEvidence = Array.isArray(results[5]) ? results[5] : [];
        state.complianceExceptions = Array.isArray(results[6]) ? results[6] : [];
        state.operationalControls = results[7] || {};
        state.operationalEvidence = results[8] || {};
        state.operationalReviews = results[9] || {};
        state.federationStatus = results[10] || {};
        state.federationConsistency = results[11] || {};
        state.federationAudit = results[12] || {};

        updateTopStats();
        renderSecurityLatest();
        renderSecurity();
        renderRequests();
        renderComplianceControls();
        renderOperationalControls();
        renderGovernanceFederation();

        document.getElementById("securityLatestDebug").textContent = JSON.stringify(state.securityLatest, null, 2);
        document.getElementById("securityDebug").textContent = JSON.stringify(state.securityEvents, null, 2);
        document.getElementById("requestDebug").textContent = JSON.stringify(state.requests, null, 2);
        document.getElementById("complianceDebug").textContent = JSON.stringify({
          controls: state.complianceControls,
          approvals: state.complianceApprovals,
          evidence: state.complianceEvidence,
          exceptions: state.complianceExceptions
        }, null, 2);
        document.getElementById("operationalDebug").textContent = JSON.stringify({
          controls: state.operationalControls,
          evidence: state.operationalEvidence,
          reviews: state.operationalReviews
        }, null, 2);
        document.getElementById("federationAuditDebug").textContent = JSON.stringify({
          status: state.federationStatus,
          consistency: state.federationConsistency,
          audit: state.federationAudit
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
          SharedNotifications.success("Security carregado com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      SharedNavigation.mountTopbar("#security-topbar", {
        brand: "Admin",
        title: "Security",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      document.getElementById("connectButton").addEventListener("click", connect);
      document.getElementById("reloadButton").addEventListener("click", () => loadData().catch((error) => SharedNotifications.error(error.message || "Falha ao recarregar.")));
      document.getElementById("securityLatestDebugToggle").addEventListener("click", () => toggleDebug("securityLatestDebug"));
      document.getElementById("securityDebugToggle").addEventListener("click", () => toggleDebug("securityDebug"));
      document.getElementById("requestDebugToggle").addEventListener("click", () => toggleDebug("requestDebug"));
      document.getElementById("complianceDebugToggle").addEventListener("click", () => toggleDebug("complianceDebug"));
      document.getElementById("operationalDebugToggle").addEventListener("click", () => toggleDebug("operationalDebug"));
      document.getElementById("federationAuditDebugToggle").addEventListener("click", () => toggleDebug("federationAuditDebug"));
      document.getElementById("complianceExportJsonButton").addEventListener("click", () => exportComplianceAuditReport("json"));
      document.getElementById("complianceExportCsvButton").addEventListener("click", () => exportComplianceAuditReport("csv"));
      document.getElementById("complianceExportHtmlButton").addEventListener("click", () => exportComplianceAuditReport("html"));

      (function bootstrap() {
        const token = readAdminTokenFromUrl() || SharedAuth.getToken(STORAGE_KEY) || "";
        if (!token) return;
        els.adminToken.value = token;
        state.token = token;
        connect();
      })();
