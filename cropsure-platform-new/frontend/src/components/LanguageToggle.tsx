import { useTranslation } from 'react-i18next';

const LANGS: Array<{ code: 'en' | 'sw'; label: string }> = [
  { code: 'en', label: 'EN' },
  { code: 'sw', label: 'SW' },
];

export default function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? i18n.language ?? 'en') as 'en' | 'sw';

  return (
    <div className="flex items-center rounded-md border border-slate-200 bg-white p-1">
      {LANGS.map((l) => {
        const active = l.code === current;
        return (
          <button
            key={l.code}
            type="button"
            onClick={() => void i18n.changeLanguage(l.code)}
            className={[
              'rounded px-2 py-1 text-xs font-semibold transition',
              active
                ? 'bg-primary text-white'
                : 'text-slate-600 hover:bg-slate-100',
            ].join(' ')}
            aria-pressed={active}
            aria-label={`Switch language to ${l.code}`}
          >
            {l.label}
          </button>
        );
      })}
    </div>
  );
}
