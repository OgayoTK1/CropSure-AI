import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/constants.dart';
import '../models/models.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});
  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  static final _client = http.Client();
  static const _headers = {'Content-Type': 'application/json'};
  static const _timeout = Duration(seconds: 20);

  // ── Health ──────────────────────────────────────────────────────────────────

  static Future<bool> ping() async {
    try {
      final res = await _client
          .get(Uri.parse('$kApiBase/health'), headers: _headers)
          .timeout(_timeout);
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Farms ───────────────────────────────────────────────────────────────────

  static Future<List<Farm>> getFarms({String? phone}) async {
    final uri = Uri.parse('$kApiBase/farms')
        .replace(queryParameters: phone != null ? {'phone': phone} : null);
    final res = await _client.get(uri, headers: _headers).timeout(_timeout);
    _check(res);
    final list = jsonDecode(res.body) as List;
    return list.map((e) => Farm.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<Farm> getFarm(String farmId) async {
    final res = await _client
        .get(Uri.parse('$kApiBase/farms/$farmId'), headers: _headers)
        .timeout(_timeout);
    _check(res);
    return Farm.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<EnrollResponse> enrollFarm(EnrollRequest req) async {
    final res = await _client
        .post(
          Uri.parse('$kApiBase/farms/enroll'),
          headers: _headers,
          body: jsonEncode(req.toJson()),
        )
        .timeout(const Duration(seconds: 30));
    _check(res, expectedStatus: 201);
    return EnrollResponse.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // ── Trigger ─────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> simulateDrought(String farmId) async {
    final res = await _client
        .post(
          Uri.parse('$kApiBase/trigger/simulate-drought/$farmId'),
          headers: _headers,
        )
        .timeout(const Duration(seconds: 30));
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> runMonitoringCycle() async {
    final res = await _client
        .post(Uri.parse('$kApiBase/trigger/run'), headers: _headers)
        .timeout(const Duration(seconds: 60));
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ── Private ─────────────────────────────────────────────────────────────────

  static void _check(http.Response res, {int expectedStatus = 200}) {
    if (res.statusCode != expectedStatus) {
      String msg = 'Request failed';
      try {
        final body = jsonDecode(res.body);
        msg = body['detail']?.toString() ?? body['message']?.toString() ?? msg;
      } catch (_) {}
      throw ApiException(msg, statusCode: res.statusCode);
    }
  }
}
