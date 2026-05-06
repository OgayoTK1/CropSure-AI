class Farm {
  final String id;
  final String farmerName;
  final String phoneNumber;
  final String village;
  final String cropType;
  final double areaAcres;
  final Map<String, dynamic> polygonGeojson;
  final String? healthStatus; // healthy / mild_stress / stress
  final double? currentNdvi;
  final String? stressType;
  final String? policyStatus;
  final DateTime createdAt;
  final FarmPolicy? policy;
  final List<NdviReading> ndviHistory;
  final List<Payout> payouts;

  const Farm({
    required this.id,
    required this.farmerName,
    required this.phoneNumber,
    required this.village,
    required this.cropType,
    required this.areaAcres,
    required this.polygonGeojson,
    this.healthStatus,
    this.currentNdvi,
    this.stressType,
    this.policyStatus,
    required this.createdAt,
    this.policy,
    required this.ndviHistory,
    required this.payouts,
  });

  factory Farm.fromJson(Map<String, dynamic> json) {
    return Farm(
      id: json['id'] as String,
      farmerName: json['farmer_name'] as String,
      phoneNumber: json['phone_number'] as String,
      village: json['village'] as String,
      cropType: json['crop_type'] as String,
      areaAcres: (json['area_acres'] as num).toDouble(),
      polygonGeojson: json['polygon_geojson'] as Map<String, dynamic>,
      healthStatus: json['health_status'] as String?,
      currentNdvi: (json['current_ndvi'] as num?)?.toDouble(),
      stressType: json['stress_type'] as String?,
      policyStatus: json['policy_status'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      policy: json['policy'] != null
          ? FarmPolicy.fromJson(json['policy'] as Map<String, dynamic>)
          : null,
      ndviHistory: (json['ndvi_history'] as List<dynamic>? ?? [])
          .map((e) => NdviReading.fromJson(e as Map<String, dynamic>))
          .toList(),
      payouts: (json['payouts'] as List<dynamic>? ?? [])
          .map((e) => Payout.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class FarmPolicy {
  final String id;
  final String status;
  final double premiumPaidKes;
  final double coverageAmountKes;
  final String seasonStart;
  final String seasonEnd;

  const FarmPolicy({
    required this.id,
    required this.status,
    required this.premiumPaidKes,
    required this.coverageAmountKes,
    required this.seasonStart,
    required this.seasonEnd,
  });

  factory FarmPolicy.fromJson(Map<String, dynamic> json) {
    return FarmPolicy(
      id: json['id'] as String,
      status: json['status'] as String,
      premiumPaidKes: (json['premium_paid_kes'] as num).toDouble(),
      coverageAmountKes: (json['coverage_amount_kes'] as num).toDouble(),
      seasonStart: json['season_start'] as String,
      seasonEnd: json['season_end'] as String,
    );
  }
}

class NdviReading {
  final String date;
  final double ndvi;
  final String? stressType;
  final double? confidence;

  const NdviReading({
    required this.date,
    required this.ndvi,
    this.stressType,
    this.confidence,
  });

  factory NdviReading.fromJson(Map<String, dynamic> json) {
    return NdviReading(
      date: json['date'] as String,
      ndvi: (json['ndvi'] as num).toDouble(),
      stressType: json['stress_type'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
    );
  }
}

class Payout {
  final String id;
  final double amountKes;
  final String stressType;
  final String status;
  final String? explanationEn;
  final String? explanationSw;
  final String triggeredAt;

  const Payout({
    required this.id,
    required this.amountKes,
    required this.stressType,
    required this.status,
    this.explanationEn,
    this.explanationSw,
    required this.triggeredAt,
  });

  factory Payout.fromJson(Map<String, dynamic> json) {
    return Payout(
      id: json['id'] as String,
      amountKes: (json['amount_kes'] as num).toDouble(),
      stressType: json['stress_type'] as String,
      status: json['status'] as String,
      explanationEn: json['explanation_en'] as String?,
      explanationSw: json['explanation_sw'] as String?,
      triggeredAt: json['triggered_at'] as String,
    );
  }
}
