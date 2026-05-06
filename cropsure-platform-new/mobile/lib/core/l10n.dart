import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Locale state — toggled by language button in AppBar
final localeProvider = StateProvider<Locale>((ref) => const Locale('en'));

class AppLocalizations {
  AppLocalizations(this.locale);
  final Locale locale;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate = _AppLocalizationsDelegate();
  static const List<Locale> supportedLocales = [Locale('en'), Locale('sw')];

  late Map<String, String> _strings;

  Future<bool> load() async {
    final jsonStr = await rootBundle.loadString('assets/i18n/${locale.languageCode}.json');
    final Map<String, dynamic> raw = json.decode(jsonStr);
    _strings = raw.map((k, v) => MapEntry(k, v.toString()));
    return true;
  }

  String translate(String key, [Map<String, String>? args]) {
    String val = _strings[key] ?? key;
    if (args != null) {
      args.forEach((k, v) => val = val.replaceAll('{$k}', v));
    }
    return val;
  }

  // Convenience shorthand
  String t(String key, [Map<String, String>? args]) => translate(key, args);
}

extension L10nContext on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
  String tr(String key, [Map<String, String>? args]) => l10n.translate(key, args);
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) => ['en', 'sw'].contains(locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) async {
    final l = AppLocalizations(locale);
    await l.load();
    return l;
  }

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}
