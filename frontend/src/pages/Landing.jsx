import { Link } from 'react-router-dom';
import { Bolt, Download, FileCheck2, Lightbulb, LockKeyhole, Rocket, SearchCheck, Target } from 'lucide-react';
import { Button } from '../components/shared';
import { LanguageToggle, useLanguage } from '../i18n/LanguageContext';
import { ThemeToggle } from '../theme/ThemeContext';

export default function Landing() {
  const { t } = useLanguage();
  const features = [
    { Icon: Target, title: t('landing.feature.match.title'), desc: t('landing.feature.match.desc') },
    { Icon: FileCheck2, title: t('landing.feature.review.title'), desc: t('landing.feature.review.desc') },
    { Icon: Lightbulb, title: t('landing.feature.suggest.title'), desc: t('landing.feature.suggest.desc') },
    { Icon: Download, title: t('landing.feature.export.title'), desc: t('landing.feature.export.desc') },
    { Icon: LockKeyhole, title: t('landing.feature.security.title'), desc: t('landing.feature.security.desc') },
    { Icon: Bolt, title: t('landing.feature.fast.title'), desc: t('landing.feature.fast.desc') },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-cyan-950">
      {/* Nav */}
      <nav className="px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-primary dark:text-blue-300">CV Reviewer</h1>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <LanguageToggle />
          <Link to="/auth/login"><Button variant="outline" size="sm">{t('landing.login')}</Button></Link>
          <Link to="/auth/register"><Button size="sm">{t('landing.register')}</Button></Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/25">
          <SearchCheck size={34} aria-hidden="true" />
        </div>
        <h1 className="text-5xl font-black text-gray-800 mb-4 dark:text-slate-100">
          {t('landing.title')}<br />
          <span className="text-primary">{t('landing.titleAccent')}</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto dark:text-slate-300">
          {t('landing.subtitle')}
        </p>
        <Link to="/auth/register">
          <Button size="lg" className="px-10 py-4 text-lg">
            <Rocket size={20} aria-hidden="true" />
            {t('landing.cta')}
          </Button>
        </Link>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        {features.map(({ Icon, ...f }, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-100 p-6 dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg bg-blue-50 text-blue-700 dark:bg-sky-950/45 dark:text-sky-200">
              <Icon size={22} aria-hidden="true" />
            </div>
            <h3 className="font-bold text-gray-800 mb-2 dark:text-slate-100">{f.title}</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
