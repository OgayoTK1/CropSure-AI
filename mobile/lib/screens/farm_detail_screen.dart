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

class FarmDetailScreen extends StatefulWidget {
  final String farmId;
  const FarmDetailScreen({super.key, required this.farmId});

  @override
  State<FarmDetailScreen> createState() => _FarmDetailScreenState();
}

class _FarmDetailScreenState extends State<FarmDetailScreen> {
  Farm? _farm;
  bool _loading = true;
  bool _simulating = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final farm = await ApiService.getFarm(widget.farmId);
      if (mounted) setState(() { _farm = farm; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _simulate() async {
    setState(() => _simulating = true);
    try {
      await ApiService.simulateDrought(widget.farmId);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('💸 Drought simulated — payout triggered!'),
          backgroundColor: kPrimary,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Error: $e'), backgroundColor: kRed,
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

    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator(color: kPrimary)));
    if (_error != null || _farm == null) {
      return Scaffold(
        appBar: AppBar(leading: BackButton(onPressed: () => context.go('/dashboard'))),
        body: Center(child: Text(_error ?? t('Farm not found', 'Shamba halipatikani'),
          style: const TextStyle(color: kRed))),
      );
    }

    final farm = _farm!;
    final color = kHealthColors[farm.statusLabel] ?? kTextMid;
    final statusLabel = loc.isSwahili
        ? kHealthLabelsSw[farm.statusLabel]
        : kHealthLabelsEn[farm.statusLabel];

    return Scaffold(
      appBar: AppBar(
        title: Text(farm.farmerName),
        leading: BackButton(onPressed: () => context.go('/dashboard')),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          TextButton(
            onPressed: loc.toggle,
            child: Text(loc.isSwahili ? 'EN' : 'SW',
              style: const TextStyle(color: kPrimary, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: kPrimary,
        onRefresh: _load,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            // Health status banner
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: color.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: color.withOpacity(0.3)),
              ),
              child: Row(children: [
                Container(
                  width: 48, height: 48,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: color.withOpacity(0.15)),
                  child: Icon(
                    farm.statusLabel == 'healthy' ? Icons.eco :
                    farm.statusLabel == 'mild_stress' ? Icons.warning_amber : Icons.warning_rounded,
                    color: color, size: 26,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(statusLabel ?? '', style: TextStyle(fontWeight: FontWeight.w700, color: color, fontSize: 15)),
                  if (farm.currentNdvi != null)
                    Text('NDVI: ${farm.currentNdvi!.toStringAsFixed(3)}',
                      style: TextStyle(color: color.withOpacity(0.75), fontSize: 12)),
                ])),
                if (farm.policy != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: farm.policy!.status == 'active' ? kPrimaryBg : const Color(0xFFFEF3C7),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      farm.policy!.status.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10, fontWeight: FontWeight.w700,
                        color: farm.policy!.status == 'active' ? kPrimary : kAmber,
                      ),
                    ),
                  ),
              ]),
            ),
            const SizedBox(height: 14),

            // Farm info grid
            Row(children: [
              _InfoCard(label: t('Village', 'Kijiji'), value: farm.village, icon: Icons.location_on_outlined),
              const SizedBox(width: 10),
              _InfoCard(label: t('Crop', 'Zao'), value: farm.cropType.toUpperCase(), icon: Icons.grass),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              _InfoCard(label: t('Farm Area', 'Eneo'), value: '${farm.areaAcres.toStringAsFixed(2)} acres', icon: Icons.landscape_outlined),
              const SizedBox(width: 10),
              if (farm.policy != null)
                _InfoCard(
                  label: t('Coverage', 'Fidia'),
                  value: 'KES ${_k(farm.policy!.coverageAmountKes)}',
                  icon: Icons.shield_outlined,
                )
              else
                _InfoCard(label: t('Phone', 'Simu'), value: farm.phoneNumber, icon: Icons.phone_outlined),
            ]),
            const SizedBox(height: 14),

            // NDVI chart
            if (farm.ndviHistory.isNotEmpty) ...[
              _SectionTitle(t('NDVI History', 'Historia ya NDVI')),
              const SizedBox(height: 8),
              _NdviDetailChart(readings: farm.ndviHistory),
              const SizedBox(height: 14),
            ],

            // Farm map
            _SectionTitle(t('Farm Location', 'Mahali pa Shamba')),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                height: 200,
                child: FlutterMap(
                  options: const MapOptions(
                    initialCenter: LatLng(kDefaultLat, kDefaultLng),
                    initialZoom: 13,
                    interactionOptions: InteractionOptions(flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag),
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.cropsure.app',
                    ),
                    // Farm polygon from GeoJSON if available
                    MarkerLayer(markers: [
                      Marker(
                        point: const LatLng(kDefaultLat, kDefaultLng),
                        width: 32, height: 32,
                        child: Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle, color: color,
                            border: Border.all(color: Colors.white, width: 3),
                            boxShadow: [const BoxShadow(color: Colors.black26, blurRadius: 8)],
                          ),
                        ),
                      ),
                    ]),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Policy details
            if (farm.policy != null) ...[
              _SectionTitle(t('Policy Details', 'Maelezo ya Polisi')),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: kBorder),
                ),
                child: Column(children: [
                  _DetailRow(t('Premium paid', 'Bima iliyolipwa'), 'KES ${_k(farm.policy!.premiumPaidKes)}'),
                  _DetailRow(t('Coverage', 'Fidia'), 'KES ${_k(farm.policy!.coverageAmountKes)}'),
                  _DetailRow(t('Season start', 'Mwanzo wa msimu'), _fmtDate(farm.policy!.seasonStart)),
                  _DetailRow(t('Season end', 'Mwisho wa msimu'), _fmtDate(farm.policy!.seasonEnd)),
                  _DetailRow(t('Status', 'Hali'), farm.policy!.status.toUpperCase()),
                ]),
              ),
              const SizedBox(height: 14),
            ],

            // Payout history
            _SectionTitle(t('Payout History', 'Historia ya Malipo')),
            const SizedBox(height: 8),
            if (farm.payouts.isEmpty)
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white, borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: kBorder),
                ),
                child: Center(child: Column(children: [
                  const Icon(Icons.payments_outlined, color: kBorder, size: 40),
                  const SizedBox(height: 8),
                  Text(t('No payouts yet', 'Hakuna malipo bado'),
                    style: const TextStyle(color: kTextMid)),
                  Text(t('Farm is being monitored every 5 days', 'Shamba linafuatiliwa kila siku 5'),
                    style: const TextStyle(color: kTextLight, fontSize: 12)),
                ])),
              )
            else
              ...farm.payouts.map((p) => _PayoutCard(payout: p)),
          ]),
        ),
      ),

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
              _simulating ? t('Simulating...', 'Inasimula...') : t('Simulate Drought', 'Simula Ukame'),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ),
      ),
    );
  }

  String _k(double v) {
    if (v >= 1000) return '${(v / 1000).toStringAsFixed(1)}K';
    return v.toStringAsFixed(0);
  }

  String _fmtDate(String iso) {
    try {
      final d = DateTime.parse(iso);
      return '${d.day} ${['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.month]} ${d.year}';
    } catch (_) { return iso; }
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);
  @override
  Widget build(BuildContext context) =>
    Text(text, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: kTextDark));
}

class _InfoCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  const _InfoCard({required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Expanded(child: Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: kBorder)),
      child: Row(children: [
        Icon(icon, size: 18, color: kPrimary),
        const SizedBox(width: 8),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: const TextStyle(fontSize: 10, color: kTextMid)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12), overflow: TextOverflow.ellipsis),
        ])),
      ]),
    ));
  }
}

class _DetailRow extends StatelessWidget {
  final String label, value;
  const _DetailRow(this.label, this.value);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(children: [
      Expanded(child: Text(label, style: const TextStyle(color: kTextMid, fontSize: 13))),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
    ]),
  );
}

class _PayoutCard extends StatelessWidget {
  final Payout payout;
  const _PayoutCard({required this.payout});

  @override
  Widget build(BuildContext context) {
    final isComplete = payout.status == 'completed';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: Row(children: [
        Container(
          width: 42, height: 42,
          decoration: BoxDecoration(
            color: isComplete ? kPrimaryBg : const Color(0xFFFEF3C7),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(isComplete ? Icons.payments : Icons.pending, color: isComplete ? kPrimary : kAmber, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            'KES ${payout.payoutAmountKes.toStringAsFixed(0).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',')}',
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: kTextDark),
          ),
          Text(payout.stressType.replaceAll('_', ' ').toUpperCase(),
            style: const TextStyle(fontSize: 11, color: kTextMid, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(payout.explanationEn, style: const TextStyle(fontSize: 11, color: kTextMid), maxLines: 2, overflow: TextOverflow.ellipsis),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isComplete ? kPrimaryBg : const Color(0xFFFEF3C7),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(payout.status.toUpperCase(),
            style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: isComplete ? kPrimary : kAmber)),
        ),
      ]),
    );
  }
}

class _NdviDetailChart extends StatelessWidget {
  final List<NdviReading> readings;
  const _NdviDetailChart({required this.readings});

  @override
  Widget build(BuildContext context) {
    final spots = readings.asMap().entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.ndviValue))
        .toList();

    return Container(
      height: 200,
      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: LineChart(LineChartData(
        minY: 0, maxY: 1,
        gridData: FlGridData(
          drawVerticalLine: false, horizontalInterval: 0.25,
          getDrawingHorizontalLine: (_) => FlLine(color: kBorder, strokeWidth: 1),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(sideTitles: SideTitles(
            showTitles: true, reservedSize: 30, interval: 0.25,
            getTitlesWidget: (v, _) => Text(v.toStringAsFixed(1), style: const TextStyle(fontSize: 9, color: kTextMid)),
          )),
          bottomTitles: AxisTitles(sideTitles: SideTitles(
            showTitles: true, reservedSize: 22, interval: 3,
            getTitlesWidget: (v, _) {
              final idx = v.toInt();
              if (idx >= readings.length) return const SizedBox.shrink();
              return Text(readings[idx].readingDate.substring(5), style: const TextStyle(fontSize: 8, color: kTextMid));
            },
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
              getDotPainter: (s, _, __, ___) => FlDotCirclePainter(
                radius: 3.5,
                color: s.y < 0.3 ? kRed : s.y < 0.5 ? kAmber : kPrimary,
                strokeWidth: 2, strokeColor: Colors.white,
              ),
            ),
          ),
          // Threshold line
          LineChartBarData(
            spots: [FlSpot(0, 0.3), FlSpot(spots.length.toDouble() - 1, 0.3)],
            color: kRed.withOpacity(0.35), barWidth: 1.5,
            dashArray: [5, 4],
            dotData: const FlDotData(show: false),
          ),
        ],
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (spots) => spots.map((s) => LineTooltipItem(
              'NDVI: ${s.y.toStringAsFixed(3)}',
              TextStyle(color: s.y < 0.3 ? kRed : kPrimary, fontWeight: FontWeight.w700, fontSize: 11),
            )).toList(),
          ),
        ),
      )),
    );
  }
}
