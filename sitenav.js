(function () {
  'use strict';

  /* ── Nav definition ── */
  var NAV_LINKS = [
    { href: 'https://hello.clung.us/', label: 'hello', path: '/' },
    { href: 'https://hello.clung.us/changelog', label: 'changelog', path: '/changelog' },
    { href: 'https://hello.clung.us/deaths', label: 'deaths', path: '/deaths' },
    { href: 'https://hello.clung.us/tasks', label: 'tasks', path: '/tasks' },
    { href: 'https://github.com/bigclungus', label: 'github', external: true },
    { href: 'https://1998.clung.us', label: '1998', external: true },
  ];

  var SUBHEADER_LINKS = [
    { href: 'https://terminal.clung.us', label: '🔒 terminal', external: true },
    { href: 'https://temporal.clung.us', label: '⏱ temporal', external: true },
    { href: 'https://terminal.clung.us/topology', label: '🕸 topology', external: true },
  ];

  /* ── Active link detection ── */
  function isActive(link) {
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
    brand.href = 'https://hello.clung.us/';
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

    nav.appendChild(links);

    var toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.id = 'theme-toggle';
    toggle.setAttribute('aria-label', 'Toggle light/dark mode');
    toggle.textContent = '🌙';
    nav.appendChild(toggle);

    return nav;
  }

  /* ── Build subheader ── */
  function buildSubheader() {
    var sub = document.createElement('div');
    sub.className = 'sitenav-subheader';

    var label = document.createElement('span');
    label.className = 'sitenav-subheader-label';
    label.textContent = 'tools';
    sub.appendChild(label);

    SUBHEADER_LINKS.forEach(function (item, i) {
      if (i > 0) {
        var sep = document.createElement('span');
        sep.className = 'sitenav-subheader-sep';
        sep.textContent = '|';
        sub.appendChild(sep);
      }
      var a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.label;
      if (item.external) {
        a.target = '_blank';
        a.rel = 'noopener';
      }
      sub.appendChild(a);
    });

    return sub;
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
    var sub = buildSubheader();

    var body = document.body;
    body.insertBefore(sub, body.firstChild);
    body.insertBefore(nav, sub);

    var toggleBtn = document.getElementById('theme-toggle');
    initTheme(toggleBtn);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
