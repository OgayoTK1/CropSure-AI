import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';

import { listFarms, simulateDrought } from '@/api/client';
import { Badge, Button, Card, CardTitle, Muted } from '@/components/ui';
import { DEFAULT_ZOOM, KENYA_CENTER, PREMIUM_PER_ACRE_KES, COVERAGE_MULTIPLIER } from '@/config';
import type { Farm } from '@/types';
import { polygonCentroid } from '@/utils/centroid';

// ── Colored Leaflet DivIcons ─────────────────────────────────────────────────

function makeMarkerIcon(color: string, pulse = false): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div class="${pulse ? 'marker-dot-red' : ''}" style="width:14px;height:14px;background:${color};border-radius:50%;border:2.5px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.35);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

const icons = {
  healthy:    makeMarkerIcon('#1D9E75'),
  mild_stress: makeMarkerIcon('#F59E0B'),
  stress:     makeMarkerIcon('#DC2626', true),
  unknown:    makeMarkerIcon('#94A3B8'),
};

function farmIcon(health?: Farm['health_status']) {
  return icons[health ?? 'unknown'];
}

// ── Satellite countdown (Sentinel-2 5-day repeat cycle) ──────────────────────

function useSatelliteCountdown() {
  const [cd, setCd] = useState({ hours: 0, minutes: 0 });
  useEffect(() => {
    function compute() {
      const refMs = new Date('2024-01-01T06:00:00Z').getTime();
      const cycleMs = 5 * 24 * 60 * 60 * 1000;
      const pos = ((Date.now() - refMs) % cycleMs + cycleMs) % cycleMs;
      const rem = cycleMs - pos;
      setCd({
        hours: Math.floor(rem / 3_600_000),
        minutes: Math.floor((rem % 3_600_000) / 60_000),
      });
    }
    compute();
    const id = setInterval(compute, 60_000);
    return () => clearInterval(id);
  }, []);
  return cd;
}

// ── Relative time helper ─────────────────────────────────────────────────────

function timeAgo(t: TFunction, iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return t('time_ago_minutes', { n: Math.max(1, mins) });
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return t('time_ago_hours', { n: hrs });
  return t('time_ago_days', { n: Math.floor(hrs / 24) });
}

// ── Activity event builder ───────────────────────────────────────────────────

interface ActivityEvent {
  id: string;
  type: 'enrolled' | 'payout';
  icon: string;
  text: string;
  sub: string;
  time: string;
}

function buildFeed(farms: Farm[], t: TFunction): ActivityEvent[] {
  const events: ActivityEvent[] = [];
  for (const f of farms) {
    events.push({
      id: `enroll-${f.id}`,
      type: 'enrolled',
      icon: '🌱',
      text: t('activity_enrolled', { name: f.farmer_name, crop: f.crop_type, village: f.village }),
      sub: `${f.area_acres.toFixed(1)} acres`,
      time: f.created_at,
    });
    if (f.health_status === 'stress') {
      const est = Math.round(f.area_acres * PREMIUM_PER_ACRE_KES * COVERAGE_MULTIPLIER * 0.6);
      events.push({
        id: `payout-${f.id}`,
        type: 'payout',
        icon: '💸',
        text: t('activity_payout', { amount: est.toLocaleString(), name: f.farmer_name }),
        sub: f.crop_type,
        time: f.created_at,
      });
    }
  }
  return events.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()).slice(0, 15);
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { t } = useTranslation();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyFarmId, setBusyFarmId] = useState<string | null>(null);
  const [selectedSimFarm, setSelectedSimFarm] = useState('');
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const countdown = useSatelliteCountdown();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await listFarms();
      setFarms(data);
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error_network'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
    timerRef.current = setInterval(() => void refresh(), 30_000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refresh]);

  // Stats
  const stats = useMemo(() => {
    const total = farms.length;
    const active = farms.filter((f) => f.policy_status === 'active').length;
    const premiums = farms
      .filter((f) => f.policy_status === 'active')
      .reduce((s, f) => s + Math.round(f.area_acres * PREMIUM_PER_ACRE_KES), 0);
    const payouts = farms
      .filter((f) => f.health_status === 'stress')
      .reduce(
        (s, f) => s + Math.round(f.area_acres * PREMIUM_PER_ACRE_KES * COVERAGE_MULTIPLIER * 0.6),
        0,
      );
    return { total, active, premiums, payouts };
  }, [farms]);

  // Alert: most recently triggered stressed farm
  const alertFarm = useMemo(
    () => farms.find((f) => f.health_status === 'stress') ?? null,
    [farms],
  );

  // Map markers
  const markers = useMemo(
    () =>
      farms
        .map((f) => {
          const c = polygonCentroid(f.polygon_geojson);
          if (!c) return null;
          return { farm: f, lat: c.lat, lng: c.lng };
        })
        .filter(Boolean) as Array<{ farm: Farm; lat: number; lng: number }>,
    [farms],
  );

  // Activity feed
  const feed = useMemo(() => buildFeed(farms, t), [farms, t]);

  async function handleSimulate() {
    if (!selectedSimFarm) return;
    setBusyFarmId(selectedSimFarm);
    setError(null);
    try {
      await simulateDrought(selectedSimFarm);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error_network'));
    } finally {
      setBusyFarmId(null);
    }
  }

  function tone(health?: Farm['health_status']): 'good' | 'warn' | 'bad' | 'neutral' {
    if (health === 'healthy') return 'good';
    if (health === 'mild_stress') return 'warn';
    if (health === 'stress') return 'bad';
    return 'neutral';
  }

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('dashboard_title')}</h1>
          <Muted>
            {t('recent_activity')} · {t('refresh_in', { seconds: 30 })}
          </Muted>
        </div>
        <Button type="button" variant="secondary" onClick={() => void refresh()} disabled={loading}>
          {loading ? t('loading') : t('retry')}
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          {
            label: t('total_farms'),
            value: stats.total,
            icon: '🌾',
            color: 'text-slate-900',
          },
          {
            label: t('active_policies'),
            value: stats.active,
            icon: '✅',
            color: 'text-emerald-700',
          },
          {
            label: t('premiums_collected'),
            value: `KES ${stats.premiums.toLocaleString()}`,
            icon: '💰',
            color: 'text-blue-700',
          },
          {
            label: t('payouts_triggered'),
            value: `KES ${stats.payouts.toLocaleString()}`,
            icon: '💸',
            color: 'text-amber-700',
          },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>{s.icon}</span>
              {s.label}
            </div>
            <div className={`stat-card-value mt-1 text-2xl font-bold ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* ── Alert banner ── */}
      {alertFarm && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm">
          <span className="text-xl">🚨</span>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-red-800">
              {t('payout_alert_title')} — {alertFarm.farmer_name}
            </div>
            <div className="text-red-700">
              {alertFarm.crop_type} · {alertFarm.village} ·{' '}
              {t('alert_payout_sent', {
                amount: Math.round(
                  alertFarm.area_acres * PREMIUM_PER_ACRE_KES * COVERAGE_MULTIPLIER * 0.6,
                ).toLocaleString(),
                phone: alertFarm.phone_number,
              })}
            </div>
            <div className="mt-0.5 text-xs text-red-600">
              {timeAgo(t, alertFarm.created_at)}
            </div>
          </div>
          <Link to={`/farms/${alertFarm.id}`}>
            <Button type="button" variant="danger" className="shrink-0 text-xs px-3 py-1.5">
              {t('view_details')}
            </Button>
          </Link>
        </div>
      )}

      {/* ── Map + Activity feed ── */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Map (2/3 width on desktop) */}
        <div className="lg:col-span-2">
          <Card>
            <CardTitle>Kenya Farm Map</CardTitle>
            <div className="mt-3 h-[420px] overflow-hidden rounded-lg border border-slate-200">
              <MapContainer center={KENYA_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom>
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {markers.map((m) => (
                  <Marker key={m.farm.id} position={[m.lat, m.lng]} icon={farmIcon(m.farm.health_status)}>
                    <Popup minWidth={180}>
                      <div className="space-y-2 py-1">
                        <div className="font-semibold text-slate-900">{m.farm.farmer_name}</div>
                        <div className="text-xs text-slate-600">
                          {m.farm.crop_type} · {m.farm.village}
                        </div>
                        <div className="text-xs text-slate-600">
                          {m.farm.area_acres.toFixed(2)} acres
                        </div>
                        <Badge tone={tone(m.farm.health_status)}>
                          {m.farm.health_status ?? 'unknown'}
                        </Badge>
                        <div className="pt-1">
                          <Link
                            to={`/farms/${m.farm.id}`}
                            className="text-sm font-semibold text-primary hover:underline"
                          >
                            {t('view_details')}
                          </Link>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
            <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-primary" /> Healthy
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" /> Watch
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" /> Payout triggered
              </span>
            </div>
          </Card>
        </div>

        {/* Activity feed (1/3 width on desktop) */}
        <Card>
          <div className="flex items-center justify-between">
            <CardTitle>{t('activity_feed_title')}</CardTitle>
            <span className="text-xs text-slate-400">auto · 30s</span>
          </div>
          <div className="mt-3 space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {feed.length === 0 && (
              <Muted>{t('no_farms')}</Muted>
            )}
            {feed.map((ev) => (
              <div
                key={ev.id}
                className={[
                  'flex gap-2 rounded-lg p-2.5 text-sm',
                  ev.type === 'payout'
                    ? 'bg-red-50 border border-red-100'
                    : 'bg-slate-50 border border-slate-100',
                ].join(' ')}
              >
                <span className="mt-0.5 text-base shrink-0">{ev.icon}</span>
                <div className="min-w-0">
                  <div className="font-medium text-slate-800 leading-snug">{ev.text}</div>
                  <div className="text-xs text-slate-500">
                    {ev.sub} · {timeAgo(t, ev.time)}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </div>
        </Card>
      </div>

      {/* ── Farm list ── */}
      <Card>
        <CardTitle>{t('view_all_farms')}</CardTitle>
        <div className="mt-3 space-y-2">
          {loading && farms.length === 0 && <Muted>{t('loading')}</Muted>}
          {!loading && farms.length === 0 && <Muted>{t('no_farms')}</Muted>}
          {farms.map((f) => (
            <div
              key={f.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="font-semibold text-slate-900">{f.farmer_name}</div>
                <div className="text-xs text-slate-500">
                  {f.crop_type} · {f.village} · {f.area_acres.toFixed(2)} ac
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge tone={tone(f.health_status)}>{f.health_status ?? 'unknown'}</Badge>
                <Link to={`/farms/${f.id}`} className="text-sm font-semibold text-primary hover:underline">
                  {t('view_details')}
                </Link>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Bottom row: Demo panel + Satellite countdown ── */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Demo panel */}
        <Card>
          <CardTitle>🔴 {t('demo_simulate_title')}</CardTitle>
          <Muted>{t('simulate_drought')}</Muted>
          <div className="mt-3 space-y-3">
            <select
              value={selectedSimFarm}
              onChange={(e) => setSelectedSimFarm(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none"
            >
              <option value="">{t('demo_select_farm')}</option>
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.farmer_name} — {f.crop_type}, {f.village}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="danger"
              className="w-full"
              disabled={!selectedSimFarm || busyFarmId === selectedSimFarm}
              onClick={() => void handleSimulate()}
            >
              {busyFarmId === selectedSimFarm ? t('simulating') : t('trigger_now')}
            </Button>
          </div>
        </Card>

        {/* Satellite countdown */}
        <Card>
          <CardTitle>🛰️ {t('satellite_countdown_title')}</CardTitle>
          <div className="mt-4 flex items-end gap-3">
            <div className="text-5xl font-bold tabular-nums text-primary">
              {String(countdown.hours).padStart(2, '0')}
              <span className="text-2xl">h</span>
              {String(countdown.minutes).padStart(2, '0')}
              <span className="text-2xl">m</span>
            </div>
          </div>
          <Muted>{t('satellite_analysing')}</Muted>
          <div className="mt-3 space-y-1 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Sentinel-2 — 10m resolution · 5-day revisit
            </div>
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
              NDVI analysis triggers within 2 h of pass
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
