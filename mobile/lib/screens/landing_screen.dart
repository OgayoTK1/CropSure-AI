import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../core/theme.dart';
import '../services/locale_service.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocaleService>();
    final t = loc.t;

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Hero ──────────────────────────────────────────────────────
              _Hero(t: t, loc: loc),

              // ── Stats row ─────────────────────────────────────────────────
              _StatsRow(),

              // ── How it works ──────────────────────────────────────────────
              _Section(
                label: t('The Process', 'Mchakato'),
                title: t('From GPS walk to M-Pesa payout', 'Kutoka GPS hadi M-Pesa'),
                child: Column(
                  children: [
                    _Step(
                      num: '01', badge: t('Enrollment', 'Uandikishaji'),
                      title: t('Walk your farm boundary', 'Tembea mipaka ya shamba'),
                      desc: t(
                        'Open the app. Press Walk Boundary and walk your farm perimeter — GPS traces automatically.',
                        'Fungua programu. Bonyeza Tembea Mipaka uende kando ya shamba lako — GPS itafuatilia otomatiki.',
                      ),
                    ),
                    _Step(
                      num: '02', badge: t('Payment', 'Malipo'),
                      title: t('Pay premium via M-Pesa', 'Lipa bima kwa M-Pesa'),
                      desc: t(
                        'We calculate your premium at KES 300/acre. An STK Push arrives — enter your PIN and you\'re covered.',
                        'Tunahesabu bima yako kwa KES 300/ekari. Ombi la M-Pesa linafika — ingiza PIN yako na uko salama.',
                      ),
                    ),
                    _Step(
                      num: '03', badge: t('Monitoring', 'Ufuatiliaji'),
                      title: t('Satellite monitors every 5 days', 'Setilaiti inafuatilia kila siku 5'),
                      desc: t(
                        'ESA Sentinel-2 passes over your exact farm and measures crop health vs your personal baseline.',
                        'Setilaiti ya ESA Sentinel-2 inapita juu ya shamba lako halisi na kupima afya ya mazao.',
                      ),
                    ),
                    _Step(
                      num: '04', badge: t('Payout', 'Malipo'),
                      title: t('Automatic M-Pesa payout <24h', 'Malipo ya M-Pesa < masaa 24'),
                      desc: t(
                        'Stress detected? M-Pesa fires automatically in under 24 hours. SMS + WhatsApp explains everything.',
                        'Msongo unagunduliwa? M-Pesa inatumwa otomatiki ndani ya masaa 24. SMS + WhatsApp inaeleza kila kitu.',
                      ),
                    ),
                  ],
                ),
              ),

              // ── Key features ──────────────────────────────────────────────
              _Section(
                label: t('Why CropSure', 'Kwa Nini CropSure'),
                title: t('Built to fix what others left behind', 'Imejengwa kutatua tatizo ambalo bado halijatatuliwa'),
                child: Wrap(
                  spacing: 12, runSpacing: 12,
                  children: [
                    _FeatureChip(
                      icon: Icons.satellite_alt,
                      text: t('10m resolution', 'Azimio la 10m'),
                      color: Colors.blue,
                    ),
                    _FeatureChip(
                      icon: Icons.bolt,
                      text: t('<24h payout', 'Malipo <masaa 24'),
                      color: kAmber,
                    ),
                    _FeatureChip(
                      icon: Icons.shield_outlined,
                      text: t('Per-farm baseline', 'Msingi wa shamba'),
                      color: kPrimary,
                    ),
                    _FeatureChip(
                      icon: Icons.visibility_outlined,
                      text: t('Full transparency', 'Uwazi kamili'),
                      color: Colors.purple,
                    ),
                    _FeatureChip(
                      icon: Icons.phone_android,
                      text: t('Any phone + USSD', 'Simu yoyote + USSD'),
                      color: Colors.teal,
                    ),
                    _FeatureChip(
                      icon: Icons.cloud_off,
                      text: t('SAR cloud bypass', 'SAR kupita mawingu'),
                      color: Colors.indigo,
                    ),
                  ],
                ),
              ),

              // ── Pricing ───────────────────────────────────────────────────
              _Section(
                label: t('Simple Pricing', 'Bei Rahisi'),
                title: t('Pay per acre, per season', 'Lipa kwa ekari, kwa msimu'),
                child: Column(
                  children: [
                    _PriceRow(crop: 'Maize / Mahindi', rate: 300, coverage: 3000),
                    _PriceRow(crop: 'Beans / Maharagwe', rate: 250, coverage: 2500),
                    _PriceRow(crop: 'Tea / Chai', rate: 400, coverage: 4000),
                    _PriceRow(crop: 'Cassava / Muhogo', rate: 200, coverage: 2000),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: kPrimaryBg,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        t(
                          'Example: 2-acre maize farm → KES 600 premium → KES 6,000 coverage',
                          'Mfano: Shamba la ekari 2 (mahindi) → KES 600 bima → KES 6,000 fidia',
                        ),
                        style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600, color: kPrimaryDark,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ),
              ),

              // ── CTA ───────────────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => context.go('/enroll'),
                      icon: const Icon(Icons.location_on, size: 20),
                      label: Text(t('Walk My Boundary', 'Tembea Mipaka Yangu')),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 18),
                        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: () => context.go('/dashboard'),
                      icon: const Icon(Icons.bar_chart, size: 20),
                      label: Text(t('View Dashboard', 'Angalia Dashibodi')),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      t('No smartphone? Dial *384# on any phone', 'Huna simu ya kisasa? Piga *384# kwenye simu yoyote'),
                      style: const TextStyle(color: kTextMid, fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Hero section ──────────────────────────────────────────────────────────────

class _Hero extends StatelessWidget {
  final String Function(String en, String sw) t;
  final LocaleService loc;
  const _Hero({required this.t, required this.loc});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0d4f35), kPrimary, kPrimaryLight],
        ),
      ),
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top bar: logo + lang toggle
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.eco, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 10),
                const Text(
                  'CropSure AI',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18),
                ),
              ]),
              GestureDetector(
                onTap: loc.toggle,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.white38),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    loc.isSwahili ? '🇬🇧 English' : '🇰🇪 Kiswahili',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),

          // Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white24),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(width: 6, height: 6,
                decoration: const BoxDecoration(color: Color(0xFF86EFAC), shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Text(
                t('IEEE Africa Summit 2026 · Climate Track', 'IEEE Afrika Summit 2026 · Hali ya Hewa'),
                style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600),
              ),
            ]),
          ),
          const SizedBox(height: 18),

          // Headline
          Text(
            t('Farm insurance that actually insures', 'Bima ya mazao inayolinda'),
            style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900, height: 1.2),
          ),
          Text(
            t('your farm.', 'shamba lako halisi.'),
            style: const TextStyle(color: Color(0xFFA7F3D0), fontSize: 28, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 14),
          Text(
            t(
              'Sentinel-2 satellites monitor your exact GPS-traced plot every 5 days. When crop stress is detected, M-Pesa fires automatically within 24 hours.',
              'Setilaiti za Sentinel-2 zinafuatilia shamba lako halisi kila siku 5. Msongo unapogunduliwa, M-Pesa inatumwa ndani ya masaa 24.',
            ),
            style: TextStyle(color: Colors.white.withOpacity(0.85), fontSize: 14, height: 1.6),
          ),
        ],
      ),
    );
  }
}

// ── Stats row ────────────────────────────────────────────────────────────────

class _StatsRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    const stats = [
      {'v': '10m', 'l': 'Resolution'},
      {'v': '5-day', 'l': 'Monitoring'},
      {'v': '<24h', 'l': 'Payout'},
      {'v': '3%', 'l': 'Industry avg'},
    ];
    return Container(
      color: const Color(0xFF111827),
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      child: Row(
        children: stats.map((s) => Expanded(
          child: Column(children: [
            Text(s['v']!, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
            Text(s['l']!, style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 11)),
          ]),
        )).toList(),
      ),
    );
  }
}

// ── Section wrapper ───────────────────────────────────────────────────────────

class _Section extends StatelessWidget {
  final String label, title;
  final Widget child;
  const _Section({required this.label, required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: kPrimaryBg, borderRadius: BorderRadius.circular(20),
          ),
          child: Text(label, style: const TextStyle(color: kPrimary, fontSize: 11, fontWeight: FontWeight.w700)),
        ),
        const SizedBox(height: 8),
        Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: kTextDark, height: 1.25)),
        const SizedBox(height: 16),
        child,
      ]),
    );
  }
}

// ── Step card ─────────────────────────────────────────────────────────────────

class _Step extends StatelessWidget {
  final String num, badge, title, desc;
  const _Step({required this.num, required this.badge, required this.title, required this.desc});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Number
        Text(num, style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Color(0xFFE5E7EB), height: 1)),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: kPrimaryBg, borderRadius: BorderRadius.circular(8)),
            child: Text(badge, style: const TextStyle(color: kPrimary, fontSize: 10, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 6),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: kTextDark)),
          const SizedBox(height: 4),
          Text(desc, style: const TextStyle(color: kTextMid, fontSize: 12, height: 1.5)),
        ])),
      ]),
    );
  }
}

// ── Feature chip ─────────────────────────────────────────────────────────────

class _FeatureChip extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;
  const _FeatureChip({required this.icon, required this.text, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

// ── Price row ─────────────────────────────────────────────────────────────────

class _PriceRow extends StatelessWidget {
  final String crop;
  final int rate, coverage;
  const _PriceRow({required this.crop, required this.rate, required this.coverage});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kBorder),
      ),
      child: Row(children: [
        Expanded(child: Text(crop, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
        Text('KES $rate/acre', style: const TextStyle(fontWeight: FontWeight.w700, color: kTextDark, fontSize: 13)),
        const SizedBox(width: 12),
        Text('→ KES $coverage', style: const TextStyle(color: kPrimary, fontWeight: FontWeight.w700, fontSize: 12)),
      ]),
    );
  }
}
