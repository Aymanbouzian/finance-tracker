import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'transport.dart';

typedef JsonMap = Map<String, dynamic>;

class ApiException implements Exception {
  ApiException(
    this.message, {
    this.status,
    this.code = 'request_failed',
    this.fields = const {},
  });
  final String message;
  final int? status;
  final String code;
  final Map<String, List<String>> fields;
  @override
  String toString() => message;
}

/// Cookie-authenticated Django API. The URL is app configuration, never a field
/// accepted from an AI response or a financial record.
class ApiClient {
  ApiClient({
    http.Client? client,
    String? baseUrl,
    this.timeout = const Duration(seconds: 25),
  }) : _client = client ?? createHttpClient(),
       baseUri = _base(baseUrl ?? const String.fromEnvironment('API_BASE_URL'));

  final http.Client _client;
  final Uri baseUri;
  final Duration timeout;
  String? _csrfToken;
  Future<JsonMap>? _bootstrap;
  static const resources = {
    'accounts',
    'categories',
    'transactions',
    'budgets',
    'goals',
    'recurring',
  };

  static Uri _base(String configured) {
    final uri = Uri.parse(configured.isEmpty ? defaultApiOrigin() : configured);
    if (!{'http', 'https'}.contains(uri.scheme) ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw ArgumentError(
        'API_BASE_URL must be an HTTP(S) server origin or API URL without credentials.',
      );
    }
    var path = uri.path.replaceAll(RegExp(r'/+$'), '');
    if (!path.endsWith('/api')) path = '$path/api';
    return uri.replace(path: '$path/');
  }

  Uri endpoint(String path, [Map<String, dynamic>? query]) {
    final uri = baseUri.resolve(path);
    return query == null || query.isEmpty
        ? uri
        : uri.replace(
            queryParameters: {
              for (final entry in query.entries)
                if (entry.value != null && entry.value.toString().isNotEmpty)
                  entry.key: entry.value.toString(),
            },
          );
  }

  Future<void> _ensureCsrf() async {
    if (_csrfToken != null) return;
    final pending = _bootstrap ??= session();
    try {
      await pending;
    } finally {
      if (identical(_bootstrap, pending)) _bootstrap = null;
    }
    if (_csrfToken == null) {
      throw ApiException(
        'The server did not provide a session token. Refresh and try again.',
        code: 'csrf_missing',
      );
    }
  }

  Future<JsonMap> _request(
    String method,
    String path, {
    JsonMap? body,
    Map<String, dynamic>? query,
    Duration? requestTimeout,
  }) async {
    final mutation = !{'GET', 'HEAD', 'OPTIONS'}.contains(method);
    if (mutation) await _ensureCsrf();
    final request = http.Request(method, endpoint(path, query))
      ..followRedirects = false
      ..headers['Accept'] = 'application/json';
    if (mutation) {
      request.headers['Content-Type'] = 'application/json';
      request.headers['X-CSRFToken'] = _csrfToken!;
      if (body != null) request.body = jsonEncode(body);
    }
    try {
      final response = await _client
          .send(request)
          .then(http.Response.fromStream)
          .timeout(requestTimeout ?? timeout);
      if (response.bodyBytes.length > 4 * 1024 * 1024) {
        throw ApiException(
          'The server response is too large. Try a smaller result set.',
          code: 'response_too_large',
        );
      }
      dynamic decoded;
      try {
        decoded = jsonDecode(utf8.decode(response.bodyBytes));
      } on FormatException {
        throw ApiException(
          response.statusCode == 403
              ? 'Your session verification expired. Refresh and try again.'
              : 'The server returned an unexpected response. Check the server address and try again.',
          status: response.statusCode,
          code: 'invalid_response',
        );
      }
      if (decoded is! Map) {
        throw ApiException(
          'The server returned an unexpected response.',
          status: response.statusCode,
          code: 'invalid_response',
        );
      }
      final data = Map<String, dynamic>.from(decoded);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final fields = <String, List<String>>{};
        if (data['errors'] is Map) {
          for (final entry in (data['errors'] as Map).entries) {
            fields[entry.key.toString()] = entry.value is List
                ? (entry.value as List)
                      .map((value) => value.toString())
                      .toList()
                : [entry.value.toString()];
          }
        }
        throw ApiException(
          data['error']?.toString() ?? 'The request could not be completed.',
          status: response.statusCode,
          code: data['code']?.toString() ?? 'request_failed',
          fields: fields,
        );
      }
      final token = data['csrfToken'];
      if (token is String && token.isNotEmpty) _csrfToken = token;
      return data;
    } on TimeoutException {
      throw ApiException(
        mutation
            ? 'The request timed out before confirmation. Refresh the data before trying again.'
            : 'The server took too long to respond. Try again.',
        code: 'timeout',
      );
    } on http.ClientException {
      throw ApiException(
        mutation
            ? 'The connection was interrupted before confirmation. Refresh the data before trying again.'
            : 'Cannot reach your server. Check the connection and try again.',
        code: 'connection',
      );
    }
  }

  Future<JsonMap> session() => _request('GET', 'session/');
  Future<JsonMap> signIn(String username, String password) => _request(
    'POST',
    'login/',
    body: {'username': username, 'password': password},
  );
  Future<JsonMap> register(
    String username,
    String password,
    String confirmPassword, {
    String firstName = '',
  }) => _request(
    'POST',
    'register/',
    body: {
      'username': username,
      'password1': password,
      'password2': confirmPassword,
      'first_name': firstName,
    },
  );
  Future<JsonMap> signOut() => _request('POST', 'logout/', body: {});
  Future<JsonMap> overview() => _request('GET', 'overview/');

  String _resourcePath(String resource, [int? id]) {
    if (!resources.contains(resource) || (id != null && id <= 0)) {
      throw ArgumentError('Unknown resource or invalid record ID.');
    }
    return '$resource/${id == null ? '' : '$id/'}';
  }

  Future<JsonMap> listResource(
    String resource, {
    Map<String, dynamic>? query,
  }) => _request('GET', _resourcePath(resource), query: query);
  Future<JsonMap> getResource(String resource, int id) =>
      _request('GET', _resourcePath(resource, id));
  Future<JsonMap> saveResource(String resource, JsonMap fields, {int? id}) =>
      _request('POST', _resourcePath(resource, id), body: fields);
  Future<JsonMap> deleteResource(String resource, int id) =>
      _request('DELETE', _resourcePath(resource, id), body: {});
  Future<JsonMap> forecast({int days = 90, String? dailySpend}) => _request(
    'GET',
    'forecast/',
    query: {'days': days, 'daily_spend': dailySpend},
  );
  Future<JsonMap> whatIf(JsonMap fields) =>
      _request('POST', 'what-if/', body: fields);
  Future<JsonMap> assistant() => _request('GET', 'assistant/');
  Future<JsonMap> askAssistant(String question, {required bool shareSummary}) =>
      _request(
        'POST',
        'assistant/',
        body: {'question': question, 'share_summary': shareSummary},
        requestTimeout: const Duration(seconds: 125),
      );

  void resetCsrf() => _csrfToken = null;
  void close() => _client.close();
}
