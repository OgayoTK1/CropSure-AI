import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { MapContainer, Polygon, TileLayer } from 'react-leaflet';
import { useTranslation } from 'react-i18next';

import { getFarm } from '@/api/client';
import NdviChart from '@/components/NdviChart';
import { Badge, Button, Card, CardTitle, Muted } from '@/components/ui';
import { DEFAULT_ZOOM } from '@/config';
import type { Farm } from '@/types';

function healthTone(health?: Farm['health_status']): 'good' | 'warn' | 'bad' | 'neutral' {
  if (health === 'healthy') return 'good';
  if (health === 'mild_stress') return 'warn';
  if (health === 'stress') return 'bad';
  return 'neutral';
}

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
  }, [farmId]);

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

  if (loading) {
    return (
      <Card>
        <div className="text-sm text-slate-600">{t('loading')}</div>
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
        <div className="text-sm text-slate-600">Farm not found.</div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('farm_detail')}</h1>
          <div className="mt-1 text-sm text-slate-700">{farm.farmer_name}</div>
          <div className="mt-1">
            <Badge tone={healthTone(farm.health_status)}>{farm.health_status ?? 'unknown'}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/dashboard">
            <Button type="button" variant="secondary">
              {t('back_to_dashboard')}
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
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
              <div className="text-xs text-slate-500">{t('area_acres')}</div>
              <div className="font-semibold">{farm.area_acres.toFixed(2)}</div>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-xs text-slate-500">{t('policy_status')}</div>
            <div className="text-sm font-semibold text-slate-900">
              {farm.policy?.status ?? farm.policy_status ?? 'n/a'}
            </div>
          </div>

          <div className="mt-4">
            <div className="text-xs text-slate-500">{t('enrolled_on')}</div>
            <div className="text-sm text-slate-700">
              {new Date(farm.created_at).toLocaleDateString()}
            </div>
          </div>
        </Card>

        <Card>
          <CardTitle>Boundary</CardTitle>
          <div className="mt-3 h-[420px] overflow-hidden rounded-lg border border-slate-200">
            <MapContainer center={center} zoom={DEFAULT_ZOOM + 2} scrollWheelZoom>
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {polygonPositions && polygonPositions.length >= 3 ? (
                <Polygon positions={polygonPositions} />
              ) : null}
            </MapContainer>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            <Muted>{t('map_click_hint')}</Muted>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>{t('ndvi_chart_title')}</CardTitle>
          {farm.ndvi_history && farm.ndvi_history.length > 0 ? (
            <div className="mt-3">
              <NdviChart readings={farm.ndvi_history} />
            </div>
          ) : (
            <div className="mt-3 text-sm text-slate-600">No NDVI readings yet.</div>
          )}
        </Card>

        <Card>
          <CardTitle>{t('payout_history')}</CardTitle>
          <div className="mt-3 space-y-2">
            {!farm.payouts || farm.payouts.length === 0 ? (
              <div className="text-sm text-slate-600">{t('no_payouts')}</div>
            ) : (
              farm.payouts.map((p) => (
                <div key={p.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-900">KES {p.amount_kes}</div>
                    <Badge tone={p.status === 'completed' ? 'good' : p.status === 'failed' ? 'bad' : 'warn'}>
                      {p.status}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-slate-600">
                    {p.stress_type} • {new Date(p.triggered_at).toLocaleString()}
                  </div>
                  {p.explanation_en ? (
                    <div className="mt-2 text-sm text-slate-700">{p.explanation_en}</div>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
