import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../../../core/api_client.dart';
import '../providers/enrollment_provider.dart';

class Step3PaymentScreen extends ConsumerStatefulWidget {
  const Step3PaymentScreen({super.key});

  @override
  ConsumerState<Step3PaymentScreen> createState() =>
      _Step3PaymentScreenState();
}

class _Step3PaymentScreenState extends ConsumerState<Step3PaymentScreen> {
  bool _loading = false;
  String? _error;

  Future<void> _pay() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = ref.read(enrollmentProvider);
      final result =
          await ref.read(apiClientProvider).enrollFarm(data.toEnrollRequest());
      if (mounted) context.go('/success', extra: result);
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(enrollmentProvider);
    final fmt = NumberFormat('#,##0', 'en_KE');
    final now = DateTime.now();
    final end = now.add(const Duration(days: 180));
    final dateFmt = DateFormat('dd MMM yyyy');

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('payment_summary'),
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _Row(
                    context.tr('payment_area'),
                    '${data.areaAcres.toStringAsFixed(2)} acres',
                  ),
                  _Row(context.tr('payment_crop'), data.cropType),
                  const Divider(height: 24),
                  _Row(
                    context.tr('payment_premium'),
                    'KES ${fmt.format(data.premiumKes)}',
                    bold: true,
                    color: AppTheme.primary,
                  ),
                  _Row(
                    context.tr('payment_coverage'),
                    'KES ${fmt.format(data.coverageKes)}',
                  ),
                  _Row(
                    context.tr('payment_period'),
                    '${dateFmt.format(now)} – ${dateFmt.format(end)}',
                  ),
                ],
              ),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _error!,
                style: const TextStyle(color: AppTheme.error, fontSize: 13),
              ),
            ),
          ],
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : ElevatedButton(
                    onPressed: _pay,
                    child: Text(
                      context.tr('payment_pay_button',
                          {'amount': 'KES ${fmt.format(data.premiumKes)}'}),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  final bool bold;
  final Color? color;

  const _Row(this.label, this.value, {this.bold = false, this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
                color: AppTheme.textSecondary, fontSize: 14),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: bold ? FontWeight.w700 : FontWeight.w500,
              color: color ?? AppTheme.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
