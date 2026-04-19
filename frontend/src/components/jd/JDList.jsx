import { Card, Button } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

function JDCard({ jd, onDelete, onSelect }) {
  const { t, language } = useLanguage();
  return (
    <Card className="flex items-center justify-between gap-4" hoverable onClick={() => onSelect?.(jd)}>
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center text-2xl">💼</div>
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
        <div className="text-4xl mb-2">📂</div>
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
