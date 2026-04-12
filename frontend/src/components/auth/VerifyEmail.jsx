import { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { authAPI } from '../../api/auth';
import OtpInput from './OtpInput';
import { Button } from '../shared';

export default function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || '';
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) {
      setError('Vui lòng nhập đủ 6 chữ số');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { data } = await authAPI.verifyEmail(email, otp);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Mã OTP không đúng hoặc đã hết hạn');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="w-full max-w-md text-center">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-4xl mb-4">📧</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Xác thực email</h2>
          <p className="text-gray-500 mb-6">
            Nhập mã OTP đã gửi đến<br />
            <span className="font-semibold text-primary">{email || 'email của bạn'}</span>
          </p>
          <form onSubmit={handleSubmit} className="space-y-6">
            <OtpInput value={otp} onChange={setOtp} length={6} />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <Button type="submit" loading={loading} className="w-full">
              Xác thực
            </Button>
          </form>
          <p className="text-sm text-gray-500 mt-4">
            Chưa nhận được mã?{' '}
            <Link to="/auth/register" className="text-primary hover:underline">Đăng ký lại</Link>
          </p>
        </div>
      </div>
    </div>
  );
}