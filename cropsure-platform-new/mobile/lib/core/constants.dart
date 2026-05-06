/// App-wide constants for CropSure AI.

class AppConstants {
  AppConstants._();

  // OSM tile URL template for flutter_map TileLayer
  static const String osmTileUrl =
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  // User-agent string sent with every tile request (required by OSM policy)
  static const String tileUserAgent = 'com.cropsure.app';

  // Primary color hex (matches AppTheme.primary)
  static const String primaryColorHex = '#1D9E75';

  // Default map center (Nairobi, Kenya)
  static const double defaultLat = -1.286;
  static const double defaultLng = 36.817;
  static const double defaultZoom = 8.0;

  // Premium calculation constants
  static const double premiumPerAcre = 300.0;
  static const double coverageMultiplier = 8.0;

  // GPS boundary walk: minimum points before polygon can be closed
  static const int minPolygonPoints = 4;

  // GPS boundary walk: distance filter in metres between position updates
  static const int gpsDistanceFilterMetres = 3;

  // Auto-close polygon when tapping within this distance (metres) of first point
  static const double polygonCloseRadiusMetres = 15.0;

  // Dashboard auto-refresh interval
  static const int dashboardRefreshSeconds = 30;

  // Payout toast display duration
  static const int toastDisplaySeconds = 4;

  // NDVI stress confidence threshold for triggering the chart marker
  static const double ndviStressConfidenceThreshold = 0.72;

  // Policy season length in days
  static const int policySeasonDays = 180;
}
