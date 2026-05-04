import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/theme.dart';
import 'services/locale_service.dart';
import 'screens/landing_screen.dart';
import 'screens/enrollment/enrollment_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/farm_detail_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);

  final localeService = LocaleService();
  await localeService.init();

  runApp(
    ChangeNotifierProvider.value(
      value: localeService,
      child: const CropSureApp(),
    ),
  );
}

final _router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/',        builder: (_, __) => const LandingScreen()),
    GoRoute(path: '/enroll',  builder: (_, __) => const EnrollmentScreen()),
    GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
    GoRoute(
      path: '/farm/:id',
      builder: (_, state) => FarmDetailScreen(farmId: state.pathParameters['id']!),
    ),
  ],
);

class CropSureApp extends StatelessWidget {
  const CropSureApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<LocaleService>(
      builder: (_, locale, __) => MaterialApp.router(
        title: 'CropSure AI',
        theme: buildTheme(),
        routerConfig: _router,
        locale: locale.locale,
        debugShowCheckedModeBanner: false,
        supportedLocales: const [Locale('en'), Locale('sw')],
        localizationsDelegates: const [
          DefaultMaterialLocalizations.delegate,
          DefaultWidgetsLocalizations.delegate,
        ],
      ),
    );
  }
}
