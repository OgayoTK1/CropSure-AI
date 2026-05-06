# CropSure AI — Flutter Mobile App

Farm-level parametric crop insurance for African smallholder farmers.

## Prerequisites

- Flutter SDK ≥ 3.3.0 (run `flutter --version`)
- Android Studio or Xcode (for device/emulator)
- Backend running at `http://localhost:8000` (or `http://10.0.2.2:8000` on Android emulator)

## Setup

```bash
cd mobile
flutter pub get
flutter run
```

## Architecture

```
lib/
├── main.dart                        # App entry point
├── core/
│   ├── theme.dart                   # Color scheme & text styles
│   ├── router.dart                  # go_router routes
│   ├── api_client.dart              # Dio HTTP client → backend
│   ├── l10n.dart                    # English/Swahili localisation
│   └── constants.dart               # OSM tile URL, magic numbers
├── models/
│   ├── farm.dart                    # Farm, FarmPolicy, NdviReading, Payout
│   └── enrollment_data.dart         # Wizard state + GeoJSON serialisation
└── features/
    ├── enrollment/
    │   ├── screens/
    │   │   ├── enrollment_screen.dart       # 3-step wizard container
    │   │   ├── step1_details_screen.dart    # Farmer details form
    │   │   ├── step2_boundary_screen.dart   # GPS walk / manual tap map
    │   │   ├── step3_payment_screen.dart    # Coverage summary + M-Pesa pay
    │   │   └── enrollment_success_screen.dart
    │   ├── providers/enrollment_provider.dart
    │   └── widgets/step_indicator.dart
    ├── dashboard/
    │   ├── screens/dashboard_screen.dart    # Map + stats + simulate drought
    │   └── providers/farms_provider.dart
    └── farm_detail/
        ├── screens/farm_detail_screen.dart  # NDVI chart + payout history
        └── providers/farm_detail_provider.dart
```

## Key Features

| Feature | Implementation |
|---|---|
| GPS boundary walk | `geolocator` stream → `flutter_map` polyline → auto-close |
| Manual boundary | Map tap listener → polygon with proximity close |
| Area calculation | Shoelace formula on projected lat/lng coordinates |
| NDVI chart | `fl_chart` line chart with stress trigger vertical marker |
| Bilingual UI | `AppLocalizations` with JSON files in `assets/i18n/` |
| M-Pesa payment | Backend STK Push call → M-Pesa prompt on farmer's phone |
| Dashboard map | Colour-coded farm markers (green/amber/red by stress) |
| Drought simulation | One-tap demo button → full payout pipeline |

## API Base URL

Change `_defaultBaseUrl` in [lib/core/api_client.dart](lib/core/api_client.dart):
- Android emulator: `http://10.0.2.2:8000`
- iOS simulator / web: `http://localhost:8000`
- Physical device (same WiFi): `http://<your-PC-IP>:8000`

## Building for Release

```bash
# Android APK
flutter build apk --release

# Android App Bundle (Play Store)
flutter build appbundle --release
```
