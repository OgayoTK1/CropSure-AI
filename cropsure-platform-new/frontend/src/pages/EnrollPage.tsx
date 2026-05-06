import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, Polygon, TileLayer } from 'react-leaflet';
import { useTranslation } from 'react-i18next';
import { format, addDays } from 'date-fns';

import BoundaryMap from '@/components/BoundaryMap';
import LanguageToggle from '@/components/LanguageToggle';
import { Button } from '@/components/ui';
import { COVERAGE_MULTIPLIER, PREMIUM_PER_ACRE_KES } from '@/config';
import { enrollFarm } from '@/api/client';
import type { EnrollRequest, EnrollResponse, GeoJSONPolygon } from '@/types';
import { polygonAreaMeters2, meters2ToAcres } from '@/utils/area';
import { polygonCentroid } from '@/utils/centroid';

type Step = 1 | 2 | 3;

interface SuccessData {
  policyId: string;
  farmerName: string;
  phone: string;
  cropType: string;
  area: number;
  premium: number;
  coverage: number;
  polygon: GeoJSONPolygon;
  seasonStart: string;
  seasonEnd: string;
}

const CROPS = [
  { value: 'Maize', labelKey: 'crop_maize' },
  { value: 'Beans', labelKey: 'crop_beans' },
  { value: 'Tea', labelKey: 'crop_tea' },
  { value: 'Wheat', labelKey: 'crop_wheat' },
  { value: 'Sorghum', labelKey: 'crop_sorghum' },
  { value: 'Coffee', labelKey: 'crop_coffee' },
  { value: 'Cassava', labelKey: 'crop_cassava' },
];

function StepDots({ current }: { current: Step }) {
  return (
    <div className="flex items-center justify-center gap-1 py-2">
      {([1, 2, 3] as Step[]).map((s, i) => (
        <div key={s} className="flex items-center gap-1">
          {i > 0 && (
            <div
              className={`h-0.5 w-6 rounded-full transition-all ${
                s <= current ? 'bg-primary' : 'bg-slate-200'
              }`}
            />
          )}
          <div
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-all ${
              s < current
                ? 'bg-primary text-white'
                : s === current
                  ? 'bg-primary text-white ring-4 ring-primary/20'
                  : 'bg-slate-100 text-slate-400'
            }`}
          >
            {s < current ? '✓' : s}
          </div>
        </div>
      ))}
    </div>
  );
}

function InputField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-sm font-medium text-slate-700">{label}</div>
      {children}
    </label>
  );
}

export default function EnrollPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>(1);

  const [farmerName, setFarmerName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [village, setVillage] = useState('');
  const [cropType, setCropType] = useState('Maize');

  const [polygon, setPolygon] = useState<GeoJSONPolygon | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<SuccessData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const acresEstimate = useMemo(() => {
    if (!polygon) return 0;
    return meters2ToAcres(polygonAreaMeters2(polygon));
  }, [polygon]);

  const premiumEstimate = useMemo(
    () => Math.max(0, Math.round(acresEstimate * PREMIUM_PER_ACRE_KES)),
    [acresEstimate],
  );

  const coverageEstimate = useMemo(
    () => Math.max(0, Math.round(premiumEstimate * COVERAGE_MULTIPLIER)),
    [premiumEstimate],
  );

  const seasonStart = useMemo(() => format(new Date(), 'dd MMM yyyy'), []);
  const seasonEnd = useMemo(() => format(addDays(new Date(), 180), 'dd MMM yyyy'), []);

  const step1Valid = farmerName.trim() && phoneNumber.trim() && village.trim() && cropType;

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      if (!polygon) throw new Error('Please confirm the farm boundary.');
      const payload: EnrollRequest = {
        farmer_name: farmerName,
        phone_number: phoneNumber,
        village,
        crop_type: cropType,
        polygon_geojson: polygon,
      };
      const res: EnrollResponse = await enrollFarm(payload);
      setSuccess({
        policyId: res.policy_id,
        farmerName: res.farmer_name,
        phone: phoneNumber,
        cropType,
        area: res.area_acres,
        premium: res.premium_amount_kes,
        coverage: res.coverage_amount_kes,
        polygon,
        seasonStart: res.season_start,
        seasonEnd: res.season_end,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : t('error_network');
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  // ── Success screen ────────────────────────────────────────────────────
  if (success) {
    const center = polygonCentroid(success.polygon);
    const positions = success.polygon.coordinates[0].map(
      (c) => [c[1], c[0]] as [number, number],
    );
    return (
      <div className="mx-auto max-w-md space-y-5 px-4 py-6">
        {/* Green checkmark */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-3xl">
            ✅
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{t('success_title')}</h1>
          <p className="text-sm text-slate-600">{t('watched_from_space')}</p>
        </div>

        {/* Policy card */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-slate-500">{t('policy_number')}</div>
              <div className="font-mono font-semibold text-primary">
                {success.policyId.slice(0, 12).toUpperCase()}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('field_name')}</div>
              <div className="font-semibold">{success.farmerName}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('farm_area_label')}</div>
              <div className="font-semibold">{success.area.toFixed(2)} acres</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('field_crop')}</div>
              <div className="font-semibold">{success.cropType}</div>
            </div>
            <div className="col-span-2">
              <div className="text-xs text-slate-500">{t('season_period')}</div>
              <div className="font-semibold">
                {success.seasonStart} – {success.seasonEnd}
              </div>
            </div>
          </div>

          {/* Coverage badge */}
          <div className="mt-4 flex items-center gap-3 rounded-lg bg-emerald-50 p-3">
            <span className="text-2xl">🛡️</span>
            <div>
              <div className="text-xs text-emerald-700">{t('coverage')}</div>
              <div className="text-lg font-bold text-emerald-800">
                KES {success.coverage.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="mt-3 rounded-lg bg-blue-50 p-3 text-xs text-blue-700">
            {t('mpesa_prompt_sent', { phone: success.phone })}
          </div>
        </div>

        {/* Mini map */}
        {center && (
          <div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm">
            <div className="h-44">
              <MapContainer
                center={[center.lat, center.lng]}
                zoom={14}
                zoomControl={false}
                dragging={false}
                scrollWheelZoom={false}
                touchZoom={false}
                doubleClickZoom={false}
                attributionControl={false}
              >
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Polygon
                  positions={positions}
                  pathOptions={{
                    color: '#1D9E75',
                    fillColor: '#1D9E75',
                    fillOpacity: 0.2,
                    weight: 2,
                  }}
                />
              </MapContainer>
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex flex-col gap-2">
          <Button type="button" className="w-full" onClick={() => navigate('/dashboard')}>
            {t('go_to_dashboard')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="w-full"
            onClick={() => {
              setSuccess(null);
              setStep(1);
              setFarmerName('');
              setPhoneNumber('');
              setVillage('');
              setCropType('Maize');
              setPolygon(null);
            }}
          >
            {t('enroll_another')}
          </Button>
        </div>
      </div>
    );
  }

  // ── Enrollment wizard ─────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-lg space-y-4 px-4 py-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-900">{t('nav_enroll')}</h1>
        <LanguageToggle />
      </div>

      {/* Step dots */}
      <StepDots current={step} />

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ── Step 1: Farmer Details ── */}
      {step === 1 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-slate-900">{t('step1_title')}</h2>
          <div className="space-y-3">
            <InputField label={t('field_name')}>
              <input
                value={farmerName}
                onChange={(e) => setFarmerName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="Jane Wanjiku"
                autoComplete="name"
              />
            </InputField>

            <InputField label={t('field_phone')}>
              <input
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="07XXXXXXXX"
                type="tel"
                autoComplete="tel"
              />
            </InputField>

            <InputField label={t('field_crop')}>
              <select
                value={cropType}
                onChange={(e) => setCropType(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {CROPS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {t(c.labelKey)}
                  </option>
                ))}
              </select>
            </InputField>

            <InputField label={t('field_village')}>
              <input
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="Kikuyu"
                autoComplete="address-level2"
              />
            </InputField>

            <Button
              type="button"
              className="mt-2 w-full"
              disabled={!step1Valid}
              onClick={() => setStep(2)}
            >
              {t('next')}
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2: Farm Boundary ── */}
      {step === 2 && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-3 text-base font-semibold text-slate-900">{t('step2_title')}</h2>
            <BoundaryMap value={polygon} onChange={setPolygon} />
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setStep(1)}
            >
              {t('back')}
            </Button>
            <Button
              type="button"
              className="flex-1"
              disabled={!polygon}
              onClick={() => setStep(3)}
            >
              {t('confirm_boundary')}
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 3: Payment Summary ── */}
      {step === 3 && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-slate-900">{t('step3_title')}</h2>

            {/* Transparent breakdown */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between border-b border-slate-100 py-1.5">
                <span className="text-slate-500">{t('farm_area_label')}</span>
                <span className="font-semibold">{acresEstimate.toFixed(2)} acres</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 py-1.5">
                <span className="text-slate-500">{t('field_crop')}</span>
                <span className="font-semibold">{cropType}</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 py-1.5">
                <span className="text-slate-500">{t('season_period')}</span>
                <span className="font-semibold">
                  {seasonStart} – {seasonEnd}
                </span>
              </div>
              <div className="flex justify-between border-b border-slate-100 py-1.5">
                <span className="text-slate-500">{t('rate_per_acre')}</span>
                <span className="font-semibold">KES {PREMIUM_PER_ACRE_KES}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="font-semibold text-slate-800">{t('premium')}</span>
                <span className="text-lg font-bold text-primary">
                  KES {premiumEstimate.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Coverage shield badge */}
            <div className="mt-4 flex items-center gap-3 rounded-xl bg-emerald-50 border border-emerald-200 p-4">
              <span className="text-3xl">🛡️</span>
              <div>
                <div className="text-xs font-medium text-emerald-700">{t('coverage')}</div>
                <div className="text-xl font-bold text-emerald-800">
                  KES {coverageEstimate.toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setStep(2)}
            >
              {t('back')}
            </Button>
            <Button
              type="button"
              className="flex-1"
              disabled={submitting || !polygon}
              onClick={() => void submit()}
            >
              {submitting ? t('enrolling') : t('pay_button', { amount: premiumEstimate.toLocaleString() })}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
