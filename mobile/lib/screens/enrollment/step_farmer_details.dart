import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../services/locale_service.dart';

class StepFarmerDetails extends StatefulWidget {
  final void Function(String name, String phone, String village, String crop) onNext;
  const StepFarmerDetails({super.key, required this.onNext});

  @override
  State<StepFarmerDetails> createState() => _StepFarmerDetailsState();
}

class _StepFarmerDetailsState extends State<StepFarmerDetails> {
  final _form = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _villageCtrl = TextEditingController();
  String _crop = 'maize';

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _villageCtrl.dispose();
    super.dispose();
  }

  String _normalizePhone(String v) {
    v = v.replaceAll(RegExp(r'[\s\-]'), '').replaceAll('+', '');
    if (v.startsWith('07') || v.startsWith('01')) return '254${v.substring(1)}';
    return v;
  }

  void _submit() {
    if (!_form.currentState!.validate()) return;
    widget.onNext(
      _nameCtrl.text.trim(),
      _normalizePhone(_phoneCtrl.text.trim()),
      _villageCtrl.text.trim(),
      _crop,
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocaleService>();
    final t = loc.t;

    return Form(
      key: _form,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        // Full name
        _label(t('Full Name', 'Jina Kamili')),
        TextFormField(
          controller: _nameCtrl,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(
            hintText: t('e.g. James Mwangi', 'mf. James Mwangi'),
            prefixIcon: const Icon(Icons.person_outline),
          ),
          validator: (v) {
            if (v == null || v.trim().length < 3) {
              return t('Enter your full name', 'Ingiza jina lako kamili');
            }
            return null;
          },
        ),
        const SizedBox(height: 16),

        // Phone
        _label(t('M-Pesa Phone Number', 'Nambari ya M-Pesa')),
        TextFormField(
          controller: _phoneCtrl,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            hintText: t('07XXXXXXXX', '07XXXXXXXX'),
            prefixIcon: const Icon(Icons.phone_outlined),
          ),
          validator: (v) {
            if (v == null) return t('Enter phone number', 'Ingiza nambari ya simu');
            final clean = v.replaceAll(RegExp(r'[\s\-+]'), '');
            if (!RegExp(r'^(07|01|2547|2541)\d{8}$').hasMatch(clean)) {
              return t('Enter a valid Kenyan number (07XXXXXXXX)', 'Ingiza nambari ya Kenya sahihi');
            }
            return null;
          },
        ),
        const SizedBox(height: 16),

        // Village
        _label(t('Village / Location', 'Kijiji / Mahali')),
        TextFormField(
          controller: _villageCtrl,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(
            hintText: t('e.g. Eldoret North', 'mf. Eldoret Kaskazini'),
            prefixIcon: const Icon(Icons.location_city_outlined),
          ),
          validator: (v) {
            if (v == null || v.trim().isEmpty) {
              return t('Enter your village', 'Ingiza kijiji chako');
            }
            return null;
          },
        ),
        const SizedBox(height: 16),

        // Crop type
        _label(t('Main Crop', 'Zao Kuu')),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: kBorder),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: kCrops.map((c) {
              final selected = _crop == c['key'];
              return GestureDetector(
                onTap: () => setState(() => _crop = c['key'] as String),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: selected ? kPrimaryBg : Colors.transparent,
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Row(children: [
                    Text(c['emoji'] as String, style: const TextStyle(fontSize: 20)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        loc.isSwahili ? (c['labelSw'] as String) : (c['label'] as String),
                        style: TextStyle(
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? kPrimary : kTextDark,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    Text(
                      'KES ${c['rate']}/acre',
                      style: TextStyle(
                        fontSize: 12,
                        color: selected ? kPrimary : kTextMid,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (selected)
                      const Icon(Icons.check_circle, color: kPrimary, size: 18)
                    else
                      const Icon(Icons.circle_outlined, color: kBorder, size: 18),
                  ]),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 28),

        ElevatedButton(
          onPressed: _submit,
          child: Text(t('Next: Draw Farm Boundary', 'Endelea: Chora Mipaka')),
        ),
      ]),
    );
  }

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
    child: Text(text, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: kTextDark)),
  );
}
