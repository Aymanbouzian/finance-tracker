import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:pocketledger/data/api_client.dart';
import 'package:pocketledger/data/money.dart';

http.Response jsonResponse(Map<String, dynamic> data, [int status = 200]) =>
    http.Response(
      jsonEncode(data),
      status,
      headers: {'content-type': 'application/json'},
    );

void main() {
  test(
    'csrf is bootstrapped before login and rotated token protects later writes',
    () async {
      final seen = <http.Request>[];
      final api = ApiClient(
        baseUrl: 'https://ledger.example',
        client: MockClient((request) async {
          seen.add(request);
          if (request.url.path == '/api/session/') {
            return jsonResponse({
              'authenticated': false,
              'csrfToken': 'initial-token',
            });
          }
          if (request.url.path == '/api/login/') {
            return jsonResponse({
              'authenticated': true,
              'csrfToken': 'rotated-token',
            });
          }
          return jsonResponse({
            'item': {'id': 1},
          }, 201);
        }),
      );
      addTearDown(api.close);
      await api.signIn('alex', 'test-password');
      await api.saveResource('transactions', {
        'amount': '9999999999.99',
        'kind': 'expense',
        'account': 1,
      });
      expect(seen.map((request) => request.url.path).toList(), [
        '/api/session/',
        '/api/login/',
        '/api/transactions/',
      ]);
      expect(seen[1].headers['X-CSRFToken'], 'initial-token');
      expect(seen[2].headers['X-CSRFToken'], 'rotated-token');
      expect(jsonDecode(seen[2].body)['amount'], isA<String>());
      expect(jsonDecode(seen[2].body)['amount'], '9999999999.99');
      expect(seen.every((request) => !request.followRedirects), isTrue);
    },
  );

  test(
    'list filters are encoded without allowing a filter to alter the endpoint',
    () async {
      late Uri requested;
      final api = ApiClient(
        baseUrl: 'https://ledger.example/api/',
        client: MockClient((request) async {
          requested = request.url;
          return jsonResponse({
            'results': [],
            'count': 0,
            'page': 1,
            'pages': 1,
          });
        }),
      );
      addTearDown(api.close);
      await api.listResource(
        'transactions',
        query: {'q': 'coffee & food/?', 'page': 2, 'kind': '', 'account': null},
      );
      expect(requested.path, '/api/transactions/');
      expect(requested.queryParameters, {'q': 'coffee & food/?', 'page': '2'});
      expect(() => api.listResource('../admin'), throwsArgumentError);
    },
  );

  test(
    'server validation errors keep field messages and HTTP status',
    () async {
      final api = ApiClient(
        baseUrl: 'https://ledger.example',
        client: MockClient((request) async {
          if (request.method == 'GET') {
            return jsonResponse({'csrfToken': 'token'});
          }
          return jsonResponse({
            'error': 'Check the highlighted fields.',
            'code': 'validation_error',
            'errors': {
              'amount': ['Must be positive.'],
            },
          }, 400);
        }),
      );
      addTearDown(api.close);
      await expectLater(
        api.saveResource('budgets', {'amount': '-1'}),
        throwsA(
          isA<ApiException>()
              .having((failure) => failure.status, 'status', 400)
              .having(
                (failure) => failure.fields['amount'],
                'amount messages',
                ['Must be positive.'],
              ),
        ),
      );
    },
  );

  test('HTML failures are not surfaced as raw server output', () async {
    final api = ApiClient(
      baseUrl: 'https://ledger.example',
      client: MockClient(
        (_) async =>
            http.Response('<html>internal server traceback</html>', 500),
      ),
    );
    addTearDown(api.close);
    await expectLater(
      api.overview(),
      throwsA(
        isA<ApiException>()
            .having((failure) => failure.code, 'code', 'invalid_response')
            .having(
              (failure) => failure.message.contains('traceback'),
              'private server output',
              isFalse,
            ),
      ),
    );
  });

  test(
    'money formatting retains exact decimal digits without float arithmetic',
    () {
      expect(
        formatMoney('9999999999.99', currency: 'MAD'),
        '9,999,999,999.99 MAD',
      );
      expect(formatMoney('-1234.50'), '−1,234.50');
      expect(formatMoney('0.1'), '0.10');
      expect(formatMoney('9007199254740993.01'), '9,007,199,254,740,993.01');
      expect(moneyInput('1234.50'), '1234.50');
      expect(formatMoney('not a number'), '—');
    },
  );
}
