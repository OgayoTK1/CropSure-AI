import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/farm.dart';
import '../../../core/api_client.dart';

final farmDetailProvider =
    FutureProvider.family<Farm, String>((ref, farmId) async {
  final client = ref.read(apiClientProvider);
  final data = await client.getFarm(farmId);
  return Farm.fromJson(data);
});
