# Finance Tracker

A Python personal finance application that combines expense tracking with explainable cash-flow forecasting and purchase planning.

It helps you plan your money, anticipate shortages before they happen, and see what you can afford.

## Features

**Tracking**
- Accounts, income / expense categories, and transfers between your own accounts
- Transfers never count as income or spending
- Dashboard with balances, monthly totals, spending by category and a 6-month history
- Filterable transaction list, CSV import (all-or-nothing, with row-level errors) and CSV export
- Per-user data isolation: every query is scoped to the logged-in user

**Planning**
- **Balance forecast**: projects your balance with a likely range and warns about a possible shortfall date
- **What-if simulator**: test a purchase, an income change or a spending cut against your forecast
- **Savings goals**: shows the monthly amount needed and whether your recent surplus covers it

### How the forecast works

Deliberately simple and transparent (see `planning/forecast.py`):

1. Start from today's real total balance.
2. Add each recurring income and bill on its due date (monthly items keep their day of month, clamped to month length; weekly items repeat every 7 days).
3. Subtract an estimated daily amount for everyday spending: your average daily spending over the last 90 days, minus recurring bills already modelled. You can override it.
4. The range moves everyday spending by ±25%.

Money uses `Decimal`, never floats.

## Tech stack

Django · Django templates + Bootstrap 5 · Chart.js · SQLite (local) or PostgreSQL (Docker) · WhiteNoise + Gunicorn

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo       # optional: demo user "demo" / "demo12345" with sample data
python manage.py runserver
```

Open http://127.0.0.1:8000. Register an account, or log in as the demo user.

To use the Django admin: `python manage.py createsuperuser`, then visit `/admin/`.

## Run with Docker (PostgreSQL)

```bash
cp .env.example .env             # then edit .env and set a real DJANGO_SECRET_KEY
docker compose up --build
docker compose exec web python manage.py seed_demo   # optional
```

Open http://localhost:8000. Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | Required when `DJANGO_DEBUG=0` |
| `DJANGO_DEBUG` | `1` | Set `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `DJANGO_HTTPS` | `0` | Set `1` behind HTTPS to enable secure cookies |
| `APP_CURRENCY` | `MAD` | Display currency (no conversion; use one currency) |
| `APP_TIME_ZONE` | `Africa/Casablanca` | Time zone |
| `POSTGRES_DB` / `_USER` / `_PASSWORD` / `_HOST` / `_PORT` | unset | If `POSTGRES_DB` is set, PostgreSQL is used instead of SQLite |

## CSV import format

```csv
date,amount,description,category
2026-11-01,-45.50,Groceries,Food
01/11/2026,"6 000,00",Salary,Salary
```

- Dates: `YYYY-MM-DD` or `DD/MM/YYYY`
- Negative amount = expense, positive = income
- `category` is optional and matched by name
- Export is meant for analysis and backup; it is not directly re-importable

## Tests

```bash
python manage.py test
```

## Project structure

```
config/      Django settings and root URLs
ledger/      Accounts, categories, transactions, dashboard, CSV import/export
planning/    Recurring items, savings goals, forecast and what-if
  forecast.py   Pure forecasting logic (no database), unit-tested
templates/   Bootstrap templates
```

## Roadmap

- Unusual-spending alerts (compare a category with the user's own history)
- Importer for a specific Moroccan bank statement format
- Shared expenses for groups (e.g. a student apartment)
- Backtesting: compare past forecasts with actual outcomes before adding more complex models
