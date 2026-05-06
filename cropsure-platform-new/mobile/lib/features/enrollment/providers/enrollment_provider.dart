import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../models/enrollment_data.dart';
import '../../../core/api_client.dart';

// Wizard step (0, 1, 2)
final enrollmentStepProvider = StateProvider<int>((ref) => 0);

// Enrollment data notifier
class EnrollmentNotifier extends Notifier<EnrollmentData> {
  @override
  EnrollmentData build() => EnrollmentData();

  void updateStep1({
    required String name,
    required String phone,
    required String village,
    required String crop,
  }) {
    state = EnrollmentData(
      farmerName: name,
      phoneNumber: phone,
      village: village,
      cropType: crop,
      polygonCoordinates: state.polygonCoordinates,
      areaAcres: state.areaAcres,
    );
  }

  void updatePolygon(List polygonCoords, double acres) {
    state = EnrollmentData(
      farmerName: state.farmerName,
      phoneNumber: state.phoneNumber,
      village: state.village,
      cropType: state.cropType,
      polygonCoordinates: List.from(polygonCoords),
      areaAcres: acres,
    );
  }

  void reset() {
    state = EnrollmentData();
  }
}

final enrollmentProvider =
    NotifierProvider<EnrollmentNotifier, EnrollmentData>(EnrollmentNotifier.new);

// Enrollment API call state
final enrollmentResultProvider =
    StateProvider<AsyncValue<Map<String, dynamic>>?>((ref) => null);
