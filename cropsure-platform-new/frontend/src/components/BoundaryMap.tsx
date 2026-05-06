import { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, Marker, Polygon, TileLayer, useMapEvents } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';

import { DEFAULT_ZOOM, KENYA_CENTER } from '@/config';
import { Button, Card, CardTitle, Muted } from '@/components/ui';
import type { GeoJSONPolygon } from '@/types';
import { pointsToPolygon, type LatLng } from '@/utils/geojson';

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
  const [mode, setMode] = useState<Mode>('manual');
  const [points, setPoints] = useState<LatLng[]>([]);
  const [walking, setWalking] = useState(false);
  const watchIdRef = useRef<number | null>(null);
  const pointsRef = useRef(points);

  const center = useMemo<LatLngExpression>(() => {
    return KENYA_CENTER;
  }, []);

  useEffect(() => {
    // If a polygon was loaded from outside, we won't attempt to reverse it here.
    // Enrollment flow starts from empty state.
    if (!value) {
      setPoints([]);
    }
  }, [value]);

  function updatePoints(next: LatLng[]) {
    setPoints(next);
    onChange(pointsToPolygon(next));
  }

  function startWalking() {
    if (!('geolocation' in navigator)) {
      alert('GPS unavailable. Please enable location access.');
      return;
    }
    setWalking(true);
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const p = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        updatePoints([...pointsRef.current, p]);
      },
      () => {
        alert('GPS unavailable. Please enable location access.');
      },
      { enableHighAccuracy: true, maximumAge: 1500, timeout: 10000 }
    );
  }

  function stopWalking() {
    setWalking(false);
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

  const polygonLatLngs = useMemo(() => points.map((p) => [p.lat, p.lng] as [number, number]), [points]);

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle>Farm Boundary</CardTitle>
          <Muted>
            {mode === 'manual'
              ? 'Click on the map to add boundary points.'
              : 'Walk around your farm boundary. Points will be captured automatically.'}
          </Muted>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant={mode === 'manual' ? 'primary' : 'secondary'}
            onClick={() => {
              stopWalking();
              setMode('manual');
            }}
          >
            Manual Mode
          </Button>
          <Button
            type="button"
            variant={mode === 'walk' ? 'primary' : 'secondary'}
            onClick={() => setMode('walk')}
          >
            Walk Mode
          </Button>
        </div>
      </div>

      <div className="mt-4 h-[420px] overflow-hidden rounded-lg border border-slate-200">
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
          {points.length >= 3 ? <Polygon positions={polygonLatLngs} /> : null}
        </MapContainer>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm text-slate-600">Points captured: {points.length}</div>
        <div className="flex items-center gap-2">
          {mode === 'walk' && !walking ? (
            <Button type="button" onClick={startWalking}>
              Start Walking Boundary
            </Button>
          ) : null}
          {mode === 'walk' && walking ? (
            <Button type="button" variant="secondary" onClick={stopWalking}>
              Stop
            </Button>
          ) : null}
          <Button
            type="button"
            variant="secondary"
            onClick={() => updatePoints([])}
          >
            Clear
          </Button>
        </div>
      </div>
    </Card>
  );
}
