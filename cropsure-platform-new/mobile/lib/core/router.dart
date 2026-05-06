import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/enrollment/screens/enrollment_screen.dart';
import '../features/dashboard/screens/dashboard_screen.dart';
import '../features/farm_detail/screens/farm_detail_screen.dart';
import '../features/enrollment/screens/enrollment_success_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const EnrollmentScreen(),
      ),
      GoRoute(
        path: '/success',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>;
          return EnrollmentSuccessScreen(enrollmentData: extra);
        },
      ),
      GoRoute(
        path: '/dashboard',
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: '/farm/:farmId',
        builder: (context, state) {
          return FarmDetailScreen(farmId: state.pathParameters['farmId']!);
        },
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(child: Text('Page not found: ${state.error}')),
    ),
  );
});
