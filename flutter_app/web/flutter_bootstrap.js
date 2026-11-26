{{flutter_js}}
{{flutter_build_config}}

// app-worker.js owns offline handling. Registering Flutter's retired worker
// on the same scope makes the workers replace each other and reload the page.
_flutter.loader.load();
