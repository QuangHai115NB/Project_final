import { Link } from 'react-router-dom';
import { Button } from '../components/shared';
import { LanguageToggle, useLanguage } from '../i18n/LanguageContext';

export default function Landing() {
  const { t } = useLanguage();
  const features = [
    { icon: '🎯', title: t('landing.feature.match.title'), desc: t('landing.feature.match.desc') },
    { icon: '📄', title: t('landing.feature.review.title'), desc: t('landing.feature.review.desc') },
    { icon: '💡', title: t('landing.feature.suggest.title'), desc: t('landing.feature.suggest.desc') },
    { icon: '📥', title: t('landing.feature.export.title'), desc: t('landing.feature.export.desc') },
    { icon: '🔐', title: t('landing.feature.security.title'), desc: t('landing.feature.security.desc') },
    { icon: '⚡', title: t('landing.feature.fast.title'), desc: t('landing.feature.fast.desc') },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-cyan-50">
      {/* Nav */}
      <nav className="px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-primary">📋 CV Reviewer</h1>
        <div className="flex items-center gap-3">
          <LanguageToggle />
          <Link to="/auth/login"><Button variant="outline" size="sm">{t('landing.login')}</Button></Link>
          <Link to="/auth/register"><Button size="sm">{t('landing.register')}</Button></Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="text-6xl mb-6">🔍</div>
        <h1 className="text-5xl font-black text-gray-800 mb-4">
          {t('landing.title')}<br />
          <span className="text-primary">{t('landing.titleAccent')}</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          {t('landing.subtitle')}
        </p>
        <Link to="/auth/register">
          <Button size="lg" className="text-lg px-10 py-4">🚀 {t('landing.cta')}</Button>
        </Link>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        {features.map((f, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-100 p-6">
            <div className="text-4xl mb-3">{f.icon}</div>
            <h3 className="font-bold text-gray-800 mb-2">{f.title}</h3>
            <p className="text-sm text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
