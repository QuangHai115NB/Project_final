import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { cvAPI, jdAPI, matchAPI } from '../api/auth';
import { CVUploader, CVList } from '../components/cv';
import { JDUploader, JDList } from '../components/jd';
import { MatchMaker, MatchReport } from '../components/match';
import { Button, Card, Modal, LoadingSpinner } from '../components/shared';
import { useToast, Toast } from '../components/shared/Toast';
import { LanguageToggle, useLanguage } from '../i18n/LanguageContext';

function CvDetailModal({ cv, onClose }) {
  const { language, t } = useLanguage();
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
      .catch(() => setError(t('dashboard.fileErrorCv')))
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
            <span>{new Date(cv.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}</span>
          )}
        </div>

        {/* PDF viewer */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner text={t('common.fileLoading')} />
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
              {t('common.openNewTab')}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}

function JdDetailModal({ jd, onClose }) {
  const { language, t } = useLanguage();
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
      .catch(() => setError(t('dashboard.fileErrorJd')))
      .finally(() => setLoading(false));
  }, [jd?.id]);

  if (!jd) return null;

  // JD dạng text thuần → hiển thị text inline
  if (jd.original_filename === 'manual_jd.txt') {
    const text = jd.content_text || t('dashboard.noContent');
    return (
      <Modal isOpen={true} onClose={onClose} title={`💼 ${jd.title}`} size="lg">
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span>{t('dashboard.manualJd')}</span>
            {jd.created_at && (
              <span>{new Date(jd.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}</span>
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
            <span>{new Date(jd.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}</span>
          )}
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner text={t('common.fileLoading')} />
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
              {t('common.openNewTab')}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { language, t } = useLanguage();
  const { toast, showToast, hideToast } = useToast();

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
    if (!confirm(t('dashboard.deleteCvConfirm'))) return;
    try {
      await cvAPI.delete(cvId);
      setCvs((prev) => prev.filter((c) => c.id !== cvId));
      showToast(t('dashboard.cvDeleted'), 'success');
    } catch (err) {
      showToast(err.response?.data?.error || t('dashboard.deleteFailed'), 'error');
    }
  };

  const handleDeleteJd = async (jdId) => {
    if (!confirm(t('dashboard.deleteJdConfirm'))) return;
    try {
      await jdAPI.delete(jdId);
      setJds((prev) => prev.filter((j) => j.id !== jdId));
      showToast(t('dashboard.jdDeleted'), 'success');
    } catch (err) {
      showToast(err.response?.data?.error || t('dashboard.deleteFailed'), 'error');
    }
  };

  const handleCvSelect = (cv) => setSelectedCv(cv);
  const handleJdSelect = (jd) => setSelectedJd(jd);

  const handleMatchSuccess = (data) => {
    setShowMatchModal(false);
    setCurrentMatchId(data.match_id);
    setShowReportModal(true);
    fetchMatches();
    showToast(t('dashboard.matchSuccess'), 'success');
  };

  const scoreClass = (score) =>
    score >= 75 ? 'text-success' : score >= 55 ? 'text-warning' : 'text-danger';

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <Toast {...toast} onClose={hideToast} />}

      {/* Top Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-primary">{t('app.name')}</h1>
          <div className="flex items-center gap-4">
            <LanguageToggle />
            <span className="text-sm text-gray-600">{user?.email}</span>
            <Button variant="secondary" size="sm" onClick={logout}>{t('dashboard.logout')}</Button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-800">{t('dashboard.title')}</h2>
          <Button onClick={() => setShowMatchModal(true)}>{t('dashboard.match')}</Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* CV Column */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-gray-800">CV ({cvs.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadCv(true)}>{t('dashboard.addCv')}</Button>
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
              <h3 className="font-bold text-gray-800">JD ({jds.length})</h3>
              <Button size="sm" variant="secondary" onClick={() => setShowUploadJd(true)}>{t('dashboard.addJd')}</Button>
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
            <h3 className="font-bold text-gray-800">{t('dashboard.matchHistory', { count: matches.length })}</h3>
            {loadingMatches ? (
              <div className="flex justify-center py-8"><LoadingSpinner size="sm" /></div>
            ) : matches.length === 0 ? (
              <Card className="text-center py-8 text-gray-400">
                <div className="mb-2 text-4xl">□</div>
                <p className="text-sm">{t('dashboard.noMatchHistory')}</p>
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
                            {new Date(m.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}
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
      <Modal isOpen={showUploadCv} onClose={() => setShowUploadCv(false)} title={t('dashboard.addNewCv')} size="md">
        <CVUploader onSuccess={() => { setShowUploadCv(false); fetchCvs(); showToast(t('dashboard.cvUploaded'), 'success'); }} />
      </Modal>

      <Modal isOpen={showUploadJd} onClose={() => setShowUploadJd(false)} title={t('dashboard.addNewJd')} size="lg">
        <JDUploader onSuccess={() => { setShowUploadJd(false); fetchJds(); showToast(t('dashboard.jdUploaded'), 'success'); }} />
      </Modal>

      <Modal isOpen={showMatchModal} onClose={() => setShowMatchModal(false)} title={t('dashboard.matchCvJd')} size="lg">
        <MatchMaker cvs={cvs} jds={jds} onSuccess={handleMatchSuccess} />
      </Modal>

      <Modal isOpen={showReportModal} onClose={() => { setShowReportModal(false); setCurrentMatchId(null); }} title={t('dashboard.matchReport')} size="xl">
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
