import 'package:flutter/foundation.dart';

import 'api_client.dart';

/// Shared application state for the Flutter UI. Accounting values remain the
/// server's decimal strings; no cached financial data is persisted on disk.
class AppController extends ChangeNotifier {
  AppController({ApiClient? api}) : api = api ?? ApiClient();

  final ApiClient api;
  bool initialized = false;
  bool authenticated = false;
  JsonMap? user;
  String currency = 'MAD';
  JsonMap overview = {};
  final Map<String, List<JsonMap>> resources = {};
  final Map<String, JsonMap> resourceMeta = {};
  final Map<String, JsonMap> resourceQueries = {};
  JsonMap forecast = {};
  JsonMap whatIfResult = {};
  JsonMap assistantInfo = {};
  String? assistantAnswer;
  String? error;
  Map<String, List<String>> fieldErrors = {};

  int _busy = 0;
  int _epoch = 0;
  bool _authPending = false;
  bool _disposed = false;
  Future<void> Function()? _retryAction;
  final Map<String, int> _resourceVersion = {};

  bool get isLoading => _busy > 0;
  bool get canRetry => _retryAction != null && !isLoading;
  List<JsonMap> records(String resource) => resources[resource] ?? const [];

  bool _current(int epoch) => !_disposed && epoch == _epoch;
  void _changed() {
    if (!_disposed) notifyListeners();
  }

  void clearError() {
    error = null;
    fieldErrors = {};
    _changed();
  }

  void _clearData() {
    overview = {};
    resources.clear();
    resourceMeta.clear();
    resourceQueries.clear();
    _resourceVersion.clear();
    forecast = {};
    whatIfResult = {};
    assistantInfo = {};
    assistantAnswer = null;
  }

  void _applySession(JsonMap session) {
    final nextUser = session['user'] is Map
        ? Map<String, dynamic>.from(session['user'] as Map)
        : null;
    final nextAuthenticated =
        session['authenticated'] == true && nextUser != null;
    if (!nextAuthenticated || nextUser['username'] != user?['username']) {
      _clearData();
    }
    authenticated = nextAuthenticated;
    user = nextAuthenticated ? nextUser : null;
    currency = session['currency']?.toString() ?? currency;
  }

  void _failure(Object failure, {String? prefix}) {
    if (failure is ApiException) {
      error = prefix == null ? failure.message : '$prefix ${failure.message}';
      fieldErrors = failure.fields;
      if (failure.status == 401) {
        ++_epoch;
        authenticated = false;
        user = null;
        _clearData();
        api.resetCsrf();
        _retryAction = initialize;
      } else if (failure.code == 'csrf_failed' ||
          failure.code == 'csrf_missing') {
        api.resetCsrf();
      }
    } else {
      error = prefix == null
          ? 'Something went wrong. Please refresh and try again.'
          : '$prefix Please refresh the data.';
      fieldErrors = {};
    }
  }

  Future<bool> _run(
    Future<void> Function(int epoch) action, {
    Future<void> Function()? retry,
  }) async {
    if (_disposed) return false;
    final epoch = _epoch;
    ++_busy;
    error = null;
    fieldErrors = {};
    _retryAction = retry;
    _changed();
    try {
      await action(epoch);
      return _current(epoch);
    } catch (failure) {
      if (_current(epoch)) _failure(failure);
      return false;
    } finally {
      --_busy;
      _changed();
    }
  }

  Future<void> initialize() async {
    if (_authPending || _disposed) return;
    _authPending = true;
    ++_epoch;
    final epoch = _epoch;
    await _run((generation) async {
      final session = await api.session();
      if (!_current(generation)) return;
      _applySession(session);
      if (authenticated) await _fetchOverview(generation);
    }, retry: initialize);
    if (_current(epoch)) initialized = true;
    _authPending = false;
    _changed();
  }

  Future<bool> _authenticate(Future<JsonMap> Function() request) async {
    if (_authPending || _disposed) return false;
    _authPending = true;
    ++_epoch; // Invalidate requests made under any previous session.
    final result = await _run((generation) async {
      final session = await request();
      if (!_current(generation)) return;
      _applySession(session);
      initialized = true;
      if (authenticated) await _fetchOverview(generation);
    }, retry: initialize);
    _authPending = false;
    _changed();
    return result && authenticated;
  }

  Future<bool> signIn(String username, String password) =>
      _authenticate(() => api.signIn(username.trim(), password));
  Future<bool> register(
    String username,
    String password,
    String confirmPassword, {
    String firstName = '',
  }) => _authenticate(
    () => api.register(
      username.trim(),
      password,
      confirmPassword,
      firstName: firstName.trim(),
    ),
  );

  Future<bool> signOut() async {
    if (_authPending || _disposed) return false;
    _authPending = true;
    ++_epoch;
    final result = await _run((generation) async {
      final session = await api.signOut();
      if (!_current(generation)) return;
      _applySession(session);
      _clearData();
      initialized = true;
    }, retry: initialize);
    _authPending = false;
    _changed();
    return result;
  }

  Future<void> _fetchOverview(int epoch) async {
    final data = await api.overview();
    if (!_current(epoch)) return;
    overview = data;
    currency = data['currency']?.toString() ?? currency;
  }

  Future<void> refreshOverview() async {
    await _run(_fetchOverview, retry: refreshOverview);
  }

  Future<void> _fetchResource(String name, JsonMap query, int epoch) async {
    final version = (_resourceVersion[name] ?? 0) + 1;
    _resourceVersion[name] = version;
    final data = await api.listResource(name, query: query);
    if (!_current(epoch) || _resourceVersion[name] != version) return;
    final results = data['results'];
    if (results is! List || results.any((value) => value is! Map)) {
      throw ApiException(
        'The server returned an unreadable list.',
        code: 'invalid_response',
      );
    }
    resources[name] = results
        .map((value) => Map<String, dynamic>.from(value as Map))
        .toList();
    resourceMeta[name] = {
      for (final entry in data.entries)
        if (entry.key != 'results') entry.key: entry.value,
    };
  }

  Future<void> loadResource(String name, {Map<String, dynamic>? query}) async {
    final selectedQuery = Map<String, dynamic>.from(
      query ?? resourceQueries[name] ?? const {},
    );
    resourceQueries[name] = selectedQuery;
    await _run(
      (epoch) => _fetchResource(name, selectedQuery, epoch),
      retry: () => loadResource(name, query: selectedQuery),
    );
  }

  Future<void> _refreshResourceAndOverview(String name, int epoch) async {
    await Future.wait([
      _fetchOverview(epoch),
      _fetchResource(
        name,
        Map<String, dynamic>.from(resourceQueries[name] ?? const {}),
        epoch,
      ),
    ]);
  }

  Future<void> _retryResourceAndOverview(String name) async {
    await _run(
      (epoch) => _refreshResourceAndOverview(name, epoch),
      retry: () => _retryResourceAndOverview(name),
    );
  }

  Future<bool> saveResource(String name, JsonMap fields, {int? id}) async {
    var saved = false;
    await _run((epoch) async {
      await api.saveResource(name, fields, id: id);
      if (!_current(epoch)) return;
      saved = true;
      try {
        await _refreshResourceAndOverview(name, epoch);
      } catch (failure) {
        if (_current(epoch)) {
          _failure(
            failure,
            prefix: 'Saved successfully, but the view could not refresh.',
          );
        }
      }
    }, retry: () => _retryResourceAndOverview(name));
    // A successful write is not reported as failed just because a later read
    // failed; doing so can invite the user to submit a duplicate transaction.
    return saved;
  }

  Future<bool> deleteResource(String name, int id) async {
    var deleted = false;
    await _run((epoch) async {
      await api.deleteResource(name, id);
      if (!_current(epoch)) return;
      deleted = true;
      try {
        await _refreshResourceAndOverview(name, epoch);
      } catch (failure) {
        if (_current(epoch)) {
          _failure(
            failure,
            prefix: 'Deleted successfully, but the view could not refresh.',
          );
        }
      }
    }, retry: () => _retryResourceAndOverview(name));
    return deleted;
  }

  Future<void> loadForecast({int days = 90, String? dailySpend}) async {
    await _run((epoch) async {
      final result = await api.forecast(days: days, dailySpend: dailySpend);
      if (_current(epoch)) forecast = result;
    }, retry: () => loadForecast(days: days, dailySpend: dailySpend));
  }

  Future<void> runWhatIf(JsonMap fields) async {
    final input = Map<String, dynamic>.from(fields);
    await _run((epoch) async {
      final result = await api.whatIf(input);
      if (_current(epoch)) whatIfResult = result;
    }, retry: () => runWhatIf(input));
  }

  Future<void> loadAssistant() async {
    await _run((epoch) async {
      final result = await api.assistant();
      if (_current(epoch)) assistantInfo = result;
    }, retry: loadAssistant);
  }

  Future<void> askAssistant(
    String question, {
    bool shareSummary = false,
  }) async {
    if (!shareSummary) {
      error =
          'Approve sharing the displayed summary with your local model before asking.';
      fieldErrors = {
        'share_summary': ['Approval is required for each request.'],
      };
      _retryAction = null;
      _changed();
      return;
    }
    assistantAnswer = null;
    await _run((epoch) async {
      final result = await api.askAssistant(question, shareSummary: true);
      if (!_current(epoch)) return;
      assistantAnswer = result['answer']?.toString();
      assistantInfo = {
        ...assistantInfo,
        'summary': result['summary'],
        'model': result['model'],
      };
    }, retry: () => askAssistant(question, shareSummary: true));
  }

  Future<void> retry() async {
    final action = _retryAction;
    if (!isLoading && action != null) await action();
  }

  @override
  void dispose() {
    _disposed = true;
    ++_epoch;
    api.close();
    super.dispose();
  }
}
