import { createContext, useContext, useEffect, useMemo, useState } from 'react';
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

  return (
    <div className={`inline-flex rounded border border-gray-200 bg-white p-1 shadow-sm ${className}`}>
      {['vi', 'en'].map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => setLanguage(lang)}
          className={`rounded px-3 py-1 text-xs font-bold transition-colors ${
            language === lang
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
