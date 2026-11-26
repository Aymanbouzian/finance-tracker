# Release verification

Validated locally on Windows with Python 3.11 and Django 5.2.19.

- Django test suite: 89 tests, including transaction arithmetic, CSV boundaries, account ownership, budgets, forecast mathematics, spending alerts, AI consent/errors and public PWA resources.
- Service worker: 5 behavioral Node tests cover its public asset allowlist, private-page cache exclusion, offline navigation and POST bypass.
- Django system checks and migration consistency checks.
- Static asset collection and JavaScript syntax checks.
- 37 route/template smoke checks using an isolated in-memory database.
- Live browser checks using synthetic demo records: desktop overview; 390px and 320px phone layouts; 768px tablet breakpoint; mobile menu focus containment and Escape; transaction search; transfer field visibility; budgets; and the disabled AI setup state.
- Fixed a table overflow observed at 320px and verified the document no longer scrolls horizontally. Tables retain their own horizontal scroll area.

Screenshots: [desktop](screenshots/desktop.jpg), [mobile](screenshots/mobile.jpg).

Not exercised here: native operating-system installation on physical phones, live Ollama generation, Docker/PostgreSQL runtime deployment, and a production HTTPS host. AI tests use mocked responses. Installation needs a secure context and the finance screens need a reachable app server.

The local preview is a development server with a disposable sample account. The source ZIP excludes its SQLite database, virtual environment, collected static files and secrets.
