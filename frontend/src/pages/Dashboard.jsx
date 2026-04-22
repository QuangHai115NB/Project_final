import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { cvAPI, jdAPI, matchAPI } from '../api/auth';
import { CVUploader, CVList } from '../components/cv';
import { JDUploader, JDList } from '../components/jd';
import { MatchMaker, MatchReport } from '../components/match';
import ProfileSettings from '../components/profile/ProfileSettings';
import { Button, Card, Modal, LoadingSpinner } from '../components/shared';
import { useToast, Toast } from '../components/shared/Toast';
import { LanguageToggle, useLanguage } from '../i18n/LanguageContext';
import { ThemeToggle } from '../theme/ThemeContext';

const MATCH_PAGE_SIZE = 8;

function getUserInitials(user) {
  const source = user?.full_name || user?.email || 'U';
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'U';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function UserAvatar({ user, size = 'md' }) {
  const initials = getUserInitials(user);
  const classes = size === 'sm' ? 'h-10 w-10 text-sm' : 'h-14 w-14 text-lg';

  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.full_name || user.email || 'User avatar'}
        className={`${classes} rounded-full object-cover ring-2 ring-blue-100 dark:ring-blue-900/40`}
      />
    );
  }

  return (
    <div
      className={`${classes} flex items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 font-black text-white ring-2 ring-blue-100 dark:ring-blue-900/40`}
    >
      {initials}
    </div>
  );
}

function PageHeader({ title, description, action }) {
  return (
    <div className="mb-6 flex flex-col gap-3 border-b border-gray-200 pb-5 dark:border-slate-700 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-100">{title}</h2>
        {description && <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">{description}</p>}
      </div>
      {action}
    </div>
  );
}

function CvDetailModal({ cv, onClose }) {
  const { language, t } = useLanguage();
  const [url, setUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    if (!cv) return;
    let cancelled = false;
    let nextUrl = null;
    setLoading(true);
    setError(null);
    setUrl(null);
    cvAPI.downloadFile(cv.id)
      .then(({ data }) => {
        nextUrl = URL.createObjectURL(data);
        if (cancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        setUrl(nextUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.response?.data?.error || t('dashboard.fileErrorCv'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (nextUrl) URL.revokeObjectURL(nextUrl);
    };
  }, [cv?.id, t]);

  if (!cv) return null;

  return (
    <Modal isOpen={true} onClose={onClose} title={`CV: ${cv.title}`} size="xl">
      <div className="space-y-3">
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>{cv.original_filename}</span>
          {cv.created_at && (
            <span>{new Date(cv.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}</span>
          )}
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner text={t('common.fileLoading')} />
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {url && !loading && (
          <iframe
            ref={iframeRef}
            src={`${url}#toolbar=1&navpanes=1&scrollbar=1`}
            className="w-full rounded-lg border border-gray-200"
            style={{ height: '70vh' }}
            title={`CV: ${cv.title}`}
          />
        )}

        {url && !loading && (
          <div className="text-center">
            <Button variant="secondary" size="sm" onClick={() => window.open(url, '_blank')}>
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
  const lowerFilename = jd?.original_filename?.toLowerCase() || '';
  const isTextFile = lowerFilename.endsWith('.txt');
  const isPdfFile = lowerFilename.endsWith('.pdf');

  useEffect(() => {
    if (!jd) return;
    let cancelled = false;
    let nextUrl = null;
    setLoading(true);
    setError(null);
    setUrl(null);

    if (jd.original_filename === 'manual_jd.txt') {
      setLoading(false);
      return;
    }

    jdAPI.downloadFile(jd.id)
      .then(({ data }) => {
        nextUrl = URL.createObjectURL(data);
        if (cancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        setUrl(nextUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.response?.data?.error || t('dashboard.fileErrorJd'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (nextUrl) URL.revokeObjectURL(nextUrl);
    };
  }, [jd?.id, t]);

  if (!jd) return null;

  if (jd.original_filename === 'manual_jd.txt') {
    const text = jd.content_text || t('dashboard.noContent');
    return (
      <Modal isOpen={true} onClose={onClose} title={`JD: ${jd.title}`} size="lg">
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span>{t('dashboard.manualJd')}</span>
            {jd.created_at && (
              <span>{new Date(jd.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}</span>
            )}
          </div>
          <div className="max-h-[60vh] overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">{text}</pre>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={`JD: ${jd.title}`} size="xl">
      <div className="space-y-3">
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span>{jd.original_filename}</span>
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
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {url && !loading && (
          isTextFile ? (
            <iframe
              ref={iframeRef}
              src={url}
              className="w-full rounded-lg border border-gray-200 bg-gray-50"
              style={{ height: '70vh' }}
              title={`JD: ${jd.title}`}
            />
          ) : isPdfFile ? (
            <iframe
              ref={iframeRef}
              src={`${url}#toolbar=1&navpanes=1&scrollbar=1`}
              className="w-full rounded-lg border border-gray-200"
              style={{ height: '70vh' }}
              title={`JD: ${jd.title}`}
            />
          ) : (
            <iframe
              src={`https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`}
              className="w-full rounded-lg border border-gray-200"
              style={{ height: '70vh' }}
              title={`JD: ${jd.title}`}
            />
          )
        )}

        {url && !loading && (
          <div className="text-center">
            <Button variant="secondary" size="sm" onClick={() => window.open(url, '_blank')}>
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
  const tx = (key, fallback, params = {}) => {
    const value = t(key, params);
    return value === key ? fallback : value;
  };

  const [activePage, setActivePage] = useState('overview');
  const [cvs, setCvs] = useState([]);
  const [jds, setJds] = useState([]);
  const [matches, setMatches] = useState([]);
  const [matchPagination, setMatchPagination] = useState({
    limit: MATCH_PAGE_SIZE,
    offset: 0,
    total: 0,
    has_next: false,
    has_prev: false,
  });
  const [loadingCvs, setLoadingCvs] = useState(true);
  const [loadingJds, setLoadingJds] = useState(true);
  const [loadingMatches, setLoadingMatches] = useState(true);

  const [showUploadCv, setShowUploadCv] = useState(false);
  const [showUploadJd, setShowUploadJd] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [currentMatchId, setCurrentMatchId] = useState(null);
  const [selectedCv, setSelectedCv] = useState(null);
  const [selectedJd, setSelectedJd] = useState(null);

  const navItems = useMemo(() => ([
    { id: 'overview', label: tx('nav.overview', 'Tổng quan') },
    { id: 'cvs', label: tx('nav.cvs', 'Quản lý CV') },
    { id: 'jds', label: tx('nav.jds', 'Quản lý JD') },
    { id: 'match', label: tx('nav.match', 'So khớp CV-JD') },
    { id: 'reports', label: tx('nav.reports', 'Lịch sử báo cáo') },
    { id: 'profile', label: tx('nav.profile', 'Tài khoản') },
  ]), [language]);

  useEffect(() => {
    fetchCvs();
    fetchJds();
    fetchMatches(0);
  }, []);

  const fetchCvs = async () => {
    setLoadingCvs(true);
    try {
      const { data } = await cvAPI.list();
      setCvs(data.cvs || []);
    } catch (err) {
      showToast(err.response?.data?.error || tx('dashboard.loadCvFailed', 'Không thể tải danh sách CV'), 'error');
    } finally {
      setLoadingCvs(false);
    }
  };

  const fetchJds = async () => {
    setLoadingJds(true);
    try {
      const { data } = await jdAPI.list();
      setJds(data.jds || []);
    } catch (err) {
      showToast(err.response?.data?.error || tx('dashboard.loadJdFailed', 'Không thể tải danh sách JD'), 'error');
    } finally {
      setLoadingJds(false);
    }
  };

  const fetchMatches = async (offset = matchPagination.offset) => {
    setLoadingMatches(true);
    try {
      const { data } = await matchAPI.list(MATCH_PAGE_SIZE, offset);
      setMatches(data.matches || []);
      setMatchPagination(data.pagination || {
        limit: MATCH_PAGE_SIZE,
        offset,
        total: data.matches?.length || 0,
        has_next: false,
        has_prev: offset > 0,
      });
    } catch (err) {
      showToast(err.response?.data?.error || tx('dashboard.loadReportsFailed', 'Không thể tải lịch sử báo cáo'), 'error');
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleDeleteCv = async (cvId) => {
    if (!confirm(t('dashboard.deleteCvConfirm'))) return;
    try {
      await cvAPI.delete(cvId);
      setCvs((prev) => prev.filter((c) => c.id !== cvId));
      fetchMatches(0);
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
      fetchMatches(0);
      showToast(t('dashboard.jdDeleted'), 'success');
    } catch (err) {
      showToast(err.response?.data?.error || t('dashboard.deleteFailed'), 'error');
    }
  };

  const handleDeleteMatch = async (matchId) => {
    if (!confirm(tx('dashboard.deleteReportConfirm', 'Xóa báo cáo này khỏi lịch sử?'))) return;
    try {
      await matchAPI.delete(matchId);
      const nextOffset = matches.length === 1 && matchPagination.offset > 0
        ? Math.max(0, matchPagination.offset - MATCH_PAGE_SIZE)
        : matchPagination.offset;
      await fetchMatches(nextOffset);
      showToast(tx('dashboard.reportDeleted', 'Đã xóa báo cáo'), 'success');
    } catch (err) {
      showToast(err.response?.data?.error || t('dashboard.deleteFailed'), 'error');
    }
  };

  const handleMatchSuccess = (data) => {
    setCurrentMatchId(data.match_id);
    setShowReportModal(true);
    setActivePage('reports');
    fetchMatches(0);
    showToast(t('dashboard.matchSuccess'), 'success');
  };

  const scoreClass = (score) =>
    score >= 75 ? 'text-success' : score >= 55 ? 'text-warning' : 'text-danger';

  const openReport = (matchId) => {
    setCurrentMatchId(matchId);
    setShowReportModal(true);
  };

  const reportStart = matchPagination.total === 0 ? 0 : matchPagination.offset + 1;
  const reportEnd = Math.min(matchPagination.offset + matchPagination.limit, matchPagination.total);

  const renderOverview = () => (
    <>
      <PageHeader
        title={t('dashboard.title')}
        description={tx('dashboard.overviewDesc', 'Theo dõi dữ liệu CV, JD và báo cáo so khớp trong một nơi.')}
        action={<Button onClick={() => setActivePage('match')}>{t('dashboard.match')}</Button>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm font-semibold text-gray-500">CV</p>
          <p className="mt-2 text-3xl font-black text-gray-900">{cvs.length}</p>
          <p className="mt-1 text-sm text-gray-500">{tx('dashboard.cvCountHelp', 'Hồ sơ đã tải lên')}</p>
        </Card>
        <Card>
          <p className="text-sm font-semibold text-gray-500">JD</p>
          <p className="mt-2 text-3xl font-black text-gray-900">{jds.length}</p>
          <p className="mt-1 text-sm text-gray-500">{tx('dashboard.jdCountHelp', 'Mô tả công việc đã lưu')}</p>
        </Card>
        <Card>
          <p className="text-sm font-semibold text-gray-500">{tx('dashboard.reports', 'Báo cáo')}</p>
          <p className="mt-2 text-3xl font-black text-gray-900">{matchPagination.total}</p>
          <p className="mt-1 text-sm text-gray-500">{tx('dashboard.reportCountHelp', 'Lịch sử so khớp đã tạo')}</p>
        </Card>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="font-bold text-gray-900">{tx('dashboard.quickActions', 'Thao tác nhanh')}</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Button variant="secondary" onClick={() => setShowUploadCv(true)}>{t('dashboard.addCv')}</Button>
            <Button variant="secondary" onClick={() => setShowUploadJd(true)}>{t('dashboard.addJd')}</Button>
            <Button variant="outline" onClick={() => setActivePage('reports')}>{tx('dashboard.viewReports', 'Xem báo cáo')}</Button>
            <Button onClick={() => setActivePage('match')}>{t('dashboard.match')}</Button>
          </div>
        </Card>
        <Card>
          <h3 className="font-bold text-gray-900">{tx('dashboard.latestReports', 'Báo cáo gần đây')}</h3>
          <div className="mt-4 space-y-3">
            {loadingMatches ? (
              <LoadingSpinner size="sm" />
            ) : matches.length === 0 ? (
              <p className="text-sm text-gray-500">{t('dashboard.noMatchHistory')}</p>
            ) : matches.slice(0, 3).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => openReport(m.id)}
                className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white p-3 text-left hover:border-primary/40"
              >
                <span>
                  <span className="block text-sm font-semibold text-gray-800">{m.cv_title}</span>
                  <span className="block text-xs text-gray-500">vs {m.jd_title}</span>
                </span>
                <span className={`text-lg font-bold ${scoreClass(m.similarity_score)}`}>
                  {(m.similarity_score ?? 0).toFixed(0)}
                </span>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </>
  );

  const renderCvs = () => (
    <>
      <PageHeader
        title={tx('nav.cvs', 'Quản lý CV')}
        description={tx('dashboard.cvPageDesc', 'Tải lên, xem trước và xóa CV của bạn.')}
        action={<Button onClick={() => setShowUploadCv(true)}>{t('dashboard.addCv')}</Button>}
      />
      <CVList cvs={cvs} onDelete={handleDeleteCv} onSelect={setSelectedCv} loading={loadingCvs} />
    </>
  );

  const renderJds = () => (
    <>
      <PageHeader
        title={tx('nav.jds', 'Quản lý JD')}
        description={tx('dashboard.jdPageDesc', 'Lưu JD bằng file hoặc nhập nội dung thủ công.')}
        action={<Button onClick={() => setShowUploadJd(true)}>{t('dashboard.addJd')}</Button>}
      />
      <JDList jds={jds} onDelete={handleDeleteJd} onSelect={setSelectedJd} loading={loadingJds} />
    </>
  );

  const renderMatch = () => (
    <>
      <PageHeader
        title={t('dashboard.matchCvJd')}
        description={tx('dashboard.matchPageDesc', 'Chọn một CV và một JD để tạo báo cáo đánh giá phù hợp.')}
      />
      <MatchMaker cvs={cvs} jds={jds} onSuccess={handleMatchSuccess} />
    </>
  );

  const renderReports = () => (
    <>
      <PageHeader
        title={tx('nav.reports', 'Lịch sử báo cáo')}
        description={tx('dashboard.reportsPageDesc', 'Xem, tải Word hoặc xóa các báo cáo đã tạo.')}
      />
      {loadingMatches ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : matches.length === 0 ? (
        <Card className="py-10 text-center text-gray-500">
          <p>{t('dashboard.noMatchHistory')}</p>
          <Button className="mt-4" onClick={() => setActivePage('match')}>{t('dashboard.match')}</Button>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {matches.map((m) => (
              <Card key={m.id}>
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <button type="button" onClick={() => openReport(m.id)} className="text-left">
                    <p className="font-semibold text-gray-900">{m.cv_title}</p>
                    <p className="text-sm text-gray-500">vs {m.jd_title}</p>
                    {m.created_at && (
                      <p className="mt-1 text-xs text-gray-400">
                        {new Date(m.created_at).toLocaleString(language === 'vi' ? 'vi-VN' : 'en-US')}
                      </p>
                    )}
                  </button>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`text-2xl font-black ${scoreClass(m.similarity_score)}`}>
                      {(m.similarity_score ?? 0).toFixed(0)}
                    </span>
                    <Button size="sm" variant="outline" onClick={() => openReport(m.id)}>
                      {tx('dashboard.viewReport', 'Xem')}
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => handleDeleteMatch(m.id)}>
                      {tx('dashboard.deleteReport', 'Xóa báo cáo')}
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
          <div className="mt-6 flex flex-col gap-3 border-t border-gray-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-gray-500">
              {tx('dashboard.paginationSummary', 'Hiển thị {start}-{end} trên {total} báo cáo', {
                start: reportStart,
                end: reportEnd,
                total: matchPagination.total,
              })}
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!matchPagination.has_prev}
                onClick={() => fetchMatches(Math.max(0, matchPagination.offset - MATCH_PAGE_SIZE))}
              >
                {tx('dashboard.prevPage', 'Trang trước')}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={!matchPagination.has_next}
                onClick={() => fetchMatches(matchPagination.offset + MATCH_PAGE_SIZE)}
              >
                {tx('dashboard.nextPage', 'Trang sau')}
              </Button>
            </div>
          </div>
        </>
      )}
    </>
  );

  const renderProfile = () => (
    <>
      <PageHeader
        title={tx('nav.profile', 'Tài khoản')}
        description={tx('profile.pageDesc', 'Quản lý avatar, thông tin cá nhân và mật khẩu tài khoản.')}
      />
      <ProfileSettings t={t} tx={tx} showToast={showToast} />
    </>
  );

  const renderContent = () => {
    if (activePage === 'cvs') return renderCvs();
    if (activePage === 'jds') return renderJds();
    if (activePage === 'match') return renderMatch();
    if (activePage === 'reports') return renderReports();
    if (activePage === 'profile') return renderProfile();
    return renderOverview();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      {toast && <Toast {...toast} onClose={hideToast} />}

      <div className="flex min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-gray-200 bg-white dark:border-slate-800 dark:bg-slate-950 lg:flex lg:flex-col">
          <div className="border-b border-gray-200 p-5 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <UserAvatar user={user} />
              <div className="min-w-0">
                <h1 className="text-xl font-black text-primary dark:text-blue-300">{t('app.name')}</h1>
                <p className="truncate text-sm font-semibold text-gray-800 dark:text-slate-100">
                  {user?.full_name || tx('profile.noName', 'Người dùng')}
                </p>
                {user?.headline && (
                  <p className="truncate text-xs font-medium text-gray-600 dark:text-slate-300">{user.headline}</p>
                )}
                <p className="truncate text-xs text-gray-500 dark:text-slate-400">{user?.email}</p>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 p-3">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActivePage(item.id)}
                className={`w-full rounded-lg px-4 py-3 text-left text-sm font-semibold transition-colors ${
                  activePage === item.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="space-y-3 border-t border-gray-200 p-4 dark:border-slate-800">
            <ThemeToggle />
            <LanguageToggle />
            <Button variant="secondary" size="sm" className="w-full" onClick={logout}>
              {t('dashboard.logout')}
            </Button>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
          <header className="sticky top-0 z-30 border-b border-gray-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-950 lg:hidden">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <UserAvatar user={user} size="sm" />
                <div>
                  <h1 className="text-lg font-black text-primary dark:text-blue-300">{t('app.name')}</h1>
                  {user?.headline && (
                    <p className="max-w-[160px] truncate text-xs font-medium text-gray-700 dark:text-slate-200">
                      {user.headline}
                    </p>
                  )}
                  <p className="max-w-[160px] truncate text-xs text-gray-500 dark:text-slate-400">{user?.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <LanguageToggle />
                <Button variant="secondary" size="sm" onClick={logout}>{t('dashboard.logout')}</Button>
              </div>
            </div>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActivePage(item.id)}
                  className={`shrink-0 rounded-lg px-3 py-2 text-sm font-semibold ${
                    activePage === item.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-200'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </header>

          <main className="mx-auto w-full max-w-6xl px-4 py-6 lg:px-8">
            {renderContent()}
          </main>
        </div>
      </div>

      <Modal isOpen={showUploadCv} onClose={() => setShowUploadCv(false)} title={t('dashboard.addNewCv')} size="md">
        <CVUploader onSuccess={() => { setShowUploadCv(false); fetchCvs(); showToast(t('dashboard.cvUploaded'), 'success'); }} />
      </Modal>

      <Modal isOpen={showUploadJd} onClose={() => setShowUploadJd(false)} title={t('dashboard.addNewJd')} size="lg">
        <JDUploader onSuccess={() => { setShowUploadJd(false); fetchJds(); showToast(t('dashboard.jdUploaded'), 'success'); }} />
      </Modal>

      <Modal
        isOpen={showReportModal}
        onClose={() => { setShowReportModal(false); setCurrentMatchId(null); }}
        title={t('dashboard.matchReport')}
        size="xl"
      >
        {currentMatchId ? <MatchReport key={currentMatchId} matchId={currentMatchId} /> : null}
      </Modal>

      {selectedCv && <CvDetailModal cv={selectedCv} onClose={() => setSelectedCv(null)} />}
      {selectedJd && <JdDetailModal jd={selectedJd} onClose={() => setSelectedJd(null)} />}
    </div>
  );
}
