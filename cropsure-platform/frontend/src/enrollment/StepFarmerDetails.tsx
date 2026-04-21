import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FarmerDetails, CropType } from '../types';

interface Props {
  initial: FarmerDetails;
  onNext: (details: FarmerDetails) => void;
}

const CROPS: CropType[] = ['Maize', 'Beans', 'Tea', 'Wheat', 'Sorghum'];
const PHONE_RE = /^07\d{8}$/;

const StepFarmerDetails: React.FC<Props> = ({ initial, onNext }) => {
  const { t } = useTranslation();
  const [form, setForm] = useState<FarmerDetails>(initial);
  const [touched, setTouched] = useState({ phone: false });

  const phoneValid = PHONE_RE.test(form.phone);
  const canNext =
    form.fullName.trim().length > 0 &&
    phoneValid &&
    form.village.trim().length > 0 &&
    form.cropType.length > 0;

  const set = (k: keyof FarmerDetails, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const fieldClass = (err?: boolean) =>
    `w-full px-4 py-3 rounded-xl border text-sm outline-none transition-colors ${
      err
        ? 'border-red-400 bg-red-50 focus:border-red-500'
        : 'border-gray-200 bg-gray-50 focus:border-primary focus:bg-white'
    }`;

  return (
    <div className="space-y-5">
      {/* Full name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {t('farmer.fullName')} <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={form.fullName}
          onChange={(e) => set('fullName', e.target.value)}
          placeholder={t('farmer.fullNamePlaceholder')}
          className={fieldClass()}
        />
      </div>

      {/* Phone */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {t('farmer.phone')} <span className="text-red-400">*</span>
        </label>
        <input
          type="tel"
          value={form.phone}
          onChange={(e) => set('phone', e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, phone: true }))}
          placeholder={t('farmer.phonePlaceholder')}
          className={fieldClass(touched.phone && !phoneValid)}
          maxLength={10}
        />
        {touched.phone && !phoneValid && (
          <p className="text-xs text-red-500 mt-1">{t('farmer.phoneError')}</p>
        )}
      </div>

      {/* Village */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {t('farmer.village')} <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={form.village}
          onChange={(e) => set('village', e.target.value)}
          placeholder={t('farmer.villagePlaceholder')}
          className={fieldClass()}
        />
      </div>

      {/* Crop type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {t('farmer.cropType')} <span className="text-red-400">*</span>
        </label>
        <select
          value={form.cropType}
          onChange={(e) => set('cropType', e.target.value as CropType)}
          aria-label={t('farmer.cropType')}
          className={`${fieldClass()} appearance-none`}
        >
          <option value="">{t('farmer.selectCrop')}</option>
          {CROPS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={() => canNext && onNext(form)}
        disabled={!canNext}
        className="w-full py-4 rounded-xl bg-primary text-white font-semibold text-base disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-dark active:scale-95 transition-all mt-2"
      >
        {t('common.next')} →
      </button>
    </div>
  );
};

export default StepFarmerDetails;