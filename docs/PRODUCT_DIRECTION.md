# PocketLedger: product direction

Reviewed 13 November 2026. This is a scope and prioritization note, not a claim of feature parity or a security audit.

## The useful difference

PocketLedger should help answer three everyday questions: **Where did my money go? What is coming next? What changes if I make this purchase?** The original project already combines a ledger with explainable forecasts and purchase scenarios. This revision brings those features together with category budgets, clearer navigation, and a local AI explanation layer.

The aim is a small, understandable personal finance app. Amounts and projections come from deterministic application code using decimal arithmetic. The optional language model explains an approved summary; it is not responsible for the ledger or for deciding whether a purchase is affordable.

## What we learned from ezBookkeeping

[ezBookkeeping's README](https://github.com/mayswind/ezbookkeeping#readme) describes a self-hosted app with mobile and desktop interfaces, PWA installation, scheduled transactions, extensive imports, multiple currencies, receipt recognition, and AI integrations. It also lists stronger account protection options such as two-factor authentication and OIDC. These are useful reference points; the README alone does not prove that any PocketLedger feature is unique.

| Area | PocketLedger in this revision | Product decision |
| --- | --- | --- |
| Daily tracking | Accounts, categories, income, expenses, transfers, filters, CSV import/export | Keep entry and review simple; preserve correct transfer accounting. |
| Planning | Recurring income/bills, cash-flow scenarios, savings goals, and purchase what-if | Make the assumptions visible and make upcoming shortfalls easy to inspect. |
| Budgets | Explicit category limits by month, remaining amounts, overspending and pacing | Connect each budget directly to recorded expenses; show spending outside budgets too. |
| Mobile and desktop | Responsive PWA using one Django server and shared account records | Start with browser installation, as requested; no separate native codebase yet. |
| AI | Opt-in Ollama companion with a server-selected local model and bounded summary | Explain figures without granting the model write access or sending individual transaction descriptions. |

Self-hosting, PWA support, and AI are therefore foundations to implement well, rather than sufficient differentiation by themselves. Our practical emphasis is the connected planning workflow and transparent calculations.

## Implemented capabilities and current limits

- **Dashboard and budgets:** real account data, category spending, upcoming recurring bills, a 30-day outlook, monthly limits, and unusual-spending comparisons. The ledger records posted activity dated today or earlier; future entries and CSV rows are rejected with guidance to use recurring bills or the what-if planner. Existing future-dated rows from earlier versions remain stored, but do not affect current balances until their dates and are not included as forecast events. Budget pacing is a linear comparison with elapsed days, not a prediction. Budgets apply to a selected month and do not automatically roll over.
- **Forecasts and what-if:** projections use entered recurring items and estimated everyday spending. The ±25% spending range is an illustrative scenario range, not a statistically calibrated confidence interval. Unknown bills and incomplete history can change the result; backtesting remains future work.
- **Local AI:** the integration supports Ollama and a configurable local model, with Qwen3 4B as the default. The model/runtime must be installed separately. It runs on the app server, including when the interface is opened on a phone. See [local AI setup](LOCAL_AI.md).
- **Installable app:** one responsive interface can be installed where the browser supports it. Financial operations need a reachable server; offline mode shows a reconnect screen and does not queue writes or cache financial pages. There are no APK, iOS, Windows, or macOS native binaries. See [installation details](INSTALL.md).
- **Data and deployment:** SQLite locally or PostgreSQL through Docker. Multiple devices use the same server database. Transaction CSV export is an analysis export, not a complete restorable backup or an automatic bank connection.

## Next work, ordered by user value

1. **Backup and recovery:** an owner-scoped, versioned export covering accounts, transactions, budgets, recurring items, and goals; validated restore; and a tested database backup procedure. A restore preview should show exactly what will change.
2. **Better statement imports:** use anonymized examples from the user's actual bank to define column/date/number mappings, preview rows, detect duplicates, and make corrections before importing. Add OFX or other formats when there is a demonstrated need.
3. **Forecast reliability:** distinguish scheduled future entries from posted transactions, reconcile recurring bills with actual entries, test forecasts against later outcomes, and show how much history supports an estimate.
4. **Shared households:** explicit membership and permissions, split expenses, settlement tracking, and clear ownership. Independent user accounts today do not form a shared household.
5. **Multiple currencies:** currency per account, dated exchange rates, conversion fees, and explicit valuation rules. Changing `APP_CURRENCY` today only changes the display label; it does not convert money.
6. **Receipts:** attachments plus optional local OCR/vision extraction, followed by a human review before a transaction is created. No receipt recognition ships in this revision.
7. **Offline entry and synchronization:** an encrypted local store, conflict handling, and reliable duplicate prevention before enabling offline writes. Current cross-device access is to one online server, not synchronization between independent databases.
8. **Public deployment hardening:** login throttling, a second authentication factor, operational monitoring, and recovery testing before broad public use. Native wrappers can follow once device-specific needs justify them.

Keeping these boundaries explicit lets the project improve without presenting unfinished integrations as available features.
