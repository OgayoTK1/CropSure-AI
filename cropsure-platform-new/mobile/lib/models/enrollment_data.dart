import 'package:latlong2/latlong.dart';

class EnrollmentData {
  String farmerName;
  String phoneNumber;
  String village;
  String cropType;
  List<LatLng> polygonCoordinates;
  double areaAcres;

  EnrollmentData({
    this.farmerName = '',
    this.phoneNumber = '',
    this.village = '',
    this.cropType = 'Maize',
    this.polygonCoordinates = const [],
    this.areaAcres = 0.0,
  });

  double get premiumKes => (areaAcres * 300).roundToDouble();
  double get coverageKes => premiumKes * 8;

  Map<String, dynamic> toPolygonGeoJson() {
    final coords =
        polygonCoordinates.map((p) => [p.longitude, p.latitude]).toList();
    if (coords.isNotEmpty) coords.add(coords.first); // close ring
    return {
      'type': 'Polygon',
      'coordinates': [coords],
    };
  }

  Map<String, dynamic> toEnrollRequest() => {
        'farmer_name': farmerName,
        'phone_number': phoneNumber,
        'village': village,
        'crop_type': cropType,
        'polygon_geojson': toPolygonGeoJson(),
      };
}
