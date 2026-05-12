(function() {
  var BRANDING_KEY = '_wl_branding';
  var cached = sessionStorage.getItem(BRANDING_KEY);
  var branding = null;

  function applyBranding(b) {
    if (!b) return;
    // Title
    if (b.product_name) document.title = b.product_name + ' - Edição Local';

    // CSS variables
    var root = document.documentElement;
    if (b.primary_color) root.style.setProperty('--accent', b.primary_color);
    if (b.secondary_color) root.style.setProperty('--secondary', b.secondary_color);

    // Elements with data-brand attributes
    document.querySelectorAll('[data-brand]').forEach(function(el) {
      var key = el.getAttribute('data-brand');
      if (b[key]) {
        if (el.tagName === 'A' || el.tagName === 'SPAN' || el.tagName === 'DIV') {
          el.textContent = b[key];
        }
      }
    });

    // Footer text replacement
    document.querySelectorAll('.footer, footer, [class*="footer"]').forEach(function(el) {
      var html = el.innerHTML;
      if (b.footer_text && html.indexOf('©') >= 0) {
        html = html.replace(/©\s*\d{4}\s*[^<]*/, b.footer_text);
        el.innerHTML = html;
      }
    });

    // Powered by
    if (b.show_powered_by === false) {
      document.querySelectorAll('[data-brand-powered]').forEach(function(el) {
        el.style.display = 'none';
      });
    }

    // Tagline
    if (b.tagline) {
      document.querySelectorAll('[data-brand="tagline"]').forEach(function(el) {
        el.textContent = b.tagline;
      });
    }

    // Capabilities title
    if (b.capabilities_title) {
      document.querySelectorAll('[data-brand="capabilities_title"]').forEach(function(el) {
        el.textContent = b.capabilities_title;
      });
    }

    cacheBranding(b);
  }

  function cacheBranding(b) {
    try { sessionStorage.setItem(BRANDING_KEY, JSON.stringify(b)); } catch(e) {}
  }

  if (cached) {
    try {
      branding = JSON.parse(cached);
      applyBranding(branding);
    } catch(e) {
      branding = null;
    }
  }

  fetch('/public/branding', { cache: 'no-cache' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(b) {
      if (b) applyBranding(b);
    })
    .catch(function() {});
})();
