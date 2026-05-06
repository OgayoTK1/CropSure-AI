import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import sw from './sw.json';

export function setupI18n(): void {
  if (i18n.isInitialized) return;

  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en },
        sw: { translation: sw },
      },
      fallbackLng: 'en',
      supportedLngs: ['en', 'sw'],
      interpolation: {
        escapeValue: false,
      },
      detection: {
        order: ['localStorage', 'navigator'],
        caches: ['localStorage'],
      },
    });
}

export default i18n;
