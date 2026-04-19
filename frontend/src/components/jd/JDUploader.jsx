import { useState, useRef } from 'react';
import { jdAPI } from '../../api/auth';
import { Button, Card } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

export default function JDUploader({ onSuccess }) {
  const { t } = useLanguage();
  const [mode, setMode] = useState('text'); // 'text' | 'file'
  const [jdText, setJdText] = useState('');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef();

  const handleUpload = async () => {
    if (mode === 'text' && !jdText.trim()) {
      setError(t('upload.jdTextRequired'));
      return;
    }
    if (mode === 'file' && !file) {
      setError(t('upload.jdFileRequired'));
      return;
    }
    setUploading(true);
    setError('');
    try {
      const { data } = await jdAPI.upload(mode === 'text' ? jdText : null, title, mode === 'file' ? file : null);
      onSuccess?.(data);
    } catch (err) {
      setError(err.response?.data?.error || t('upload.failed'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="space-y-4">
      <h3 className="text-lg font-bold text-gray-800 dark:text-white">{t('upload.jdTitle')}</h3>

      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode('text')}
          className={`rounded-lg px-4 py-2 font-medium transition-all ${mode === 'text' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-300'}`}
        >
          {t('upload.enterText')}
        </button>
        <button
          onClick={() => setMode('file')}
          className={`rounded-lg px-4 py-2 font-medium transition-all ${mode === 'file' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-300'}`}
        >
          {t('upload.uploadFile')}
        </button>
      </div>

      {mode === 'text' ? (
        <textarea
          placeholder={t('upload.jdTextPlaceholder')}
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={8}
          className="w-full resize-none rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
        />
      ) : (
        <div
          onClick={() => fileRef.current?.click()}
          className="cursor-pointer rounded-xl border-2 border-dashed border-gray-300 p-8 text-center transition-all hover:border-primary/50 hover:bg-gray-50 dark:border-slate-700 dark:hover:bg-slate-800/70"
        >
          <input ref={fileRef} type="file" accept=".pdf,.txt" onChange={(e) => setFile(e.target.files[0])} className="hidden" />
          <div className="text-4xl mb-2">📎</div>
          {file ? (
            <p className="font-semibold text-primary">{file.name}</p>
          ) : (
            <p className="text-gray-500 dark:text-slate-400">{t('upload.choosePdfTxt')}</p>
          )}
        </div>
      )}

      <input
        type="text"
        placeholder={t('upload.jdPlaceholder')}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
      />

      {error && <p className="text-red-500 text-sm dark:text-rose-300">{error}</p>}

      <Button onClick={handleUpload} loading={uploading} className="w-full">
        {uploading ? t('upload.uploading') : t('upload.uploadJd')}
      </Button>
    </Card>
  );
}
