import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-6 inline-flex text-sm font-semibold text-primary hover:underline">
          {t('auth.backHome')}
        </Link>

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary">CV Reviewer</h1>
          <p className="mt-2 text-gray-500">{t('auth.loginSubtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 rounded-lg bg-white p-8 shadow-xl">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-base transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t('auth.password')}</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-2.5 pr-12 text-base transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-gray-500 hover:text-gray-700"
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

          <p className="text-center text-sm text-gray-500">
            {t('auth.noAccount')}{' '}
            <Link to="/auth/register" className="font-semibold text-primary hover:underline">
              {t('auth.registerNow')}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
