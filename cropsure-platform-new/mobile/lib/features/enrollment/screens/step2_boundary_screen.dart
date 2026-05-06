import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../providers/enrollment_provider.dart';

class Step2BoundaryScreen extends ConsumerStatefulWidget {
  final VoidCallback onNext;
  const Step2BoundaryScreen({super.key, required this.onNext});

  @override
  ConsumerState<Step2BoundaryScreen> createState() =>
      _Step2BoundaryScreenState();
}

class _Step2BoundaryScreenState extends ConsumerState<Step2BoundaryScreen> {
  final MapController _mapController = MapController();
  final List<LatLng> _points = [];
  bool _isWalking = false;
  bool _isClosed = false;
  bool _isManualMode = false;
  StreamSubscription<Position>? _positionSub;
  double _areaAcres = 0.0;

  static const LatLng _kenyaCenter = LatLng(-1.286, 36.817);

  @override
  void dispose() {
    _positionSub?.cancel();
    super.dispose();
  }

  Future<bool> _ensurePermission() async {
    LocationPermission perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    return perm != LocationPermission.denied &&
        perm != LocationPermission.deniedForever;
  }

  void _startWalking() async {
    if (!await _ensurePermission()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.tr('map_location_error'))),
        );
      }
      return;
    }
    setState(() {
      _isWalking = true;
      _points.clear();
      _isClosed = false;
    });
    _positionSub = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 3,
      ),
    ).listen((pos) {
      final pt = LatLng(pos.latitude, pos.longitude);
      setState(() {
        _points.add(pt);
        _mapController.move(pt, 17);
      });
    });
  }

  void _stopWalking() {
    _positionSub?.cancel();
    if (_points.length >= 4) {
      _closePolygon();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('map_min_points'))),
      );
    }
    setState(() => _isWalking = false);
  }

  void _closePolygon() {
    setState(() {
      _isClosed = true;
      _areaAcres = _computeArea();
    });
  }

  void _onMapTap(TapPosition _, LatLng pt) {
    if (!_isManualMode || _isClosed) return;
    setState(() {
      _points.add(pt);
    });
    // Auto-close if tapping near first point and have 4+ points
    if (_points.length >= 4) {
      final first = _points.first;
      final dist =
          const Distance().as(LengthUnit.Meter, first, pt);
      if (dist < 15) {
        _points.removeLast();
        _closePolygon();
      }
    }
  }

  double _computeArea() {
    if (_points.length < 3) return 0.0;
    // Shoelace on projected coordinates
    double area = 0.0;
    const double degToM = 111320.0;
    for (int i = 0; i < _points.length; i++) {
      final j = (i + 1) % _points.length;
      final xi = _points[i].longitude *
          degToM *
          math.cos(_points[i].latitude * math.pi / 180);
      final yi = _points[i].latitude * degToM;
      final xj = _points[j].longitude *
          degToM *
          math.cos(_points[j].latitude * math.pi / 180);
      final yj = _points[j].latitude * degToM;
      area += xi * yj - xj * yi;
    }
    return (area.abs() / 2) / 4047; // m² → acres
  }

  void _confirm() {
    ref
        .read(enrollmentProvider.notifier)
        .updatePolygon(List.from(_points), _areaAcres);
    widget.onNext();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: _kenyaCenter,
            initialZoom: 13,
            onTap: _onMapTap,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.cropsure.app',
            ),
            if (_points.isNotEmpty && !_isClosed)
              PolylineLayer(polylines: [
                Polyline(
                  points: _points,
                  color: AppTheme.primary,
                  strokeWidth: 3,
                ),
              ]),
            if (_isClosed && _points.isNotEmpty)
              PolygonLayer(polygons: [
                Polygon(
                  points: _points,
                  color: AppTheme.primary.withOpacity(0.25),
                  borderColor: AppTheme.primary,
                  borderStrokeWidth: 3,
                ),
              ]),
            MarkerLayer(
              markers: _points.isEmpty
                  ? []
                  : [
                      Marker(
                        point: _points.first,
                        width: 16,
                        height: 16,
                        child: Container(
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                  color: Colors.black26, blurRadius: 4),
                            ],
                          ),
                        ),
                      ),
                    ],
            ),
          ],
        ),
        // Top mode toggle
        Positioned(
          top: 12,
          left: 16,
          right: 16,
          child: Row(
            children: [
              Expanded(
                child: _ModeButton(
                  label: context.tr('map_walk_mode'),
                  selected: !_isManualMode,
                  onTap: () => setState(() {
                    _isManualMode = false;
                    _points.clear();
                    _isClosed = false;
                  }),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ModeButton(
                  label: context.tr('map_manual_mode'),
                  selected: _isManualMode,
                  onTap: () => setState(() {
                    _isManualMode = true;
                    _isWalking = false;
                    _positionSub?.cancel();
                    _points.clear();
                    _isClosed = false;
                  }),
                ),
              ),
            ],
          ),
        ),
        // Point counter
        if (_points.isNotEmpty && !_isClosed)
          Positioned(
            top: 68,
            left: 16,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: const [
                  BoxShadow(color: Colors.black12, blurRadius: 4)
                ],
              ),
              child: Text(
                context.tr(
                    'map_points_captured', {'count': '${_points.length}'}),
                style: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ),
          ),
        // Bottom controls
        Positioned(
          bottom: 24,
          left: 16,
          right: 16,
          child: Column(
            children: [
              if (_isClosed)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    context.tr('map_area_display',
                        {'acres': _areaAcres.toStringAsFixed(2)}),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.primary,
                    ),
                  ),
                ),
              if (!_isManualMode && !_isClosed)
                SizedBox(
                  width: double.infinity,
                  child: _isWalking
                      ? ElevatedButton.icon(
                          onPressed:
                              _points.length >= 4 ? _stopWalking : null,
                          icon: const Icon(Icons.stop_circle_outlined),
                          label: Text(context.tr('map_stop_close')),
                          style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.error),
                        )
                      : ElevatedButton.icon(
                          onPressed: _startWalking,
                          icon: const Icon(Icons.directions_walk),
                          label: Text(context.tr('map_start_walking')),
                        ),
                ),
              if (_isManualMode && !_isClosed && _points.length >= 4)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _closePolygon,
                    child: Text(context.tr('map_stop_close')),
                  ),
                ),
              if (_isClosed)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _confirm,
                    child: Text(context.tr('map_confirm_boundary')),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ModeButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _ModeButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary : Colors.white,
          borderRadius: BorderRadius.circular(10),
          boxShadow: const [
            BoxShadow(color: Colors.black12, blurRadius: 4),
          ],
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              color: selected ? Colors.white : AppTheme.textPrimary,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}
