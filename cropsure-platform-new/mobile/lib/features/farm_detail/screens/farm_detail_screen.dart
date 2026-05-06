import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../../../models/farm.dart';
import '../providers/farm_detail_provider.dart';

class FarmDetailScreen extends ConsumerWidget {
  final String farmId;
  const FarmDetailScreen({super.key, required this.farmId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final farmAsync = ref.watch(farmDetailProvider(farmId));
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('farm_detail_title'))),
      body: farmAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text(e.toString())),
        data: (farm) => _FarmDetailBody(farm: farm),
      ),
    );
  }
}

class _FarmDetailBody extends StatelessWidget {
  final Farm farm;
  const _FarmDetailBody({required this.farm});

  List<LatLng> get _polygonPoints {
    try {
      final coords = farm.polygonGeojson['coordinates'][0] as List;
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
    final fmt = NumberFormat('#,##0', 'en_KE');
    final locale = Localizations.localeOf(context).languageCode;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Farm map
          if (_polygonPoints.isNotEmpty)
            SizedBox(
              height: 220,
              child: FlutterMap(
                options: MapOptions(
                  initialCenter: _polygonPoints.first,
                  initialZoom: 15,
                ),
                children: [
                  TileLayer(
                    urlTemplate:
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.cropsure.app',
                  ),
                  PolygonLayer(polygons: [
                    Polygon(
                      points: _polygonPoints,
                      color: AppTheme.primary.withOpacity(0.25),
                      borderColor: AppTheme.primary,
                      borderStrokeWidth: 2,
                    ),
                  ]),
                ],
              ),
            ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Farm info card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        _InfoRow('Farmer', farm.farmerName),
                        _InfoRow('Village', farm.village),
                        _InfoRow('Crop', farm.cropType),
                        _InfoRow('Area',
                            '${farm.areaAcres.toStringAsFixed(2)} acres'),
                        if (farm.policy != null) ...[
                          const Divider(height: 20),
                          _InfoRow(
                            context.tr('farm_policy_status'),
                            _policyLabel(context, farm.policy!.status),
                          ),
                          _InfoRow('Coverage',
                              'KES ${fmt.format(farm.policy!.coverageAmountKes)}'),
                          _InfoRow('Season',
                              '${farm.policy!.seasonStart} → ${farm.policy!.seasonEnd}'),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 20),
                Text(
                  context.tr('farm_ndvi_chart'),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),

                // NDVI chart
                if (farm.ndviHistory.isNotEmpty)
                  _NdviChart(readings: farm.ndviHistory)
                else
                  const Text('No NDVI data yet',
                      style: TextStyle(color: AppTheme.textSecondary)),

                const SizedBox(height: 24),
                Text(
                  context.tr('farm_payouts_title'),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),

                if (farm.payouts.isEmpty)
                  Text(
                    context.tr('farm_no_payouts'),
                    style:
                        const TextStyle(color: AppTheme.textSecondary),
                  )
                else
                  ...farm.payouts.map((p) => _PayoutCard(
                        payout: p,
                        locale: locale,
                        fmt: fmt,
                      )),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _policyLabel(BuildContext context, String status) {
    switch (status) {
      case 'active':
        return context.tr('farm_policy_active');
      case 'pending_payment':
        return context.tr('farm_policy_pending');
      default:
        return context.tr('farm_policy_expired');
    }
  }
}

class _InfoRow extends StatelessWidget {
  final String label, value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 13)),
          Text(value,
              style: const TextStyle(
                  fontWeight: FontWeight.w600, fontSize: 13)),
        ],
      ),
    );
  }
}

class _NdviChart extends StatelessWidget {
  final List<NdviReading> readings;
  const _NdviChart({required this.readings});

  @override
  Widget build(BuildContext context) {
    final spots = readings
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.ndvi))
        .toList();

    // Find payout trigger point (stress reading)
    final triggerIdx = readings.indexWhere((r) =>
        r.stressType != null &&
        r.stressType != 'no_stress' &&
        (r.confidence ?? 0) > 0.72);

    return SizedBox(
      height: 200,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: 1,
          gridData: const FlGridData(show: true),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            bottomTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 36,
                getTitlesWidget: (v, _) => Text(
                  v.toStringAsFixed(1),
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            ),
          ),
          extraLinesData: triggerIdx >= 0
              ? ExtraLinesData(verticalLines: [
                  VerticalLine(
                    x: triggerIdx.toDouble(),
                    color: AppTheme.error,
                    strokeWidth: 2,
                    dashArray: [4, 4],
                  ),
                ])
              : null,
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              color: AppTheme.primary,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppTheme.primary.withOpacity(0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PayoutCard extends StatelessWidget {
  final Payout payout;
  final String locale;
  final NumberFormat fmt;

  const _PayoutCard({
    required this.payout,
    required this.locale,
    required this.fmt,
  });

  @override
  Widget build(BuildContext context) {
    final explanation =
        locale == 'sw' ? payout.explanationSw : payout.explanationEn;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'KES ${fmt.format(payout.amountKes)}',
                  style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.primary),
                ),
                _StatusBadge(payout.status),
              ],
            ),
            const SizedBox(height: 6),
            if (explanation != null && explanation.isNotEmpty)
              Text(
                explanation,
                style: const TextStyle(
                    color: AppTheme.textSecondary, fontSize: 13),
              ),
            const SizedBox(height: 4),
            Text(
              payout.triggeredAt.substring(0, 10),
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge(this.status);

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (status) {
      case 'completed':
        color = AppTheme.success;
        break;
      case 'failed':
        color = AppTheme.error;
        break;
      default:
        color = AppTheme.warning;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        status.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
