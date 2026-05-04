import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../services/locale_service.dart';

class StepGpsBoundary extends StatefulWidget {
  final void Function(List<LatLng> boundary, double areaAcres) onConfirm;
  final VoidCallback onBack;
  const StepGpsBoundary({super.key, required this.onConfirm, required this.onBack});

  @override
  State<StepGpsBoundary> createState() => _StepGpsBoundaryState();
}

class _StepGpsBoundaryState extends State<StepGpsBoundary> {
  final _mapController = MapController();
  final List<LatLng> _points = [];
  LatLng? _currentPos;
  StreamSubscription<Position>? _posStream;
  bool _walking = false;
  bool _locating = true;
  bool _manualMode = false;
  double _areaAcres = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initLocation();
  }

  @override
  void dispose() {
    _posStream?.cancel();
    super.dispose();
  }

  Future<void> _initLocation() async {
    final status = await Permission.locationWhenInUse.request();
    if (!status.isGranted) {
      setState(() {
        _error = 'Location permission required';
        _locating = false;
        _manualMode = true;
      });
      return;
    }
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      final ll = LatLng(pos.latitude, pos.longitude);
      setState(() { _currentPos = ll; _locating = false; });
      _mapController.move(ll, kDefaultZoom);
    } catch (e) {
      setState(() { _locating = false; _manualMode = true; });
    }
  }

  void _startWalking() {
    setState(() { _walking = true; _points.clear(); _areaAcres = 0; });
    _posStream = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, distanceFilter: 2),
    ).listen((pos) {
      final ll = LatLng(pos.latitude, pos.longitude);
      setState(() {
        _currentPos = ll;
        if (_points.isEmpty || _dist(_points.last, ll) > 2) {
          _points.add(ll);
          _areaAcres = _calcArea(_points);
        }
      });
      _mapController.move(ll, kDefaultZoom);
    });
  }

  void _stopWalking() {
    _posStream?.cancel();
    setState(() { _walking = false; });
    if (_points.length >= 3) {
      if (_points.first != _points.last) _points.add(_points.first);
    }
  }

  void _onMapTap(TapPosition _, LatLng ll) {
    if (!_manualMode) return;
    setState(() {
      _points.add(ll);
      _areaAcres = _calcArea(_points);
    });
  }

  void _undoLast() {
    if (_points.isEmpty) return;
    setState(() {
      _points.removeLast();
      _areaAcres = _calcArea(_points);
    });
  }

  void _confirm() {
    final t = context.read<LocaleService>().t;
    if (_points.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(t('Walk at least 3 boundary points', 'Tembea angalau pointi 3 za mipaka')),
        backgroundColor: kRed,
      ));
      return;
    }
    widget.onConfirm(List.from(_points), _areaAcres);
  }

  // Shoelace formula → acres
  double _calcArea(List<LatLng> pts) {
    if (pts.length < 3) return 0;
    final ref = pts[0];
    double area = 0;
    for (int i = 0; i < pts.length; i++) {
      final j = (i + 1) % pts.length;
      final xi = (pts[i].longitude - ref.longitude) * 111320 *
          math.cos(ref.latitude * math.pi / 180);
      final yi = (pts[i].latitude - ref.latitude) * 111320;
      final xj = (pts[j].longitude - ref.longitude) * 111320 *
          math.cos(ref.latitude * math.pi / 180);
      final yj = (pts[j].latitude - ref.latitude) * 111320;
      area += xi * yj - xj * yi;
    }
    return (area.abs() / 2) / 4046.856;
  }

  double _dist(LatLng a, LatLng b) {
    final dx = (a.longitude - b.longitude) * 111320;
    final dy = (a.latitude - b.latitude) * 111320;
    return math.sqrt(dx * dx + dy * dy);
  }

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocaleService>();
    final t = loc.t;
    final center = _currentPos ?? const LatLng(kDefaultLat, kDefaultLng);

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      // Mode tabs
      Row(children: [
        Expanded(child: _ModeTab(
          label: t('Walk Mode (GPS)', 'Tembea (GPS)'),
          active: !_manualMode,
          icon: Icons.directions_walk,
          onTap: () => setState(() => _manualMode = false),
        )),
        Expanded(child: _ModeTab(
          label: t('Tap Mode (Manual)', 'Gonga (Mikono)'),
          active: _manualMode,
          icon: Icons.touch_app,
          onTap: () => setState(() => _manualMode = true),
        )),
      ]),
      const SizedBox(height: 12),

      // Map
      ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: SizedBox(
          height: 320,
          child: _locating
              ? const Center(child: CircularProgressIndicator(color: kPrimary))
              : FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: center,
                    initialZoom: kDefaultZoom,
                    onTap: _onMapTap,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.cropsure.app',
                    ),
                    if (_points.length >= 3)
                      PolygonLayer(polygons: [
                        Polygon(
                          points: _points,
                          color: kPrimary.withOpacity(0.15),
                          borderColor: kPrimary,
                          borderStrokeWidth: 2.5,
                        ),
                      ]),
                    PolylineLayer(polylines: [
                      Polyline(points: _points, color: kPrimary, strokeWidth: 2),
                    ]),
                    MarkerLayer(markers: [
                      // Boundary markers
                      ..._points.asMap().entries.map((e) => Marker(
                        point: e.value,
                        width: 16, height: 16,
                        child: Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: e.key == 0 ? kAmber : kPrimary,
                            border: Border.all(color: Colors.white, width: 2),
                            boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
                          ),
                        ),
                      )),
                      // Current position
                      if (_currentPos != null)
                        Marker(
                          point: _currentPos!,
                          width: 22, height: 22,
                          child: Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.blue,
                              border: Border.all(color: Colors.white, width: 3),
                              boxShadow: [BoxShadow(color: Colors.black38, blurRadius: 6)],
                            ),
                          ),
                        ),
                    ]),
                  ],
                ),
        ),
      ),
      const SizedBox(height: 10),

      // Status pill
      if (_error != null)
        _Pill(text: _error!, color: kRed)
      else if (_points.isNotEmpty)
        _Pill(
          text: _areaAcres > 0
              ? t('${_points.length} points · ${_areaAcres.toStringAsFixed(2)} acres',
                  'Pointi ${_points.length} · ekari ${_areaAcres.toStringAsFixed(2)}')
              : t('${_points.length} points captured', 'Pointi ${_points.length} zimechukuliwa'),
          color: kPrimary,
        )
      else
        _Pill(
          text: _manualMode
              ? t('Tap on the map to add boundary points', 'Gonga ramani kuongeza pointi za mipaka')
              : t('Press Start Walking then walk your farm boundary', 'Bonyeza Anza Kutembea kisha tembea mipaka'),
          color: kTextMid,
        ),
      const SizedBox(height: 14),

      // Action buttons
      if (!_manualMode) ...[
        if (!_walking)
          ElevatedButton.icon(
            onPressed: _startWalking,
            icon: const Icon(Icons.directions_walk),
            label: Text(t('Start Walking', 'Anza Kutembea')),
            style: ElevatedButton.styleFrom(backgroundColor: kPrimary),
          )
        else
          ElevatedButton.icon(
            onPressed: _stopWalking,
            icon: const Icon(Icons.stop_circle_outlined),
            label: Text(t('Stop & Close Boundary', 'Simama & Funga Mipaka')),
            style: ElevatedButton.styleFrom(backgroundColor: kAmber),
          ),
      ],

      if (_points.isNotEmpty) ...[
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _undoLast,
              icon: const Icon(Icons.undo, size: 16),
              label: Text(t('Undo', 'Rudisha')),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => setState(() { _points.clear(); _areaAcres = 0; }),
              icon: const Icon(Icons.delete_outline, size: 16),
              label: Text(t('Clear', 'Futa')),
              style: OutlinedButton.styleFrom(foregroundColor: kRed, side: const BorderSide(color: kRed)),
            ),
          ),
        ]),
      ],

      const SizedBox(height: 20),

      ElevatedButton(
        onPressed: _points.length >= 3 ? _confirm : null,
        child: Text(t('Confirm Farm Boundary', 'Thibitisha Mipaka ya Shamba')),
      ),
      const SizedBox(height: 10),
      TextButton(
        onPressed: widget.onBack,
        child: Text('← ${t('Back', 'Rudi')}', style: const TextStyle(color: kTextMid)),
      ),
    ]);
  }
}

class _ModeTab extends StatelessWidget {
  final String label;
  final bool active;
  final IconData icon;
  final VoidCallback onTap;
  const _ModeTab({required this.label, required this.active, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.symmetric(horizontal: 2),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: active ? kPrimary : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: active ? kPrimary : kBorder),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 14, color: active ? Colors.white : kTextMid),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: active ? Colors.white : kTextMid, fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  final String text;
  final Color color;
  const _Pill({required this.text, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600), textAlign: TextAlign.center),
    );
  }
}
