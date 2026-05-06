import { useEffect, useMemo, useState } from 'react';
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { listFarms, runMonitoring, simulateDrought } from '@/api/client';
import { Button, Card, CardTitle, Muted, Badge } from '@/components/ui';
import { DEFAULT_ZOOM, KENYA_CENTER } from '@/config';
import type { Farm } from '@/types';
import { polygonCentroid } from '@/utils/centroid';

function toneForHealth(health?: Farm['health_status']): 'good' | 'warn' | 'bad' | 'neutral' {
  if (health === 'healthy') return 'good';
  if (health === 'mild_stress') return 'warn';
  if (health === 'stress') return 'bad';
  return 'neutral';
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyFarmId, setBusyFarmId] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    setLoading(true);
    try {
      const data = await listFarms();
      setFarms(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error_network'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const stats = useMemo(() => {
    const total = farms.length;
    const active = farms.filter((f) => f.policy_status === 'active').length;
    const stressed = farms.filter((f) => f.health_status === 'stress').length;
    return { total, active, stressed };
  }, [farms]);

  const markers = useMemo(() => {
    return farms
      .map((f) => {
        const c = polygonCentroid(f.polygon_geojson);
        if (!c) return null;
        return { farm: f, lat: c.lat, lng: c.lng };
      })
      .filter(Boolean) as Array<{ farm: Farm; lat: number; lng: number }>;
  }, [farms]);

  async function handleRunMonitoring() {
    try {
      setError(null);
      await runMonitoring();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error_network'));
    }
  }

  async function handleSimulateDrought(farmId: string) {
    try {
      setBusyFarmId(farmId);
      setError(null);
      const res = await simulateDrought(farmId);
      console.log('simulateDrought result', res);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error_network'));
    } finally {
      setBusyFarmId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('dashboard_title')}</h1>
          <Muted>{t('recent_activity')}</Muted>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" onClick={() => void refresh()}>
            {t('retry')}
          </Button>
          <Button type="button" onClick={() => void handleRunMonitoring()}>
            Run Monitoring
          </Button>
        </div>
      </div>

      {error ? (
        <Card>
          <div className="text-sm text-red-700">{error}</div>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-xs text-slate-500">{t('total_farms')}</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{stats.total}</div>
        </Card>
        <Card>
          <div className="text-xs text-slate-500">{t('active_policies')}</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{stats.active}</div>
        </Card>
        <Card>
          <div className="text-xs text-slate-500">{t('farms_stressed')}</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{stats.stressed}</div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>Map</CardTitle>
          <div className="mt-3 h-[420px] overflow-hidden rounded-lg border border-slate-200">
            <MapContainer center={KENYA_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom>
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {markers.map((m) => (
                <Marker key={m.farm.id} position={[m.lat, m.lng]}>
                  <Popup>
                    <div className="space-y-2">
                      <div className="font-semibold text-slate-900">{m.farm.farmer_name}</div>
                      <div className="text-xs text-slate-600">
                        {m.farm.crop_type} • {m.farm.village}
                      </div>
                      <div>
                        <Badge tone={toneForHealth(m.farm.health_status)}>
                          {m.farm.health_status ?? 'unknown'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/farms/${m.farm.id}`}
                          className="text-sm font-semibold text-primary hover:underline"
                        >
                          {t('view_details')}
                        </Link>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => void handleSimulateDrought(m.farm.id)}
                          disabled={busyFarmId === m.farm.id}
                        >
                          {busyFarmId === m.farm.id ? t('simulating') : t('simulate_drought')}
                        </Button>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
          <div className="mt-2 text-xs text-slate-500">{t('select_farm_prompt')}</div>
        </Card>

        <Card>
          <CardTitle>{t('view_all_farms')}</CardTitle>
          <div className="mt-3">
            {loading ? <div className="text-sm text-slate-600">{t('loading')}</div> : null}
            {!loading && farms.length === 0 ? (
              <div className="text-sm text-slate-600">{t('no_farms')}</div>
            ) : null}

            <div className="space-y-2">
              {farms.map((f) => (
                <div
                  key={f.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-3"
                >
                  <div>
                    <div className="font-semibold text-slate-900">{f.farmer_name}</div>
                    <div className="text-xs text-slate-600">
                      {f.crop_type} • {f.village} • {f.area_acres.toFixed(2)} acres
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={toneForHealth(f.health_status)}>
                      {f.health_status ?? 'unknown'}
                    </Badge>
                    <Link
                      to={`/farms/${f.id}`}
                      className="text-sm font-semibold text-primary hover:underline"
                    >
                      {t('view_details')}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
