import { cvAPI } from '../../api/auth';
import { Card, Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

function CVCard({ cv, onDelete, onSelect }) {
  const { t, language } = useLanguage();
  return (
    <Card className="flex items-center justify-between gap-4" hoverable onClick={() => onSelect?.(cv)}>
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">📄</div>
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
        <div className="text-4xl mb-2">📂</div>
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
