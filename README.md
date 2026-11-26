# PocketLedger

**Flutter is now the primary interface at `/app/`.** Build the `flutter_app` project before opening the root URL; see [Flutter setup](flutter_app/README.md). This document describes the backend and the retained classic interface at `/classic/`, including CSV import/export.

Your money, with a little more clarity. PocketLedger is a self-hosted personal finance app for tracking spending, setting monthly budgets, and looking ahead before making a purchase. One responsive app works on desktop and mobile and can be installed from a supporting browser.

The project builds on the supplied Finance Tracker Django app. [ezBookkeeping](https://github.com/mayswind/ezbookkeeping) inspired the self-hosted, cross-device approach; this is an independent implementation with its own planning experience.

## What you can do

- **Track everyday money:** accounts, income, expenses, categories and transfers. Transfers between your accounts never count as income or spending.
- **See the bigger picture:** an overview of balances, monthly income and spending, category breakdowns, recent transactions and six months of history.
- **Set category budgets:** separate monthly limits, automatic spending totals, remaining amounts, overspending alerts, spending pace and visibility into expenses without a budget. Past and future months have their own budgets.
- **Plan ahead:** recurring income and bills, a cash-flow forecast, a what-if purchase simulator and savings goals with required monthly contributions.
- **Ask a local model:** an optional read-only companion explains an approved aggregate summary through Ollama. Its default is the Apache-2.0 licensed Qwen3:4b. The financial snapshot works without a model.
- **Use mobile and desktop:** responsive layouts, an installable progressive web app (PWA), app icons, installation instructions and a generic offline reconnect page.
- **Move your data:** validated CSV import with row-level errors and CSV transaction export.

The interface's CSS and chart library are bundled locally. Accounts and records are scoped to the signed-in user. There is no bank connection or commercial AI service required.

## Quick start on Windows

Use Python 3.11 or 3.12. The app stays on Django 5.2, which supports Python 3.11. See [Django's compatibility table](https://docs.djangoproject.com/en/5.2/faq/install/#what-python-version-can-i-use-with-django).

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open [PocketLedger locally](http://127.0.0.1:8000), register an account, and create your first money account. These commands call the virtual environment directly; changing PowerShell's execution policy is unnecessary.

## Quick start on macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

SQLite is used by default. To explore sample records first, run `python manage.py seed_demo` using your virtual environment's Python. It creates the local demonstration login `demo` / `demo12345` and skips an existing demo account. Do not seed this known password on a public server. New personal accounts start with their own empty records and default categories.

For Django's administrative interface, run `python manage.py createsuperuser`, then visit `/admin/`.

## Install on a phone or desktop

Choose **Install app** inside PocketLedger, or use your browser's installation action. Chrome/Edge desktop and Android support installation; iPhone/iPad use Safari's **Share → Add to Home Screen**. Browser support and menu wording vary.

For a phone, host the app at an HTTPS address reachable from that phone and sign in to the same account. The app server must stay running. `localhost` on a phone means the phone itself, not your computer. Localhost development on desktop is supported; a plain HTTP LAN address normally cannot install a service worker.

Installation adds an icon and a standalone window. This release still needs the server for financial records and changes. It does not create a separate offline database, queue offline transactions, or produce Android/iOS/Windows native installers. See [the installation guide](docs/INSTALL.md) for platform and hosting details.

## Connect the optional local AI

Install [Ollama](https://ollama.com/download), start it, then run:

```text
ollama pull qwen3:4b
```

For a local PowerShell session:

```powershell
$env:OLLAMA_ENABLED = '1'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe manage.py runserver
```

Open **Money assistant**, preview the exact summary, and approve sharing it for your question. The model runs on your configured app server, including when you use the app from a phone. AI is disabled by default; no model is downloaded automatically and there is no cloud fallback.

See [local AI setup](docs/LOCAL_AI.md) for model choices, Docker connectivity, timeout settings and data handling. Automated tests use a mocked Ollama endpoint; they do not establish that a live model is installed or has answered successfully.

## Docker with PostgreSQL

Copy `.env.example` to `.env` (`Copy-Item .env.example .env` on PowerShell or `cp .env.example .env` on macOS/Linux). Set a random `DJANGO_SECRET_KEY` and a unique database password. To generate a Django key from your virtual environment:

```text
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Then run:

```text
docker compose up --build
```

Open [PocketLedger on Docker](http://localhost:8000). The container runs migrations, collects static assets, and starts Gunicorn with a 90-second worker timeout. PostgreSQL records persist in the `pgdata` named volume. Do not remove that volume when you need to keep your records.

Ollama is optional and is not started or downloaded by Compose. To use Ollama running on the host, set `OLLAMA_ENABLED=1` and `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env`. The Compose configuration includes the host-gateway mapping. Ollama must listen on an address reachable from the container; keep its API private. See the [AI guide](docs/LOCAL_AI.md) before exposing any additional network listener.

## Configuration

Django reads process environment variables. **It does not automatically load `.env` during local development**; the file is for Docker Compose. Set local values in the shell that starts Django.

| Variable | Local default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | development-only key | Set a random secret when `DJANGO_DEBUG=0`. |
| `DJANGO_DEBUG` | `1` | Set `0` in production; Compose defaults to `0`. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated server hostnames, without schemes. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Explicit trusted origins such as `https://money.example.com`, when needed. |
| `DJANGO_HTTPS` | `0` | Enable secure cookies and trusted proxy HTTPS handling. |
| `APP_CURRENCY` | `MAD` | Single display currency; no exchange-rate conversion. |
| `APP_TIME_ZONE` | `Africa/Casablanca` | Date boundaries and display time zone. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | unset | Setting `POSTGRES_DB` selects PostgreSQL instead of SQLite. Compose supplies these. |
| `OLLAMA_ENABLED` | `0` | Explicitly enable the AI connection. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Server-owned endpoint; Compose defaults to `http://host.docker.internal:11434`. |
| `OLLAMA_MODEL` | `qwen3:4b` | Exact locally installed model tag. |
| `OLLAMA_TIMEOUT` | `45` | Request timeout in seconds, bounded to 1–120. Keep the application/proxy timeout longer. |

For production, use a trusted HTTPS reverse proxy, set the exact allowed hostname, and enable `DJANGO_HTTPS=1` only when the proxy sets `X-Forwarded-Proto` itself. Serve the app from the origin root (`/`). Use Gunicorn in Docker or another supported production WSGI server; Django's `runserver` is for development. Run `python manage.py check --deploy` under your production environment and assess its output for your deployment.

## How the numbers work

Money is stored and calculated with `Decimal`; charts use numeric display values. Transfers move funds between accounts without inflating income or expenses.

The forecast starts with the recorded balance, adds configured recurring income/bills on their due dates, and subtracts estimated everyday spending. The estimate uses up to 90 days of available history and subtracts recurring costs already modeled. You can override it on the forecast page. The low/high range changes everyday spending by ±25%; it is an assumption range, not a statistical confidence interval. Due dates on short months are clamped to the month's final day.

The ledger accepts posted transactions dated today or earlier. Use recurring bills and the what-if planner for future commitments. Legacy future-dated records remain in the transaction list but do not affect current totals or forecasts until their date; review them when migrating an older database.

Recurring entries describe the forecast; they do not automatically post transactions. Savings goal amounts are manually maintained and do not move funds. Budget pacing compares spending with the fraction of the month elapsed; a bill paid early can legitimately be ahead of pace. Budgets are monthly records and do not automatically roll over.

## CSV import and export

Import into a selected account using this UTF-8 format:

```csv
date,amount,description,category
2026-11-01,-45.50,Groceries,Food
01/11/2026,"6 000,00",Salary,Salary
```

- Dates: `YYYY-MM-DD` or `DD/MM/YYYY`.
- Negative amount means expense; positive means income.
- Category is optional and matched to your category names.
- Maximum upload size is 2 MB. Any invalid row prevents the whole file from being imported.
- Imports do not detect duplicates; importing the same file twice adds the rows twice.
- The transaction export is for analysis. It has a different schema and is not directly re-importable or a complete application backup.

Back up the database for complete recovery of accounts, budgets, goals, users and records. For SQLite, stop the app before copying `db.sqlite3`; for PostgreSQL use database backup tools such as `pg_dump`, and test restoration separately.

## Privacy and current limits

Financial records live in your server's database. The service worker caches only an allowlist of public assets and a generic reconnect page. Authenticated pages, CSV exports, model responses and posted data are not put in that cache. Dynamic responses use `private, no-store`. Unsaved form input is not stored or queued by the app.

Ollama receives only the approved summary and the question you type. Account names and transaction descriptions are excluded from the summary; category names are included. The companion has no write tools, and PocketLedger does not save chat transcripts. A trusted app host and model server remain part of the privacy boundary. AI-generated explanations may be wrong; the app's deterministic calculations remain the source of the displayed totals.

This release has one display currency, an English interface, manual account entry and no bank sync, receipt OCR, shared household ledger, automatic reconciliation, push reminders, 2FA or account-recovery email setup. No native app store package is included. HTTPS hosting, backups and live-device/model testing are deployment responsibilities.

## Development and checks

Using your virtual environment's Python:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
node --test core/tests_service_worker.cjs
python manage.py collectstatic --noinput
```

Node is only needed for the service-worker behavior tests, not to run the Django app. The tests cover transaction/forecast arithmetic, ownership, imports, monthly budgets, AI consent/error handling, PWA responses and public-cache behavior. Native installation and live Ollama generation require separate checks on the intended device/server.

```text
config/       Django configuration and routes
ledger/       Accounts, categories, transactions, dashboard, CSV
planning/     Recurring items, forecasts, what-if scenarios, savings goals
budgets/      Monthly category budgets and spending pace
assistant/    Read-only financial snapshot and Ollama integration
core/         PWA installation, service worker and response-cache policy
templates/    Server-rendered responsive interface
static/       App styling/scripts, bundled vendors and PWA icons
docs/         Installation and local AI guides
```

See [third-party notices](THIRD_PARTY_NOTICES.md) for inspiration, bundled libraries and model attribution. Future work can build on this foundation with tested bank import formats, receipt-assisted entry, forecast backtesting, shared households and multi-currency accounting.

