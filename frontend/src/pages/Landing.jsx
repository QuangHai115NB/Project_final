import { Link } from 'react-router-dom';
import { Button } from '../components/shared';

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-100">
      {/* Nav */}
      <nav className="px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-primary">📋 CV Reviewer</h1>
        <div className="flex gap-3">
          <Link to="/auth/login"><Button variant="outline" size="sm">Đăng nhập</Button></Link>
          <Link to="/auth/register"><Button size="sm">Đăng ký</Button></Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="text-6xl mb-6">🔍</div>
        <h1 className="text-5xl font-black text-gray-800 mb-4">
          So khớp CV với JD<br />
          <span className="text-primary">thông minh hơn bao giờ hết</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          Phân tích CV của bạn bằng AI, so sánh với yêu cầu công việc và nhận báo cáo chi tiết giúp bạn cải thiện cơ hội việc làm
        </p>
        <Link to="/auth/register">
          <Button size="lg" className="text-lg px-10 py-4">🚀 Bắt đầu ngay — Miễn phí</Button>
        </Link>
      </div>

      {/* Features */}
      <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { icon: '🎯', title: 'So khớp chính xác', desc: '5 layers phân tích: skills, semantic, keywords, experience, structure' },
          { icon: '📄', title: 'Review toàn diện', desc: 'Kiểm tra cấu trúc CV, ngữ pháp, tiếng Anh, bullet quality' },
          { icon: '💡', title: 'Gợi ý thông minh', desc: 'Đề xuất cải thiện cụ thể theo từng lỗi với AI-powered rewrite' },
          { icon: '📥', title: 'Xuất báo cáo Word', desc: 'Tải báo cáo chi tiết dưới dạng .docx để chia sẻ hoặc in ấn' },
          { icon: '🔐', title: 'Bảo mật', desc: 'JWT authentication, refresh token rotation, OTP verification' },
          { icon: '⚡', title: 'Nhanh chóng', desc: 'Upload CV, dán JD, nhận kết quả trong vài giây' },
        ].map((f, i) => (
          <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="text-4xl mb-3">{f.icon}</div>
            <h3 className="font-bold text-gray-800 mb-2">{f.title}</h3>
            <p className="text-sm text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}