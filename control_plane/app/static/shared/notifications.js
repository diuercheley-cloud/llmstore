(function(global) {
  "use strict";

  let host = null;

  function ensureHost() {
    if (host && document.body.contains(host)) return host;

    host = document.createElement("div");
    host.setAttribute("data-notification-host", "true");
    host.style.position = "fixed";
    host.style.top = "16px";
    host.style.right = "16px";
    host.style.zIndex = "9999";
    host.style.display = "grid";
    host.style.gap = "12px";
    host.style.maxWidth = "min(360px, calc(100vw - 32px))";
    document.body.appendChild(host);
    return host;
  }

  function palette(type) {
    switch (type) {
      case "success":
        return { bg: "rgba(22, 101, 52, 0.12)", border: "rgba(22, 101, 52, 0.25)", color: "#166534" };
      case "warning":
        return { bg: "rgba(146, 64, 14, 0.12)", border: "rgba(146, 64, 14, 0.25)", color: "#92400e" };
      case "error":
        return { bg: "rgba(153, 27, 27, 0.12)", border: "rgba(153, 27, 27, 0.25)", color: "#991b1b" };
      default:
        return { bg: "rgba(29, 78, 216, 0.12)", border: "rgba(29, 78, 216, 0.25)", color: "#1d4ed8" };
    }
  }

  function toast(message, options) {
    const settings = options || {};
    const colors = palette(settings.type);
    const node = document.createElement("div");
    node.setAttribute("role", "status");
    node.style.padding = "12px 14px";
    node.style.borderRadius = "16px";
    node.style.background = colors.bg;
    node.style.border = "1px solid " + colors.border;
    node.style.color = colors.color;
    node.style.boxShadow = "0 12px 32px rgba(0, 0, 0, 0.08)";
    node.style.backdropFilter = "blur(10px)";
    node.style.font = "600 14px/1.4 -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    node.textContent = String(message);

    ensureHost().appendChild(node);

    const duration = typeof settings.duration === "number" ? settings.duration : 3200;
    if (duration > 0) {
      global.setTimeout(function() {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, duration);
    }

    return node;
  }

  function info(message, options) {
    return toast(message, Object.assign({}, options, { type: "info" }));
  }

  function success(message, options) {
    return toast(message, Object.assign({}, options, { type: "success" }));
  }

  function warning(message, options) {
    return toast(message, Object.assign({}, options, { type: "warning" }));
  }

  function error(message, options) {
    return toast(message, Object.assign({}, options, { type: "error" }));
  }

  function alertMessage(message) {
    global.alert(String(message));
  }

  global.SharedNotifications = {
    toast: toast,
    info: info,
    success: success,
    warning: warning,
    error: error,
    alert: alertMessage
  };
})(window);
