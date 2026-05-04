# CropSure AI — Flutter Mobile App

Parametric crop insurance for Kenyan smallholder farmers. GPS boundary tracing, satellite NDVI monitoring, automatic M-Pesa payouts.

## Quick Start

```bash
cd mobile
flutter pub get
flutter run
```

## Screens

| Screen | Route | Description |
|--------|-------|-------------|
| Landing | `/` | Marketing page, hero, how-it-works, pricing |
| Enrollment | `/enroll` | 3-step: farmer details → GPS boundary → M-Pesa payment |
| Dashboard | `/dashboard` | Admin map, stats, NDVI chart, farm list |
| Farm Detail | `/farm/:id` | Individual farm, NDVI history, payout list |

## Connecting to Backend

Set the API URL in `lib/core/constants.dart`:
```dart
const String kApiBase = 'http://YOUR_BACKEND_URL:8000';
```

Or at build time:
```bash
flutter run --dart-define=API_BASE_URL=http://your-server:8000
```

**Android emulator:** use `http://10.0.2.2:8000` to reach localhost.  
**Physical device:** use your machine's local IP e.g. `http://192.168.1.x:8000`.

## GPS Enrollment

The GPS Walk mode streams device location via `geolocator` and traces the polygon in real time.
Tap Mode (Manual) allows placing points on the map for devices where GPS is unavailable.

## Languages

Toggle English/Swahili with the language button in any screen header.
All UI strings use the `LocaleService.t(en, sw)` helper.

## Architecture

```
lib/
├── main.dart                   # App entry + GoRouter
├── core/
│   ├── theme.dart              # Colors, typography, component styles
│   └── constants.dart          # API URL, crop rates, map defaults
├── models/
│   └── models.dart             # Farm, Policy, NdviReading, Payout, EnrollRequest
├── services/
│   ├── api_service.dart        # HTTP client (getFarms, enrollFarm, simulate)
│   └── locale_service.dart     # EN/SW toggle, persisted to SharedPreferences
└── screens/
    ├── landing_screen.dart
    ├── enrollment/
    │   ├── enrollment_screen.dart   # Step controller
    │   ├── step_farmer_details.dart # Name, phone, village, crop selector
    │   ├── step_gps_boundary.dart   # flutter_map + geolocator GPS tracing
    │   └── step_payment.dart        # Summary + API call + success screen
    ├── dashboard_screen.dart        # Map + stats + NDVI chart + farm list
    └── farm_detail_screen.dart      # Full farm view + payout history
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `flutter_map` | OpenStreetMap tile rendering + polygon/marker layers |
| `geolocator` | Real-time GPS position stream for boundary tracing |
| `permission_handler` | Location permission request |
| `fl_chart` | NDVI line charts with stress threshold line |
| `go_router` | Declarative routing |
| `provider` | LocaleService state management |
| `http` | REST API calls to FastAPI backend |
| `shared_preferences` | Persist language preference |

## Building for Release

```bash
# Android APK
flutter build apk --release --dart-define=API_BASE_URL=https://your-backend.railway.app

# Android App Bundle (Play Store)
flutter build appbundle --release
```
