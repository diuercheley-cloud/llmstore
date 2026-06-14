      const STORAGE_KEY = "adminToken";
      const state = {
        token: "",
        plans: [],
        revenue: {},
        financials: null,
        wallets: [],
        qosOverview: {},
        qosRecords: []
      };

      const els = {
        adminToken: document.getElementById("adminToken"),
        authStatus: document.getElementById("authStatus"),
        billingApp: document.getElementById("billingApp"),
        loginPrompt: document.getElementById("loginPrompt"),
        statPlans: document.getElementById("statPlans"),
        statOverdueInvoices: document.getElementById("statOverdueInvoices"),
        statWallets: document.getElementById("statWallets"),
        statQosBilling: document.getElementById("statQosBilling"),
        plansSummary: document.getElementById("plansSummary"),
        plansTable: document.getElementById("plansTable"),
        plansDebug: document.getElementById("plansDebug"),
        pricingTable: document.getElementById("pricingTable"),
        pricingDebug: document.getElementById("pricingDebug"),
        revenueStats: document.getElementById("revenueStats"),
        revenueDebug: document.getElementById("revenueDebug"),
        walletTable: document.getElementById("walletTable"),
        walletDebug: document.getElementById("walletDebug"),
        qosStats: document.getElementById("qosStats"),
        qosTable: document.getElementById("qosTable"),
        qosDebug: document.getElementById("qosDebug")
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

      function formatBrl(value) {
        return "R$ " + num(value).toFixed(2);
      }

      function formatTokenLimit(value) {
        return Number(value) > 0 ? Number(value).toLocaleString("pt-BR") : "Ilimitado";
      }

      function setConnected(connected) {
        els.billingApp.classList.toggle("hidden", !connected);
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

      function renderStats() {
        els.statPlans.textContent = String(state.plans.length);
        els.statOverdueInvoices.textContent = String(num(state.revenue.invoices_overdue));
        els.statWallets.textContent = String(state.wallets.filter((item) => item.status === "active").length);
        els.statQosBilling.textContent = formatBrl(num(state.qosOverview.total_calculated_brl));
      }

      function renderPlans() {
        const plans = Array.isArray(state.plans) ? state.plans : [];
        els.plansSummary.textContent = plans.length
          ? `${plans.length} planos carregados.`
          : "Nenhum plano encontrado.";

        if (!plans.length) {
          els.plansTable.innerHTML = '<div class="empty-state">Nenhum plano encontrado.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Plano</th><th>Code</th><th>Status</th><th>Rate Limit</th><th>Quotas</th><th>Atualizacao</th></tr></thead><tbody>";
        plans.forEach((plan) => {
          html += `
            <tr>
              <td>
                <strong>${escapeHtml(plan.name || plan.billing_plan_name || "-")}</strong><br />
                <small class="subtle">${escapeHtml(plan.id || "-")}</small>
              </td>
              <td><code>${escapeHtml(plan.code || plan.billing_plan_code || "-")}</code></td>
              <td><span class="pill ${plan.is_active === false ? "pill-warning" : "pill-success"}">${plan.is_active === false ? "inactive" : "active"}</span></td>
              <td>${num(plan.rate_limit_per_minute).toLocaleString("pt-BR")}/min</td>
              <td>
                dia ${formatTokenLimit(plan.daily_token_quota)}<br />
                semana ${formatTokenLimit(plan.weekly_token_quota)}<br />
                mes ${formatTokenLimit(plan.monthly_token_quota)}
              </td>
              <td>${formatTimestamp(plan.updated_at || plan.created_at)}</td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.plansTable.innerHTML = html;
      }

      function renderPricingRules() {
        const data = state.financials;
        if (!data) {
          els.pricingTable.innerHTML = '<div class="empty-state">Sem dados financeiros.</div>';
          return;
        }

        const costs = data.costs_config || {};
        const entries = Object.entries(costs);
        if (!entries.length) {
          els.pricingTable.innerHTML = '<div class="empty-state">Nenhuma pricing rule encontrada.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Provider</th><th>Prompt (USD/1K)</th><th>Completion (USD/1K)</th><th>Pricing Configured</th></tr></thead><tbody>";
        entries.forEach(([providerId, cfg]) => {
          html += `
            <tr>
              <td><strong>${escapeHtml(providerId)}</strong></td>
              <td>$${num(cfg.cost_usd_per_1k_prompt).toFixed(6)}</td>
              <td>$${num(cfg.cost_usd_per_1k_completion).toFixed(6)}</td>
              <td><span class="pill ${cfg.pricing_configured ? "pill-success" : "pill-danger"}">${cfg.pricing_configured ? "YES" : "NO"}</span></td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.pricingTable.innerHTML = html;
      }

      function renderRevenue() {
        const data = state.revenue || {};
        const revenue = num(data.revenue_usd);
        const pending = num(data.pending_usd);
        const overdue = num(data.overdue_usd);
        els.revenueStats.innerHTML = `
          <div class="stat">
            <strong>Total Revenue</strong>
            <span>$${revenue.toFixed(2)}</span>
            <small class="subtle">${num(data.invoices_paid)} paid invoices</small>
          </div>
          <div class="stat">
            <strong>Pending Revenue</strong>
            <span>$${pending.toFixed(2)}</span>
            <small class="subtle">${num(data.invoices_pending)} pending invoices</small>
          </div>
          <div class="stat">
            <strong>Overdue Revenue</strong>
            <span>$${overdue.toFixed(2)}</span>
            <small class="subtle">${num(data.invoices_overdue)} overdue invoices</small>
          </div>
        `;
      }

      function renderWallets() {
        const wallets = Array.isArray(state.wallets) ? state.wallets : [];
        if (!wallets.length) {
          els.walletTable.innerHTML = '<div class="empty-state">No wallets found.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Client ID</th><th>Currency</th><th>Balance (BRL)</th><th>Reserved (BRL)</th><th>Available (BRL)</th><th>Status</th></tr></thead><tbody>";
        wallets.forEach((wallet) => {
          html += `
            <tr>
              <td><code>${escapeHtml(shortId(wallet.client_id))}</code></td>
              <td>${escapeHtml(wallet.currency || "-")}</td>
              <td>${formatBrl(wallet.balance_brl)}</td>
              <td>${formatBrl(wallet.reserved_brl)}</td>
              <td>${formatBrl(wallet.available_brl)}</td>
              <td><span class="pill ${wallet.status === "active" ? "pill-success" : "pill-danger"}">${escapeHtml(wallet.status || "unknown")}</span></td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.walletTable.innerHTML = html;
      }

      function renderQosBilling() {
        const overview = state.qosOverview || {};
        const records = Array.isArray(state.qosRecords) ? state.qosRecords : [];

        els.qosStats.innerHTML = `
          <div class="stat">
            <strong>Calculated BRL</strong>
            <span>${formatBrl(overview.total_calculated_brl)}</span>
            <small class="subtle">Ready to be invoiced/debited</small>
          </div>
          <div class="stat">
            <strong>Invoiced BRL</strong>
            <span>${formatBrl(overview.total_invoiced_brl)}</span>
            <small class="subtle">Attached to invoices</small>
          </div>
          <div class="stat">
            <strong>Debited BRL</strong>
            <span>${formatBrl(overview.total_debited_brl)}</span>
            <small class="subtle">Automatically debited from wallet</small>
          </div>
        `;

        if (!records.length) {
          els.qosTable.innerHTML = '<div class="empty-state">Nenhum billing record encontrado.</div>';
          return;
        }

        let html = "<table><thead><tr><th>Cliente</th><th>Tier</th><th>Valor</th><th>Status</th><th>Acoes</th></tr></thead><tbody>";
        records.forEach((record) => {
          const canDebit = record.status === "calculated" || record.status === "failed";
          html += `
            <tr>
              <td><code>${escapeHtml(shortId(record.client_id))}</code></td>
              <td>${escapeHtml(record.qos_tier || "-")}</td>
              <td>${formatBrl(record.billable_amount_brl)}</td>
              <td><span class="pill ${record.status === "debited" || record.status === "invoiced" ? "pill-success" : "pill-warning"}">${escapeHtml(record.status || "unknown")}</span></td>
              <td>
                ${canDebit
                  ? `<button class="button secondary" type="button" data-action="debit" data-record-id="${escapeHtml(record.id)}">Debit wallet</button>`
                  : "-"}
              </td>
            </tr>
          `;
        });
        html += "</tbody></table>";
        els.qosTable.innerHTML = html;
      }

      async function loadData() {
        const [plans, revenue, financials, wallets, qosOverview, qosRecords] = await Promise.all([
          adminFetch("/admin/billing/plans"),
          adminFetch("/admin/revenue/summary"),
          adminFetch("/admin/hybrid/financials"),
          adminFetch("/admin/hybrid/wallets"),
          adminFetch("/admin/billing/qos/overview"),
          adminFetch("/admin/billing/qos/records?limit=10")
        ]);

        state.plans = Array.isArray(plans) ? plans : [];
        state.revenue = revenue || {};
        state.financials = financials || null;
        state.wallets = Array.isArray(wallets) ? wallets : [];
        state.qosOverview = qosOverview || {};
        state.qosRecords = Array.isArray(qosRecords) ? qosRecords : [];

        renderStats();
        renderPlans();
        renderPricingRules();
        renderRevenue();
        renderWallets();
        renderQosBilling();

        els.plansDebug.textContent = JSON.stringify(state.plans, null, 2);
        els.pricingDebug.textContent = JSON.stringify(state.financials, null, 2);
        els.revenueDebug.textContent = JSON.stringify(state.revenue, null, 2);
        els.walletDebug.textContent = JSON.stringify(state.wallets, null, 2);
        els.qosDebug.textContent = JSON.stringify({ overview: state.qosOverview, records: state.qosRecords }, null, 2);
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
          SharedNotifications.success("Billing carregado com sucesso.");
        } catch (error) {
          setConnected(false);
          SharedNotifications.error(error.message || "Falha ao autenticar.");
        }
      }

      async function debitWallet(recordId) {
        if (!window.confirm("Deseja realmente debitar a wallet do cliente?")) return;
        try {
          await adminFetch("/admin/billing/qos/" + recordId + "/debit-wallet", { method: "POST" });
          SharedNotifications.success("Debito realizado com sucesso.");
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao debitar wallet.");
        }
      }

      async function generateQosBilling() {
        try {
          const data = await adminFetch("/admin/billing/qos/generate", { method: "POST" });
          SharedNotifications.success("Generated " + num(data.calculated_count) + " billing records.");
          await loadData();
        } catch (error) {
          SharedNotifications.error(error.message || "Falha ao gerar billing.");
        }
      }

      function exportQosBilling(format) {
        const token = state.token || els.adminToken.value.trim();
        window.open("/admin/billing/qos/export?format=" + encodeURIComponent(format) + "&X-Admin-Token=" + encodeURIComponent(token), "_blank");
      }

      SharedNavigation.mountTopbar("#billing-topbar", {
        brand: "Admin",
        title: "Billing",
        actions: [
          { label: "Admin Hub", href: "/admin-dashboard" },
          { label: "Legacy", href: "/static/admin/index.legacy.html" }
        ]
      });

      document.getElementById("connectButton").addEventListener("click", connect);
      document.getElementById("reloadButton").addEventListener("click", () => loadData().catch((error) => SharedNotifications.error(error.message || "Falha ao recarregar.")));
      document.getElementById("plansDebugToggle").addEventListener("click", () => toggleDebug("plansDebug"));
      document.getElementById("pricingDebugToggle").addEventListener("click", () => toggleDebug("pricingDebug"));
      document.getElementById("revenueDebugToggle").addEventListener("click", () => toggleDebug("revenueDebug"));
      document.getElementById("walletDebugToggle").addEventListener("click", () => toggleDebug("walletDebug"));
      document.getElementById("qosDebugToggle").addEventListener("click", () => toggleDebug("qosDebug"));
      document.getElementById("generateQosButton").addEventListener("click", generateQosBilling);
      document.getElementById("exportQosCsvButton").addEventListener("click", () => exportQosBilling("csv"));
      document.getElementById("exportQosJsonButton").addEventListener("click", () => exportQosBilling("json"));
      els.qosTable.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action='debit']");
        if (!button) return;
        debitWallet(button.getAttribute("data-record-id"));
      });

      (function bootstrap() {
        const token = readAdminTokenFromUrl() || SharedAuth.getToken(STORAGE_KEY) || "";
        if (!token) return;
        els.adminToken.value = token;
        state.token = token;
        connect();
      })();
