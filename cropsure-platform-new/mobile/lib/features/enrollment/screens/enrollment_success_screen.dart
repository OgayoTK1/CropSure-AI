import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:intl/intl.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../providers/enrollment_provider.dart';

class EnrollmentSuccessScreen extends ConsumerWidget {
  final Map<String, dynamic> enrollmentData;
  const EnrollmentSuccessScreen({super.key, required this.enrollmentData});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final polygon = ref.read(enrollmentProvider).polygonCoordinates;
    final policyId = enrollmentData['policy_id'] as String? ?? '';
    final farmId = enrollmentData['farm_id'] as String? ?? '';
    final amount = enrollmentData['premium_amount_kes'] as num? ?? 0;
    final phone = enrollmentData['farmer_name'] as String? ?? '';
    final fmt = NumberFormat('#,##0', 'en_KE');

    return Scaffold(
      appBar: AppBar(title: Text(context.tr('app_name'))),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                color: AppTheme.primaryLight,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check_circle,
                color: AppTheme.primary,
                size: 64,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              context.tr('payment_success_title'),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              context.tr('payment_success_body', {'phone': phone}),
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 24),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      context.tr('payment_policy_number'),
                      style: const TextStyle(
                          color: AppTheme.textSecondary, fontSize: 12),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      policyId.length >= 8
                          ? policyId.substring(0, 8).toUpperCase()
                          : policyId.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primary,
                        letterSpacing: 2,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (polygon.isNotEmpty)
              SizedBox(
                height: 200,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: FlutterMap(
                    options: MapOptions(
                      initialCenter: polygon.first,
                      initialZoom: 15,
                      interactionOptions: const InteractionOptions(
                          flags: InteractiveFlag.none),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.cropsure.app',
                      ),
                      PolygonLayer(polygons: [
                        Polygon(
                          points: polygon,
                          color: AppTheme.primary.withOpacity(0.3),
                          borderColor: AppTheme.primary,
                          borderStrokeWidth: 2,
                        ),
                      ]),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => context.go('/dashboard'),
                child: const Text('Go to Dashboard'),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => context.go('/farm/$farmId'),
                child: const Text('View Farm Details'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
