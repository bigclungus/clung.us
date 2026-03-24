(function () {
  'use strict';

  /* ── Nav definition ── */
  var NAV_LINKS = [
    { href: 'https://clung.us/', label: 'hello', path: '/' },
    { href: 'https://clung.us/tasks', label: 'tasks', path: '/tasks' },
    { href: 'https://clung.us/congress', label: 'congress', path: '/congress' },
    { href: 'https://clung.us/wallet', label: 'wallet', path: '/wallet' },
    { href: 'https://github.com/bigclungus', label: 'github', external: true },
  ];

  var TOOL_LINKS = [
    { href: 'https://terminal.clung.us', label: 'terminal', external: true, toolHost: 'terminal.clung.us' },
    { href: 'https://temporal.clung.us', label: 'temporal', external: true, toolHost: 'temporal.clung.us' },
    { href: 'https://terminal.clung.us/topology', label: 'topology', external: true },
  ];

  /* ── Active link detection ── */
  function isActive(link) {
    if (link.external) return false;
    // Tool links with a toolHost: active when on that hostname
    if (link.toolHost) {
      return window.location.hostname === link.toolHost;
    }
    // For links with a full href, compare hostname + pathname
    if (link.href) {
      try {
        var linkUrl = new URL(link.href);
        if (linkUrl.hostname === window.location.hostname) {
          var lp = linkUrl.pathname.replace(/\/+$/, '') || '/';
          var p = window.location.pathname.replace(/\/+$/, '') || '/';
          return p === lp;
        }
      } catch(e) {}
    }
    if (!link.path) return false;
    var p = window.location.pathname.replace(/\/+$/, '') || '/';
    var lp = link.path.replace(/\/+$/, '') || '/';
    return p === lp;
  }

  /* ── Build main nav ── */
  function buildNav() {
    var nav = document.createElement('nav');
    nav.className = 'sitenav';

    var brand = document.createElement('a');
    brand.className = 'sitenav-brand';
    brand.href = 'https://clung.us/';
    brand.textContent = '🤖 clung.us';
    nav.appendChild(brand);

    var links = document.createElement('div');
    links.className = 'sitenav-links';

    NAV_LINKS.forEach(function (item) {
      var a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      if (item.external) {
        a.target = '_blank';
        a.rel = 'noopener';
      }
      if (isActive(item)) {
        a.className = 'active';
      }
      links.appendChild(a);
    });

    var sep = document.createElement('span');
    sep.className = 'sitenav-sep';
    sep.textContent = '|';
    links.appendChild(sep);

    TOOL_LINKS.forEach(function (item) {
      var a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      a.className = isActive(item) ? 'sitenav-tool-link active' : 'sitenav-tool-link';
      if (item.external && !item.toolHost) {
        a.target = '_blank';
        a.rel = 'noopener';
      }
      links.appendChild(a);
    });

    nav.appendChild(links);

    var toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.id = 'theme-toggle';
    toggle.setAttribute('aria-label', 'Toggle light/dark mode');
    toggle.textContent = '🌙';
    nav.appendChild(toggle);

    return nav;
  }

  /* ── Theme logic ── */
  function applyTheme(theme, toggleBtn) {
    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
      toggleBtn.textContent = '☀';
    } else {
      document.documentElement.removeAttribute('data-theme');
      toggleBtn.textContent = '🌙';
    }
  }

  function initTheme(toggleBtn) {
    var saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved, toggleBtn);

    toggleBtn.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      var next = current === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', next);
      applyTheme(next, toggleBtn);
    });
  }

  /* ── Inject into page ── */
  function inject() {
    var nav = buildNav();

    var body = document.body;
    body.insertBefore(nav, body.firstChild);

    var toggleBtn = document.getElementById('theme-toggle');
    initTheme(toggleBtn);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
