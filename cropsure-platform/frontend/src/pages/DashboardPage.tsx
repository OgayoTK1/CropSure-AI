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
import EmptyState from '../components/EmptyState';
import { useToast } from '../context/ToastContext';
import { api } from '../api/client';
import { MOCK_FARMS } from '../data/mockFarms';
import { Farm, FarmStatus } from '../types';
import { getCentroid } from '../utils/geo';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

// ── Helpers ───────────────────────────────────────────────────────────────────

function farmIcon(status: FarmStatus, selected: boolean) {
  const color = status === 'healthy' ? '#1D9E75' : status === 'mild_stress' ? '#F59E0B' : '#EF4444';
  const size = selected ? 22 : 14;
  const border = selected ? 4 : 2;
  return L.divIcon({
    html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:${border}px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.35);transition:all .2s"></div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function StatusBadge({ status }: { status: FarmStatus }) {
  const { t } = useTranslation();
  const map: Record<FarmStatus, string> = {
    healthy: 'bg-green-100 text-green-700',
    mild_stress: 'bg-amber-100 text-amber-700',
    severe_stress: 'bg-red-100 text-red-700',
  };
  const label = status === 'healthy'
    ? t('dashboard.healthy')
    : status === 'mild_stress'
    ? t('dashboard.mildStress')
    : t('dashboard.severeStress');
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${map[status]}`}>
      {label}
    </span>
  );
}

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

const FlyToFarm: React.FC<{ farm: Farm | null }> = ({ farm }) => {
  const map = useMap();
  useEffect(() => {
    if (farm && farm.boundary.length > 0) {
      const c = getCentroid(farm.boundary);
      map.flyTo([c.lat, c.lng], 13, { duration: 1 });
    }
  }, [farm, map]);
  return null;
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { showToast } = useToast();

  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);
  const [selectedFarm, setSelectedFarm] = useState<Farm | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [farmSearch, setFarmSearch] = useState('');

  const fetchFarms = useCallback(async () => {
    try {
      const data = await api.getFarms();
      setFarms(data);
      setUsingMock(false);
      setLastUpdated(new Date());
    } catch {
      setFarms(MOCK_FARMS);
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFarms();
    const id = setInterval(fetchFarms, 30000);
    return () => clearInterval(id);
  }, [fetchFarms]);

  useEffect(() => {
    if (selectedFarm) {
      const updated = farms.find((f) => f.id === selectedFarm.id);
      if (updated) setSelectedFarm(updated);
    }
  }, [farms, selectedFarm]);

  const handleSimulate = async () => {
    if (!selectedFarm) return;
    setSimulating(true);
    try {
      const res = await api.simulateDrought(selectedFarm.id);
      setFarms((prev) =>
        prev.map((f) => f.id === selectedFarm.id ? { ...f, status: 'severe_stress' } : f)
      );
      showToast(t('dashboard.payoutToast', { amount: res.payout.toLocaleString(), phone: res.phone }));
    } catch {
      const payout = Math.round(selectedFarm.coverage * 0.5);
      setFarms((prev) =>
        prev.map((f) => f.id === selectedFarm.id ? { ...f, status: 'severe_stress' } : f)
      );
      showToast(t('dashboard.payoutToast', { amount: payout.toLocaleString(), phone: selectedFarm.phone }));
    } finally {
      setSimulating(false);
    }
  };

  // ── Derived data ───────────────────────────────────────────────────────────
  const stats = {
    totalFarms: farms.length,
    activePolicies: farms.filter((f) => f.policyId).length,
    totalPayoutsKes: farms.flatMap((f) => f.payouts).reduce((s, p) => s + p.amount, 0),
    farmsUnderStress: farms.filter((f) => f.status !== 'healthy').length,
  };

  const filteredFarms = farms.filter((f) =>
    farmSearch === '' ||
    f.farmerName.toLowerCase().includes(farmSearch.toLowerCase()) ||
    f.village.toLowerCase().includes(farmSearch.toLowerCase())
  );

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

  // ── Loading ────────────────────────────────────────────────────────────────
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

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-5">

        {/* Title row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
            {lastUpdated && (
              <p className="text-xs text-gray-400 mt-0.5">
                Updated {lastUpdated.toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit' })}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {usingMock && (
              <span className="inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-amber-200">
                <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
                Demo data
              </span>
            )}
            {!usingMock && (
              <span className="inline-flex items-center gap-1.5 bg-green-50 text-green-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-green-200">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Live
              </span>
            )}
            <button
              onClick={fetchFarms}
              className="p-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition-colors"
              title="Refresh"
            >
              <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: t('dashboard.totalFarms'), value: stats.totalFarms, icon: '🌿', color: 'bg-green-50 text-green-700' },
            { label: t('dashboard.activePolicies'), value: stats.activePolicies, icon: '📋', color: 'bg-blue-50 text-blue-700' },
            { label: t('dashboard.payouts'), value: `KES ${stats.totalPayoutsKes.toLocaleString()}`, icon: '💸', color: 'bg-amber-50 text-amber-700' },
            { label: t('dashboard.farmsUnderStress'), value: stats.farmsUnderStress, icon: '⚠️', color: 'bg-red-50 text-red-700' },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-lg mb-2 ${s.color}`}>
                {s.icon}
              </div>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-tight">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Map + Farm list */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

          {/* Map */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden" style={{ height: '420px' }}>
            <MapContainer center={[-1.0, 37.0]} zoom={6} style={{ width: '100%', height: '100%' }}>
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              <FlyToFarm farm={selectedFarm} />
              {farms.map((farm) => {
                const c = getCentroid(farm.boundary);
                if (!c.lat && !c.lng) return null;
                return (
                  <Marker
                    key={farm.id}
                    position={[c.lat, c.lng]}
                    icon={farmIcon(farm.status, selectedFarm?.id === farm.id)}
                    eventHandlers={{ click: () => setSelectedFarm(farm) }}
                  >
                    <Popup>
                      <div className="text-sm space-y-1 min-w-[160px]">
                        <p className="font-semibold">{farm.farmerName}</p>
                        <p className="text-gray-500">{farm.cropType} · {farm.areaAcres.toFixed(1)} acres</p>
                        {farm.currentNDVI > 0 && <p>NDVI: <strong>{farm.currentNDVI.toFixed(2)}</strong></p>}
                        <StatusBadge status={farm.status} />
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

          {/* Farm list */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col" style={{ maxHeight: '420px' }}>
            <div className="p-3 border-b border-gray-100">
              <input
                type="text"
                value={farmSearch}
                onChange={(e) => setFarmSearch(e.target.value)}
                placeholder="Search farms…"
                className="w-full px-3 py-2 text-sm rounded-xl border border-gray-200 bg-gray-50 outline-none focus:border-primary focus:bg-white transition-colors"
              />
            </div>

            <div className="overflow-y-auto flex-1">
              {filteredFarms.length === 0 ? (
                <div className="p-4">
                  <EmptyState title={farmSearch ? 'No matching farms' : t('common.noData')} />
                </div>
              ) : (
                filteredFarms.map((farm) => {
                  const isSelected = selectedFarm?.id === farm.id;
                  return (
                    <button
                      key={farm.id}
                      onClick={() => setSelectedFarm(isSelected ? null : farm)}
                      className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors flex items-center gap-3 ${isSelected ? 'bg-primary/5 border-l-2 border-l-primary' : ''}`}
                    >
                      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                        farm.status === 'healthy' ? 'bg-green-500' :
                        farm.status === 'mild_stress' ? 'bg-amber-400' : 'bg-red-500'
                      }`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-gray-900 truncate">{farm.farmerName}</p>
                        <p className="text-xs text-gray-500 truncate">{farm.village} · {farm.cropType} · {farm.areaAcres.toFixed(1)} ac</p>
                      </div>
                      {farm.currentNDVI > 0 && (
                        <span className="text-xs font-mono text-gray-400 shrink-0">
                          {farm.currentNDVI.toFixed(2)}
                        </span>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Selected farm panel */}
        {selectedFarm && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <h2 className="text-lg font-bold text-gray-900">{selectedFarm.farmerName}</h2>
                  <StatusBadge status={selectedFarm.status} />
                </div>
                <p className="text-sm text-gray-500">
                  {selectedFarm.village} · {selectedFarm.cropType} · {selectedFarm.areaAcres.toFixed(1)} acres
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Link
                  to={`/farm/${selectedFarm.id}`}
                  className="px-3 py-1.5 text-xs font-semibold text-primary border border-primary/30 rounded-xl hover:bg-primary/5 transition-colors"
                >
                  Details →
                </Link>
                <button
                  onClick={() => setSelectedFarm(null)}
                  className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                ['NDVI', selectedFarm.currentNDVI > 0 ? selectedFarm.currentNDVI.toFixed(2) : '—'],
                ['Premium', `KES ${selectedFarm.premium.toLocaleString()}`],
                ['Coverage', `KES ${selectedFarm.coverage.toLocaleString()}`],
                ['Payouts', selectedFarm.payouts.length.toString()],
              ].map(([label, val]) => (
                <div key={label} className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="font-bold text-gray-900 text-sm mt-0.5">{val}</p>
                </div>
              ))}
            </div>

            {/* NDVI chart */}
            {ndviData.length > 0 ? (
              <div style={{ height: '200px' }}>
                <Line data={chartData} options={chartOptions} plugins={[payoutLinePlugin]} />
              </div>
            ) : (
              <div className="h-24 flex items-center justify-center text-sm text-gray-400 bg-gray-50 rounded-xl">
                No NDVI readings yet
              </div>
            )}

            {/* Simulate drought button */}
            <button
              onClick={handleSimulate}
              disabled={simulating}
              className="w-full py-3.5 rounded-xl bg-red-600 text-white font-bold text-sm shadow-md hover:bg-red-700 active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {simulating ? (
                <><LoadingSpinner size="sm" /> {t('dashboard.simulating')}</>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  {t('dashboard.simulateDrought')} — {selectedFarm.farmerName.split(' ')[0]}
                </>
              )}
            </button>
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
          {[
            { color: 'bg-green-500', label: t('dashboard.healthy') },
            { color: 'bg-amber-400', label: t('dashboard.mildStress') },
            { color: 'bg-red-500', label: t('dashboard.severeStress') },
          ].map((l) => (
            <div key={l.label} className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${l.color}`} />
              {l.label}
            </div>
          ))}
          <span className="text-gray-300">·</span>
          <span>Click a farm on the map or list to inspect</span>
        </div>

      </main>
    </div>
  );
};

export default DashboardPage;
