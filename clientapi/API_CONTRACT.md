# PocketLedger Flutter API

The Django API is the accounting authority for Flutter web and native clients.
All routes begin with `/api/` and have a trailing slash. The Flutter web build
uses the same origin as Django. No cross-origin browser access is enabled.

## Sessions and transport

1. `GET /api/session/` obtains a CSRF cookie and the masked `csrfToken`.
2. Preserve cookies, including the `sessionid` returned by sign-in.
3. Send `X-CSRFToken` with every POST or DELETE. JSON mutations use
   `Content-Type: application/json`. Native clients also send the API origin in
   `Origin`; HTTPS clients must use the configured trusted server origin.
4. Replace the CSRF token with the one returned after login, registration, or
   logout. A token from before login is no longer valid.

Production deployments use HTTPS and secure session/CSRF cookies. The provided
native transport keeps cookies in memory; restarting the app requires signing
in again. Browser clients use the browser's cookie jar. Financial API responses
include `Cache-Control: private, no-store, no-cache, max-age=0`.

Session response:

```json
{
  "authenticated": true,
  "user": {"username": "amal", "first_name": "Amal"},
  "csrfToken": "masked-token",
  "currency": "MAD"
}
```

For an anonymous session, `authenticated` is false and `user` is null. Currency
is the deployment's single display currency (`APP_CURRENCY`); there is no FX
conversion.

| Route | Method | Input / result |
| --- | --- | --- |
| `session/` | GET | Public session bootstrap |
| `login/` | POST | `username`, `password`; returns session |
| `register/` | POST | `username`, `password1`, `password2`, optional `first_name`; returns session with 201 |
| `logout/` | POST | `{}`; returns anonymous session |

Login failures use a generic message. Ten failed attempts for an IP/username
pair, or 50 failed attempts for an IP, trigger a 600-second limit and HTTP 429
with `Retry-After`. Configure a shared Django cache when using multiple workers.

## Data conventions

- Money is a base-10 string, such as `"12.34"`; clients should send strings too.
  Financial calculations use Python `Decimal` on the server. Flutter converts
  values to doubles only for graph coordinates.
- Dates are `YYYY-MM-DD`. Budget months are `YYYY-MM`.
- IDs are integers. Optional relations and dates are null when absent.
- JSON bodies contain simple scalar values, not nested objects or arrays, and
  are limited to 64 KiB. CSV upload is a separate multipart endpoint.
- Ownership comes from the authenticated session, never a submitted `user` ID.
  Foreign records return 404; foreign relation choices fail field validation.

## Resource CRUD

Resources: `accounts`, `categories`, `transactions`, `budgets`, `goals`,
`recurring`.

| Route | Method | Result |
| --- | --- | --- |
| `<resource>/` | GET | `{results: [...], count, page, pages}` |
| `<resource>/` | POST | `{item: record}` with 201 |
| `<resource>/<id>/` | GET | `{item: record}` |
| `<resource>/<id>/` | POST | `{item: record}` after a full form update |
| `<resource>/<id>/` | DELETE | `{deleted: true}` |

Updates use POST with all editable fields, not partial PATCH. Lists accept
`page` (starting at 1) and `page_size` (1–200, default 100). An out-of-range
page returns 404. Empty lists return page 1 of 1.

| Resource | Editable fields | Additional response fields |
| --- | --- | --- |
| accounts | `name`, `opening_balance` | `id`, `balance` |
| categories | `name`, `kind` (`income` or `expense`) | `id` |
| transactions | `kind` (`income`, `expense`, `transfer`), `amount`, `date`, `account`, optional `to_account`, `category`, `description` | `id`, `account_name`, `to_account_name`, `category_name` |
| budgets | `category`, `month`, `amount` | `id`, `category_name`, `spent`, `remaining`, `over_amount`, `percent`, `status`, `status_label` |
| goals | `name`, `target_amount`, `saved_so_far`, `target_date` | `id`, `remaining`, `monthly_required` (nullable), `percent` (integer) |
| recurring | `name`, `kind` (`income` or `expense`), `amount`, `frequency` (`monthly` or `weekly`), `next_date`, optional `end_date`, `active` (boolean) | `id` |

Amounts for transactions, budgets, recurring items and goal targets must be
positive; saved amounts must be nonnegative. Account opening balances may be
negative. Account/category names are unique per user, case-insensitively in
form validation. Account names are limited to 100 characters; categories to
60; descriptions to 200.

Transactions dated after today are rejected; future plans belong in recurring
items or what-if simulations. Transfers require a different destination owned
by the user, have no category, and do not affect combined balance or income and
expense totals. Categories on income/expense transactions must match the kind.

Deleting an account also deletes its transactions, including transfers to or
from it. Deleting a category uncategorizes its transactions and removes its
budgets. Clients must explain this before submitting deletion. A category's
kind cannot change while transactions or budgets use it.

Transaction list filters:

- `q`: case-insensitive description, category name, or source account name.
- `kind`: `income`, `expense`, or `transfer`.
- `account`: source or destination account ID.
- `category`: category ID.
- `month`: `YYYY-MM`.

Budget lists accept `month`, defaulting to the current month, and return a
`summary` alongside pagination. Only expense categories can be budgeted, once
per category per month. The summary contains `month`, `month_label`,
`total_budget`, `total_spent`, `total_remaining`, `unbudgeted_spent`,
`elapsed_percent`, `over_count`, and `rows`. Budget percentages and overview
spending percentages are decimal strings; goal and insight percentages are
integers.

## Overview and planning

`GET /api/overview/` returns:

- `as_of`, `currency`, `month_label`.
- `balance`, month-to-date `income`, `expense`, `net`, and `savings_rate`.
- `accounts`, up to eight posted `recent` transactions, `goals`, `recurring`.
- Six-month `history` entries with `label`, `income`, `expense`.
- `spending` entries with `name`, `amount`, `percent`, `color`.
- `budgets`: the current-month summary described above.
- `forecast`: the 30-day forecast described below.
- `upcoming`: up to eight forecast expense events (`date`, `name`, signed
  `amount`).
- `insights`: category spending changes with `category`, `change`, `percent`.

Balances and recent dashboard activity exclude legacy future-dated postings.
Resource lists still expose those records so they can be corrected.

`GET /api/forecast/?days=90&daily_spend=20.00` accepts horizons 30, 60, 90,
180, or 365. The optional nonnegative `daily_spend` overrides the estimate
derived from the last 90 days. Response:

```text
days, start_balance, daily_spend, estimated_daily_spend,
end_expected, end_low, end_high, lowest_date, lowest_value,
shortfall_expected, shortfall_low,
dates[], expected[], low[], high[], events[]
```

Dates and monetary series contain `days + 1` entries including today. A
shortfall date is null when that path never falls below zero. Events have
`date`, `name`, and a signed `amount`. Forecasts include active recurring items
and variable spending; cautious/optimistic paths vary spending by ±25%. They
are estimates, do not post transactions, and do not include unrecorded bills.

`POST /api/what-if/` accepts `days` (default 90), optional `purchase_amount`,
`purchase_date`, `monthly_income_change`, and `monthly_expense_cut`. At least
one nonzero change is required. A purchase requires a date. Income change can
be negative; expense cut cannot. Purchase dates on or before today apply on the
first projected day; dates beyond the horizon do not affect the shown period.
Monthly income change begins one month from today. Response:

```text
baseline_end, scenario_end, difference, scenario_end_low,
baseline_min: {date, amount}, scenario_min: {date, amount},
baseline_shortfall, scenario_shortfall, scenario_shortfall_low,
dates[], baseline[], scenario[]
```

The simulation changes no saved records.

## Local model assistant

`GET /api/assistant/` returns `summary`, `enabled`, `model`, and
`status: {ready, label, detail}`. The aggregate summary includes current balance,
month-to-date totals, previous full month expenses, top category totals, daily
spending and 30-day forecast assumptions. It excludes account names and
transaction descriptions. Display it before sending a question.

`POST /api/assistant/` accepts `question` (1–1200 characters) and
`share_summary: true`. Consent
must be the literal JSON boolean true for each request. It returns `answer`
(plain text), `summary`, and `model`. The server recomputes the summary at
request time, so a concurrent ledger change can update it. Responses are
read-only explanations; the model cannot modify records or invoke tools.

Ollama configuration is server-owned (`OLLAMA_ENABLED`, `OLLAMA_BASE_URL`,
`OLLAMA_MODEL`, `OLLAMA_TIMEOUT`). Client-supplied endpoints are ignored.
Defaults use the open-weight `qwen3:4b` model on local Ollama, disabled until
enabled by the owner. Unavailable/offline/model errors return HTTP 503 with
`code: assistant_unavailable`; they never fabricate a model answer.

## CSV

- `GET /api/export/`: owned transactions as a CSV attachment with columns
  `date,account,kind,amount,category,description,to_account`. Amounts are
  positive and the kind supplies direction. Text cells are protected against
  spreadsheet formula interpretation.
- `POST /api/import/`: multipart `file` and owned `account` ID, with the usual
  CSRF header. UTF-8 CSV, at most 2 MiB. Accepts bank columns `date,amount,
  description` plus optional `category`; negative amount means expense.
  Ledger exports are not an import template: CSV files with a `kind` column
  are rejected to prevent interpreting exported expenses as income. Convert
  income/expense rows to signed amounts before importing; record transfers
  in the ledger. A valid import
  returns `{imported: count}` with 201. Invalid input imports nothing.

## Errors

```json
{
  "error": "Check the highlighted fields.",
  "code": "validation_error",
  "errors": {"amount": ["Ensure this value is greater than or equal to 0.01."]}
}
```

`errors` is optional; non-field form errors use `__all__`. Important statuses:
400 validation/bad input, 401 unauthenticated/invalid credentials, 403
`csrf_failed`, 404 missing or foreign record, 405 wrong method, 409 duplicate
conflict, 413 oversized body, 415 wrong content type, 429 sign-in limit,
503 assistant unavailable. Error responses remain JSON and non-cacheable.

After CSRF failure, refresh the session token before retrying an explicit
mutation. Do not automatically retry a write after an ambiguous network
failure: it may already have succeeded. This API does not provide idempotency
keys. Refresh reads are safe to retry.
