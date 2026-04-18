import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { cvAPI, jdAPI, matchAPI } from '../api/auth';
import { CVUploader, CVList } from '../components/cv';
import { JDUploader, JDList } from '../components/jd';
import { MatchMaker, MatchReport } from '../components/match';
import { Button, Card, Modal, LoadingSpinner } from '../components/shared';
import { useToast, Toast } from '../components/shared/Toast';

function CvDetailModal({ cv, onClose }) {
  const [url, setUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    if (!cv) return;
    setLoading(true);
    setError(null);
    setUrl(null);
    cvAPI.getSignedUrl(cv.id)
      .then(({ data }) => setUrl(data.url))
      .catch(() => setError('Không thể lấy file CV'))
      .finally(() => setLoading(false));
  }, [cv?.id]);

  if (!cv) return null;

  return (
    <Modal isOpen={true} onClose={onClose} title={`📄 ${cv.title}`} size="xl">
      <div className="space-y-3">
        {/* File meta */}
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>📎 {cv.original_filename}</span>
          {cv.created_at && (
            <span>{new Date(cv.created_at).toLocaleDateString('vi-VN')}</span>
          )}
        </div>

        {/* PDF viewer */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner text="Đang tải file..." />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl text-sm text-center">
            {error}
          </div>
        )}

        {url && !loading && (
          <iframe
            ref={iframeRef}
            src={`${url}#toolbar=1&navpanes=1&scrollbar=1`}
            className="w-full rounded-xl border border-gray-200"
            style={{ height: '70vh' }}
            title={`CV: ${cv.title}`}
          />
        )}

        {/* Fallback: nếu iframe không hoạt động, hiển thị nút mở tab mới */}
        {url && !loading && (
          <div className="text-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.open(url, '_blank')}
            >
              🔗 Mở trong tab mới
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}

function JdDetailModal({ jd, onClose }) {
  const [url, setUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    if (!jd) return;
    setLoading(true);
    setError(null);
    setUrl(null);

    // JD dạng text thuần → hiển thị text trực tiếp
    if (jd.original_filename === 'manual_jd.txt') {
      setLoading(false);
      return;
    }

    jdAPI.getSignedUrl(jd.id)
      .then(({ data }) => setUrl(data.url))
      .catch(() => setError('Không thể lấy file JD'))
      .finally(() => setLoading(false));
  }, [jd?.id]);

  if (!jd) return null;

  // JD dạng text thuần → hiển thị text inline
  if (jd.original_filename === 'manual_jd.txt') {
    const text = jd.content_text || 'Không có nội dung.';
    return (
      <Modal isOpen={true} onClose={onClose} title={`💼 ${jd.title}`} size="lg">
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span>📝 Nhập text thủ công</span>
            {jd.created_at && (
              <span>{new Date(jd.created_at).toLocaleDateString('vi-VN')}</span>
            )}
          </div>
          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 max-h-[60vh] overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">{text}</pre>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={`💼 ${jd.title}`} size="xl">
      <div className="space-y-3">
        {/* File meta */}
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>📎 {jd.original_filename}</span>
          {jd.created_at && (
            <span>{new Date(jd.created_at).toLocaleDateString('vi-VN')}</span>
          )}
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner text="Đang tải file..." />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl text-sm text-center">
            {error}
          </div>
        )}

        {url && !loading && (
          <>
            {/* TXT: hiển thị inline */}
            {jd.original_filename?.endsWith('.txt') ? (
              <iframe
                ref={iframeRef}
                src={url}
                className="w-full rounded-xl border border-gray-200 bg-gray-50"
                style={{ height: '70vh' }}
                title={`JD: ${jd.title}`}
              />
            ) : (
              /* PDF: dùng Google Docs viewer để hỗ trợ cross-origin */
              <iframe
                src={`https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`}
                className="w-full rounded-xl border border-gray-200"
                style={{ height: '70vh' }}
                title={`JD: ${jd.title}`}
              />
            )}
          </>
        )}

        {url && !loading && (
          <div className="text-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.open(url, '_blank')}
            >
              🔗 Mở trong tab mới
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}

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

  // CV / JD detail modals
  const [selectedCv, setSelectedCv] = useState(null);
  const [selectedJd, setSelectedJd] = useState(null);

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

  const handleCvSelect = (cv) => setSelectedCv(cv);
  const handleJdSelect = (jd) => setSelectedJd(jd);

  const handleMatchSuccess = (data) => {
    setShowMatchModal(false);
    setCurrentMatchId(data.match_id);
    setShowReportModal(true);
    fetchMatches();
    showToast('So khớp thành công!', 'success');
  };

  const scoreClass = (score) =>
    score >= 75 ? 'text-success' : score >= 55 ? 'text-warning' : 'text-danger';

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

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
          <Button onClick={() => setShowMatchModal(true)}>🔗 So khớp</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* CV Column */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800">📄 CV ({cvs.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadCv(true)}>+ Thêm CV</Button>
            </div>
            <CVList
              cvs={cvs}
              onDelete={handleDeleteCv}
              onSelect={handleCvSelect}
              loading={loadingCvs}
            />
          </div>

          {/* JD Column */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800">💼 JD ({jds.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadJd(true)}>+ Thêm JD</Button>
            </div>
            <JDList
              jds={jds}
              onDelete={handleDeleteJd}
              onSelect={handleJdSelect}
              loading={loadingJds}
            />
          </div>

          {/* Match History Column */}
          <div className="space-y-4">
            <h3 className="font-bold text-gray-800">📜 Lịch sử so khớp ({matches.length})</h3>
            {loadingMatches ? (
              <div className="flex justify-center py-8"><LoadingSpinner size="sm" /></div>
            ) : matches.length === 0 ? (
              <Card className="text-center py-8 text-gray-400">
                <div className="text-4xl mb-2">📝</div>
                <p className="text-sm">Chưa có lịch sử so khớp</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {matches.map((m) => (
                  <Card
                    key={m.id}
                    hoverable
                    onClick={() => { setCurrentMatchId(m.id); setShowReportModal(true); }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-sm text-gray-800">{m.cv_title}</p>
                        <p className="text-xs text-gray-500">vs {m.jd_title}</p>
                        {m.created_at && (
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(m.created_at).toLocaleDateString('vi-VN')}
                          </p>
                        )}
                      </div>
                      <div className={`text-xl font-bold ${scoreClass(m.similarity_score)}`}>
                        {(m.similarity_score ?? 0).toFixed(0)}
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
        <CVUploader onSuccess={() => { setShowUploadCv(false); fetchCvs(); showToast('Đã tải CV lên!', 'success'); }} />
      </Modal>

      <Modal isOpen={showUploadJd} onClose={() => setShowUploadJd(false)} title="💼 Thêm JD mới" size="lg">
        <JDUploader onSuccess={() => { setShowUploadJd(false); fetchJds(); showToast('Đã tải JD lên!', 'success'); }} />
      </Modal>

      <Modal isOpen={showMatchModal} onClose={() => setShowMatchModal(false)} title="🔗 So khớp CV-JD" size="lg">
        <MatchMaker cvs={cvs} jds={jds} onSuccess={handleMatchSuccess} />
      </Modal>

      <Modal isOpen={showReportModal} onClose={() => { setShowReportModal(false); setCurrentMatchId(null); }} title="📊 Báo cáo so khớp" size="xl">
        {currentMatchId ? <MatchReport key={currentMatchId} matchId={currentMatchId} /> : null}
      </Modal>

      {/* CV / JD Detail Modals */}
      {selectedCv && (
        <CvDetailModal cv={selectedCv} onClose={() => setSelectedCv(null)} />
      )}
      {selectedJd && (
        <JdDetailModal jd={selectedJd} onClose={() => setSelectedJd(null)} />
      )}
    </div>
  );
}
