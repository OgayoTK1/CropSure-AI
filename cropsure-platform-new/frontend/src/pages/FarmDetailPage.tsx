import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { MapContainer, Polygon, TileLayer } from 'react-leaflet';
import { useTranslation } from 'react-i18next';

import { getFarm } from '@/api/client';
import NdviChart from '@/components/NdviChart';
import { Badge, Button, Card, CardTitle, Muted } from '@/components/ui';
import { DEFAULT_ZOOM } from '@/config';
import type { Farm, NdviReading } from '@/types';

// ── Stats computation ──────────────────────────────────────────────────────

interface FarmStats {
  baseline: number;
  currentNdvi: number;
  deviationPct: number;
  zScore: number;
}

function computeStats(history: NdviReading[], currentNdvi?: number): FarmStats {
  const values = history.map((r) => r.ndvi);
  if (values.length < 2) {
    const ndvi = currentNdvi ?? 0.6;
    return { baseline: 0.6, currentNdvi: ndvi, deviationPct: 0, zScore: 0 };
  }
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);
  const ndvi = currentNdvi ?? values[values.length - 1];
  const deviationPct = mean > 0 ? ((ndvi - mean) / mean) * 100 : 0;
  const zScore = std > 0 ? (ndvi - mean) / std : 0;
  return { baseline: mean, currentNdvi: ndvi, deviationPct, zScore };
}

// ── Health tone ────────────────────────────────────────────────────────────

function healthTone(health?: Farm['health_status']): 'good' | 'warn' | 'bad' | 'neutral' {
  if (health === 'healthy') return 'good';
  if (health === 'mild_stress') return 'warn';
  if (health === 'stress') return 'bad';
  return 'neutral';
}

function metricColor(health?: Farm['health_status']) {
  if (health === 'healthy') return 'text-emerald-700';
  if (health === 'mild_stress') return 'text-amber-700';
  if (health === 'stress') return 'text-red-700';
  return 'text-slate-700';
}

function metricBg(health?: Farm['health_status']) {
  if (health === 'healthy') return 'bg-emerald-50 border-emerald-200';
  if (health === 'mild_stress') return 'bg-amber-50 border-amber-200';
  if (health === 'stress') return 'bg-red-50 border-red-200';
  return 'bg-slate-50 border-slate-200';
}

// ── Component ──────────────────────────────────────────────────────────────

export default function FarmDetailPage() {
  const { t } = useTranslation();
  const { farmId } = useParams();
  const [farm, setFarm] = useState<Farm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!farmId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await getFarm(farmId);
        setFarm(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : t('error_network'));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [farmId, t]);

  const polygonPositions = useMemo(() => {
    if (!farm) return null;
    const ring = farm.polygon_geojson.coordinates?.[0] ?? [];
    return ring.map((c) => [c[1], c[0]] as [number, number]);
  }, [farm]);

  const center = useMemo<[number, number]>(() => {
    if (!polygonPositions || polygonPositions.length === 0) return [-1.286, 36.817];
    const lat = polygonPositions.reduce((s, p) => s + p[0], 0) / polygonPositions.length;
    const lng = polygonPositions.reduce((s, p) => s + p[1], 0) / polygonPositions.length;
    return [lat, lng];
  }, [polygonPositions]);

  const stats = useMemo<FarmStats | null>(() => {
    if (!farm) return null;
    return computeStats(farm.ndvi_history ?? [], farm.current_ndvi);
  }, [farm]);

  // Earliest payout trigger date for the red line on chart
  const triggerDate = useMemo(() => {
    if (!farm?.payouts || farm.payouts.length === 0) return null;
    const sorted = [...farm.payouts].sort(
      (a, b) => new Date(a.triggered_at).getTime() - new Date(b.triggered_at).getTime(),
    );
    return sorted[0].triggered_at.slice(0, 10);
  }, [farm]);

  // ── Loading / error states ─────────────────────────────────────────────
  if (loading) {
    return (
      <Card>
        <Muted>{t('loading')}</Muted>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="text-sm text-red-700">{error}</div>
        <div className="mt-3">
          <Link to="/dashboard" className="text-sm font-semibold text-primary hover:underline">
            {t('back_to_dashboard')}
          </Link>
        </div>
      </Card>
    );
  }

  if (!farm) {
    return (
      <Card>
        <Muted>Farm not found.</Muted>
      </Card>
    );
  }

  const tone = healthTone(farm.health_status);
  const col = metricColor(farm.health_status);
  const bg = metricBg(farm.health_status);

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{farm.farmer_name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge tone={tone}>{farm.health_status ?? 'unknown'}</Badge>
            <span className="text-sm text-slate-500">
              {farm.crop_type} · {farm.village}
            </span>
          </div>
        </div>
        <Link to="/dashboard">
          <Button type="button" variant="secondary">{t('back_to_dashboard')}</Button>
        </Link>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Current NDVI */}
        <div className={`rounded-xl border p-4 ${bg}`}>
          <div className="text-xs text-slate-500">{t('current_ndvi')}</div>
          <div className={`mt-1 text-2xl font-bold ${col}`}>
            {stats ? stats.currentNdvi.toFixed(2) : '—'}
          </div>
          {stats && (
            <div className="mt-0.5 text-xs text-slate-500">
              {t('baseline_comparison', { value: stats.baseline.toFixed(2) })}
            </div>
          )}
        </div>

        {/* NDVI Deviation */}
        <div className={`rounded-xl border p-4 ${bg}`}>
          <div className="text-xs text-slate-500">{t('ndvi_deviation')}</div>
          <div className={`mt-1 text-2xl font-bold ${col}`}>
            {stats ? `${stats.deviationPct >= 0 ? '+' : ''}${stats.deviationPct.toFixed(1)}%` : '—'}
          </div>
          <div className="mt-0.5 text-xs text-slate-500">
            {t('z_score')}: {stats ? stats.zScore.toFixed(2) : '—'}
          </div>
        </div>

        {/* Total Coverage */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-xs text-slate-500">{t('total_coverage')}</div>
          <div className="mt-1 text-2xl font-bold text-emerald-700">
            {farm.policy ? `KES ${farm.policy.coverage_amount_kes.toLocaleString()}` : '—'}
          </div>
          <div className="mt-0.5 text-xs text-slate-500">{t('policy_status')}</div>
        </div>

        {/* Policy status */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs text-slate-500">{t('policy_status')}</div>
          <div className="mt-1">
            <Badge
              tone={
                farm.policy?.status === 'active'
                  ? 'good'
                  : farm.policy?.status === 'expired'
                    ? 'neutral'
                    : 'warn'
              }
            >
              {farm.policy?.status ?? farm.policy_status ?? 'n/a'}
            </Badge>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {t('enrolled_on')} {new Date(farm.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {/* ── Map + Overview ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Farm boundary map */}
        <Card>
          <CardTitle>Boundary Map</CardTitle>
          <div className="mt-3 h-80 overflow-hidden rounded-lg border border-slate-200">
            <MapContainer center={center} zoom={DEFAULT_ZOOM + 3} scrollWheelZoom>
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {polygonPositions && polygonPositions.length >= 3 ? (
                <Polygon
                  positions={polygonPositions}
                  pathOptions={{
                    color: tone === 'bad' ? '#DC2626' : tone === 'warn' ? '#F59E0B' : '#1D9E75',
                    fillOpacity: 0.15,
                    weight: 2,
                  }}
                />
              ) : null}
            </MapContainer>
          </div>
        </Card>

        {/* Farm details */}
        <Card>
          <CardTitle>Overview</CardTitle>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-slate-500">{t('phone')}</div>
              <div className="font-semibold">{farm.phone_number}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('village')}</div>
              <div className="font-semibold">{farm.village}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('crop')}</div>
              <div className="font-semibold">{farm.crop_type}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">{t('area_acres', { acres: '' })}</div>
              <div className="font-semibold">{farm.area_acres.toFixed(2)} acres</div>
            </div>
            {farm.policy && (
              <>
                <div>
                  <div className="text-xs text-slate-500">{t('premium')}</div>
                  <div className="font-semibold">KES {farm.policy.premium_paid_kes.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">{t('season_period')}</div>
                  <div className="font-semibold text-xs">
                    {farm.policy.season_start} – {farm.policy.season_end}
                  </div>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* ── NDVI Chart + Payout history ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* NDVI Chart */}
        <Card>
          <CardTitle>{t('ndvi_chart_title')}</CardTitle>
          {farm.ndvi_history && farm.ndvi_history.length > 0 ? (
            <>
              <div className="mt-3">
                <NdviChart readings={farm.ndvi_history} triggerDate={triggerDate} />
              </div>
              {triggerDate && (
                <div className="mt-2 flex items-center gap-2 text-xs text-red-600">
                  <span className="inline-block h-0.5 w-6 border-t-2 border-dashed border-red-500" />
                  Drought trigger fired on {triggerDate}
                </div>
              )}
              {!triggerDate && (
                <div className="mt-2 flex items-center gap-2 text-xs text-emerald-600">
                  <span>✓</span>
                  {t('no_stress_detected')}
                </div>
              )}
            </>
          ) : (
            <div className="mt-3 text-sm text-slate-500">No NDVI readings yet.</div>
          )}
        </Card>

        {/* Payout history */}
        <Card>
          <CardTitle>{t('payout_history')}</CardTitle>
          <div className="mt-3 space-y-3">
            {!farm.payouts || farm.payouts.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <span className="text-3xl">🌿</span>
                <Muted>{t('no_payouts')}</Muted>
              </div>
            ) : (
              farm.payouts.map((p) => (
                <div key={p.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-base font-bold text-slate-900">
                      KES {p.amount_kes.toLocaleString()}
                    </div>
                    <Badge
                      tone={
                        p.status === 'completed'
                          ? 'good'
                          : p.status === 'failed'
                            ? 'bad'
                            : 'warn'
                      }
                    >
                      {p.status}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {p.stress_type} · {new Date(p.triggered_at).toLocaleDateString()}
                  </div>
                  {p.explanation_en && (
                    <div className="mt-2 text-sm text-slate-700">{p.explanation_en}</div>
                  )}
                  {p.explanation_sw && (
                    <div className="mt-1 text-sm text-slate-600 italic">{p.explanation_sw}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
