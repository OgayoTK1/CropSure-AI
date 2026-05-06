import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import BoundaryMap from '@/components/BoundaryMap';
import { Button, Card, CardTitle, Muted } from '@/components/ui';
import { COVERAGE_MULTIPLIER, PREMIUM_PER_ACRE_KES } from '@/config';
import { enrollFarm } from '@/api/client';
import type { EnrollRequest, GeoJSONPolygon } from '@/types';
import { polygonAreaMeters2, meters2ToAcres } from '@/utils/area';

type Step = 1 | 2 | 3;

export default function EnrollPage() {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>(1);

  const [farmerName, setFarmerName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [village, setVillage] = useState('');
  const [cropType, setCropType] = useState('Maize');

  const [polygon, setPolygon] = useState<GeoJSONPolygon | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<{ policyId: string; phone: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const acresEstimate = useMemo(() => {
    if (!polygon) return 0;
    return meters2ToAcres(polygonAreaMeters2(polygon));
  }, [polygon]);

  const premiumEstimate = useMemo(() => {
    return Math.max(0, Math.round(acresEstimate * PREMIUM_PER_ACRE_KES));
  }, [acresEstimate]);

  const coverageEstimate = useMemo(() => {
    return Math.max(0, Math.round(premiumEstimate * COVERAGE_MULTIPLIER));
  }, [premiumEstimate]);

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
      const res = await enrollFarm(payload as EnrollRequest);
      setSuccess({ policyId: res.policy_id, phone: phoneNumber });
      setStep(1);
      setFarmerName('');
      setPhoneNumber('');
      setVillage('');
      setCropType('Maize');
      setPolygon(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : t('error_network');
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <Card>
        <CardTitle>{t('success_title')}</CardTitle>
        <div className="mt-2 text-sm text-slate-700">
          {t('success_body', { phone: success.phone, policy: success.policyId })}
        </div>
        <div className="mt-4">
          <Button type="button" onClick={() => setSuccess(null)}>
            {t('view_all_farms')}
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t('nav_enroll')}</h1>
        <Muted>{t('tagline')}</Muted>
      </div>

      {error ? (
        <Card>
          <div className="text-sm text-red-700">{error}</div>
        </Card>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <CardTitle>
              {step === 1 ? t('step1_title') : step === 2 ? t('step2_title') : t('step3_title')}
            </CardTitle>
            <div className="text-xs text-slate-500">Step {step}/3</div>
          </div>

          {step === 1 ? (
            <div className="mt-4 space-y-3">
              <label className="block">
                <div className="text-sm font-medium text-slate-700">{t('field_name')}</div>
                <input
                  value={farmerName}
                  onChange={(e) => setFarmerName(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  placeholder="Jane Wanjiku"
                />
              </label>

              <label className="block">
                <div className="text-sm font-medium text-slate-700">{t('field_phone')}</div>
                <input
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  placeholder="07XXXXXXXX"
                />
              </label>

              <label className="block">
                <div className="text-sm font-medium text-slate-700">{t('field_village')}</div>
                <input
                  value={village}
                  onChange={(e) => setVillage(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  placeholder="Kikuyu"
                />
              </label>

              <label className="block">
                <div className="text-sm font-medium text-slate-700">{t('field_crop')}</div>
                <select
                  value={cropType}
                  onChange={(e) => setCropType(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                >
                  {['Maize', 'Beans', 'Wheat', 'Rice', 'Sorghum', 'Millet', 'Cassava', 'Irish Potatoes'].map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>

              <div className="mt-4 flex justify-end">
                <Button
                  type="button"
                  onClick={() => setStep(2)}
                  disabled={!farmerName || !phoneNumber || !village || !cropType}
                >
                  {t('next')}
                </Button>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="mt-4 space-y-3">
              <Muted>{t('map_click_hint')}</Muted>
              <div className="text-sm text-slate-700">
                {t('area_display', { acres: acresEstimate.toFixed(2) })}
              </div>
              <div className="flex justify-between">
                <Button type="button" variant="secondary" onClick={() => setStep(1)}>
                  {t('back')}
                </Button>
                <Button type="button" onClick={() => setStep(3)} disabled={!polygon}>
                  {t('confirm_boundary')}
                </Button>
              </div>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-sm font-semibold text-slate-900">{t('payment_summary')}</div>
                <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-lg border border-slate-200 p-3">
                    <div className="text-slate-500">{t('premium')}</div>
                    <div className="text-lg font-bold">KES {premiumEstimate}</div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-3">
                    <div className="text-slate-500">{t('coverage')}</div>
                    <div className="text-lg font-bold">KES {coverageEstimate}</div>
                  </div>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  Estimates are based on your drawn boundary. Final premium/coverage is confirmed by the backend.
                </div>
              </div>

              <div className="flex justify-between">
                <Button type="button" variant="secondary" onClick={() => setStep(2)}>
                  {t('back')}
                </Button>
                <Button type="button" onClick={submit} disabled={submitting || !polygon}>
                  {submitting ? t('enrolling') : t('pay_button', { amount: premiumEstimate })}
                </Button>
              </div>
            </div>
          ) : null}
        </Card>

        <div className="space-y-6">
          {step === 2 ? (
            <BoundaryMap
              value={polygon}
              onChange={(poly) => {
                setPolygon(poly);
              }}
            />
          ) : (
            <Card>
              <CardTitle>{t('step2_title')}</CardTitle>
              <Muted>Go to Step 2 to draw the farm boundary.</Muted>
            </Card>
          )}

          <Card>
            <CardTitle>{t('payment_summary')}</CardTitle>
            <div className="mt-2 text-sm text-slate-700">
              Premium: <span className="font-semibold">KES {premiumEstimate}</span>
            </div>
            <div className="mt-1 text-sm text-slate-700">
              Coverage: <span className="font-semibold">KES {coverageEstimate}</span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
