import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../../api/auth';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [step, setStep] = useState('input'); // 'input' | 'reset'
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setError('');
    try {
      await authAPI.forgotPassword(email);
      setSuccess('Mã OTP đã được gửi đến email của bạn.');
      setStep('reset');
    } catch (err) {
      setError(err.response?.data?.error || 'Không thể gửi mã OTP. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Mật khẩu phải có ít nhất 8 ký tự.');
      return;
    }
    setLoading(true);
    try {
      await authAPI.resetPassword(email, otp, newPassword);
      setSuccess('Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay.');
      setStep('done');
    } catch (err) {
      setError(err.response?.data?.error || 'Mã OTP không đúng hoặc đã hết hạn.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary">CV Reviewer</h1>
          <p className="text-gray-500 mt-2">
            {step === 'done' ? 'Thành công' : 'Khôi phục mật khẩu'}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-5">
          {step === 'done' ? (
            <div className="text-center space-y-4">
              <div className="text-5xl">✅</div>
              <p className="text-gray-600">{success}</p>
              <Link
                to="/auth/login"
                className="block w-full text-center bg-primary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity"
              >
                Đăng nhập ngay
              </Link>
            </div>
          ) : step === 'reset' ? (
            <form onSubmit={handleResetPassword} className="space-y-5">
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm">
                {success}
              </div>
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
                  {error}
                </div>
              )}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  disabled
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-gray-500 text-base"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Mã OTP</label>
                <input
                  type="text"
                  placeholder="Nhập mã 6 chữ số"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  maxLength={6}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-base focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all hover:border-gray-400 text-center text-2xl tracking-widest font-mono"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Mật khẩu mới</label>
                <input
                  type="password"
                  placeholder="Ít nhất 8 ký tự"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-base focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all hover:border-gray-400"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Xác nhận mật khẩu mới</label>
                <input
                  type="password"
                  placeholder="Nhập lại mật khẩu mới"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-base focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all hover:border-gray-400"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-60"
              >
                {loading ? 'Đang xử lý...' : 'Đặt lại mật khẩu'}
              </button>
              <p className="text-center text-gray-500 text-sm">
                <button
                  type="button"
                  onClick={() => { setStep('input'); setSuccess(''); setError(''); }}
                  className="text-primary hover:underline"
                >
                  ← Gửi lại mã OTP
                </button>
              </p>
            </form>
          ) : (
            <form onSubmit={handleRequestOtp} className="space-y-5">
              <div className="text-center">
                <div className="text-4xl mb-3">🔑</div>
                <h2 className="text-xl font-bold text-gray-800">Quên mật khẩu?</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Nhập email đã đăng ký, chúng tôi sẽ gửi mã OTP để đặt lại mật khẩu.
                </p>
              </div>
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm">
                  {error}
                </div>
              )}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Email</label>
                <input
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-base focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all hover:border-gray-400"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-white font-semibold py-3 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-60"
              >
                {loading ? 'Đang gửi mã OTP...' : 'Gửi mã OTP'}
              </button>
              <p className="text-center text-gray-500 text-sm">
                Nhớ mật khẩu rồi?{' '}
                <Link to="/auth/login" className="text-primary font-semibold hover:underline">
                  Đăng nhập
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
