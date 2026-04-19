import { cvAPI } from '../../api/auth';
import { FileText, FolderOpen } from 'lucide-react';
import { Card, Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

function CVCard({ cv, onDelete, onSelect }) {
  const { t, language } = useLanguage();
  return (
    <Card className="flex items-center justify-between gap-4" hoverable onClick={() => onSelect?.(cv)}>
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 text-blue-700 dark:bg-sky-950/45 dark:text-sky-200">
          <FileText size={23} aria-hidden="true" />
        </div>
        <div>
          <h4 className="font-semibold text-gray-800">{cv.title}</h4>
          <p className="text-sm text-gray-500">{cv.original_filename}</p>
          {cv.created_at && (
            <p className="text-xs text-gray-400 mt-1">
              {new Date(cv.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}
            </p>
          )}
        </div>
      </div>
      <Button
        variant="danger"
        size="sm"
        onClick={(e) => { e.stopPropagation(); onDelete?.(cv.id); }}
      >
        {t('list.delete')}
      </Button>
    </Card>
  );
}

export default function CVList({ cvs, onDelete, onSelect, loading }) {
  const { t } = useLanguage();
  if (loading) {
    return <div className="text-center py-8 text-gray-500">{t('common.loading')}</div>;
  }

  if (!cvs || cvs.length === 0) {
    return (
      <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-300">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400">
          <FolderOpen size={24} aria-hidden="true" />
        </div>
        <p className="text-gray-500">{t('list.noCv')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cvs.map((cv) => (
        <CVCard key={cv.id} cv={cv} onDelete={onDelete} onSelect={onSelect} />
      ))}
    </div>
  );
}
