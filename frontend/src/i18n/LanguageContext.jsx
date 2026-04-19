import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Languages } from 'lucide-react';
import { translations } from './translations';

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem('cv-review-language');
    return saved === 'en' || saved === 'vi' ? saved : 'vi';
  });

  useEffect(() => {
    localStorage.setItem('cv-review-language', language);
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo(() => {
    const t = (key, params = {}) => {
      const template = translations[language]?.[key] || translations.en[key] || key;
      return Object.entries(params).reduce(
        (text, [name, val]) => text.replaceAll(`{${name}}`, String(val)),
        template,
      );
    };

    return {
      language,
      setLanguage,
      toggleLanguage: () => setLanguage((current) => (current === 'vi' ? 'en' : 'vi')),
      t,
    };
  }, [language]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used inside LanguageProvider');
  }
  return context;
}

export function LanguageToggle({ className = '' }) {
  const { language, setLanguage } = useLanguage();
  const labels = {
    vi: { short: 'VI', name: 'Vietnamese' },
    en: { short: 'EN', name: 'English' },
  };

  return (
    <div className={`inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm dark:border-slate-700 dark:bg-slate-900 ${className}`}>
      <span className="flex items-center px-2 text-gray-400 dark:text-slate-500" aria-hidden="true">
        <Languages size={15} />
      </span>
      {['vi', 'en'].map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => setLanguage(lang)}
          className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-bold transition-all ${
            language === lang
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-100 dark:text-slate-300 dark:hover:bg-slate-800'
          }`}
          title={lang === 'vi' ? 'Tiếng Việt' : 'English'}
        >
          <span>{labels[lang].short}</span>
          <span className="hidden sm:inline">{labels[lang].name}</span>
        </button>
      ))}
    </div>
  );
}
