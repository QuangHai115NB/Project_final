import { Link } from 'react-router-dom';
import { LanguageToggle, useLanguage } from '../../i18n/LanguageContext';
import { ThemeToggle } from '../../theme/ThemeContext';

export default function AuthShell({ children, mode = 'login' }) {
  const { t } = useLanguage();
  const isRegister = mode === 'register';

  return (
    <div className="auth-shell min-h-screen overflow-hidden px-4 py-5 text-gray-900 dark:text-slate-100 sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-7xl flex-col gap-5 lg:flex-row lg:items-stretch">
        <section className="auth-home-shrink relative flex flex-1 flex-col justify-between overflow-hidden rounded-lg border border-white/70 bg-white/72 p-6 shadow-xl backdrop-blur-xl dark:border-slate-700/70 dark:bg-slate-900/72 lg:p-8">
          <div className="flex items-center justify-between gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-bold text-blue-700 shadow-sm transition-all hover:-translate-y-0.5 hover:bg-blue-50 hover:shadow-md dark:border-sky-700/60 dark:bg-slate-900 dark:text-sky-200 dark:hover:bg-sky-950/40"
            >
              <span aria-hidden="true">←</span>
              {t('auth.backHome')}
            </Link>
            <div className="flex items-center gap-2">
              <ThemeToggle className="h-9" />
              <LanguageToggle />
            </div>
          </div>

          <div className="my-10 max-w-2xl lg:my-0">
            <div className="mb-5 inline-flex rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 dark:border-emerald-700/60 dark:bg-emerald-950/35 dark:text-emerald-200">
              CV Reviewer
            </div>
            <h1 className="max-w-xl text-4xl font-black leading-tight text-gray-950 dark:text-white sm:text-5xl">
              {isRegister ? t('landing.title') : t('landing.titleAccent')}
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-gray-600 dark:text-slate-300">
              {isRegister ? t('landing.subtitle') : t('auth.loginSubtitle')}
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {[
                ['🎯', t('landing.feature.match.title')],
                ['📄', t('landing.feature.review.title')],
                ['💡', t('landing.feature.suggest.title')],
              ].map(([icon, label]) => (
                <div key={label} className="rounded-lg border border-white/80 bg-white/75 p-4 shadow-sm dark:border-slate-700/70 dark:bg-slate-800/70">
                  <div className="text-2xl">{icon}</div>
                  <p className="mt-2 text-sm font-bold text-gray-800 dark:text-slate-100">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="pointer-events-none absolute bottom-6 right-6 hidden h-28 w-28 rounded-full border border-cyan-200/70 bg-cyan-100/40 blur-sm dark:border-cyan-700/40 dark:bg-cyan-900/20 lg:block" />
          <div className="float-soft pointer-events-none absolute right-12 top-28 hidden rounded-lg border border-blue-200/70 bg-white/80 px-4 py-3 text-sm font-bold text-blue-700 shadow-lg dark:border-sky-700/50 dark:bg-slate-800/80 dark:text-sky-200 lg:block">
            {t('report.scoreBreakdown')}
          </div>
          <div className="float-soft-delay pointer-events-none absolute bottom-28 right-24 hidden rounded-lg border border-emerald-200/70 bg-white/80 px-4 py-3 text-sm font-bold text-emerald-700 shadow-lg dark:border-emerald-700/50 dark:bg-slate-800/80 dark:text-emerald-200 lg:block">
            {t('report.rewriteExamples')}
          </div>
        </section>

        <aside className="auth-panel-enter flex w-full items-center justify-center rounded-lg border border-white/80 bg-white/86 p-5 shadow-2xl backdrop-blur-xl dark:border-slate-700/70 dark:bg-slate-950/86 lg:max-w-[480px] lg:p-8">
          <div className="w-full max-w-md">{children}</div>
        </aside>
      </div>
    </div>
  );
}
