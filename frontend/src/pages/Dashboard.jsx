import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { cvAPI, jdAPI, matchAPI } from '../api/auth';
import { CVUploader, CVList } from '../components/cv';
import { JDUploader, JDList } from '../components/jd';
import { MatchMaker, MatchReport } from '../components/match';
import { Button, Card, Modal, useToast, LoadingSpinner } from '../components/shared';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { toast, showToast } = useToast();

  const [cvs, setCvs] = useState([]);
  const [jds, setJds] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loadingCvs, setLoadingCvs] = useState(true);
  const [loadingJds, setLoadingJds] = useState(true);
  const [loadingMatches, setLoadingMatches] = useState(true);

  const [showUploadCv, setShowUploadCv] = useState(false);
  const [showUploadJd, setShowUploadJd] = useState(false);
  const [showMatchModal, setShowMatchModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [currentMatchId, setCurrentMatchId] = useState(null);

  useEffect(() => {
    fetchCvs();
    fetchJds();
    fetchMatches();
  }, []);

  const fetchCvs = async () => {
    try {
      const { data } = await cvAPI.list();
      setCvs(data.cvs || []);
    } catch { /* ignore */ }
    finally { setLoadingCvs(false); }
  };

  const fetchJds = async () => {
    try {
      const { data } = await jdAPI.list();
      setJds(data.jds || []);
    } catch { /* ignore */ }
    finally { setLoadingJds(false); }
  };

  const fetchMatches = async () => {
    try {
      const { data } = await matchAPI.list();
      setMatches(data.matches || []);
    } catch { /* ignore */ }
    finally { setLoadingMatches(false); }
  };

  const handleDeleteCv = async (cvId) => {
    if (!confirm('Xóa CV này?')) return;
    try {
      await cvAPI.delete(cvId);
      setCvs((prev) => prev.filter((c) => c.id !== cvId));
      showToast('Đã xóa CV', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Xóa thất bại', 'error');
    }
  };

  const handleDeleteJd = async (jdId) => {
    if (!confirm('Xóa JD này?')) return;
    try {
      await jdAPI.delete(jdId);
      setJds((prev) => prev.filter((j) => j.id !== jdId));
      showToast('Đã xóa JD', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Xóa thất bại', 'error');
    }
  };

  const handleMatchSuccess = (data) => {
    setShowMatchModal(false);
    setCurrentMatchId(data.match_id);
    setShowReportModal(true);
    fetchMatches();
    showToast('So khớp thành công!', 'success');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <toast.Component />}

      {/* Top Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-primary">📋 CV Reviewer</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <Button variant="secondary" size="sm" onClick={logout}>Đăng xuất</Button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
          <div className="flex gap-3">
            <Button onClick={() => setShowMatchModal(true)}>🔗 So khớp</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* CV Column */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800">📄 CV ({cvs.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadCv(true)}>+ Thêm CV</Button>
            </div>
            <CVList cvs={cvs} onDelete={handleDeleteCv} loading={loadingCvs} />
          </div>

          {/* JD Column */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800">💼 JD ({jds.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadJd(true)}>+ Thêm JD</Button>
            </div>
            <JDList jds={jds} onDelete={handleDeleteJd} loading={loadingJds} />
          </div>

          {/* Match History Column */}
          <div className="space-y-4">
            <h3 className="font-bold text-gray-800">📜 Lịch sử so khớp ({matches.length})</h3>
            {loadingMatches ? (
              <LoadingSpinner size="sm" />
            ) : matches.length === 0 ? (
              <Card className="text-center py-8 text-gray-400">
                <div className="text-4xl mb-2">📝</div>
                <p className="text-sm">Chưa có lịch sử so khớp</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {matches.map((m) => (
                  <Card key={m.id} hoverable onClick={() => { setCurrentMatchId(m.id); setShowReportModal(true); }}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-sm text-gray-800">{m.cv_title}</p>
                        <p className="text-xs text-gray-500">vs {m.jd_title}</p>
                        {m.created_at && <p className="text-xs text-gray-400 mt-1">{new Date(m.created_at).toLocaleDateString('vi-VN')}</p>}
                      </div>
                      <div className={`text-xl font-bold ${m.similarity_score >= 75 ? 'text-success' : m.similarity_score >= 55 ? 'text-warning' : 'text-danger'}`}>
                        {m.similarity_score.toFixed(0)}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      <Modal isOpen={showUploadCv} onClose={() => setShowUploadCv(false)} title="📄 Thêm CV mới" size="md">
        <CVUploader onSuccess={(data) => { setShowUploadCv(false); fetchCvs(); showToast('Đã tải CV lên!', 'success'); }} />
      </Modal>

      <Modal isOpen={showUploadJd} onClose={() => setShowUploadJd(false)} title="💼 Thêm JD mới" size="lg">
        <JDUploader onSuccess={(data) => { setShowUploadJd(false); fetchJds(); showToast('Đã tải JD lên!', 'success'); }} />
      </Modal>

      <Modal isOpen={showMatchModal} onClose={() => setShowMatchModal(false)} title="🔗 So khớp CV-JD" size="lg">
        <MatchMaker cvs={cvs} jds={jds} onSuccess={handleMatchSuccess} />
      </Modal>

      <Modal isOpen={showReportModal} onClose={() => setShowReportModal(false)} title="📊 Báo cáo so khớp" size="xl">
        {currentMatchId && <MatchReport matchId={currentMatchId} />}
      </Modal>
    </div>
  );
}