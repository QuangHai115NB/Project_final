import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI } from '../../api/auth';
import { Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';
import AuthShell from './AuthShell';

function PasswordField({ label, value, onChange, placeholder, t }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-slate-200">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 pr-12 text-base text-gray-900 transition-all hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
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
    <AuthShell mode="register">
      <div className="mb-7 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-600 text-xl text-white shadow-lg shadow-emerald-600/20">
          ✨
        </div>
        <h1 className="text-3xl font-black text-gray-950 dark:text-white">CV Reviewer</h1>
        <p className="mt-2 text-gray-500 dark:text-slate-400">{t('auth.registerSubtitle')}</p>
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

          <p className="text-center text-sm text-gray-500 dark:text-slate-400">
            {t('auth.hasAccount')}{' '}
            <Link to="/auth/login" className="font-semibold text-primary hover:underline">
              {t('auth.login')}
            </Link>
          </p>
      </form>
    </AuthShell>
  );
}
