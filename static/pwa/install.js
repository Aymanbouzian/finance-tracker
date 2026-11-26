(() => {
  let deferredPrompt = null;
  const buttons = [...document.querySelectorAll('[data-pwa-install]')];
  const status = document.querySelector('[data-pwa-status]');
  const connection = document.querySelector('[data-pwa-connection]');
  const standalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

  const showStatus = (message) => {
    if (status) { status.hidden = false; status.textContent = message; }
  };
  const markInstalled = () => {
    buttons.forEach((button) => { button.hidden = true; });
    showStatus('PocketLedger is running as an installed app.');
  };
  if (standalone()) markInstalled();

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    buttons.forEach((button) => { button.hidden = false; });
    showStatus('Ready to install on this device.');
  });
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    markInstalled();
  });

  buttons.forEach((button) => button.addEventListener('click', async (event) => {
    if (!deferredPrompt) {
      if (button.tagName !== 'A') window.location.assign('/install/');
      return;
    }
    event.preventDefault();
    const prompt = deferredPrompt;
    deferredPrompt = null;
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      showStatus(choice.outcome === 'accepted' ? 'Installation requested. Look for PocketLedger on your device.' : 'You can install later from your browser menu.');
    } catch (_) {
      showStatus('Use your browser menu to install PocketLedger.');
    }
  }));

  const updateConnection = () => {
    if (!connection) return;
    connection.hidden = navigator.onLine;
    connection.textContent = 'You are offline. Reconnect before saving changes. Unsaved changes are not queued.';
  };
  window.addEventListener('online', updateConnection);
  window.addEventListener('offline', updateConnection);
  updateConnection();

  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js', {scope: '/', updateViaCache: 'none'})
        .catch(() => showStatus('Offline fallback is unavailable. You can still use PocketLedger online.'));
    });
  } else if (!window.isSecureContext) {
    showStatus('Installation requires HTTPS, or localhost on this device.');
  }
})();
