import 'package:http/http.dart' as http;

import 'transport_native.dart'
    if (dart.library.js_interop) 'transport_web.dart'
    as platform;

http.Client createHttpClient() => platform.createHttpClient();

String defaultApiOrigin() => platform.defaultApiOrigin();
