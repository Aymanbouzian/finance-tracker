import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

http.Client createHttpClient() => MemoryCookieClient();

String defaultApiOrigin() => 'http://127.0.0.1:8000';

/// A native IOClient with an ephemeral, origin/path-scoped cookie jar.
/// Session cookies are never written to files or platform preferences.
class MemoryCookieClient extends http.BaseClient {
  MemoryCookieClient({http.Client? inner, DateTime Function()? now})
    : _inner = inner ?? IOClient(),
      _now = now ?? DateTime.now;

  final http.Client _inner;
  final DateTime Function() _now;
  final Map<String, _StoredCookie> _cookies = {};

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final now = _now().toUtc();
    _cookies.removeWhere(
      (_, value) => value.expires != null && !value.expires!.isAfter(now),
    );
    final selected =
        _cookies.values.where((value) => value.matches(request.url)).toList()
          ..sort((a, b) => b.path.length.compareTo(a.path.length));
    if (selected.isNotEmpty) {
      request.headers['cookie'] = selected
          .map((value) => '${value.cookie.name}=${value.cookie.value}')
          .join('; ');
    }
    if (!{'GET', 'HEAD', 'OPTIONS'}.contains(request.method)) {
      // Django verifies an Origin/Referer for HTTPS cookie-authenticated writes.
      // Browsers supply their own Origin; this branch is compiled only natively.
      request.headers['origin'] = request.url.origin;
    }
    // API redirects are an error, not a reason to forward session credentials.
    request.followRedirects = false;
    final response = await _inner.send(request);
    final header = response.headers['set-cookie'];
    if (header != null) {
      // http combines repeated headers. An Expires date contains a comma but
      // does not match the start of another cookie name=value pair.
      for (final raw in header.split(RegExp(r',(?=\s*[^;,\s=]+=)'))) {
        try {
          final cookie = Cookie.fromSetCookieValue(raw.trim());
          final host = request.url.host.toLowerCase();
          final domain =
              cookie.domain?.replaceFirst(RegExp(r'^\.'), '').toLowerCase() ??
              host;
          if (host != domain && !host.endsWith('.$domain')) continue;
          final cookiePath = cookie.path;
          final path = cookiePath != null && cookiePath.startsWith('/')
              ? cookiePath
              : _defaultPath(request.url.path);
          final expires = cookie.maxAge != null
              ? now.add(Duration(seconds: cookie.maxAge!))
              : cookie.expires?.toUtc();
          final key = '$domain|$path|${cookie.name}';
          if (cookie.maxAge == 0 ||
              (expires != null && !expires.isAfter(now))) {
            _cookies.remove(key);
          } else {
            _cookies[key] = _StoredCookie(
              cookie,
              domain,
              path,
              cookie.domain == null,
              expires,
            );
          }
        } on FormatException {
          // Ignore malformed cookie metadata; never convert it to app state.
        }
      }
    }
    return response;
  }

  static String _defaultPath(String path) {
    final lastSlash = path.lastIndexOf('/');
    return lastSlash <= 0 ? '/' : path.substring(0, lastSlash);
  }

  @override
  void close() {
    _cookies.clear();
    _inner.close();
    super.close();
  }
}

class _StoredCookie {
  _StoredCookie(
    this.cookie,
    this.domain,
    this.path,
    this.hostOnly,
    this.expires,
  );
  final Cookie cookie;
  final String domain;
  final String path;
  final bool hostOnly;
  final DateTime? expires;

  bool matches(Uri uri) {
    final host = uri.host.toLowerCase();
    final domainMatches =
        host == domain || (!hostOnly && host.endsWith('.$domain'));
    final pathMatches =
        uri.path == path ||
        (uri.path.startsWith(path) &&
            (path.endsWith('/') ||
                uri.path.substring(path.length).startsWith('/')));
    return domainMatches &&
        pathMatches &&
        (!cookie.secure || uri.scheme == 'https');
  }
}
