(() => {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const scrim = document.getElementById('sidebar-scrim');
  if (!toggle || !sidebar || !scrim) return;

  const mobile = window.matchMedia('(max-width: 767px)');
  const background = [...document.querySelectorAll('.app-shell, .mobile-tabs, .skip-link')];
  const previousInert = new Map();
  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.className = 'sidebar-close btn btn-sm btn-outline-secondary align-self-end mb-3';
  closeButton.textContent = 'Close navigation';
  sidebar.prepend(closeButton);
  scrim.tabIndex = -1;
  scrim.setAttribute('aria-hidden', 'true');
  sidebar.querySelector('.nav-entry.active')?.setAttribute('aria-current', 'page');

  let isOpen = false;
  let previousOverflow = null;
  const focusableElements = () => [...sidebar.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter(element => !element.hidden && element.getClientRects().length > 0);

  const setMenu = (requestedOpen, {restoreFocus = true} = {}) => {
    const open = requestedOpen && mobile.matches;
    const wasOpen = isOpen;
    isOpen = open;
    sidebar.classList.toggle('is-open', open);
    scrim.classList.toggle('is-open', open);
    scrim.hidden = !open;
    closeButton.hidden = !mobile.matches;
    if (open || !mobile.matches) {
      sidebar.inert = false;
      sidebar.removeAttribute('aria-hidden');
    }
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');

    if (open) {
      sidebar.setAttribute('role', 'dialog');
      sidebar.setAttribute('aria-modal', 'true');
      sidebar.setAttribute('aria-label', 'Navigation');
      if (!wasOpen) {
        background.forEach(element => {
          previousInert.set(element, element.inert);
          element.inert = true;
        });
        previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
      }
      (sidebar.querySelector('.nav-entry.active') || closeButton).focus();
    } else {
      sidebar.removeAttribute('role');
      sidebar.removeAttribute('aria-modal');
      sidebar.removeAttribute('aria-label');
      previousInert.forEach((inert, element) => { element.inert = inert; });
      previousInert.clear();
      if (previousOverflow !== null) {
        document.body.style.overflow = previousOverflow;
        previousOverflow = null;
      }
      if (restoreFocus && mobile.matches) toggle.focus();
      // Return focus before hiding the panel from assistive technology.
      sidebar.inert = mobile.matches;
      if (mobile.matches) sidebar.setAttribute('aria-hidden', 'true');
    }
  };

  const syncViewport = () => {
    const focusInSidebar = sidebar.contains(document.activeElement);
    const focusedCloseButton = document.activeElement === closeButton;
    setMenu(false, {restoreFocus: mobile.matches && focusInSidebar});
    if (!mobile.matches && focusedCloseButton) sidebar.querySelector('.nav-entry.active, a')?.focus();
  };
  toggle.addEventListener('click', () => setMenu(!isOpen));
  closeButton.addEventListener('click', () => setMenu(false));
  scrim.addEventListener('click', () => setMenu(false));
  mobile.addEventListener('change', syncViewport);

  document.addEventListener('keydown', event => {
    if (!isOpen) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      setMenu(false);
    } else if (event.key === 'Tab') {
      const focusable = focusableElements();
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!sidebar.contains(document.activeElement) || (event.shiftKey && document.activeElement === first)) {
        event.preventDefault();
        (event.shiftKey ? last : first)?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
  });
  document.addEventListener('focusin', event => {
    if (isOpen && !sidebar.contains(event.target)) focusableElements()[0]?.focus();
  });
  syncViewport();
})();
