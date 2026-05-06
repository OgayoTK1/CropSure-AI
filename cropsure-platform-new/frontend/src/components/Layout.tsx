import { PropsWithChildren } from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import LanguageToggle from '@/components/LanguageToggle';

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          'rounded-md px-3 py-2 text-sm font-medium transition',
          isActive
            ? 'bg-primary-light text-primary'
            : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900',
        ].join(' ')
      }
    >
      {label}
    </NavLink>
  );
}

export default function Layout({ children }: PropsWithChildren) {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-primary-light text-primary grid place-items-center font-bold">
              CS
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-slate-900">{t('app_name')}</div>
              <div className="text-xs text-slate-500">{t('tagline')}</div>
            </div>
          </div>

          <nav className="flex items-center gap-2">
            <NavItem to="/enroll" label={t('nav_enroll')} />
            <NavItem to="/dashboard" label={t('nav_dashboard')} />
            <LanguageToggle />
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>

      <footer className="border-t border-slate-200">
        <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
          {t('demo_badge')} — {new Date().getFullYear()}
        </div>
      </footer>
    </div>
  );
}
