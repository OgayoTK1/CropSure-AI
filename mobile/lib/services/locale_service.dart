import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocaleService extends ChangeNotifier {
  Locale _locale = const Locale('en');

  Locale get locale => _locale;
  bool get isSwahili => _locale.languageCode == 'sw';

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final lang = prefs.getString('lang') ?? 'en';
    _locale = Locale(lang);
    notifyListeners();
  }

  Future<void> toggle() async {
    _locale = isSwahili ? const Locale('en') : const Locale('sw');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lang', _locale.languageCode);
    notifyListeners();
  }

  String t(String en, String sw) => isSwahili ? sw : en;
}
