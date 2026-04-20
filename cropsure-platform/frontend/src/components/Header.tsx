import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n/index';

const Header: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const isDashboard = location.pathname === '/dashboard';

  const toggleLang = () => {
    i18n.changeLanguage(i18n.language === 'en' ? 'sw' : 'en');
  };

  return (
    <header className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
            </svg>
          </div>
          <span className="font-bold text-lg text-[#1A1A1A]">CropSure<span className="text-primary"> AI</span></span>
        </Link>

        <div className="flex items-center gap-3">
          {/* Demo badge on dashboard */}
          {isDashboard && (
            <span className="hidden sm:inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-amber-200">
              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
              {t('dashboard.demo')}
            </span>
          )}

          {/* Nav links */}
          <nav className="hidden sm:flex items-center gap-1">
            <Link
              to="/"
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === '/'
                  ? 'bg-primary/10 text-primary'
                  : 'text-gray-600 hover:text-primary hover:bg-gray-50'
              }`}
            >
              {t('nav.enroll')}
            </Link>
            <Link
              to="/dashboard"
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                isDashboard
                  ? 'bg-primary/10 text-primary'
                  : 'text-gray-600 hover:text-primary hover:bg-gray-50'
              }`}
            >
              {t('nav.dashboard')}
            </Link>
          </nav>

          {/* Language toggle */}
          <button
            onClick={toggleLang}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:border-primary hover:text-primary transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            {t('lang.toggle')}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;