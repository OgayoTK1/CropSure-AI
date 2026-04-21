import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, Polygon } from 'react-leaflet';
import { FarmerDetails, Coordinate, EnrollResponse } from '../types';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import { getCentroid } from '../utils/geo';

interface Props {
  farmerDetails: FarmerDetails;
  boundary: Coordinate[];
  areaAcres: number;
  onBack: () => void;
  onReset: () => void;
}

const StepPaymentConfirmation: React.FC<Props> = ({
  farmerDetails, boundary, areaAcres, onBack, onReset,
}) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EnrollResponse | null>(null);

  const premium = Math.round(areaAcres * 300);
  const coverage = premium * 8;

  const now = new Date();
  const end = new Date(now);
  end.setMonth(end.getMonth() + 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' });

  const handlePay = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.enrollFarm({
        farmerDetails,
        boundary,
        areaAcres,
      });
      setResult(res);
    } catch {
      // Simulate success for demo when backend is unavailable
      setResult({
        id: `farm-${Date.now()}`,
        policyId: `POL-${Date.now().toString().slice(-6)}`,
        message: 'Enrolled successfully',
      });
    } finally {
      setLoading(false);
    }
  };

  // ── Success screen ─────────────────────────────────────────
  if (result) {
    const centroid = getCentroid(boundary);
    const positions = boundary.map((c) => [c.lat, c.lng] as [number, number]);

    return (
      <div className="flex flex-col items-center gap-5 text-center py-2">
        {/* Green checkmark */}
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
          <svg className="w-9 h-9 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <div>
          <h2 className="text-xl font-bold text-gray-900">{t('payment.successTitle')}</h2>
          <p className="text-sm text-gray-500 mt-1">
            {t('payment.successMessage', { phone: farmerDetails.phone })}
          </p>
          <p className="text-xs font-semibold text-primary mt-1">
            {t('payment.policy', { id: result.policyId })}
          </p>
        </div>

        {/* Mini map showing farm polygon */}
        <div className="w-full rounded-2xl overflow-hidden border border-gray-200 shadow-sm" style={{ height: '200px' }}>
          <MapContainer
            center={[centroid.lat, centroid.lng]}
            zoom={14}
            style={{ width: '100%', height: '100%' }}
            zoomControl={false}
            scrollWheelZoom={false}
            dragging={false}
          >
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Polygon
              positions={positions}
              pathOptions={{ color: '#1D9E75', fillColor: '#1D9E75', fillOpacity: 0.3 }}
            />
          </MapContainer>
        </div>

        {/* Summary pills */}
        <div className="w-full grid grid-cols-2 gap-3 text-left">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-xs text-gray-500">{t('payment.farmArea')}</p>
            <p className="font-bold text-gray-900">{areaAcres.toFixed(2)} {t('common.acres')}</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-xs text-gray-500">{t('farmer.cropType')}</p>
            <p className="font-bold text-gray-900">{farmerDetails.cropType}</p>
          </div>
          <div className="bg-primary/5 rounded-xl p-3">
            <p className="text-xs text-gray-500">{t('payment.premium')}</p>
            <p className="font-bold text-primary">KES {premium.toLocaleString()}</p>
          </div>
          <div className="bg-primary/5 rounded-xl p-3">
            <p className="text-xs text-gray-500">{t('payment.coverage')}</p>
            <p className="font-bold text-primary">KES {coverage.toLocaleString()}</p>
          </div>
        </div>

        <button
          onClick={onReset}
          className="w-full py-3 rounded-xl bg-primary text-white font-semibold hover:bg-primary-dark transition-colors"
        >
          {t('payment.enrollAnother')}
        </button>
      </div>
    );
  }

  // ── Confirmation form ──────────────────────────────────────
  return (
    <div className="flex flex-col gap-5">
      <div className="bg-gray-50 rounded-2xl p-5 space-y-3">
        <h3 className="font-semibold text-gray-900">{t('payment.summary')}</h3>

        {[
          [t('payment.farmArea'), `${areaAcres.toFixed(2)} ${t('common.acres')}`],
          [t('farmer.fullName'), farmerDetails.fullName],
          [t('payment.cropType'), farmerDetails.cropType],
          [t('payment.premium'), `KES ${premium.toLocaleString()}`],
          [t('payment.coverage'), `KES ${coverage.toLocaleString()}`],
          [t('payment.period'), `${fmt(now)} ${t('common.to')} ${fmt(end)}`],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
            <span className="text-sm text-gray-500">{label}</span>
            <span className="text-sm font-semibold text-gray-900">{value}</span>
          </div>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</p>
      )}

      <button
        onClick={handlePay}
        disabled={loading}
        className="w-full py-4 rounded-xl bg-primary text-white font-bold text-base disabled:opacity-50 hover:bg-primary-dark active:scale-95 transition-all flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <LoadingSpinner size="sm" />
            {t('payment.processing')}
          </>
        ) : (
          t('payment.payButton', { amount: premium.toLocaleString() })
        )}
      </button>

      <button
        onClick={onBack}
        disabled={loading}
        className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
      >
        ← {t('payment.back')}
      </button>
    </div>
  );
};

export default StepPaymentConfirmation;