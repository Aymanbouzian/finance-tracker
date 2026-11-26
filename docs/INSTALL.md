# Install PocketLedger on mobile and desktop

PocketLedger is a progressive web app (PWA). The same Django server serves your desktop and phone. Installation adds an app icon and a standalone window; it does not install a separate local database or a native executable.

## Local desktop

1. Start the Django server using the README instructions.
2. Open `http://localhost:8000` in Chrome or Edge.
3. Sign in, then choose **Install app** in PocketLedger or your browser's install/menu action. If the install prompt is unavailable, the app opens a guide with platform instructions.

The app works in an ordinary browser even where standalone installation is unsupported. Safari on supported Macs offers **File → Add to Dock**.

## Phone or another computer

Use a stable HTTPS address for your server. Set `DJANGO_ALLOWED_HOSTS` to the server hostname, `DJANGO_CSRF_TRUSTED_ORIGINS` to its full HTTPS origin when needed, and `DJANGO_HTTPS=1` when your trusted reverse proxy terminates TLS. Configure the proxy to set `X-Forwarded-Proto` itself, and do not expose Django directly behind an untrusted forwarded header. Keep the app served at the origin root (`/`).

Open that address on each device and sign in with the same account. All devices then use the same server records. Your server must remain running and reachable. `localhost` on a phone points to the phone itself, not your PC. A plain HTTP LAN IP can be used for development browsing, but it will not provide normal PWA installation/service-worker support.

- **Android / Chrome:** browser menu → **Install app** or **Add to Home screen**.
- **iPhone / iPad / Safari:** **Share** → **Add to Home Screen** → **Add**.
- **Desktop / Chrome or Edge:** use the install icon in the address bar or the browser menu.

Installation behavior and menu names vary by browser and operating system. The custom install prompt is offered only when the browser supplies it; iOS uses its Share menu. See [MDN's PWA installation guide](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).

## Offline behavior and privacy

This release needs a connection for account balances, transactions, budgets, forecasts, AI, and saving changes. It does **not** queue offline transactions or synchronize separate databases.

The service worker stores an exact allowlist of public app styles/scripts, icons, and a generic reconnect page. Authenticated pages, JSON endpoints, CSV exports, and POST requests never enter its cache. Navigation fetches bypass the browser HTTP cache, and dynamic HTML/JSON/CSV responses carry `Cache-Control: private, no-store`. If a navigation fails, the worker displays the reconnect page rather than previously viewed financial records.

The browser must first load the app online for the offline fallback to install. An offline notice appears when the browser reports a lost connection; browser network status does not guarantee the server is reachable. Unsaved form input is not stored or queued by the app.

## Deployment and checks

Run `python manage.py collectstatic --noinput` in production so WhiteNoise can serve the checked-in static files. The Django root routes `/manifest.webmanifest` and `/service-worker.js` must remain accessible without signing in and must not redirect to static storage. The service worker response sets its allowed scope to `/` and disables long-term HTTP caching.

The worker includes a hash of its public asset contents, so asset updates create a new public cache. It removes only older `pocketledger-public-*` caches and leaves other applications' caches alone. The worker never deletes financial records from the database.

```powershell
.venv\Scripts\python.exe manage.py test core
node --test core/tests_service_worker.cjs
```

In browser developer tools, inspect **Application → Manifest**, **Service workers**, and **Cache Storage**. Verify that only the public allowlist is cached, then disconnect and navigate to another page to check the reconnect screen. Test installation on the actual target phone before distributing it; automated checks cannot confirm each operating system's installation UI.

Icons are checked in at 192×192 and 512×512 with maskable-safe artwork. To regenerate them after a branding change, install Pillow in a development environment and run `python core/generate_icons.py`. Pillow is not a runtime dependency.

See [MDN's service-worker guide](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers) for the browser lifecycle and secure-context requirements.
