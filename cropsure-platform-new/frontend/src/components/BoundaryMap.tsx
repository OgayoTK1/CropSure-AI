import { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, Marker, Polygon, TileLayer, useMapEvents } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { useTranslation } from 'react-i18next';

import { DEFAULT_ZOOM, KENYA_CENTER } from '@/config';
import { Button } from '@/components/ui';
import type { GeoJSONPolygon } from '@/types';
import { pointsToPolygon, type LatLng } from '@/utils/geojson';
import { polygonAreaMeters2, meters2ToAcres } from '@/utils/area';

type Mode = 'manual' | 'walk';

function ClickCapture({ enabled, onPoint }: { enabled: boolean; onPoint: (p: LatLng) => void }) {
  useMapEvents({
    click: (e) => {
      if (!enabled) return;
      onPoint({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

export default function BoundaryMap({
  value,
  onChange,
}: {
  value: GeoJSONPolygon | null;
  onChange: (polygon: GeoJSONPolygon | null) => void;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>('walk');
  const [points, setPoints] = useState<LatLng[]>([]);
  const [walking, setWalking] = useState(false);
  const [gpsStatus, setGpsStatus] = useState<'idle' | 'acquiring' | 'active' | 'error'>('idle');
  const watchIdRef = useRef<number | null>(null);
  const pointsRef = useRef(points);

  const center = useMemo<LatLngExpression>(() => KENYA_CENTER, []);

  useEffect(() => {
    if (!value) setPoints([]);
  }, [value]);

  function updatePoints(next: LatLng[]) {
    pointsRef.current = next;
    setPoints(next);
    onChange(pointsToPolygon(next));
  }

  function startWalking() {
    if (!('geolocation' in navigator)) {
      alert(t('gps_error'));
      return;
    }
    setGpsStatus('acquiring');
    setWalking(true);
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setGpsStatus('active');
        const p = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        updatePoints([...pointsRef.current, p]);
      },
      () => {
        setGpsStatus('error');
        setWalking(false);
        alert(t('gps_error'));
      },
      { enableHighAccuracy: true, maximumAge: 1500, timeout: 10000 },
    );
  }

  function stopWalking() {
    setWalking(false);
    setGpsStatus('idle');
    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }

  useEffect(() => {
    pointsRef.current = points;
  }, [points]);

  useEffect(() => {
    return () => {
      if (watchIdRef.current != null) navigator.geolocation.clearWatch(watchIdRef.current);
    };
  }, []);

  const polygonLatLngs = useMemo(
    () => points.map((p) => [p.lat, p.lng] as [number, number]),
    [points],
  );

  const areaAcres = useMemo(() => {
    const poly = pointsToPolygon(points);
    if (!poly) return 0;
    return meters2ToAcres(polygonAreaMeters2(poly));
  }, [points]);

  const tipText = mode === 'walk' ? t('tip_walk') : t('tip_manual');

  return (
    <div className="flex flex-col gap-3">
      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode('walk')}
          className={[
            'flex-1 rounded-lg border py-2 text-sm font-semibold transition',
            mode === 'walk'
              ? 'border-primary bg-primary text-white'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
          ].join(' ')}
        >
          {t('walk_mode')}
        </button>
        <button
          type="button"
          onClick={() => {
            stopWalking();
            setMode('manual');
          }}
          className={[
            'flex-1 rounded-lg border py-2 text-sm font-semibold transition',
            mode === 'manual'
              ? 'border-primary bg-primary text-white'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
          ].join(' ')}
        >
          {t('manual_mode')}
        </button>
      </div>

      {/* Yellow tip bar */}
      <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
        <span className="mt-0.5 shrink-0 text-base">💡</span>
        <span>{tipText}</span>
      </div>

      {/* GPS status bar (walk mode only) */}
      {mode === 'walk' && walking && (
        <div className="flex items-center gap-2 rounded-lg bg-primary-light px-3 py-2 text-sm text-primary">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
          {gpsStatus === 'acquiring' ? t('gps_acquiring') : t('gps_status_walking')}
        </div>
      )}

      {/* Map */}
      <div className="h-72 overflow-hidden rounded-xl border border-slate-200 shadow-sm sm:h-96">
        <MapContainer center={center} zoom={DEFAULT_ZOOM} scrollWheelZoom>
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickCapture
            enabled={mode === 'manual'}
            onPoint={(p) => updatePoints([...points, p])}
          />
          {points.map((p, idx) => (
            <Marker key={idx} position={[p.lat, p.lng]} />
          ))}
          {points.length >= 3 ? (
            <Polygon
              positions={polygonLatLngs}
              pathOptions={{ color: '#1D9E75', fillColor: '#1D9E75', fillOpacity: 0.15, weight: 2 }}
            />
          ) : null}
        </MapContainer>
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
        <span className="text-slate-600">
          {t('points_captured', { count: points.length })}
        </span>
        {areaAcres > 0 && (
          <span className="font-semibold text-primary">
            {areaAcres.toFixed(2)} acres
          </span>
        )}
      </div>

      {/* Walk controls */}
      {mode === 'walk' && (
        <div className="flex gap-2">
          {!walking ? (
            <Button type="button" className="flex-1" onClick={startWalking}>
              {t('start_walking')}
            </Button>
          ) : (
            <Button type="button" variant="secondary" className="flex-1" onClick={stopWalking}>
              {t('stop_close')}
            </Button>
          )}
          {points.length > 0 && (
            <Button type="button" variant="secondary" onClick={() => updatePoints([])}>
              Clear
            </Button>
          )}
        </div>
      )}

      {/* Manual controls */}
      {mode === 'manual' && points.length > 0 && (
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={() => updatePoints([])}>
            Clear Points
          </Button>
        </div>
      )}

      {points.length > 0 && points.length < 3 && (
        <p className="text-xs text-amber-700">{t('min_points_warning')}</p>
      )}
    </div>
  );
}
