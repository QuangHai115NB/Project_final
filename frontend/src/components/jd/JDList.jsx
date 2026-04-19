import { BriefcaseBusiness, FolderOpen } from 'lucide-react';
import { Card, Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

function JDCard({ jd, onDelete, onSelect }) {
  const { t, language } = useLanguage();
  return (
    <Card className="flex items-center justify-between gap-4" hoverable onClick={() => onSelect?.(jd)}>
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
          <BriefcaseBusiness size={23} aria-hidden="true" />
        </div>
        <div>
          <h4 className="font-semibold text-gray-800">{jd.title}</h4>
          <p className="text-sm text-gray-500">{jd.original_filename}</p>
          {jd.created_at && (
            <p className="text-xs text-gray-400 mt-1">
              {new Date(jd.created_at).toLocaleDateString(language === 'vi' ? 'vi-VN' : 'en-US')}
            </p>
          )}
        </div>
      </div>
      <Button variant="danger" size="sm" onClick={(e) => { e.stopPropagation(); onDelete?.(jd.id); }}>
        {t('list.delete')}
      </Button>
    </Card>
  );
}

export default function JDList({ jds, onDelete, onSelect, loading }) {
  const { t } = useLanguage();
  if (loading) return <div className="text-center py-8 text-gray-500">{t('common.loading')}</div>;
  if (!jds || jds.length === 0) {
    return (
      <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-300">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400">
          <FolderOpen size={24} aria-hidden="true" />
        </div>
        <p className="text-gray-500">{t('list.noJd')}</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {jds.map((jd) => (
        <JDCard key={jd.id} jd={jd} onDelete={onDelete} onSelect={onSelect} />
      ))}
    </div>
  );
}
