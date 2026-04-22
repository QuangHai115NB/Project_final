import { useEffect, useMemo, useRef, useState } from 'react';
import { authAPI } from '../../api/auth';
import { useAuth } from '../../context/AuthContext';
import { Button, Card, Input } from '../shared';

function buildInitials(user) {
  const source = user?.full_name || user?.email || 'U';
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'U';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function AvatarPreview({ user, size = 'lg' }) {
  const initials = useMemo(() => buildInitials(user), [user]);
  const sizeClass = size === 'sm' ? 'h-11 w-11 text-sm' : 'h-28 w-28 text-3xl';

  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.full_name || user.email || 'User avatar'}
        className={`${sizeClass} rounded-full object-cover ring-4 ring-blue-100 dark:ring-blue-900/40`}
      />
    );
  }

  return (
    <div
      className={`${sizeClass} flex items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 font-black text-white ring-4 ring-blue-100 dark:ring-blue-900/40`}
    >
      {initials}
    </div>
  );
}

export default function ProfileSettings({ t, tx, showToast }) {
  const { user, setUser } = useAuth();
  const fileInputRef = useRef(null);

  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || '',
    headline: user?.headline || '',
  });
  const [passwordForm, setPasswordForm] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    setProfileForm({
      full_name: user?.full_name || '',
      headline: user?.headline || '',
    });
  }, [user]);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (event) => {
    const { name, value } = event.target;
    setPasswordForm((prev) => ({ ...prev, [name]: value }));
  };

  const submitProfile = async (event) => {
    event.preventDefault();
    setSavingProfile(true);
    try {
      const { data } = await authAPI.updateProfile(profileForm);
      setUser(data.user);
      showToast(data.message || tx('profile.updateSuccess', 'Da cap nhat thong tin ca nhan'), 'success');
    } catch (error) {
      showToast(
        error.response?.data?.error || tx('profile.updateFailed', 'Khong the cap nhat thong tin ca nhan'),
        'error'
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const chooseAvatar = () => {
    fileInputRef.current?.click();
  };

  const uploadAvatar = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setUploadingAvatar(true);
    try {
      const { data } = await authAPI.uploadAvatar(file);
      setUser(data.user);
      showToast(data.message || tx('profile.avatarUploadSuccess', 'Da cap nhat avatar'), 'success');
    } catch (error) {
      showToast(
        error.response?.data?.error || tx('profile.avatarUploadFailed', 'Khong the cap nhat avatar'),
        'error'
      );
    } finally {
      setUploadingAvatar(false);
    }
  };

  const deleteAvatar = async () => {
    setUploadingAvatar(true);
    try {
      const { data } = await authAPI.deleteAvatar();
      setUser(data.user);
      showToast(data.message || tx('profile.avatarDeleteSuccess', 'Da xoa avatar'), 'success');
    } catch (error) {
      showToast(
        error.response?.data?.error || tx('profile.avatarDeleteFailed', 'Khong the xoa avatar'),
        'error'
      );
    } finally {
      setUploadingAvatar(false);
    }
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    if (passwordForm.newPassword.length < 8) {
      showToast(tx('profile.passwordTooShort', 'Mat khau moi phai co it nhat 8 ky tu'), 'error');
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      showToast(tx('profile.passwordMismatch', 'Xac nhan mat khau khong khop'), 'error');
      return;
    }

    setSavingPassword(true);
    try {
      const { data } = await authAPI.changePassword(passwordForm.oldPassword, passwordForm.newPassword);
      setPasswordForm({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      showToast(data.message || tx('profile.passwordUpdateSuccess', 'Da doi mat khau'), 'success');
    } catch (error) {
      showToast(
        error.response?.data?.error || tx('profile.passwordUpdateFailed', 'Khong the doi mat khau'),
        'error'
      );
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.05fr_1.4fr]">
      <div className="space-y-6">
        <Card className="overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 via-sky-500 to-cyan-400 p-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <AvatarPreview user={user} />
              <div className="text-white">
                <h3 className="text-xl font-black">{user?.full_name || tx('profile.noName', 'Chua cap nhat ten')}</h3>
                <p className="mt-1 text-sm text-blue-50">{user?.headline || user?.email}</p>
              </div>
            </div>
          </div>
          <div className="space-y-3 p-5">
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={uploadAvatar}
            />
            <Button className="w-full" onClick={chooseAvatar} loading={uploadingAvatar}>
              {tx('profile.uploadAvatar', 'Tai avatar moi')}
            </Button>
            <Button
              className="w-full"
              variant="outline"
              onClick={deleteAvatar}
              disabled={!user?.avatar_url || uploadingAvatar}
            >
              {tx('profile.removeAvatar', 'Xoa avatar')}
            </Button>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {tx('profile.avatarHint', 'Ho tro PNG, JPG, JPEG, WEBP. Avatar hien thi dang khung tron.')}
            </p>
          </div>
        </Card>

        <Card>
          <h3 className="text-lg font-bold text-gray-900 dark:text-slate-100">
            {tx('profile.accountSummary', 'Thong tin tai khoan')}
          </h3>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex items-start justify-between gap-4">
              <dt className="text-gray-500 dark:text-slate-400">{tx('profile.email', 'Email')}</dt>
              <dd className="text-right font-medium text-gray-900 dark:text-slate-100">{user?.email}</dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-gray-500 dark:text-slate-400">{tx('profile.joinedAt', 'Ngay tao tai khoan')}</dt>
              <dd className="text-right font-medium text-gray-900 dark:text-slate-100">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-gray-500 dark:text-slate-400">{tx('profile.status', 'Trang thai')}</dt>
              <dd className="text-right font-medium text-gray-900 dark:text-slate-100">
                {user?.is_verified ? tx('profile.verified', 'Da xac minh') : tx('profile.unverified', 'Chua xac minh')}
              </dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <div className="mb-5">
            <h3 className="text-lg font-bold text-gray-900 dark:text-slate-100">
              {tx('profile.personalInfo', 'Thong tin ca nhan')}
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
              {tx('profile.personalInfoHint', 'Cap nhat cac thong tin co ban de giao dien va ho so nhin day du hon.')}
            </p>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={submitProfile}>
            <Input
              label={tx('profile.fullName', 'Ho va ten')}
              name="full_name"
              value={profileForm.full_name}
              onChange={handleProfileChange}
            />
            <Input
              label={tx('profile.job', 'Job')}
              name="headline"
              value={profileForm.headline}
              onChange={handleProfileChange}
            />
            <div className="md:col-span-2 flex justify-end">
              <Button type="submit" loading={savingProfile}>
                {tx('profile.saveProfile', 'Luu thong tin')}
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <div className="mb-5">
            <h3 className="text-lg font-bold text-gray-900 dark:text-slate-100">
              {tx('profile.changePassword', 'Doi mat khau')}
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
              {tx('profile.changePasswordHint', 'Dung mat khau moi du manh de bao ve tai khoan.')}
            </p>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={submitPassword}>
            <Input
              className="md:col-span-2"
              type="password"
              label={tx('profile.oldPassword', 'Mat khau hien tai')}
              name="oldPassword"
              value={passwordForm.oldPassword}
              onChange={handlePasswordChange}
              placeholder={tx('profile.oldPasswordPlaceholder', 'Nhap mat khau hien tai')}
            />
            <Input
              type="password"
              label={tx('profile.newPassword', 'Mat khau moi')}
              name="newPassword"
              value={passwordForm.newPassword}
              onChange={handlePasswordChange}
              placeholder={tx('profile.newPasswordPlaceholder', 'Nhap mat khau moi')}
            />
            <Input
              type="password"
              label={tx('profile.confirmNewPassword', 'Xac nhan mat khau moi')}
              name="confirmPassword"
              value={passwordForm.confirmPassword}
              onChange={handlePasswordChange}
              placeholder={tx('profile.confirmNewPasswordPlaceholder', 'Nhap lai mat khau moi')}
            />
            <div className="md:col-span-2 flex justify-end">
              <Button type="submit" loading={savingPassword}>
                {tx('profile.updatePassword', 'Cap nhat mat khau')}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
