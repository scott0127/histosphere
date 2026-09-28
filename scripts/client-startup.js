(function () {
  var retryKey = 'histosphere:startup-reload-at';
  var handled = false;
  var mounted = false;
  var reloadTimer;
  var errorPanel;

  function isAppModule(value) {
    try {
      var url = new URL(value, window.location.href);
      return url.origin === window.location.origin && url.pathname.startsWith('/_nuxt/');
    } catch (_) {
      return false;
    }
  }

  function showRetry() {
    if (mounted || errorPanel) return;
    if (!document.body) {
      document.addEventListener('DOMContentLoaded', showRetry, { once: true });
      return;
    }

    errorPanel = document.createElement('section');
    errorPanel.id = 'histosphere-startup-error';
    errorPanel.setAttribute('role', 'alert');
    errorPanel.style.cssText = 'position:fixed;inset:0;z-index:2147483647;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:32px;background:#f5f2ec;color:#342d27;font-family:system-ui,sans-serif;text-align:center;';

    var title = document.createElement('h1');
    title.textContent = '系統未能完成載入';
    title.style.cssText = 'margin:0;font-size:24px;';
    var description = document.createElement('p');
    description.textContent = '頁面載入中斷，請重新載入後再操作。';
    description.style.cssText = 'margin:0;line-height:1.6;';
    var button = document.createElement('button');
    button.type = 'button';
    button.textContent = '重新載入';
    button.style.cssText = 'margin-top:8px;padding:12px 24px;border:0;border-radius:8px;background:#795c48;color:white;font:inherit;cursor:pointer;';
    button.addEventListener('click', function () { window.location.reload(); });

    errorPanel.append(title, description, button);
    document.body.append(errorPanel);
    button.focus();
  }

  function recover() {
    if (mounted || handled) return;
    handled = true;

    try {
      var now = Date.now();
      // Keep the marker until a successful mount, even if a failed load takes a long time.
      if (window.sessionStorage.getItem(retryKey)) {
        showRetry();
        return;
      }
      window.sessionStorage.setItem(retryKey, String(now));
    } catch (_) {
      // Without persistent retry accounting, automatic reload could loop.
      showRetry();
      return;
    }

    reloadTimer = window.setTimeout(function () { window.location.reload(); }, 250);
  }

  function onScriptError(event) {
    var target = event.target;
    if (target && target.tagName === 'SCRIPT' && target.src && isAppModule(target.src)) {
      recover();
    }
  }

  function onRejection(event) {
    var reason = event.reason;
    var message = typeof reason === 'string' ? reason : reason && reason.message;
    if (typeof message !== 'string') return;
    var match = message.match(/(?:Failed to fetch dynamically imported module|error loading dynamically imported module):\s*(\S+)/i);
    if (match && isAppModule(match[1])) recover();
  }

  function onMounted() {
    mounted = true;
    window.clearTimeout(reloadTimer);
    window.removeEventListener('error', onScriptError, true);
    window.removeEventListener('unhandledrejection', onRejection);
    window.removeEventListener('histosphere:app-mounted', onMounted);
    document.removeEventListener('DOMContentLoaded', showRetry);
    if (errorPanel) errorPanel.remove();
    try {
      window.sessionStorage.removeItem(retryKey);
    } catch (_) {
      // The app is ready even when browser storage is unavailable.
    }
  }

  window.addEventListener('error', onScriptError, true);
  window.addEventListener('unhandledrejection', onRejection);
  window.addEventListener('histosphere:app-mounted', onMounted);
})();
