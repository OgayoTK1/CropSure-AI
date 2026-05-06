import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme.dart';
import '../../../core/l10n.dart';
import '../providers/enrollment_provider.dart';

class Step1DetailsScreen extends ConsumerStatefulWidget {
  final VoidCallback onNext;
  const Step1DetailsScreen({super.key, required this.onNext});

  @override
  ConsumerState<Step1DetailsScreen> createState() => _Step1DetailsScreenState();
}

class _Step1DetailsScreenState extends ConsumerState<Step1DetailsScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _villageCtrl = TextEditingController();
  String _cropType = 'Maize';

  static const List<String> _cropKeys = [
    'Maize',
    'Beans',
    'Tea',
    'Wheat',
    'Sorghum',
    'Coffee',
  ];

  @override
  void initState() {
    super.initState();
    final data = ref.read(enrollmentProvider);
    _nameCtrl.text = data.farmerName;
    _phoneCtrl.text = data.phoneNumber;
    _villageCtrl.text = data.village;
    _cropType = data.cropType.isEmpty ? 'Maize' : data.cropType;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _villageCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      ref.read(enrollmentProvider.notifier).updateStep1(
            name: _nameCtrl.text.trim(),
            phone: _phoneCtrl.text.trim(),
            village: _villageCtrl.text.trim(),
            crop: _cropType,
          );
      widget.onNext();
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('enroll_step1'),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 24),
            TextFormField(
              controller: _nameCtrl,
              decoration: InputDecoration(
                labelText: context.tr('field_name'),
                hintText: context.tr('field_name_hint'),
                prefixIcon: const Icon(Icons.person_outline),
              ),
              textCapitalization: TextCapitalization.words,
              validator: (v) =>
                  (v == null || v.trim().length < 2)
                      ? 'Please enter your full name'
                      : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _phoneCtrl,
              decoration: InputDecoration(
                labelText: context.tr('field_phone'),
                hintText: context.tr('field_phone_hint'),
                prefixIcon: const Icon(Icons.phone_outlined),
              ),
              keyboardType: TextInputType.phone,
              validator: (v) {
                if (v == null) return 'Required';
                final clean = v.replaceAll(RegExp(r'\s'), '');
                if (!RegExp(r'^(07|01|2547|2541)\d{7,8}$').hasMatch(clean)) {
                  return 'Enter a valid Kenyan M-Pesa number';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _villageCtrl,
              decoration: InputDecoration(
                labelText: context.tr('field_village'),
                hintText: context.tr('field_village_hint'),
                prefixIcon: const Icon(Icons.location_city_outlined),
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _cropType,
              decoration: InputDecoration(
                labelText: context.tr('field_crop'),
                prefixIcon: const Icon(Icons.grass_outlined),
              ),
              items: _cropKeys
                  .map((k) => DropdownMenuItem(
                        value: k,
                        child: Text(context.tr('crop_${k.toLowerCase()}')),
                      ))
                  .toList(),
              onChanged: (v) => setState(() => _cropType = v!),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submit,
                child: Text(context.tr('next')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
