import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useLanguage } from '../i18n/LanguageContext';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('cv-review-theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    localStorage.setItem('cv-review-theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const value = useMemo(() => ({
    theme,
    setTheme,
    toggleTheme: () => setTheme((current) => (current === 'dark' ? 'light' : 'dark')),
  }), [theme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }
  return context;
}

export function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();
  const { t } = useLanguage();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-700 shadow-sm transition-colors hover:bg-gray-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800 ${className}`}
      aria-label={isDark ? t('theme.switchLight') : t('theme.switchDark')}
    >
      {isDark ? t('theme.dark') : t('theme.light')}
    </button>
  );
}
