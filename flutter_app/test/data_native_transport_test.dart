import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:pocketledger/data/transport_native.dart';

void main() {
  test(
    'native cookies survive combined Set-Cookie headers and Origin is supplied for writes',
    () async {
      final requests = <http.Request>[];
      final client = MemoryCookieClient(
        now: () => DateTime.utc(2026, 11, 14),
        inner: MockClient((request) async {
          requests.add(request);
          return request.url.path == '/api/session/'
              ? http.Response(
                  '{}',
                  200,
                  headers: {
                    'set-cookie':
                        'csrftoken=csrf; Path=/; Expires=Tue, 01 Jan 2030 00:00:00 GMT, sessionid=session; Path=/; HttpOnly',
                  },
                )
              : http.Response('{}', 200);
        }),
      );
      addTearDown(client.close);
      await client.get(Uri.parse('https://ledger.example/api/session/'));
      await client.post(
        Uri.parse('https://ledger.example/api/transactions/'),
        body: '{}',
      );
      expect(requests.last.headers['cookie'], contains('csrftoken=csrf'));
      expect(requests.last.headers['cookie'], contains('sessionid=session'));
      expect(requests.last.headers['origin'], 'https://ledger.example');
      expect(requests.last.followRedirects, isFalse);
    },
  );

  test('native cookies respect host, path, and Secure attributes', () async {
    final received = <String, String?>{};
    final client = MemoryCookieClient(
      inner: MockClient((request) async {
        received[request.url.toString()] = request.headers['cookie'];
        return request.url.path == '/bootstrap'
            ? http.Response(
                '{}',
                200,
                headers: {
                  'set-cookie':
                      'sessionid=secret; Path=/api/; Secure, scoped=ok; Path=/special/, foreign=bad; Domain=evil.example; Path=/',
                },
              )
            : http.Response('{}', 200);
      }),
    );
    addTearDown(client.close);
    await client.get(Uri.parse('https://ledger.example/bootstrap'));
    for (final url in [
      'https://ledger.example/api/items/',
      'http://ledger.example/api/items/',
      'https://other.example/api/items/',
      'https://ledger.example/special/item',
      'https://ledger.example/specialish/item',
    ]) {
      await client.get(Uri.parse(url));
    }
    expect(received['https://ledger.example/api/items/'], 'sessionid=secret');
    expect(received['http://ledger.example/api/items/'], isNull);
    expect(received['https://other.example/api/items/'], isNull);
    expect(received['https://ledger.example/special/item'], 'scoped=ok');
    expect(received['https://ledger.example/specialish/item'], isNull);
  });

  test('server logout and expiration remove native session cookies', () async {
    var now = DateTime.utc(2026, 11, 14);
    String? lastCookie;
    final client = MemoryCookieClient(
      now: () => now,
      inner: MockClient((request) async {
        lastCookie = request.headers['cookie'];
        if (request.url.path == '/login') {
          return http.Response(
            '{}',
            200,
            headers: {'set-cookie': 'sessionid=secret; Path=/; Max-Age=60'},
          );
        }
        if (request.url.path == '/logout') {
          return http.Response(
            '{}',
            200,
            headers: {'set-cookie': 'sessionid=; Path=/; Max-Age=0'},
          );
        }
        return http.Response('{}', 200);
      }),
    );
    addTearDown(client.close);
    await client.get(Uri.parse('https://ledger.example/login'));
    await client.get(Uri.parse('https://ledger.example/check'));
    expect(lastCookie, 'sessionid=secret');
    now = now.add(const Duration(seconds: 61));
    await client.get(Uri.parse('https://ledger.example/check'));
    expect(lastCookie, isNull);
    await client.get(Uri.parse('https://ledger.example/login'));
    await client.post(Uri.parse('https://ledger.example/logout'));
    await client.get(Uri.parse('https://ledger.example/check'));
    expect(lastCookie, isNull);
  });
}
