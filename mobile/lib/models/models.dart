import 'package:latlong2/latlong.dart';

// ── Farm ─────────────────────────────────────────────────────────────────────

class Farm {
  final String id;
  final String farmerName;
  final String phoneNumber;
  final double areaAcres;
  final String cropType;
  final String village;
  final String createdAt;
  final String? healthStatus;   // drought | flood | none | null
  final String? policyStatus;   // active | pending_payment | expired
  final String? policyId;
  final double? currentNdvi;
  final List<NdviReading> ndviHistory;
  final Policy? policy;
  final List<Payout> payouts;
  final List<LatLng> boundary;

  const Farm({
    required this.id,
    required this.farmerName,
    required this.phoneNumber,
    required this.areaAcres,
    required this.cropType,
    required this.village,
    required this.createdAt,
    this.healthStatus,
    this.policyStatus,
    this.policyId,
    this.currentNdvi,
    this.ndviHistory = const [],
    this.policy,
    this.payouts = const [],
    this.boundary = const [],
  });

  static List<LatLng> _parseBoundary(dynamic geojson) {
    if (geojson == null) return const [];
    final coords = (geojson['coordinates'] as List<dynamic>?)?.firstOrNull as List<dynamic>?;
    if (coords == null) return const [];
    return coords
        .whereType<List<dynamic>>()
        .map((c) => LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble()))
        .toList();
  }

  factory Farm.fromJson(Map<String, dynamic> j) => Farm(
        id: j['id'] as String,
        farmerName: j['farmer_name'] as String,
        phoneNumber: j['phone_number'] as String,
        areaAcres: (j['area_acres'] as num).toDouble(),
        cropType: j['crop_type'] as String,
        village: j['village'] as String,
        createdAt: j['created_at'] as String? ?? '',
        healthStatus: j['health_status'] as String?,
        policyStatus: j['policy_status'] as String?,
        policyId: j['policy_id'] as String? ?? (j['policy'] != null ? j['policy']['id'] as String? : null),
        currentNdvi: j['latest_ndvi'] != null
            ? (j['latest_ndvi']['ndvi_value'] as num?)?.toDouble()
            : null,
        ndviHistory: (j['ndvi_history'] as List<dynamic>? ?? [])
            .map((e) => NdviReading.fromJson(e as Map<String, dynamic>))
            .toList(),
        policy: j['policy'] != null
            ? Policy.fromJson(j['policy'] as Map<String, dynamic>)
            : null,
        payouts: (j['payout_history'] as List<dynamic>? ?? [])
            .map((e) => Payout.fromJson(e as Map<String, dynamic>))
            .toList(),
        boundary: _parseBoundary(j['polygon_geojson']),
      );

  String get statusLabel {
    switch (healthStatus) {
      case 'drought':
      case 'flood':
      case 'pest_disease':
        return 'severe_stress';
      case 'none':
        return 'healthy';
      default:
        return healthStatus ?? 'none';
    }
  }
}

// ── Policy ────────────────────────────────────────────────────────────────────

class Policy {
  final String id;
  final String seasonStart;
  final String seasonEnd;
  final double premiumPaidKes;
  final double coverageAmountKes;
  final String status;
  final String? mpesaReference;

  const Policy({
    required this.id,
    required this.seasonStart,
    required this.seasonEnd,
    required this.premiumPaidKes,
    required this.coverageAmountKes,
    required this.status,
    this.mpesaReference,
  });

  factory Policy.fromJson(Map<String, dynamic> j) => Policy(
        id: j['id'] as String,
        seasonStart: j['season_start'] as String,
        seasonEnd: j['season_end'] as String,
        premiumPaidKes: (j['premium_paid_kes'] as num).toDouble(),
        coverageAmountKes: (j['coverage_amount_kes'] as num).toDouble(),
        status: j['status'] as String,
        mpesaReference: j['mpesa_reference'] as String?,
      );
}

// ── NDVI Reading ──────────────────────────────────────────────────────────────

class NdviReading {
  final String readingDate;
  final double ndviValue;
  final String? stressType;
  final double? confidence;
  final bool cloudContaminated;

  const NdviReading({
    required this.readingDate,
    required this.ndviValue,
    this.stressType,
    this.confidence,
    this.cloudContaminated = false,
  });

  factory NdviReading.fromJson(Map<String, dynamic> j) => NdviReading(
        readingDate: j['reading_date'] as String,
        ndviValue: (j['ndvi_value'] as num).toDouble(),
        stressType: j['stress_type'] as String?,
        confidence: (j['confidence'] as num?)?.toDouble(),
        cloudContaminated: j['cloud_contaminated'] as bool? ?? false,
      );
}

// ── Payout ────────────────────────────────────────────────────────────────────

class Payout {
  final String id;
  final double payoutAmountKes;
  final String stressType;
  final String explanationEn;
  final String explanationSw;
  final String status;
  final String triggeredAt;

  const Payout({
    required this.id,
    required this.payoutAmountKes,
    required this.stressType,
    required this.explanationEn,
    this.explanationSw = '',
    required this.status,
    required this.triggeredAt,
  });

  factory Payout.fromJson(Map<String, dynamic> j) => Payout(
        id: j['id'] as String,
        payoutAmountKes: (j['payout_amount_kes'] as num).toDouble(),
        stressType: j['stress_type'] as String,
        explanationEn: j['explanation_en'] as String? ?? '',
        explanationSw: j['explanation_sw'] as String? ?? '',
        status: j['status'] as String,
        triggeredAt: j['triggered_at'] as String,
      );
}

// ── Enroll request ────────────────────────────────────────────────────────────

class EnrollRequest {
  final String farmerName;
  final String phoneNumber;
  final String village;
  final String cropType;
  final List<LatLng> boundary;
  final double areaAcres;

  const EnrollRequest({
    required this.farmerName,
    required this.phoneNumber,
    required this.village,
    required this.cropType,
    required this.boundary,
    required this.areaAcres,
  });

  Map<String, dynamic> toJson() {
    final coords = boundary.map((p) => [p.longitude, p.latitude]).toList();
    if (coords.isNotEmpty && coords.first != coords.last) {
      coords.add(coords.first);
    }
    return {
      'farmer_name': farmerName,
      'phone_number': phoneNumber,
      'village': village,
      'crop_type': cropType,
      'polygon_geojson': {
        'type': 'Polygon',
        'coordinates': [coords],
      },
    };
  }
}

// ── Enroll response ───────────────────────────────────────────────────────────

class EnrollResponse {
  final String farmId;
  final String policyId;
  final double premiumAmount;
  final bool mpesaStkInitiated;

  const EnrollResponse({
    required this.farmId,
    required this.policyId,
    required this.premiumAmount,
    required this.mpesaStkInitiated,
  });

  factory EnrollResponse.fromJson(Map<String, dynamic> j) => EnrollResponse(
        farmId: j['farm_id'] as String,
        policyId: j['policy_id'] as String,
        premiumAmount: (j['premium_amount'] as num).toDouble(),
        mpesaStkInitiated: j['mpesa_stk_initiated'] as bool? ?? false,
      );
}
