import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, Polygon } from 'react-leaflet';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import Header from '../components/Header';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import EmptyState from '../components/EmptyState';
import { api } from '../api/client';
import { MOCK_FARMS } from '../data/mockFarms';
import { Farm } from '../types';
import { getCentroid } from '../utils/geo';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const payoutLinePlugin = {
  id: 'payoutLine',
  afterDatasetsDraw(chart: ChartJS, _: unknown, opts: { weekIndex?: number }) {
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
    ctx.restore();
  },
};

const FarmDetailPage: React.FC = () => {
  const { farmId } = useParams<{ farmId: string }>();
  const { t, i18n } = useTranslation();
  const [farm, setFarm] = useState<Farm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await api.getFarm(farmId!);
        setFarm(data);
      } catch {
        const mock = MOCK_FARMS.find((f) => f.id === farmId);
        if (mock) setFarm(mock);
        else setError(true);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [farmId]);

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

  if (error || !farm) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-lg mx-auto px-4 py-10">
          <ErrorMessage message="Farm not found." />
          <Link to="/dashboard" className="block text-center text-sm text-primary mt-4">
            ← {t('farmDetail.back')}
          </Link>
        </div>
      </div>
    );
  }

  const centroid = getCentroid(farm.boundary);
  const positions = farm.boundary.map((c) => [c.lat, c.lng] as [number, number]);

  const payoutWeekIndex = farm.payouts.length
    ? farm.ndviHistory.findIndex((p) => p.ndvi < p.baseline * 0.55)
    : undefined;

  const chartData = {
    labels: farm.ndviHistory.map((p) => `W${p.week}`),
    datasets: [
      {
        label: t('dashboard.baseline'),
        data: farm.ndviHistory.map((p) => p.baseline),
        borderColor: '#1D9E75',
        borderDash: [6, 4],
        backgroundColor: 'transparent',
        pointRadius: 0,
        tension: 0.4,
      },
      {
        label: t('dashboard.current'),
        data: farm.ndviHistory.map((p) => p.ndvi),
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
        ? { weekIndex: payoutWeekIndex }
        : {},
    },
  };

  const statusColor =
    farm.status === 'healthy'
      ? 'bg-green-100 text-green-700'
      : farm.status === 'mild_stress'
      ? 'bg-amber-100 text-amber-700'
      : 'bg-red-100 text-red-700';

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      <Header />

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-5">
        {/* Back link */}
        <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm text-primary font-medium hover:underline">
          ← {t('farmDetail.back')}
        </Link>

        {/* Hero card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-start justify-between mb-1">
            <h1 className="text-xl font-bold text-gray-900">{farm.farmerName}</h1>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor}`}>
              {farm.status === 'healthy'
                ? t('dashboard.healthy')
                : farm.status === 'mild_stress'
                ? t('dashboard.mildStress')
                : t('dashboard.severeStress')}
            </span>
          </div>
          <p className="text-sm text-gray-500">{farm.village} · {farm.cropType}</p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            {[
              ['Farm Area', `${farm.areaAcres.toFixed(1)} ${t('common.acres')}`],
              ['Current NDVI', farm.currentNDVI.toFixed(2)],
              ['Premium', `KES ${farm.premium.toLocaleString()}`],
              ['Coverage', `KES ${farm.coverage.toLocaleString()}`],
            ].map(([label, val]) => (
              <div key={label} className="bg-gray-50 rounded-xl p-3">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="font-bold text-gray-900 text-sm mt-0.5">{val}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Policy status card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 mb-3">{t('farmDetail.policy')}</h2>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${farm.status !== 'severe_stress' ? 'bg-primary' : 'bg-red-500'}`} />
            <div>
              <p className="text-sm font-semibold text-gray-900">
                {farm.status !== 'severe_stress' ? t('farmDetail.active') : t('farmDetail.inactive')}
              </p>
              <p className="text-xs text-gray-500">
                {farm.policyId} ·{' '}
                {new Date(farm.coverageStart).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })}
                {' '}{t('common.to')}{' '}
                {new Date(farm.coverageEnd).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })}
              </p>
            </div>
          </div>
        </div>

        {/* Farm map */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden" style={{ height: '260px' }}>
          <MapContainer
            center={[centroid.lat, centroid.lng]}
            zoom={14}
            style={{ width: '100%', height: '100%' }}
          >
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
            <Polygon
              positions={positions}
              pathOptions={{ color: '#1D9E75', fillColor: '#1D9E75', fillOpacity: 0.3, weight: 2 }}
            />
          </MapContainer>
        </div>

        {/* NDVI chart */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 mb-3">{t('farmDetail.ndviTrend')}</h2>
          <div style={{ height: '220px' }}>
            <Line data={chartData} options={chartOptions} plugins={[payoutLinePlugin]} />
          </div>
        </div>

        {/* Payouts */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 mb-3">{t('farmDetail.payoutHistory')}</h2>
          {farm.payouts.length === 0 ? (
            <EmptyState title={t('farmDetail.noPayouts')} />
          ) : (
            <div className="space-y-3">
              {farm.payouts.map((p) => (
                <div key={p.id} className="border border-gray-100 rounded-xl p-4 bg-red-50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-red-700 text-lg">
                      KES {p.amount.toLocaleString()}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(p.triggeredAt).toLocaleDateString('en-KE', {
                        day: 'numeric', month: 'short', year: 'numeric',
                      })}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mb-1">
                    <span className="font-medium">{t('farmDetail.payoutReason')}:</span>{' '}
                    {i18n.language === 'sw' ? p.reasonSw : p.reason}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default FarmDetailPage;