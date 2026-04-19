import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { LockKeyhole } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';
import AuthShell from './AuthShell';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || t('auth.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell mode="login">
      <div className="mb-7 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-xl text-white shadow-lg shadow-blue-600/20">
          <LockKeyhole size={22} aria-hidden="true" />
        </div>
        <h1 className="text-3xl font-black text-gray-950 dark:text-white">CV Reviewer</h1>
        <p className="mt-2 text-gray-500 dark:text-slate-400">{t('auth.loginSubtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900">
          {error && (
            <div className="ui-soft-red rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">Email</label>
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-base text-gray-900 transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">{t('auth.password')}</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 pr-12 text-base text-gray-900 transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
              >
                {showPassword ? t('auth.hide') : t('auth.show')}
              </button>
            </div>
          </div>

          <div className="text-right">
            <Link to="/auth/forgot-password" className="text-sm text-primary hover:underline">
              {t('auth.forgotPassword')}
            </Link>
          </div>

          <Button type="submit" loading={loading} className="w-full">
            {t('auth.login')}
          </Button>

          <p className="text-center text-sm text-gray-500 dark:text-slate-400">
            {t('auth.noAccount')}{' '}
            <Link to="/auth/register" className="font-semibold text-primary hover:underline">
              {t('auth.registerNow')}
            </Link>
          </p>
      </form>
    </AuthShell>
  );
}
