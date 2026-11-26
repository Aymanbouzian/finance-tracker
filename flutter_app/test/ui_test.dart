import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pocketledger/data/api_client.dart';
import 'package:pocketledger/data/app_controller.dart';
import 'package:pocketledger/main.dart';

void main() {
  for (final width in [390.0, 1440.0]) {
    testWidgets('Sign in, overview and navigation fit width $width', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      bool authenticated = false;
      final api = ApiClient(
        baseUrl: 'http://localhost:8000',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/login/')) authenticated = true;
          if (path.endsWith('/logout/')) authenticated = false;
          Object data;
          if (path.contains('session') ||
              path.contains('login') ||
              path.contains('logout')) {
            data = {
              'authenticated': authenticated,
              'csrfToken': 'token',
              'currency': 'MAD',
              'user': authenticated
                  ? {'username': 'demo', 'first_name': 'Ayman'}
                  : null,
            };
          } else if (path.endsWith('/overview/')) {
            data = {
              'balance': '25000.25',
              'income': '15000.00',
              'expense': '3500.50',
              'month_label': 'November 2026',
              'accounts': [],
              'history': [
                {'label': 'Oct', 'income': '20000', 'expense': '3000'},
                {'label': 'Nov', 'income': '15000', 'expense': '3500.50'},
              ],
              'recent': [],
              'goals': [],
              'budgets': {
                'total_budget': '5000',
                'total_remaining': '1499.50',
                'rows': [],
              },
              'forecast': {'end_expected': '27000.25', 'daily_spend': '25.00'},
            };
          } else if (path.endsWith('/assistant/')) {
            data = {
              'status': {
                'ready': false,
                'label': 'Not enabled',
                'detail': 'Connect Ollama when ready.',
              },
              'summary': {'balance': '25000.25'},
              'model': 'qwen3:4b',
            };
          } else {
            data = {'results': [], 'page': 1, 'pages': 1, 'count': 0};
          }
          return http.Response(
            jsonEncode(data),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );
      final controller = AppController(api: api);
      addTearDown(controller.dispose);
      await tester.pumpWidget(PocketLedgerApp(controller: controller));
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('Welcome back.'), findsOneWidget);
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Username'),
        'demo',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'password',
      );
      await tester.tap(find.text('Step inside'));
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      expect(
        find.text('Your money,\nfinally clear.', findRichText: true),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
      if (width >= 900) {
        await tester.tap(find.byTooltip('Activity'));
      } else {
        await tester.tap(find.text('Activity'));
      }
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('Your activity'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.enterText(find.byType(TextField), 'groceries');
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pump();
      expect(controller.resourceQueries['transactions']?['q'], 'groceries');
      await tester.tap(
        width >= 900 ? find.byTooltip('Plan ahead') : find.text('Plan'),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.tap(find.text('Savings goals'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 180));
      expect(find.text('Little by little'), findsOneWidget);
      await tester.pump(const Duration(seconds: 1));
      await tester.tap(find.byTooltip('Pause motion'));
      await tester.pump();
      await tester.tap(find.text('Budgets'));
      await tester.pump();
      expect(find.text('Your monthly rhythm'), findsOneWidget);
      expect(tester.takeException(), isNull);
      if (width >= 900) {
        await tester.tap(find.byTooltip('Local AI'));
      } else {
        await tester.tap(find.text('AI'));
      }
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('A fresh perspective.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
    });
  }
}
