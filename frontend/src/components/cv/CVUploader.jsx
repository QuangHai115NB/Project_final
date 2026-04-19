import { useState, useRef } from 'react';
import { Paperclip } from 'lucide-react';
import { cvAPI } from '../../api/auth';
import { Button, Card } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

export default function CVUploader({ onSuccess }) {
  const { t } = useLanguage();
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const fileRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.type === 'application/pdf') {
      setFile(dropped);
      setError('');
    } else {
      setError(t('upload.pdfOnly'));
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f && f.type === 'application/pdf') {
      setFile(f);
      setError('');
    } else {
      setError(t('upload.pdfOnly'));
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError(t('upload.pdfOnly'));
      return;
    }
    setUploading(true);
    setError('');
    setProgress(10);
    try {
      const { data } = await cvAPI.upload(file, title);
      setProgress(100);
      onSuccess?.(data);
    } catch (err) {
      setError(err.response?.data?.error || t('upload.failed'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="space-y-4">
      <h3 className="text-lg font-bold text-gray-800 dark:text-white">{t('upload.cvTitle')}</h3>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
          ${dragOver ? 'border-primary bg-blue-50 dark:bg-sky-950/40' : 'border-gray-300 hover:border-primary/50 hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800/70'}
        `}
      >
        <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} className="hidden" />
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-blue-700 dark:bg-sky-950/45 dark:text-sky-200">
          <Paperclip size={24} aria-hidden="true" />
        </div>
        {file ? (
          <div>
            <p className="font-semibold text-primary">{file.name}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="font-medium text-gray-700 dark:text-slate-200">{t('upload.dragPdf')}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('upload.clickChoose')}</p>
          </div>
        )}
      </div>

      {/* Title input */}
      <input
        type="text"
        placeholder={t('upload.cvPlaceholder')}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
      />

      {/* Progress bar */}
      {uploading && (
        <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-slate-800">
          <div className="bg-primary h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
        </div>
      )}

      {error && <p className="text-red-500 text-sm dark:text-rose-300">{error}</p>}

      <Button onClick={handleUpload} loading={uploading} disabled={!file} className="w-full">
        {uploading ? t('upload.uploading') : t('upload.uploadCv')}
      </Button>
    </Card>
  );
}
