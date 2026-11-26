/// Money arrives from Django as decimal strings. Formatting never converts it
/// to a binary floating-point number, including values larger than JS integers.
String formatMoney(Object? value, {String? currency}) {
  final raw = value?.toString() ?? '0.00';
  final match = RegExp(r'^(-?)(\d+)(?:\.(\d+))?$').firstMatch(raw);
  if (match == null) return currency == null ? '—' : '— $currency';
  final whole = match
      .group(2)!
      .replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
  final fraction = (match.group(3) ?? '').padRight(2, '0');
  final sign = match.group(1) == '-' ? '−' : '';
  final result = '$sign$whole.$fraction';
  return currency == null || currency.isEmpty ? result : '$result $currency';
}

/// Use the server string directly when prefilling monetary form fields.
String moneyInput(Object? value) => value?.toString() ?? '0.00';
