import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:pocketledger/data/api_client.dart';
import 'package:pocketledger/data/app_controller.dart';

class FakeApi extends ApiClient {
  FakeApi()
    : super(
        baseUrl: 'https://ledger.example',
        client: MockClient((_) async => http.Response('{}', 200)),
      );
  Future<JsonMap> Function()? onOverview;
  Future<JsonMap> Function(String, Map<String, dynamic>?)? onList;
  Future<JsonMap> Function(String, JsonMap, int?)? onSave;
  Future<JsonMap> Function()? onSession;
  int askCalls = 0;
  int saveCalls = 0;

  @override
  Future<JsonMap> session() async => onSession == null
      ? {
          'authenticated': true,
          'user': {'username': 'alex'},
          'csrfToken': 'token',
          'currency': 'MAD',
        }
      : await onSession!();
  @override
  Future<JsonMap> overview() async => onOverview == null
      ? {'balance': '100.00', 'currency': 'MAD'}
      : await onOverview!();
  @override
  Future<JsonMap> signOut() async => {
    'authenticated': false,
    'user': null,
    'csrfToken': 'after-logout',
    'currency': 'MAD',
  };
  @override
  Future<JsonMap> listResource(
    String resource, {
    Map<String, dynamic>? query,
  }) async => onList == null
      ? {'results': [], 'count': 0, 'page': 1, 'pages': 1}
      : await onList!(resource, query);
  @override
  Future<JsonMap> saveResource(
    String resource,
    JsonMap fields, {
    int? id,
  }) async {
    ++saveCalls;
    return onSave == null
        ? {
            'item': {'id': 1, ...fields},
          }
        : await onSave!(resource, fields, id);
  }

  @override
  Future<JsonMap> askAssistant(
    String question, {
    required bool shareSummary,
  }) async {
    ++askCalls;
    return {
      'answer': 'A local explanation.',
      'summary': {'balance': '100.00'},
      'model': 'qwen3:4b',
    };
  }
}

void main() {
  test('initialization failures leave a usable retry state', () async {
    final api = FakeApi();
    api.onSession = () async =>
        throw ApiException('Server unavailable.', status: 503);
    final controller = AppController(api: api);
    addTearDown(controller.dispose);
    await controller.initialize();
    expect(controller.initialized, isTrue);
    expect(controller.isLoading, isFalse);
    expect(controller.error, 'Server unavailable.');
    expect(controller.canRetry, isTrue);
    api.onSession = null;
    await controller.retry();
    expect(controller.authenticated, isTrue);
    expect(controller.overview['balance'], '100.00');
    expect(controller.error, isNull);
  });

  test('a late read cannot put private data back after logout', () async {
    final api = FakeApi();
    final controller = AppController(api: api);
    addTearDown(controller.dispose);
    await controller.initialize();
    final late = Completer<JsonMap>();
    api.onOverview = () => late.future;
    final pending = controller.refreshOverview();
    await controller.signOut();
    expect(controller.authenticated, isFalse);
    expect(controller.overview, isEmpty);
    late.complete({'balance': 'secret-stale-value'});
    await pending;
    expect(controller.overview, isEmpty);
    expect(controller.user, isNull);
  });

  test(
    'the latest filter response wins when network responses arrive out of order',
    () async {
      final api = FakeApi();
      final first = Completer<JsonMap>();
      final second = Completer<JsonMap>();
      api.onList = (_, query) =>
          query?['q'] == 'first' ? first.future : second.future;
      final controller = AppController(api: api);
      addTearDown(controller.dispose);
      final oldRequest = controller.loadResource(
        'transactions',
        query: {'q': 'first'},
      );
      final newRequest = controller.loadResource(
        'transactions',
        query: {'q': 'second'},
      );
      second.complete({
        'results': [
          {'id': 2, 'amount': '12.34'},
        ],
        'count': 1,
        'page': 1,
        'pages': 1,
      });
      await newRequest;
      first.complete({
        'results': [
          {'id': 1, 'amount': '99.99'},
        ],
        'count': 1,
        'page': 1,
        'pages': 1,
      });
      await oldRequest;
      expect(controller.records('transactions').single['id'], 2);
      expect(controller.resourceQueries['transactions'], {'q': 'second'});
    },
  );

  test(
    'a confirmed save stays successful when refresh fails and retry does not save twice',
    () async {
      final api = FakeApi();
      api.onOverview = () async =>
          throw ApiException('Read failed.', status: 503);
      final controller = AppController(api: api);
      addTearDown(controller.dispose);
      expect(
        await controller.saveResource('transactions', {'amount': '12.34'}),
        isTrue,
      );
      expect(controller.error, contains('Saved successfully'));
      expect(api.saveCalls, 1);
      api.onOverview = null;
      await controller.retry();
      expect(api.saveCalls, 1);
      expect(controller.error, isNull);
      expect(controller.overview['balance'], '100.00');
    },
  );

  test('an expired server session clears every private view', () async {
    final api = FakeApi();
    final controller = AppController(api: api);
    addTearDown(controller.dispose);
    await controller.initialize();
    controller.resources['transactions'] = [
      {'amount': '500.00'},
    ];
    controller.assistantAnswer = 'Private answer';
    api.onOverview = () async =>
        throw ApiException('Sign in again.', status: 401);
    await controller.refreshOverview();
    expect(controller.authenticated, isFalse);
    expect(controller.overview, isEmpty);
    expect(controller.resources, isEmpty);
    expect(controller.assistantAnswer, isNull);
    expect(controller.error, 'Sign in again.');
  });

  test('AI requests require explicit summary approval', () async {
    final api = FakeApi();
    final controller = AppController(api: api);
    addTearDown(controller.dispose);
    await controller.askAssistant('Explain my month');
    expect(api.askCalls, 0);
    expect(controller.fieldErrors, contains('share_summary'));
    await controller.askAssistant('Explain my month', shareSummary: true);
    expect(api.askCalls, 1);
    expect(controller.assistantAnswer, 'A local explanation.');
    expect(controller.error, isNull);
  });
}
