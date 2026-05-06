import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const String _defaultBaseUrl = 'http://10.0.2.2:8000'; // Android emulator → localhost

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

class ApiClient {
  late final Dio _dio;

  ApiClient({String? baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl ?? _defaultBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(LogInterceptor(responseBody: true, error: true));
  }

  Future<Map<String, dynamic>> enrollFarm(Map<String, dynamic> data) async {
    final r = await _dio.post('/farms/enroll', data: data);
    return r.data as Map<String, dynamic>;
  }

  Future<List<dynamic>> listFarms() async {
    final r = await _dio.get('/farms');
    return r.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> getFarm(String farmId) async {
    final r = await _dio.get('/farms/$farmId');
    return r.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> simulateDrought(String farmId) async {
    final r = await _dio.post('/trigger/simulate-drought/$farmId');
    return r.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> runMonitoring() async {
    final r = await _dio.post('/trigger/run');
    return r.data as Map<String, dynamic>;
  }

  Future<bool> checkHealth() async {
    try {
      final r = await _dio.get('/health');
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
