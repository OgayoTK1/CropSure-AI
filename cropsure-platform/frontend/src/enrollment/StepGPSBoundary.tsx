import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, Polyline, Polygon, CircleMarker, useMapEvents, useMap } from 'react-leaflet';
import { Coordinate } from '../types';
import { computeAreaAcres } from '../utils/geo';

// Inner component — lives inside MapContainer, handles events and auto-pan
const MapController: React.FC<{
  mode: 'walk' | 'manual';
  coordinates: Coordinate[];
  isClosed: boolean;
  onAddPoint: (c: Coordinate) => void;
  onClose: () => void;
}> = ({ mode, coordinates, isClosed, onAddPoint, onClose }) => {
  const map = useMap();

  // Auto-pan to latest GPS point during walk mode
  useEffect(() => {
    if (coordinates.length > 0) {
      const last = coordinates[coordinates.length - 1];
      map.panTo([last.lat, last.lng]);
    }
  }, [coordinates, map]);

  useMapEvents({
    click(e) {
      if (mode !== 'manual' || isClosed) return;
      const clicked: Coordinate = { lat: e.latlng.lat, lng: e.latlng.lng };

      // Click near first point (within ~150m) closes the polygon
      if (coordinates.length >= 3) {
        const first = coordinates[0];
        const dlat = (clicked.lat - first.lat) * 111000;
        const dlng = (clicked.lng - first.lng) * 111000 * Math.cos((first.lat * Math.PI) / 180);
        if (Math.sqrt(dlat * dlat + dlng * dlng) < 150) {
          onClose();
          return;
        }
      }
      onAddPoint(clicked);
    },
  });

  const positions = coordinates.map((c) => [c.lat, c.lng] as [number, number]);

  return (
    <>
      {/* Open polyline while walking / placing points */}
      {!isClosed && positions.length >= 2 && (
        <Polyline positions={positions} pathOptions={{ color: '#EF4444', weight: 3 }} />
      )}

      {/* Closed polygon */}
      {isClosed && positions.length >= 3 && (
        <Polygon
          positions={positions}
          pathOptions={{ color: '#1D9E75', fillColor: '#1D9E75', fillOpacity: 0.25, weight: 2 }}
        />
      )}

      {/* Point markers */}
      {positions.map((pos, i) => (
        <CircleMarker
          key={i}
          center={pos}
          radius={i === 0 && mode === 'manual' && !isClosed ? 8 : 5}
          pathOptions={{
            color: i === 0 && mode === 'manual' && !isClosed ? '#1D9E75' : '#EF4444',
            fillColor: i === 0 && mode === 'manual' && !isClosed ? '#1D9E75' : '#EF4444',
            fillOpacity: 0.9,
          }}
        />
      ))}
    </>
  );
};

interface Props {
  onConfirm: (boundary: Coordinate[], areaAcres: number) => void;
  onBack: () => void;
}

const StepGPSBoundary: React.FC<Props> = ({ onConfirm, onBack }) => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'walk' | 'manual'>('walk');
  const [coordinates, setCoordinates] = useState<Coordinate[]>([]);
  const [isClosed, setIsClosed] = useState(false);
  const [isWalking, setIsWalking] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const watchIdRef = useRef<number | null>(null);

  // Clean up geolocation watch on unmount
  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  const startWalking = () => {
    if (!navigator.geolocation) {
      setGpsError(t('map.gpsError'));
      return;
    }
    setGpsError(null);
    setCoordinates([]);
    setIsClosed(false);
    setIsWalking(true);

    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setCoordinates((prev) => [
          ...prev,
          { lat: pos.coords.latitude, lng: pos.coords.longitude },
        ]);
      },
      () => {
        setGpsError(t('map.gpsError'));
        setIsWalking(false);
      },
      { enableHighAccuracy: true, maximumAge: 2000 }
    );
  };

  const stopWalking = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setIsWalking(false);
    if (coordinates.length >= 3) setIsClosed(true);
  };

  const closeBoundary = useCallback(() => {
    setIsClosed(true);
  }, []);

  const reset = () => {
    setCoordinates([]);
    setIsClosed(false);
    setIsWalking(false);
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  };

  const switchMode = (m: 'walk' | 'manual') => {
    reset();
    setMode(m);
  };

  const areaAcres = computeAreaAcres(coordinates);
  const canConfirm = isClosed && coordinates.length >= 3;

  return (
    <div className="flex flex-col gap-4">
      {/* Mode toggle */}
      <div className="flex rounded-xl overflow-hidden border border-gray-200 bg-gray-50">
        {(['walk', 'manual'] as const).map((m) => (
          <button
            key={m}
            onClick={() => switchMode(m)}
            className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
              mode === m
                ? 'bg-primary text-white'
                : 'text-gray-600 hover:text-primary'
            }`}
          >
            {m === 'walk' ? t('map.walkMode') : t('map.manualMode')}
          </button>
        ))}
      </div>

      {/* GPS point count */}
      {coordinates.length > 0 && (
        <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl px-4 py-2.5">
          <span className="text-sm font-medium text-green-800">
            {t('map.gpsPoints', { count: coordinates.length })}
          </span>
          {isClosed && (
            <span className="text-sm font-bold text-primary">
              {areaAcres.toFixed(2)} {t('common.acres')}
            </span>
          )}
        </div>
      )}

      {/* Hint text */}
      {!isWalking && !isClosed && mode === 'manual' && coordinates.length === 0 && (
        <p className="text-xs text-gray-500 text-center">{t('map.clickToAdd')}</p>
      )}
      {!isWalking && !isClosed && mode === 'manual' && coordinates.length >= 3 && (
        <p className="text-xs text-green-600 text-center">{t('map.clickToClose')}</p>
      )}

      {/* Error */}
      {gpsError && (
        <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-xl px-4 py-2.5">{gpsError}</p>
      )}

      {/* Map */}
      <div className="rounded-2xl overflow-hidden border border-gray-200 shadow-sm" style={{ height: '340px' }}>
        <MapContainer
          center={[-1.286, 36.817]}
          zoom={12}
          style={{ width: '100%', height: '100%' }}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          <MapController
            mode={mode}
            coordinates={coordinates}
            isClosed={isClosed}
            onAddPoint={(c) => setCoordinates((prev) => [...prev, c])}
            onClose={closeBoundary}
          />
        </MapContainer>
      </div>

      {/* Walk mode controls */}
      {mode === 'walk' && (
        <div>
          {!isWalking ? (
            <button
              onClick={startWalking}
              className="w-full py-4 rounded-xl bg-primary text-white font-bold text-lg hover:bg-primary-dark active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {t('map.startWalking')}
            </button>
          ) : (
            <button
              onClick={stopWalking}
              disabled={coordinates.length < 4}
              className="w-full py-4 rounded-xl bg-red-500 text-white font-bold text-lg hover:bg-red-600 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <span className="w-3 h-3 bg-white rounded-sm" />
              {coordinates.length < 4 ? t('map.minPoints') : t('map.stopClose')}
            </button>
          )}
        </div>
      )}

      {/* Manual mode close button */}
      {mode === 'manual' && !isClosed && coordinates.length >= 3 && (
        <button
          onClick={closeBoundary}
          className="w-full py-3 rounded-xl border-2 border-primary text-primary font-semibold hover:bg-primary/5 transition-colors"
        >
          Close Boundary
        </button>
      )}

      {/* Reset */}
      {coordinates.length > 0 && (
        <button onClick={reset} className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors">
          ↺ Reset boundary
        </button>
      )}

      {/* Confirm */}
      <button
        onClick={() => canConfirm && onConfirm(coordinates, areaAcres)}
        disabled={!canConfirm}
        className="w-full py-4 rounded-xl bg-primary text-white font-semibold text-base disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-dark active:scale-95 transition-all"
      >
        {t('map.confirm')}
      </button>

      <button onClick={onBack} className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors">
        ← {t('common.back')}
      </button>
    </div>
  );
};

export default StepGPSBoundary;