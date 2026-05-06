import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'dart:async';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../../../core/api_client.dart';
import '../../../models/farm.dart';
import '../providers/farms_provider.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  Timer? _refreshTimer;
  bool _simulating = false;
  String? _toastMessage;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      ref.invalidate(farmsProvider);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Color _healthColor(String? status) {
    switch (status) {
      case 'stress':
        return AppTheme.error;
      case 'mild_stress':
        return AppTheme.warning;
      default:
        return AppTheme.success;
    }
  }

  Future<void> _simulateDrought(String? farmId) async {
    if (farmId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Select a farm first by tapping it on the map')),
      );
      return;
    }
    setState(() => _simulating = true);
    try {
      final result =
          await ref.read(apiClientProvider).simulateDrought(farmId);
      final amount = result['payout_amount_kes'] ?? 0;
      final phone = result['phone'] ?? '';
      final fmt = NumberFormat('#,##0', 'en_KE');
      setState(() => _toastMessage = context.tr(
          'dashboard_payout_toast',
          {'amount': fmt.format(amount), 'phone': phone}));
      ref.invalidate(farmsProvider);
      await Future.delayed(const Duration(seconds: 4));
      if (mounted) setState(() => _toastMessage = null);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _simulating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final farmsAsync = ref.watch(farmsProvider);
    final selectedId = ref.watch(selectedFarmIdProvider);
    final fmt = NumberFormat('#,##0', 'en_KE');

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('dashboard_title')),
        actions: [
          TextButton(
            onPressed: () => context.go('/'),
            child: const Text('+ Enroll',
                style: TextStyle(color: Colors.white)),
          ),
          TextButton(
            onPressed: () {
              final locale = ref.read(localeProvider);
              ref.read(localeProvider.notifier).state =
                  locale.languageCode == 'en'
                      ? const Locale('sw')
                      : const Locale('en');
            },
            child: Text(context.tr('language_toggle'),
                style: const TextStyle(color: Colors.white70)),
          ),
        ],
      ),
      body: farmsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.wifi_off_outlined,
                  size: 64, color: AppTheme.textSecondary),
              const SizedBox(height: 12),
              Text(context.tr('error_network'),
                  textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(farmsProvider),
                child: Text(context.tr('retry')),
              ),
            ],
          ),
        ),
        data: (farms) {
          final totalPayouts = farms.fold(
              0.0,
              (sum, f) =>
                  sum +
                  f.payouts.fold(0.0, (s, p) => s + p.amountKes));
          final stressed =
              farms.where((f) => f.healthStatus == 'stress').length;
          final active =
              farms.where((f) => f.policyStatus == 'active').length;

          return Stack(
            children: [
              RefreshIndicator(
                onRefresh: () async => ref.invalidate(farmsProvider),
                child: CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(
                      child: _StatsRow(
                        total: farms.length,
                        active: active,
                        payouts: totalPayouts,
                        stressed: stressed,
                        fmt: fmt,
                      ),
                    ),
                    SliverToBoxAdapter(
                      child: _MapSection(
                        farms: farms,
                        selectedId: selectedId,
                        healthColor: _healthColor,
                        onMarkerTap: (id) => ref
                            .read(selectedFarmIdProvider.notifier)
                            .state = id,
                        onViewDetail: (id) => context.go('/farm/$id'),
                      ),
                    ),
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _simulating
                                ? null
                                : () => _simulateDrought(selectedId),
                            icon: _simulating
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.thunderstorm_outlined),
                            label: Text(_simulating
                                ? context.tr('dashboard_simulating')
                                : context.tr('dashboard_simulate')),
                            style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.error),
                          ),
                        ),
                      ),
                    ),
                    if (farms.isEmpty)
                      SliverToBoxAdapter(
                        child: Center(
                          child: Padding(
                            padding: const EdgeInsets.all(32),
                            child: Text(
                              context.tr('dashboard_no_farms'),
                              style: const TextStyle(
                                  color: AppTheme.textSecondary),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              if (_toastMessage != null)
                Positioned(
                  bottom: 80,
                  left: 16,
                  right: 16,
                  child: Material(
                    borderRadius: BorderRadius.circular(12),
                    color: AppTheme.success,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle,
                              color: Colors.white),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              _toastMessage!,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final int total, active, stressed;
  final double payouts;
  final NumberFormat fmt;

  const _StatsRow({
    required this.total,
    required this.active,
    required this.payouts,
    required this.stressed,
    required this.fmt,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 2.2,
        children: [
          _StatCard(context.tr('dashboard_farms'), '$total',
              Icons.agriculture_outlined, AppTheme.primary),
          _StatCard(context.tr('dashboard_active'), '$active',
              Icons.verified_outlined, AppTheme.success),
          _StatCard(context.tr('dashboard_payouts'),
              'KES ${fmt.format(payouts)}', Icons.payments_outlined, AppTheme.warning),
          _StatCard(context.tr('dashboard_stressed'), '$stressed',
              Icons.warning_amber_outlined, AppTheme.error),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;

  const _StatCard(this.label, this.value, this.icon, this.color);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    value,
                    style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: color),
                  ),
                  Text(
                    label,
                    style: const TextStyle(
                        fontSize: 11, color: AppTheme.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MapSection extends StatelessWidget {
  final List<Farm> farms;
  final String? selectedId;
  final Color Function(String?) healthColor;
  final void Function(String) onMarkerTap;
  final void Function(String) onViewDetail;

  const _MapSection({
    required this.farms,
    required this.selectedId,
    required this.healthColor,
    required this.onMarkerTap,
    required this.onViewDetail,
  });

  List<LatLng> _polygonPoints(Farm f) {
    try {
      final coords = f.polygonGeojson['coordinates'][0] as List;
      return coords
          .map<LatLng>((c) =>
              LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()))
          .toList();
    } catch (_) {
      return [];
    }
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 320,
      child: FlutterMap(
        options: const MapOptions(
            initialCenter: LatLng(-1.286, 36.817), initialZoom: 8),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'com.cropsure.app',
          ),
          PolygonLayer(
            polygons: farms.map((f) {
              final pts = _polygonPoints(f);
              final color = healthColor(f.healthStatus);
              return Polygon(
                points: pts,
                color: color.withOpacity(0.2),
                borderColor: color,
                borderStrokeWidth: 2,
              );
            }).toList(),
          ),
          MarkerLayer(
            markers: farms
                .map((f) {
                  final pts = _polygonPoints(f);
                  if (pts.isEmpty) return null;
                  final center = LatLng(
                    pts
                            .map((p) => p.latitude)
                            .reduce((a, b) => a + b) /
                        pts.length,
                    pts
                            .map((p) => p.longitude)
                            .reduce((a, b) => a + b) /
                        pts.length,
                  );
                  final color = healthColor(f.healthStatus);
                  final isSelected = f.id == selectedId;
                  return Marker(
                    point: center,
                    width: isSelected ? 36 : 28,
                    height: isSelected ? 36 : 28,
                    child: GestureDetector(
                      onTap: () => onMarkerTap(f.id),
                      onDoubleTap: () => onViewDetail(f.id),
                      child: Container(
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: Colors.white,
                              width: isSelected ? 3 : 2),
                          boxShadow: const [
                            BoxShadow(
                                color: Colors.black26, blurRadius: 4)
                          ],
                        ),
                        child: const Icon(Icons.agriculture,
                            color: Colors.white, size: 16),
                      ),
                    ),
                  );
                })
                .whereType<Marker>()
                .toList(),
          ),
        ],
      ),
    );
  }
}
