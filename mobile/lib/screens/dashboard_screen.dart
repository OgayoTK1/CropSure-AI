import 'dart:async';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/locale_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<Farm> _farms = [];
  bool _loading = true;
  bool _simulating = false;
  Farm? _selected;
  bool _loadingDetail = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final farms = await ApiService.getFarms();
      if (mounted) setState(() { _farms = farms; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; });
    }
  }

  Future<void> _simulate() async {
    if (_selected == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(context.read<LocaleService>().t('Select a farm first', 'Chagua shamba kwanza')),
        backgroundColor: kAmber,
      ));
      return;
    }
    setState(() => _simulating = true);
    try {
      final res = await ApiService.simulateDrought(_selected!.id);
      final payout = res['payout_amount_kes'] ?? 0;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('💸 KES ${payout.toString()} sent to ${_selected!.phoneNumber}'),
          backgroundColor: kPrimary,
          duration: const Duration(seconds: 4),
        ));
        _load();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Simulation error: $e'),
          backgroundColor: kRed,
        ));
      }
    } finally {
      if (mounted) setState(() => _simulating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocaleService>();
    final t = loc.t;

    // Stats
    final total = _farms.length;
    final active = _farms.where((f) => f.policyStatus == 'active').length;
    final stressed = _farms.where((f) => f.statusLabel == 'severe_stress' || f.statusLabel == 'mild_stress').length;
    final payouts = _farms.fold<double>(0, (s, f) => s + f.payouts.fold(0.0, (p, py) => p + py.payoutAmountKes));

    return Scaffold(
      appBar: AppBar(
        title: Text(t('Dashboard', 'Dashibodi')),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          TextButton(
            onPressed: loc.toggle,
            child: Text(loc.isSwahili ? 'EN' : 'SW',
              style: const TextStyle(color: kPrimary, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kPrimary))
          : RefreshIndicator(
              color: kPrimary,
              onRefresh: _load,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  // Stats row
                  Row(children: [
                    _StatCard(label: t('Farms', 'Mashamba'), value: '$total', icon: Icons.grass, color: kPrimary),
                    const SizedBox(width: 10),
                    _StatCard(label: t('Active', 'Zinafanya kazi'), value: '$active', icon: Icons.shield_outlined, color: Colors.blue),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: [
                    _StatCard(label: t('Payouts KES', 'Malipo KES'), value: _fmt(payouts), icon: Icons.payments_outlined, color: kAmber),
                    const SizedBox(width: 10),
                    _StatCard(label: t('Under stress', 'Msongo'), value: '$stressed', icon: Icons.warning_amber_rounded, color: kRed),
                  ]),
                  const SizedBox(height: 16),

                  // Map
                  _SectionTitle(t('Farm Map', 'Ramani ya Mashamba')),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: SizedBox(
                      height: 280,
                      child: FlutterMap(
                        options: MapOptions(
                          initialCenter: const LatLng(kDefaultLat, kDefaultLng),
                          initialZoom: kKenyaZoom,
                        ),
                        children: [
                          TileLayer(
                            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                            userAgentPackageName: 'com.cropsure.app',
                          ),
                          MarkerLayer(markers: _farms.map((f) {
                            final color = kHealthColors[f.statusLabel] ?? kTextMid;
                            final selected = _selected?.id == f.id;
                            return Marker(
                              point: const LatLng(kDefaultLat, kDefaultLng), // centroid would be computed
                              width: selected ? 24 : 18,
                              height: selected ? 24 : 18,
                              child: GestureDetector(
                                onTap: () => setState(() => _selected = f),
                                child: Container(
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle, color: color,
                                    border: Border.all(color: Colors.white, width: selected ? 3 : 2),
                                    boxShadow: [BoxShadow(color: Colors.black26, blurRadius: selected ? 8 : 4)],
                                  ),
                                ),
                              ),
                            );
                          }).toList()),
                        ],
                      ),
                    ),
                  ),

                  if (_farms.isEmpty) ...[
                    const SizedBox(height: 20),
                    Center(
                      child: Column(children: [
                        const Icon(Icons.grass, size: 48, color: kBorder),
                        const SizedBox(height: 8),
                        Text(t('No farms enrolled yet', 'Hakuna mashamba yaliyoandikishwa'),
                          style: const TextStyle(color: kTextMid)),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: () => context.go('/enroll'),
                          icon: const Icon(Icons.add),
                          label: Text(t('Enroll First Farm', 'Andikisha Shamba la Kwanza')),
                        ),
                      ]),
                    ),
                  ] else ...[
                    // NDVI chart (selected farm)
                    const SizedBox(height: 16),
                    _SectionTitle(
                      _selected != null
                          ? '${t('NDVI', 'NDVI')} — ${_selected!.farmerName} (${_selected!.village})'
                          : t('Select a farm to view NDVI', 'Chagua shamba kuona NDVI'),
                    ),
                    const SizedBox(height: 8),
                    if (_selected != null && _selected!.ndviHistory.isNotEmpty)
                      _NdviChart(readings: _selected!.ndviHistory)
                    else
                      Container(
                        height: 160,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: kBorder),
                        ),
                        child: Text(
                          _selected == null
                              ? t('Tap a farm marker on the map', 'Gonga alama ya shamba kwenye ramani')
                              : t('No NDVI readings yet', 'Hakuna data ya NDVI bado'),
                          style: const TextStyle(color: kTextMid, fontSize: 13),
                        ),
                      ),

                    // Farm list
                    const SizedBox(height: 16),
                    _SectionTitle(t('All Farms', 'Mashamba Yote')),
                    const SizedBox(height: 8),
                    ..._farms.map((f) => _FarmCard(
                      farm: f,
                      selected: _selected?.id == f.id,
                      onTap: () {
                        setState(() => _selected = f);
                        context.go('/farm/${f.id}');
                      },
                      onSelect: () => setState(() => _selected = f),
                    )),
                  ],
                ]),
              ),
            ),

      // Floating simulate button
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: SizedBox(
          width: double.infinity,
          child: FloatingActionButton.extended(
            onPressed: _simulating ? null : _simulate,
            backgroundColor: kRed,
            icon: _simulating
                ? const SizedBox(width: 18, height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.warning_amber_rounded),
            label: Text(
              _simulating
                  ? t('Simulating...', 'Inasimula...')
                  : _selected != null
                      ? t('Simulate Drought (${_selected!.farmerName.split(' ')[0]})',
                          'Simula Ukame (${_selected!.farmerName.split(' ')[0]})')
                      : t('Simulate Drought Event', 'Simula Tukio la Ukame'),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ),
      ),
    );
  }

  String _fmt(double v) {
    if (v >= 1000000) return '${(v / 1000000).toStringAsFixed(1)}M';
    if (v >= 1000) return '${(v / 1000).toStringAsFixed(1)}K';
    return v.toStringAsFixed(0);
  }
}

// ── Stat card ─────────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;
  const _StatCard({required this.label, required this.value, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: kBorder),
        ),
        child: Row(children: [
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: kTextDark)),
            Text(label, style: const TextStyle(fontSize: 11, color: kTextMid), overflow: TextOverflow.ellipsis),
          ])),
        ]),
      ),
    );
  }
}

// ── Section title ─────────────────────────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(text, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: kTextDark));
  }
}

// ── NDVI chart ────────────────────────────────────────────────────────────────

class _NdviChart extends StatelessWidget {
  final List<NdviReading> readings;
  const _NdviChart({required this.readings});

  @override
  Widget build(BuildContext context) {
    final spots = readings.asMap().entries.map((e) =>
      FlSpot(e.key.toDouble(), e.value.ndviValue)
    ).toList();

    return Container(
      height: 180,
      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: LineChart(
        LineChartData(
          minY: 0, maxY: 1,
          gridData: FlGridData(
            show: true,
            drawHorizontalLine: true,
            drawVerticalLine: false,
            horizontalInterval: 0.25,
            getDrawingHorizontalLine: (_) => FlLine(color: kBorder, strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(sideTitles: SideTitles(
              showTitles: true, reservedSize: 32,
              interval: 0.25,
              getTitlesWidget: (v, _) => Text(v.toStringAsFixed(1),
                style: const TextStyle(fontSize: 9, color: kTextMid)),
            )),
            bottomTitles: AxisTitles(sideTitles: SideTitles(
              showTitles: true, reservedSize: 20, interval: 4,
              getTitlesWidget: (v, _) => Text('W${v.toInt() + 1}',
                style: const TextStyle(fontSize: 9, color: kTextMid)),
            )),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              color: kPrimary,
              barWidth: 2.5,
              belowBarData: BarAreaData(show: true, color: kPrimary.withOpacity(0.08)),
              dotData: FlDotData(
                show: true,
                getDotPainter: (s, _, __, ___) => FlDotCirclePainter(
                  radius: 3,
                  color: s.y < 0.3 ? kRed : kPrimary,
                  strokeWidth: 1.5,
                  strokeColor: Colors.white,
                ),
              ),
            ),
            // Stress threshold line
            LineChartBarData(
              spots: [FlSpot(0, 0.3), FlSpot(spots.length.toDouble() - 1, 0.3)],
              color: kRed.withOpacity(0.4),
              barWidth: 1,
              dashArray: [5, 4],
              dotData: const FlDotData(show: false),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Farm card ─────────────────────────────────────────────────────────────────

class _FarmCard extends StatelessWidget {
  final Farm farm;
  final bool selected;
  final VoidCallback onTap, onSelect;
  const _FarmCard({required this.farm, required this.selected, required this.onTap, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    final color = kHealthColors[farm.statusLabel] ?? kTextMid;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: selected ? kPrimary : kBorder, width: selected ? 2 : 1),
        ),
        child: Row(children: [
          Container(
            width: 12, height: 44,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
          ),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(farm.farmerName, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
            const SizedBox(height: 2),
            Text('${farm.village} · ${farm.cropType} · ${farm.areaAcres.toStringAsFixed(1)} acres',
              style: const TextStyle(color: kTextMid, fontSize: 12)),
            if (farm.currentNdvi != null)
              Text('NDVI: ${farm.currentNdvi!.toStringAsFixed(2)}',
                style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
          ])),
          const Icon(Icons.chevron_right, color: kTextLight),
        ]),
      ),
    );
  }
}
