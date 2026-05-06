import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/farm.dart';
import '../../../core/api_client.dart';

final farmsProvider = FutureProvider<List<Farm>>((ref) async {
  final client = ref.read(apiClientProvider);
  final data = await client.listFarms();
  return data
      .map((e) => Farm.fromJson(e as Map<String, dynamic>))
      .toList();
});

final selectedFarmIdProvider = StateProvider<String?>((ref) => null);

final simulateDroughtProvider =
    StateProvider<AsyncValue<Map<String, dynamic>>?>((ref) => null);
