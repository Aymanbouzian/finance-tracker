# Flutter validation · 16 November 2026

The user's updates in main.dart, design.dart and dashboard.dart are retained. An exact copy of those files before this review's small motion correction is saved locally in `docs/snapshots/user-ui-2026-11-16.zip`.

## Passed

- Flutter analysis: no issues.
- 16 Flutter tests: CSRF/session handling, exact decimal formatting, native cookie isolation, stale-request handling, confirmed-write retries, assistant consent, sign-in and navigation at 390px and 1440px.
- 117 Django tests, including 20 API checks and 8 Flutter asset-serving checks.
- 10 web-worker tests, including the regression for competing worker registration.
- Release web build with local CanvasKit resources and `/app/` base path.
- Browser checks of the real release: dashboard at 390×844 and 1440×1000, transaction dialog, planning/forecast, AI connection state, and motion toggle. No browser console errors observed.

## Corrections during review

The Flutter default bootstrap registered its retired service worker on the same scope as our offline worker. They replaced each other, causing repeated reloads and a blank screen. The explicit bootstrap now starts Flutter without that registration. The public offline worker remains responsible for the reconnect page.

Budget progress animation now respects reduced-motion settings. The widget test recognizes the user's new hero text. The AI setup instruction correctly refers to an environment variable rather than implying Django reads `.env` automatically.

## Current limits

Native project scaffolds are included; native installers, physical-device installation and live Ollama generation have not been verified. The preview reports local AI as disabled. CSV tools remain in the classic interface. Records require a connection to the backend.

Visual review noted optional refinements in the user's metric cards: stronger small-text contrast on the light gradient, and moving the inset radial highlight to the whole card. Those visual choices were preserved during this review.

Screenshots: `screenshots/desktop.jpg` and `screenshots/mobile.jpg` use the demonstration account.
