import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminAPI } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { Button, Card, LoadingSpinner, Modal } from '../components/shared';
import { Toast, useToast } from '../components/shared/Toast';
import { formatApiDateTime } from '../utils/dateTime';

const PAGE_SIZE = 12;

function toDateInputValue(value) {
  const date = new Date(value);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
}

function defaultOverviewFilters() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 13);
  return {
    startDate: toDateInputValue(start),
    endDate: toDateInputValue(end),
    granularity: 'day',
  };
}

function formatDate(value) {
  if (!value) return 'Không giới hạn';
  return formatApiDateTime(value, 'vi-VN');
}

function scoreClass(score) {
  if (score >= 75) return 'text-green-600';
  if (score >= 55) return 'text-amber-600';
  return 'text-red-600';
}

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const { toast, showToast, hideToast } = useToast();
  const [activePage, setActivePage] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [userPagination, setUserPagination] = useState({ offset: 0, total: 0, has_next: false, has_prev: false });
  const [matches, setMatches] = useState([]);
  const [matchPagination, setMatchPagination] = useState({ offset: 0, total: 0, has_next: false, has_prev: false });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [matchSearch, setMatchSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [uploadingQr, setUploadingQr] = useState(false);
  const [overviewFilters, setOverviewFilters] = useState(defaultOverviewFilters);

  const navItems = useMemo(() => ([
    { id: 'overview', label: 'Tổng quan' },
    { id: 'users', label: 'Người dùng' },
    { id: 'matches', label: 'Lịch sử so khớp' },
    { id: 'payment', label: 'Thanh toán' },
  ]), []);

  useEffect(() => {
    fetchOverview();
    fetchUsers(0);
    fetchMatches(0);
    fetchPaymentInfo();
  }, []);

  const fetchOverview = async (filters = overviewFilters) => {
    try {
      const { data } = await adminAPI.overview(filters);
      setOverview(data);
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải tổng quan admin', 'error');
    }
  };

  const fetchUsers = async (offset = userPagination.offset, nextSearch = search) => {
    setLoading(true);
    try {
      const { data } = await adminAPI.listUsers(PAGE_SIZE, offset, nextSearch);
      setUsers(data.users || []);
      setUserPagination(data.pagination || {});
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải danh sách người dùng', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchMatches = async (offset = matchPagination.offset, nextSearch = matchSearch) => {
    setLoading(true);
    try {
      const { data } = await adminAPI.listMatches(PAGE_SIZE, offset, '', nextSearch);
      setMatches(data.matches || []);
      setMatchPagination(data.pagination || {});
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải lịch sử so khớp', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchPaymentInfo = async () => {
    try {
      const { data } = await adminAPI.getPaymentInfo();
      setPaymentInfo(data);
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải cấu hình thanh toán', 'error');
    }
  };

  const handleUploadQr = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadingQr(true);
    try {
      const { data } = await adminAPI.uploadPaymentQr(file);
      setPaymentInfo(data);
      showToast('Đã cập nhật mã QR thanh toán', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Upload QR thất bại', 'error');
    } finally {
      setUploadingQr(false);
      event.target.value = '';
    }
  };

  const handleDeleteQr = async () => {
    try {
      const { data } = await adminAPI.deletePaymentQr();
      setPaymentInfo(data);
      showToast('Đã xóa mã QR thanh toán', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Xóa QR thất bại', 'error');
    }
  };

  const openUser = async (userId) => {
    try {
      const { data } = await adminAPI.getUser(userId);
      setSelectedUser(data);
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải chi tiết người dùng', 'error');
    }
  };

  const openMatch = async (matchId) => {
    try {
      const { data } = await adminAPI.getMatch(matchId);
      setSelectedMatch(data);
    } catch (err) {
      showToast(err.response?.data?.error || 'Không thể tải báo cáo so khớp', 'error');
    }
  };

  const updateUser = async (userId, payload) => {
    try {
      await adminAPI.updateUser(userId, payload);
      await Promise.all([fetchOverview(), fetchUsers(userPagination.offset)]);
      if (selectedUser?.user?.id === userId) await openUser(userId);
      showToast('Đã cập nhật người dùng', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Cập nhật thất bại', 'error');
    }
  };

  const renderOverview = () => (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Tổng quan hệ thống</h2>
        <p className="mt-1 text-sm text-gray-500">Theo dõi người dùng, tài liệu và lịch sử so khớp toàn hệ thống.</p>
      </div>
      <form
        className="mb-5 grid gap-3 rounded-lg border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 md:grid-cols-[1fr_1fr_170px_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          fetchOverview(overviewFilters);
        }}
      >
        <label className="text-sm font-semibold text-gray-700 dark:text-slate-200">
          Từ ngày
          <input
            type="date"
            value={overviewFilters.startDate}
            onChange={(event) => setOverviewFilters((current) => ({ ...current, startDate: event.target.value }))}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
          />
        </label>
        <label className="text-sm font-semibold text-gray-700 dark:text-slate-200">
          Tới ngày
          <input
            type="date"
            value={overviewFilters.endDate}
            onChange={(event) => setOverviewFilters((current) => ({ ...current, endDate: event.target.value }))}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
          />
        </label>
        <label className="text-sm font-semibold text-gray-700 dark:text-slate-200">
          Thống kê
          <select
            value={overviewFilters.granularity}
            onChange={(event) => setOverviewFilters((current) => ({ ...current, granularity: event.target.value }))}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950 dark:text-white"
          >
            <option value="day">Theo ngày</option>
            <option value="month">Theo tháng</option>
            <option value="year">Theo năm</option>
          </select>
        </label>
        <div className="flex items-end">
          <Button type="submit" size="sm" className="w-full">Lọc</Button>
        </div>
      </form>
      {!overview ? <LoadingSpinner /> : (
        <>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Người dùng', overview.users],
            ['Premium', overview.premium_users],
            ['CV', overview.cvs],
            ['JD', overview.jds],
            ['So khớp', overview.matches],
            ['Admin', overview.admins],
            ['Active', overview.active_users],
            ['Free', overview.free_users],
          ].map(([label, value]) => (
            <Card key={label}>
              <p className="text-sm font-semibold text-gray-500 dark:text-gray-400">{label}</p>
              <p className="mt-2 text-3xl font-black text-gray-900 dark:text-white">{value}</p>
            </Card>
          ))}
        </div>
        <div className="mt-5 grid gap-4 xl:grid-cols-[1.45fr_1fr]">
          <DailyMatchesChart data={overview.matches_by_period || overview.matches_by_day || []} period={overview.period} />
          <TopUsersChart users={overview.top_users || []} />
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <PlanDistribution overview={overview} />
          <DocumentMix overview={overview} />
        </div>
        </>
      )}
    </>
  );

  const renderUsers = () => (
    <>
      <div className="mb-6 flex flex-col gap-3 border-b border-gray-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Quản lý người dùng</h2>
          <p className="mt-1 text-sm text-gray-500">Xem usage, khóa/mở tài khoản và nâng cấp gói.</p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            fetchUsers(0, search);
          }}
        >
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="Tìm email"
          />
          <Button type="submit" size="sm">Tìm</Button>
        </form>
      </div>
      {loading ? <LoadingSpinner /> : (
        <div className="space-y-3">
          {users.map((item) => (
            <Card key={item.id}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <button type="button" className="text-left" onClick={() => openUser(item.id)}>
                  <p className="font-bold text-gray-900">{item.email}</p>
                  <p className="text-sm text-gray-500">
                    {item.role} · {item.effective_plan} · CV {item.cv_count} · JD {item.jd_count} · Match {item.match_count}
                  </p>
                </button>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => openUser(item.id)}>Chi tiết</Button>
                  <Button size="sm" variant="secondary" onClick={() => updateUser(item.id, { plan: 'premium', extend_days: 30 })}>
                    +30 ngày
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => updateUser(item.id, { is_active: !item.is_active })}>
                    {item.is_active ? 'Khóa' : 'Mở khóa'}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
          <Pagination pagination={userPagination} onPage={fetchUsers} />
        </div>
      )}
    </>
  );

  const renderMatches = () => (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Lịch sử so khớp toàn hệ thống</h2>
        <p className="mt-1 text-sm text-gray-500">Admin có thể review từng báo cáo CV-JD đã tạo.</p>
      </div>
      {matchSearchForm}
      {loading ? <LoadingSpinner /> : (
        <div className="space-y-3">
          {matches.map((item) => (
            <Card key={item.id}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <button type="button" className="text-left" onClick={() => openMatch(item.id)}>
                  <p className="font-bold text-gray-900">{item.cv_title}</p>
                  <p className="text-sm text-gray-500">vs {item.jd_title}</p>
                  <p className="mt-1 text-xs text-gray-400">{item.user_email} · {formatDate(item.created_at)}</p>
                </button>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-black ${scoreClass(item.similarity_score)}`}>
                    {(item.similarity_score ?? 0).toFixed(0)}
                  </span>
                  <Button size="sm" variant="outline" onClick={() => openMatch(item.id)}>Review</Button>
                </div>
              </div>
            </Card>
          ))}
          <Pagination pagination={matchPagination} onPage={fetchMatches} />
        </div>
      )}
    </>
  );

  const renderPayment = () => (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Cấu hình thanh toán</h2>
        <p className="mt-1 text-sm text-gray-500">Upload ảnh QR ngân hàng để hiển thị cho người dùng khi nâng cấp tài khoản.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card>
          <h3 className="font-bold text-gray-900">Mã QR hiện tại</h3>
          {paymentInfo?.payment_qr_data_url ? (
            <img
              src={paymentInfo.payment_qr_data_url}
              alt="QR thanh toán"
              className="mt-4 aspect-square w-full rounded-lg border border-gray-200 object-contain"
            />
          ) : (
            <div className="mt-4 flex aspect-square w-full items-center justify-center rounded-lg border border-dashed border-gray-300 text-sm text-gray-500">
              Chưa có QR
            </div>
          )}
          <label className="mt-4 inline-flex w-full cursor-pointer items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            {uploadingQr ? 'Đang tải...' : 'Tải ảnh QR lên'}
            <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleUploadQr} disabled={uploadingQr} />
          </label>
          {paymentInfo?.payment_qr_data_url && (
            <Button className="mt-2 w-full" size="sm" variant="secondary" onClick={handleDeleteQr}>Xóa QR</Button>
          )}
        </Card>
        <Card>
          <h3 className="font-bold text-gray-900">Gói đang bán</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(paymentInfo?.plans || []).map((plan) => (
              <div key={plan.id} className="rounded-lg border border-gray-200 p-4">
                <p className="text-sm font-semibold text-gray-500">{plan.label}</p>
                <p className="mt-1 text-3xl font-black text-gray-900">{plan.price.toLocaleString('vi-VN')}đ</p>
                <p className="mt-2 text-sm text-gray-500">Admin cộng thủ công {plan.months * 30} ngày sau khi xác nhận chuyển khoản.</p>
              </div>
            ))}
          </div>
          <div className="mt-5 rounded-lg bg-amber-50 p-4 text-sm leading-6 text-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
            Nội dung chuyển khoản đang dùng phía user: <span className="font-bold">{paymentInfo?.transfer_template || '{email_prefix}_{full_name_no_dau}'}</span>.
            Ví dụ: <span className="font-bold">{paymentInfo?.transfer_example || 'nguyenvana_NguyenVanA'}</span>.
          </div>
        </Card>
      </div>
    </>
  );

  const matchSearchForm = (
    <form
      className="mb-5 flex max-w-xl gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        fetchMatches(0, matchSearch);
      }}
    >
      <input
        value={matchSearch}
        onChange={(event) => setMatchSearch(event.target.value)}
        className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
        placeholder="Tìm theo email"
      />
      <Button type="submit" size="sm">Tìm</Button>
    </form>
  );

  const content = activePage === 'users'
    ? renderUsers()
    : activePage === 'matches'
      ? renderMatches()
      : activePage === 'payment'
        ? renderPayment()
        : renderOverview();

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <Toast {...toast} onClose={hideToast} />}
      <div className="flex min-h-screen">
        <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-gray-200 bg-white lg:block">
          <div className="border-b border-gray-200 p-5">
            <h1 className="text-xl font-black text-primary">Admin</h1>
            <p className="mt-1 truncate text-sm text-gray-500">{user?.email}</p>
          </div>
          <nav className="space-y-1 p-3">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActivePage(item.id)}
                className={`w-full rounded-lg px-4 py-3 text-left text-sm font-semibold ${
                  activePage === item.id ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="absolute bottom-0 left-0 right-0 space-y-2 border-t border-gray-200 p-4">
            <Link to="/dashboard" className="block rounded-lg bg-gray-100 px-4 py-2 text-center text-sm font-semibold text-gray-700">
              Dashboard user
            </Link>
            <Button variant="secondary" size="sm" className="w-full" onClick={logout}>Đăng xuất</Button>
          </div>
        </aside>
        <main className="mx-auto w-full max-w-6xl px-4 py-6 lg:pl-72 lg:pr-8">
          <div className="mb-4 flex gap-2 overflow-x-auto lg:hidden">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActivePage(item.id)}
                className={`shrink-0 rounded-lg px-3 py-2 text-sm font-semibold ${
                  activePage === item.id ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          {content}
        </main>
      </div>
      <UserModal data={selectedUser} onClose={() => setSelectedUser(null)} onUpdate={updateUser} />
      <MatchModal data={selectedMatch} onClose={() => setSelectedMatch(null)} />
    </div>
  );
}

function Pagination({ pagination, onPage }) {
  if (!pagination?.total) return null;
  return (
    <div className="flex items-center justify-between border-t border-gray-200 pt-4">
      <p className="text-sm text-gray-500">Tổng {pagination.total}</p>
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" disabled={!pagination.has_prev} onClick={() => onPage(Math.max(0, pagination.offset - PAGE_SIZE))}>
          Trước
        </Button>
        <Button size="sm" variant="secondary" disabled={!pagination.has_next} onClick={() => onPage(pagination.offset + PAGE_SIZE)}>
          Sau
        </Button>
      </div>
    </div>
  );
}

function formatPeriodLabel(value, granularity) {
  if (granularity === 'year') return value;
  if (granularity === 'month') {
    const [year, month] = value.split('-');
    return `${month}/${year}`;
  }
  return new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function DailyMatchesChart({ data, period }) {
  const displayData = data.map((item) => ({
    ...item,
    matches: Number(item.matches || 0),
    avg_score: Number(item.avg_score || 0),
  }));
  const granularity = period?.granularity || 'day';
  const maxMatches = Math.max(1, ...displayData.map((item) => item.matches || 0));
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-bold text-gray-900 dark:text-white">Lượt so khớp theo thời gian</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Theo khoảng lọc đã chọn</p>
          {period && (
            <p className="mt-1 text-xs font-semibold text-gray-400 dark:text-slate-500">
              {period.start_date} - {period.end_date} ({period.granularity}, {period.timezone})
            </p>
          )}
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700 dark:bg-blue-950/60 dark:text-blue-200">
          {displayData.reduce((sum, item) => sum + (item.matches || 0), 0)} lượt
        </span>
      </div>
      <div className="mt-5 flex h-56 items-end gap-2 overflow-x-auto pb-2">
        {displayData.map((item) => {
          const height = item.matches > 0
            ? Math.max(8, Math.round((item.matches / maxMatches) * 180))
            : 0;
          const label = formatPeriodLabel(item.period || item.date, granularity);
          return (
            <div key={item.date} className="flex min-w-[42px] flex-1 flex-col items-center justify-end gap-2">
              <div className="flex h-[180px] w-full items-end justify-center">
                <div
                  className="w-full max-w-[34px] rounded-t-md bg-blue-600 transition hover:bg-blue-700 dark:bg-blue-500"
                  style={{ height }}
                  title={`${label}: ${item.matches || 0} lượt, điểm TB ${item.avg_score || 0}`}
                />
              </div>
              <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400">{label}</span>
              <span className="text-xs font-bold text-gray-900 dark:text-white">{item.matches || 0}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function TopUsersChart({ users }) {
  const maxMatches = Math.max(1, ...users.map((item) => item.match_count || 0));
  return (
    <Card>
      <h3 className="font-bold text-gray-900 dark:text-white">Tài khoản năng suất nhất</h3>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Xếp theo số lượt so khớp đã tạo</p>
      <div className="mt-5 space-y-4">
        {users.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">Chưa có dữ liệu so khớp.</p>
        ) : users.map((item) => (
          <div key={item.user_id}>
            <div className="mb-1 flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-sm font-bold text-gray-900 dark:text-white">{item.email}</p>
              <p className="shrink-0 text-sm font-black text-blue-700 dark:text-blue-300">{item.match_count}</p>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800">
              <div
                className="h-full rounded-full bg-blue-600 dark:bg-blue-500"
                style={{ width: `${Math.max(6, ((item.match_count || 0) / maxMatches) * 100)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Điểm TB {item.avg_score || 0} · gần nhất {formatDate(item.latest_match_at)}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function PlanDistribution({ overview }) {
  const free = overview.free_users || 0;
  const premium = overview.premium_users || 0;
  const total = Math.max(1, free + premium);
  const segments = [
    ['Free', free, 'bg-gray-500'],
    ['Premium', premium, 'bg-emerald-500'],
  ];
  return (
    <Card>
      <h3 className="font-bold text-gray-900 dark:text-white">Phân bổ tài khoản</h3>
      <div className="mt-5 flex h-4 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800">
        {segments.map(([label, value, color]) => (
          <div
            key={label}
            className={color}
            style={{ width: `${(value / total) * 100}%` }}
            title={`${label}: ${value}`}
          />
        ))}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {segments.map(([label, value, color]) => (
          <div key={label} className="rounded-lg border border-gray-200 p-3 dark:border-slate-700">
            <div className={`mb-2 h-2 w-8 rounded-full ${color}`} />
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">{label}</p>
            <p className="mt-1 text-xl font-black text-gray-900 dark:text-white">{value}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function DocumentMix({ overview }) {
  const rows = [
    ['CV', overview.cvs || 0],
    ['JD', overview.jds || 0],
    ['Match', overview.matches || 0],
  ];
  const maxValue = Math.max(1, ...rows.map(([, value]) => value));
  return (
    <Card>
      <h3 className="font-bold text-gray-900 dark:text-white">Tài liệu và báo cáo</h3>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">So sánh khối lượng dữ liệu trong hệ thống</p>
      <div className="mt-5 space-y-4">
        {rows.map(([label, value]) => (
          <div key={label}>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-sm font-bold text-gray-900 dark:text-white">{label}</span>
              <span className="text-sm font-black text-gray-700 dark:text-gray-200">{value}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-gray-100 dark:bg-slate-800">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{ width: `${Math.max(6, (value / maxValue) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function UserModal({ data, onClose, onUpdate }) {
  if (!data) return null;
  const { user, quota, cvs, jds, matches } = data;
  return (
    <Modal isOpen={true} onClose={onClose} title={`User: ${user.email}`} size="xl">
      <div className="space-y-5">
        <div className="grid gap-3 md:grid-cols-3">
          <Card>
            <p className="text-sm text-gray-500">Gói</p>
            <p className="mt-1 text-xl font-black">{user.effective_plan}</p>
            <p className="text-xs text-gray-500">Hạn: {formatDate(user.premium_until)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">CV/JD</p>
            <p className="mt-1 text-xl font-black">{quota.usage.cv}/{quota.limits.cv ?? '∞'} · {quota.usage.jd}/{quota.limits.jd ?? '∞'}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Match hôm nay</p>
            <p className="mt-1 text-xl font-black">{quota.usage.matches_today}/{quota.limits.daily_matches ?? '∞'}</p>
          </Card>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => onUpdate(user.id, { plan: 'premium', extend_days: 30 })}>Nâng cấp 30 ngày</Button>
          <Button size="sm" variant="secondary" onClick={() => onUpdate(user.id, { plan: 'free', premium_until: null })}>Chuyển free</Button>
          <Button size="sm" variant="secondary" onClick={() => onUpdate(user.id, { role: user.role === 'admin' ? 'user' : 'admin' })}>
            {user.role === 'admin' ? 'Gỡ admin' : 'Cấp admin'}
          </Button>
          <Button size="sm" variant="danger" onClick={() => onUpdate(user.id, { is_active: !user.is_active })}>
            {user.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
          </Button>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <MiniList title="CV" items={cvs} />
          <MiniList title="JD" items={jds} />
          <MiniList title="Match gần đây" items={matches.map((m) => ({ ...m, title: `${m.cv_title} vs ${m.jd_title}` }))} />
        </div>
      </div>
    </Modal>
  );
}

function MiniList({ title, items }) {
  return (
    <div>
      <h3 className="mb-2 font-bold text-gray-900">{title}</h3>
      <div className="max-h-72 space-y-2 overflow-y-auto">
        {items.length === 0 ? <p className="text-sm text-gray-500">Không có dữ liệu</p> : items.map((item) => (
          <div key={item.id} className="rounded-lg border border-gray-200 p-3">
            <p className="text-sm font-semibold text-gray-900">{item.title}</p>
            <p className="text-xs text-gray-500">{formatDate(item.created_at)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchModal({ data, onClose }) {
  if (!data) return null;
  const summary = data.report?.summary || {};
  const issues = data.report?.issues || [];
  return (
    <Modal isOpen={true} onClose={onClose} title={`Review match #${data.id}`} size="xl">
      <div className="space-y-5">
        <div className="grid gap-3 lg:grid-cols-[260px_1fr]">
          <Card>
            <p className="text-sm text-gray-500">{data.user_email}</p>
            <p className="mt-1 font-bold text-gray-900 dark:text-white">{data.cv_title} vs {data.jd_title}</p>
            <p className={`mt-3 text-5xl font-black ${scoreClass(data.similarity_score)}`}>
              {(data.similarity_score ?? 0).toFixed(0)}/100
            </p>
            <p className="mt-2 text-sm text-gray-500">{formatDate(data.created_at)}</p>
          </Card>
          <Card className="min-h-full">
            <h3 className="font-bold text-gray-900 dark:text-white">Đánh giá của người dùng</h3>
            {data.user_review ? (
              <p className="mt-3 whitespace-pre-wrap rounded-lg bg-blue-50 p-4 text-sm leading-6 text-gray-800 dark:bg-blue-950/50 dark:text-blue-50">
                {data.user_review}
              </p>
            ) : (
              <p className="mt-3 rounded-lg bg-gray-50 p-4 text-sm text-gray-500 dark:bg-slate-800 dark:text-slate-300">
                Người dùng chưa viết đánh giá cho lần so khớp này.
              </p>
            )}
          </Card>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <Card>
            <h3 className="font-bold text-gray-900 dark:text-white">Tóm tắt</h3>
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-200">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </Card>
          <Card>
            <h3 className="font-bold text-gray-900 dark:text-white">Vấn đề phát hiện ({issues.length})</h3>
            <div className="mt-3 max-h-72 space-y-2 overflow-auto">
              {issues.length === 0 ? <p className="text-sm text-gray-500">Không có vấn đề</p> : issues.map((issue, index) => (
                <div key={`${issue.code}-${index}`} className="rounded-lg border border-gray-200 p-3 dark:border-slate-700">
                  <p className="text-sm font-bold text-gray-900 dark:text-white">{issue.title || issue.code}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{issue.severity}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </Modal>
  );
}
