const STORAGE_KEY = "adminToken";
const state = { token: "" };
const els = {
  adminToken: document.getElementById("adminToken"),
  connectButton: document.getElementById("connectButton"),
  authStatus: document.getElementById("authStatus"),
  settingsApp: document.getElementById("settingsApp"),
  loginPrompt: document.getElementById("loginPrompt"),
  systemInfo: document.getElementById("systemInfo")
};

function setConnected(connected) {
  els.settingsApp.classList.toggle("hidden", !connected);
  els.loginPrompt.classList.toggle("hidden", connected);
  els.authStatus.textContent = connected ? "Conectado" : "Desconectado";
  els.authStatus.className = connected ? "badge success" : "badge warning";
}

async function connect() {
  const token = els.adminToken.value.trim();
  if (!token) return;
  state.token = token;
  SharedAuth.setToken(STORAGE_KEY, token);
  try {
    const status = await SharedAPI.request("/admin/status", { headers: SharedAuth.headerForAdminToken(token) });
    els.systemInfo.innerHTML = `<pre class="code">${JSON.stringify(status, null, 2)}</pre>`;
    setConnected(true);
    SharedNotifications.success("Status do sistema carregado.");
  } catch (error) {
    setConnected(false);
    SharedNotifications.error("Falha ao conectar: " + error.message);
  }
}

els.connectButton.addEventListener("click", connect);

SharedNavigation.mountTopbar("#settings-topbar", {
  brand: "Admin / Settings",
  title: "Configurações",
  actions: [{ label: "Admin Hub", href: "/admin-dashboard" }]
});

if (SharedAuth.getToken(STORAGE_KEY)) {
  els.adminToken.value = SharedAuth.getToken(STORAGE_KEY);
  connect();
}
