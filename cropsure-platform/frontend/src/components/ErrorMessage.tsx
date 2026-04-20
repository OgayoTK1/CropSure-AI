import React from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  message?: string;
  onRetry?: () => void;
}

const ErrorMessage: React.FC<Props> = ({ message, onRetry }) => {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12 px-4 text-center">
      {/* Broken plant SVG illustration */}
      <svg className="w-20 h-20 text-gray-300" viewBox="0 0 80 80" fill="none">
        <circle cx="40" cy="40" r="38" stroke="currentColor" strokeWidth="2" strokeDasharray="6 4" />
        <path d="M40 58V36" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M40 44 C34 38 26 38 24 30" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
        <path d="M40 40 C46 34 54 36 56 28" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
        <circle cx="40" cy="62" r="4" fill="#EF4444" fillOpacity="0.2" stroke="#EF4444" strokeWidth="1.5" />
        <path d="M32 18l4 4-4 4" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M48 18l-4 4 4 4" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>

      <div>
        <p className="font-semibold text-gray-800">{t('common.error')}</p>
        {message && <p className="text-sm text-gray-500 mt-1 max-w-xs">{message}</p>}
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="px-5 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
        >
          {t('common.retry')}
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;