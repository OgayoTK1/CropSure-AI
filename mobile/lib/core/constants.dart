import 'package:flutter/material.dart';

// API base URL — override with your deployed URL
const String kApiBase = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000', // Android emulator → localhost
);

// Crop options
const List<Map<String, dynamic>> kCrops = [
  {'key': 'maize',   'label': 'Maize',   'labelSw': 'Mahindi',  'rate': 300, 'emoji': '🌽'},
  {'key': 'beans',   'label': 'Beans',   'labelSw': 'Maharagwe','rate': 250, 'emoji': '🫘'},
  {'key': 'tea',     'label': 'Tea',     'labelSw': 'Chai',     'rate': 400, 'emoji': '🍵'},
  {'key': 'cassava', 'label': 'Cassava', 'labelSw': 'Muhogo',   'rate': 200, 'emoji': '🥔'},
  {'key': 'wheat',   'label': 'Wheat',   'labelSw': 'Ngano',    'rate': 350, 'emoji': '🌾'},
  {'key': 'sorghum', 'label': 'Sorghum', 'labelSw': 'Mtama',    'rate': 220, 'emoji': '🌾'},
];

// Map defaults (Central Kenya)
const double kDefaultLat = -0.3031;
const double kDefaultLng = 36.8219;
const double kDefaultZoom = 13.0;
const double kKenyaZoom = 6.0;

// Premium rate (KES per acre if crop not matched)
const int kDefaultPremiumRate = 300;
const int kCoverageMultiplier = 10;

// Health status colours
const Map<String, Color> kHealthColors = {
  'healthy':      Color(0xFF1D9E75),
  'mild_stress':  Color(0xFFF59E0B),
  'severe_stress':Color(0xFFEF4444),
  'none':         Color(0xFF9CA3AF),
};

const Map<String, String> kHealthLabelsEn = {
  'healthy':      'Healthy',
  'mild_stress':  'Mild Stress',
  'severe_stress':'Severe Stress',
  'none':         'No reading',
};

const Map<String, String> kHealthLabelsSw = {
  'healthy':      'Afya Nzuri',
  'mild_stress':  'Msongo Kidogo',
  'severe_stress':'Msongo Mkubwa',
  'none':         'Hakuna data',
};
