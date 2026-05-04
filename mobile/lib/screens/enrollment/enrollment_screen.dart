import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../services/locale_service.dart';
import 'step_farmer_details.dart';
import 'step_gps_boundary.dart';
import 'step_payment.dart';

class EnrollmentScreen extends StatefulWidget {
  const EnrollmentScreen({super.key});

  @override
  State<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends State<EnrollmentScreen> {
  int _step = 0;

  // Farmer details
  String _name = '', _phone = '', _village = '', _crop = 'maize';

  // Boundary
  List<LatLng> _boundary = [];
  double _areaAcres = 0;

  void _reset() => setState(() {
        _step = 0;
        _name = _phone = _village = _crop = '';
        _crop = 'maize';
        _boundary = [];
        _areaAcres = 0;
      });

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocaleService>();
    final t = loc.t;

    final stepLabels = [
      t('Details', 'Maelezo'),
      t('Boundary', 'Mipaka'),
      t('Payment', 'Malipo'),
    ];

    return Scaffold(
      backgroundColor: kGrayBg,
      appBar: AppBar(
        title: Text(t('Enroll Your Farm', 'Andikisha Shamba Lako')),
        leading: _step > 0
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => setState(() => _step--),
              )
            : null,
        actions: [
          TextButton(
            onPressed: loc.toggle,
            child: Text(
              loc.isSwahili ? 'EN' : 'SW',
              style: const TextStyle(color: kPrimary, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
      body: Column(children: [
        // Step indicator
        _StepIndicator(current: _step, labels: stepLabels),

        // Content
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: KeyedSubtree(
                key: ValueKey(_step),
                child: _stepContent(),
              ),
            ),
          ),
        ),
      ]),
    );
  }

  Widget _stepContent() {
    switch (_step) {
      case 0:
        return StepFarmerDetails(
          onNext: (name, phone, village, crop) => setState(() {
            _name = name; _phone = phone; _village = village; _crop = crop;
            _step = 1;
          }),
        );
      case 1:
        return StepGpsBoundary(
          onConfirm: (boundary, area) => setState(() {
            _boundary = boundary; _areaAcres = area; _step = 2;
          }),
          onBack: () => setState(() => _step = 0),
        );
      case 2:
        return StepPayment(
          farmerName: _name,
          phone: _phone,
          village: _village,
          crop: _crop,
          boundary: _boundary,
          areaAcres: _areaAcres,
          onBack: () => setState(() => _step = 1),
          onReset: _reset,
        );
      default:
        return const SizedBox.shrink();
    }
  }
}

// ── Step indicator ────────────────────────────────────────────────────────────

class _StepIndicator extends StatelessWidget {
  final int current;
  final List<String> labels;
  const _StepIndicator({required this.current, required this.labels});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      child: Row(
        children: List.generate(labels.length * 2 - 1, (i) {
          if (i.isOdd) {
            // Connector line
            final done = (i ~/ 2) < current;
            return Expanded(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                height: 2,
                margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
                color: done ? kPrimary : kBorder,
              ),
            );
          }
          final idx = i ~/ 2;
          final done = idx < current;
          final active = idx == current;
          return AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: 34, height: 34,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: done ? kPrimaryBg : active ? kPrimary : Colors.white,
              border: Border.all(
                color: done || active ? kPrimary : kBorder,
                width: active ? 2.5 : 1.5,
              ),
            ),
            child: Center(
              child: done
                  ? const Icon(Icons.check, size: 16, color: kPrimary)
                  : Text(
                      '${idx + 1}',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: active ? Colors.white : kTextMid,
                      ),
                    ),
            ),
          );
        }),
      ),
    );
  }
}
