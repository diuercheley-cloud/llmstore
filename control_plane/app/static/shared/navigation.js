(function(global) {
  "use strict";

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalizeItems(items) {
    return Array.isArray(items) ? items : [];
  }

  function renderLink(item, currentPath) {
    const href = item.href || "#";
    const label = escapeHtml(item.label || href);
    const icon = item.icon ? '<span class="nav-icon">' + escapeHtml(item.icon) + "</span>" : "";
    const current = currentPath && currentPath === href ? ' aria-current="page"' : "";
    return '<a href="' + escapeHtml(href) + '"' + current + ">" + icon + "<span>" + label + "</span></a>";
  }

  function renderList(items, currentPath) {
    return '<div class="sidebar-nav">' + normalizeItems(items).map(function(item) {
      return renderLink(item, currentPath);
    }).join("") + "</div>";
  }

  function mountSidebar(target, items, options) {
    const host = typeof target === "string" ? document.querySelector(target) : target;
    if (!host) return null;
    const settings = options || {};
    host.innerHTML = renderList(items, settings.currentPath || global.location.pathname);
    return host;
  }

  function mountTopbar(target, options) {
    const host = typeof target === "string" ? document.querySelector(target) : target;
    if (!host) return null;
    const settings = options || {};
    const title = escapeHtml(settings.title || "");
    const brand = escapeHtml(settings.brand || "");
    const actions = normalizeItems(settings.actions).map(function(item) {
      const href = escapeHtml(item.href || "#");
      const label = escapeHtml(item.label || href);
      return '<a class="button secondary" href="' + href + '">' + label + "</a>";
    }).join("");

    host.innerHTML =
      '<div class="topbar">' +
        '<div class="stack" style="gap:4px;">' +
          (brand ? '<div class="muted" style="font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;">' + brand + "</div>" : "") +
          (title ? "<h1 style=\"margin:0;\">" + title + "</h1>" : "") +
        "</div>" +
        '<div class="topbar-actions">' + actions + "</div>" +
      "</div>";
    return host;
  }

  global.SharedNavigation = {
    mountSidebar: mountSidebar,
    mountTopbar: mountTopbar,
    renderList: renderList
  };
})(window);
