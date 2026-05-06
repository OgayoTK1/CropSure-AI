import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../providers/enrollment_provider.dart';
import '../widgets/step_indicator.dart';
import 'step1_details_screen.dart';
import 'step2_boundary_screen.dart';
import 'step3_payment_screen.dart';

class EnrollmentScreen extends ConsumerStatefulWidget {
  const EnrollmentScreen({super.key});

  @override
  ConsumerState<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends ConsumerState<EnrollmentScreen> {
  final _pageController = PageController();

  void _nextPage() {
    final current = ref.read(enrollmentStepProvider);
    if (current < 2) {
      ref.read(enrollmentStepProvider.notifier).state = current + 1;
      _pageController.animateToPage(
        current + 1,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOut,
      );
    }
  }

  void _prevPage() {
    final current = ref.read(enrollmentStepProvider);
    if (current > 0) {
      ref.read(enrollmentStepProvider.notifier).state = current - 1;
      _pageController.animateToPage(
        current - 1,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = ref.watch(enrollmentStepProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('enroll_title')),
        leading: step > 0
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: _prevPage,
              )
            : null,
        actions: [
          TextButton(
            onPressed: () {
              final locale = ref.read(localeProvider);
              ref.read(localeProvider.notifier).state =
                  locale.languageCode == 'en'
                      ? const Locale('sw')
                      : const Locale('en');
            },
            child: Text(
              context.tr('language_toggle'),
              style: const TextStyle(color: Colors.white),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pushNamed('/dashboard'),
            child: const Text(
              'Dashboard',
              style: TextStyle(color: Colors.white70),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          StepIndicator(
            currentStep: step,
            totalSteps: 3,
            labels: [
              context.tr('enroll_step1'),
              context.tr('enroll_step2'),
              context.tr('enroll_step3'),
            ],
          ),
          Expanded(
            child: PageView(
              controller: _pageController,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                Step1DetailsScreen(onNext: _nextPage),
                Step2BoundaryScreen(onNext: _nextPage),
                const Step3PaymentScreen(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
