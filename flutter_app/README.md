# PocketLedger for Flutter

A responsive Flutter client for the existing PocketLedger Django backend. The app presents a warm, fluid money dashboard with translucent panels, amber and peach highlights, blue charts, lavender details and gentle water-like motion. Desktop uses a spacious navigation shell; narrower screens rearrange the same financial workflows for touch.

The visual direction was informed by the user's [Behance healthtech reference](https://www.behance.net/gallery/253466975/UIUX-Design-for-a-Healthtech-Product) and a request for an Apple-inspired glass effect. This is an independent Flutter implementation, not Apple's native Liquid Glass framework or a copy of the reference's assets.

## Architecture and migration

```text
Flutter web / native client
        |
        | JSON + session cookies + CSRF verification
        v
Django /api/ ---- SQLite or PostgreSQL
        |
        +------- Optional Ollama server
```

The Django database remains the accounting authority. Existing accounts, transactions, budgets, goals and recurring items are retained; they are not migrated into a second local database. All monetary API fields are decimal strings. Flutter preserves these strings for forms and formatting and converts values to doubles only when drawing charts.

The Django root redirects to `/app/`, where it serves the compiled Flutter client alongside `/api/` on the same origin. The previous Django interface remains at `/classic/`, with its existing forms and CSV tools. Both interfaces use the same records and authentication system. The documented API contract is at [`../clientapi/API_CONTRACT.md`](../clientapi/API_CONTRACT.md).

Included Flutter flows cover authentication, dashboard, transactions, accounts, categories, monthly budgets, savings goals, recurring plans, forecasts, what-if scenarios and the read-only local AI companion. Create/edit dialogs use the existing server validation rules; account/category deletion shows the consequences before submitting.

## Toolchain

This rebuild uses **Flutter 3.50.0 and Dart 3.14**. The Material widgets are imported from `package:material_ui/material_ui.dart` with `material_ui: 1.1.0`, matching the generated Flutter scaffold. Keep `pubspec.lock` for reproducible dependency selection.

Check your installation with:

```text
flutter --version
flutter doctor -v
flutter devices
```

## Run the web app with Django

From this `flutter_app` directory:

```text
flutter pub get
flutter build web --release --base-href /app/ --no-web-resources-cdn
```

Then, from the repository root, use the backend's virtual environment:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open [PocketLedger](http://127.0.0.1:8000/app/). Registration creates your own empty ledger; the existing local demo account can be used if the sample data was seeded. No sample records are hardcoded into the Flutter client.

The web build defaults to the browser's current origin for `/api/`; serving it through Django keeps cookies and CSRF on the same origin. A separate `flutter run -d chrome` web origin is not configured for cross-origin API access. Rebuild the web output after UI changes and refresh the Django URL. The `--no-web-resources-cdn` flag bundles Flutter's web rendering resources locally.

By default, Django reads `flutter_app/build/web`. Override its `FLUTTER_WEB_DIR` environment variable when the compiled assets live elsewhere. If the build is missing, `/app/` returns an explicit setup message; `/classic/` remains available.

## Desktop and mobile targets

Platform scaffolds are included for Windows, Android, iOS, macOS, Linux and web. A generated scaffold does not mean a signed binary for each platform has been built or tested. This work validates the Flutter web client; native packaging needs the corresponding toolchain and device checks.

### Windows

Install Visual Studio with the **Desktop development with C++** workload; Visual Studio Code alone does not provide that compiler. Confirm the Windows and Visual Studio sections of `flutter doctor -v`, following [Flutter's Windows setup](https://docs.flutter.dev/platform-integration/windows/setup).

Run Django, then from `flutter_app`:

```text
flutter run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

For a release connected to your hosted server:

```text
flutter build windows --release --dart-define=API_BASE_URL=https://money.example.com
```

Distribute the entire generated release directory with its supporting files, not just the `.exe`. Installer creation, code signing and installation testing are separate release steps.

### Android

Install the Android SDK/toolchain through Android Studio, review the licenses with `flutter doctor --android-licenses`, and configure an emulator or physical device. Follow the [official Android setup](https://docs.flutter.dev/platform-integration/android/setup). Use a reachable HTTPS backend for a physical phone:

```text
flutter run -d YOUR_DEVICE_ID --dart-define=API_BASE_URL=https://money.example.com
flutter build apk --release --dart-define=API_BASE_URL=https://money.example.com
```

Replace `YOUR_DEVICE_ID` with a value from `flutter devices`. `127.0.0.1` on a phone is the phone, not the development PC. Native release manifests and platform network permissions must be verified before distribution. Release signing and store submission are not configured by these commands.

### iOS and macOS

iOS and macOS builds require a Mac with the applicable Xcode tooling. Windows cannot compile their native releases. Use [Flutter's iOS setup](https://docs.flutter.dev/platform-integration/ios/setup) and [macOS setup](https://docs.flutter.dev/platform-integration/macos/setup), then configure signing, a reachable HTTPS backend and the required app entitlements. An Apple developer account is needed for the relevant distribution channels.

### Linux

Install the platform's native compiler and desktop libraries using [Flutter's Linux setup](https://docs.flutter.dev/platform-integration/linux/setup). Build on Linux with the server origin passed through `API_BASE_URL` as above.

## Server configuration and deployment

Use the backend's existing production environment settings: a strong secret key, `DJANGO_DEBUG=0`, exact allowed hosts, HTTPS cookies behind a trusted reverse proxy, and an appropriate database backup strategy. See [`../README.md`](../README.md).

Build Flutter web before running `docker compose up --build` from the repository root. The Dockerfile includes the compiled `flutter_app/build/web` directory at the path Django serves.

Keep `/app/` and `/api/` on the same origin for the browser build. Native clients use the origin compiled with `API_BASE_URL`, retain cookies only in memory, and require sign-in again after restarting. They send CSRF verification on writes; do not disable CSRF to connect a native client.

## Local AI

Ollama remains a server-side optional integration. Set `OLLAMA_ENABLED=1`, install the selected local model, and configure its endpoint on Django. The Flutter client cannot set or redirect the Ollama endpoint. The companion shows aggregate context and requires approval before sending a question. It cannot modify the ledger, make payments or execute model-provided code. See [`../docs/LOCAL_AI.md`](../docs/LOCAL_AI.md).

Live inference requires Ollama and its model to be installed and reachable; mocked integration tests do not establish that live inference was performed.

## Motion, accessibility and offline behavior

The design uses clipped backdrop blur, translucent surfaces, gradient highlights and subtle motion. The shell offers a motion toggle. Custom animation should respect platform reduced-motion preferences; Flutter's [animation accessibility guidance](https://api.flutter.dev/flutter/widgets/MediaQueryData/disableAnimations.html) distinguishes `disableAnimations` from iOS `reduceMotion`. The [BackdropFilter reference](https://api.flutter.dev/flutter/widgets/BackdropFilter-class.html) describes clipping and grouped-filter performance. Profile on the intended device before adding more simultaneous blurred surfaces.

The web manifest permits browser installation on supporting platforms. The custom service worker caches only a public reconnect page; it does not cache financial API responses, credentials or records. This release needs a connection to the server for records, AI and saving changes. It does not queue offline writes or synchronize independent device databases. Native clients also hold financial state only in memory.

## Checks

From `flutter_app`:

```text
flutter analyze
flutter test
flutter build web --release --base-href /app/ --no-web-resources-cdn
```

From `finance-tracker`, using its Python environment:

```text
python manage.py check
python manage.py test
```

The automated suites exercise API ownership and validation, session/CSRF behavior, money formatting, controller state, transport handling and responsive widget layout. Browser verification, native builds, live-device installation and actual Ollama answers are separate checks; report them only after they have been performed.
