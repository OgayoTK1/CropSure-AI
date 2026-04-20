import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  MapContainer, TileLayer, Marker, Popup, useMap,
} from 'react-leaflet';
import L from 'leaflet';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import Header from '../components/Header';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import EmptyState from '../components/EmptyState';
import { useToast } from '../context/ToastContext';
import { api } from '../api/client';
import { MOCK_FARMS, MOCK_ACTIVITIES } from '../data/mockFarms';
import { Farm, ActivityEvent, FarmStatus } from '../types';
import { getCentroid } from '../utils/geo';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

// ── Helpers ───────────────────────────────────────────────────────────────────

function farmIcon(status: FarmStatus) {
  const color = status === 'healthy' ? '#1D9E75' : status === 'mild_stress' ? '#F59E0B' : '#EF4444';
  return L.divIcon({
    html: `<div style="background:${color};width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>`,
    className: '',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function activityIcon(type: ActivityEvent['type']) {
  if (type === 'payout') return '💸';
  if (type === 'enrollment') return '🌱';
  return '📡';
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('en-KE', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

// Vertical-line plugin for payout week marker
const payoutLinePlugin = {
  id: 'payoutLine',
  afterDatasetsDraw(chart: ChartJS, _: unknown, opts: { weekIndex?: number; label?: string }) {
    if (opts.weekIndex === undefined) return;
    const { ctx, chartArea, scales } = chart as ChartJS & { scales: Record<string, { getPixelForValue: (v: number) => number }> };
    const x = scales.x.getPixelForValue(opts.weekIndex);
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#EF4444';
    ctx.setLineDash([5, 4]);
    ctx.stroke();
    if (opts.label) {
      ctx.fillStyle = '#EF4444';
      ctx.font = '11px sans-serif';
      ctx.fillText(opts.label, x + 4, chartArea.top + 14);
    }
    ctx.restore();
  },
};

// ── Sub-components ────────────────────────────────────────────────────────────

const FlyToFarm: React.FC<{ farm: Farm | null }> = ({ farm }) => {
  const map = useMap();
  useEffect(() => {
    if (farm) {
      const c = getCentroid(farm.boundary);
      map.flyTo([c.lat, c.lng], 13, { duration: 1 });
    }
  }, [farm, map]);
  return null;
};

// ── Dashboard page ────────────────────────────────────────────────────────────

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();

  const [farms, setFarms] = useState<Farm[]>([]);
  const [activities, setActivities] = useState<ActivityEvent[]>(MOCK_ACTIVITIES);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [selectedFarm, setSelectedFarm] = useState<Farm | null>(null);
  const [simulating, setSimulating] = useState(false);

  const fetchFarms = useCallback(async () => {
    try {
      const data = await api.getFarms();
      setFarms(data);
      setFetchError(false);
    } catch {
      // Fall back to mock data so the demo always looks populated
      setFarms(MOCK_FARMS);
      setFetchError(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFarms();
    const id = setInterval(fetchFarms, 30000);
    return () => clearInterval(id);
  }, [fetchFarms]);

  // Keep selectedFarm in sync with farms list (e.g., status changed after simulate)
  useEffect(() => {
    if (selectedFarm) {
      const updated = farms.find((f) => f.id === selectedFarm.id);
      if (updated) setSelectedFarm(updated);
    }
  }, [farms]);

  const handleSimulate = async () => {
    if (!selectedFarm) {
      showToast(t('dashboard.noFarmSelected'), 'info');
      return;
    }
    setSimulating(true);
    try {
      const res = await api.simulateDrought(selectedFarm.id);
      setFarms((prev) =>
        prev.map((f) => f.id === selectedFarm.id ? { ...f, status: 'severe_stress' } : f)
      );
      showToast(t('dashboard.payoutToast', { amount: res.payout.toLocaleString(), phone: res.phone }));
      const newActivity: ActivityEvent = {
        id: `act-sim-${Date.now()}`,
        type: 'payout',
        farmName: `${selectedFarm.farmerName} – ${selectedFarm.village}`,
        description: `Simulated payout of KES ${res.payout.toLocaleString()} triggered.`,
        timestamp: new Date().toISOString(),
      };
      setActivities((prev) => [newActivity, ...prev.slice(0, 9)]);
    } catch {
      // Demo simulation without backend
      const payout = Math.round(selectedFarm.coverage * 0.6);
      setFarms((prev) =>
        prev.map((f) => f.id === selectedFarm.id ? { ...f, status: 'severe_stress' } : f)
      );
      showToast(t('dashboard.payoutToast', { amount: payout.toLocaleString(), phone: selectedFarm.phone }));
      const newActivity: ActivityEvent = {
        id: `act-sim-${Date.now()}`,
        type: 'payout',
        farmName: `${selectedFarm.farmerName} – ${selectedFarm.village}`,
        description: `Simulated payout of KES ${payout.toLocaleString()} triggered.`,
        timestamp: new Date().toISOString(),
      };
      setActivities((prev) => [newActivity, ...prev.slice(0, 9)]);
    } finally {
      setSimulating(false);
    }
  };

  // ── Stats ──────────────────────────────────────────────────
  const stats = {
    totalFarms: farms.length,
    activePolicies: farms.filter((f) => f.status !== 'severe_stress').length,
    totalPayoutsKes: farms.flatMap((f) => f.payouts).reduce((s, p) => s + p.amount, 0),
    farmsUnderStress: farms.filter((f) => f.status !== 'healthy').length,
  };

  const statCards = [
    { label: t('dashboard.totalFarms'), value: stats.totalFarms, icon: '🌿', color: 'bg-green-50 text-green-700' },
    { label: t('dashboard.activePolicies'), value: stats.activePolicies, icon: '📋', color: 'bg-blue-50 text-blue-700' },
    {
      label: t('dashboard.payouts'),
      value: `KES ${stats.totalPayoutsKes.toLocaleString()}`,
      icon: '💸',
      color: 'bg-amber-50 text-amber-700',
    },
    { label: t('dashboard.farmsUnderStress'), value: stats.farmsUnderStress, icon: '⚠️', color: 'bg-red-50 text-red-700' },
  ];

  // ── NDVI chart ─────────────────────────────────────────────
  const ndviData = selectedFarm?.ndviHistory ?? [];
  const payoutWeekIndex = selectedFarm?.payouts.length
    ? selectedFarm.ndviHistory.findIndex((p) => p.ndvi < p.baseline * 0.55)
    : undefined;

  const chartData = {
    labels: ndviData.map((p) => `W${p.week}`),
    datasets: [
      {
        label: t('dashboard.baseline'),
        data: ndviData.map((p) => p.baseline),
        borderColor: '#1D9E75',
        borderDash: [6, 4],
        backgroundColor: 'transparent',
        pointRadius: 0,
        tension: 0.4,
      },
      {
        label: t('dashboard.current'),
        data: ndviData.map((p) => p.ndvi),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59,130,246,0.08)',
        fill: true,
        pointRadius: 2,
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 1, title: { display: true, text: 'NDVI' } },
      x: { title: { display: true, text: 'Weeks' } },
    },
    plugins: {
      legend: { position: 'top' as const },
      payoutLine: payoutWeekIndex !== undefined && payoutWeekIndex >= 0
        ? { weekIndex: payoutWeekIndex, label: t('dashboard.payoutTrigger') }
        : {},
    },
  };

  // ── Render ─────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <LoadingSpinner size="lg" label={t('common.loading')} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Page title */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
          <span className="sm:hidden inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-amber-200">
            <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
            {t('dashboard.demo')}
          </span>
        </div>

        {fetchError && (
          <ErrorMessage message="Could not reach backend — showing demo data." onRetry={fetchFarms} />
        )}

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {statCards.map((s) => (
            <div key={s.label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-lg mb-2 ${s.color}`}>
                {s.icon}
              </div>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-tight">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Map + Activity feed */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Map (60%) */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden" style={{ height: '420px' }}>
            <MapContainer center={[-1.0, 37.0]} zoom={6} style={{ width: '100%', height: '100%' }}>
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              <FlyToFarm farm={selectedFarm} />
              {farms.map((farm) => {
                const c = getCentroid(farm.boundary);
                return (
                  <Marker
                    key={farm.id}
                    position={[c.lat, c.lng]}
                    icon={farmIcon(farm.status)}
                    eventHandlers={{ click: () => setSelectedFarm(farm) }}
                  >
                    <Popup>
                      <div className="text-sm space-y-1 min-w-[160px]">
                        <p className="font-semibold">{farm.farmerName}</p>
                        <p className="text-gray-500">{farm.cropType} · {farm.areaAcres.toFixed(1)} acres</p>
                        <p>NDVI: <strong>{farm.currentNDVI.toFixed(2)}</strong></p>
                        <span
                          className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
                            farm.status === 'healthy'
                              ? 'bg-green-100 text-green-700'
                              : farm.status === 'mild_stress'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {farm.status === 'healthy'
                            ? t('dashboard.healthy')
                            : farm.status === 'mild_stress'
                            ? t('dashboard.mildStress')
                            : t('dashboard.severeStress')}
                        </span>
                        <br />
                        <Link to={`/farm/${farm.id}`} className="text-primary text-xs underline">
                          {t('common.viewDetails')}
                        </Link>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          </div>

          {/* Activity feed (40%) */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex flex-col" style={{ maxHeight: '420px' }}>
            <h2 className="font-semibold text-gray-900 mb-3">{t('dashboard.recentActivity')}</h2>
            <div className="overflow-y-auto flex-1 space-y-2 pr-1">
              {activities.length === 0 ? (
                <EmptyState title={t('common.noData')} />
              ) : (
                activities.map((a) => (
                  <div key={a.id} className="flex gap-3 p-2.5 rounded-xl hover:bg-gray-50 transition-colors">
                    <span className="text-lg shrink-0">{activityIcon(a.type)}</span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-900 truncate">{a.farmName}</p>
                      <p className="text-xs text-gray-500 leading-snug">{a.description}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{fmtTime(a.timestamp)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* NDVI chart */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 mb-1">{t('dashboard.ndviTrend')}</h2>
          {selectedFarm && (
            <p className="text-xs text-gray-500 mb-3">
              {selectedFarm.farmerName} – {selectedFarm.village} ({selectedFarm.cropType})
            </p>
          )}
          {!selectedFarm ? (
            <EmptyState title={t('dashboard.selectFarm')} />
          ) : (
            <div style={{ height: '220px' }}>
              <Line
                data={chartData}
                options={chartOptions}
                plugins={[payoutLinePlugin]}
              />
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
          {[
            { color: 'bg-primary', label: t('dashboard.healthy') },
            { color: 'bg-amber-400', label: t('dashboard.mildStress') },
            { color: 'bg-red-500', label: t('dashboard.severeStress') },
          ].map((l) => (
            <div key={l.label} className="flex items-center gap-1.5">
              <span className={`w-3 h-3 rounded-full ${l.color}`} />
              {l.label}
            </div>
          ))}
        </div>
      </main>

      {/* Floating Simulate button */}
      <div className="fixed bottom-6 right-4 left-4 md:left-auto">
        <button
          onClick={handleSimulate}
          disabled={simulating}
          className={`w-full md:w-auto px-6 py-4 rounded-2xl bg-red-600 text-white font-bold text-sm shadow-xl hover:bg-red-700 active:scale-95 transition-all flex items-center justify-center gap-2 ${
            simulating ? 'animate-pulse-fast' : ''
          }`}
        >
          {simulating ? (
            <>
              <LoadingSpinner size="sm" />
              {t('dashboard.simulating')}
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              {t('dashboard.simulateDrought')}
              {selectedFarm && (
                <span className="ml-1 font-normal opacity-80">({selectedFarm.farmerName.split(' ')[0]})</span>
              )}
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default DashboardPage;