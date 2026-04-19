import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI } from '../../api/auth';
import { Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

function PasswordField({ label, value, onChange, placeholder, t }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required
          className="w-full rounded-lg border border-gray-300 px-4 py-2.5 pr-12 text-base transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-gray-500 hover:text-gray-700"
        >
          {show ? t('auth.hide') : t('auth.show')}
        </button>
      </div>
    </div>
  );
}

export default function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    if (password !== confirm) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    if (password.length < 8) {
      setError(t('auth.passwordTooShort'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authAPI.register(email, password);
      navigate('/auth/verify-email', { state: { email } });
    } catch (err) {
      setError(err.response?.data?.error || t('auth.registerFailed'));
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
          <p className="mt-2 text-gray-500">{t('auth.registerSubtitle')}</p>
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

          <PasswordField
            label={t('auth.password')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('auth.passwordMin')}
            t={t}
          />
          <PasswordField
            label={t('auth.confirmPassword')}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={t('auth.reenterPassword')}
            t={t}
          />

          <Button type="submit" loading={loading} className="w-full">
            {t('auth.register')}
          </Button>

          <p className="text-center text-sm text-gray-500">
            {t('auth.hasAccount')}{' '}
            <Link to="/auth/login" className="font-semibold text-primary hover:underline">
              {t('auth.login')}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
