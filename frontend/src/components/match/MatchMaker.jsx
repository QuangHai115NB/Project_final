import { useState } from 'react';
import { matchAPI } from '../../api/auth';
import { Button, Card } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

export default function MatchMaker({ cvs, jds, onSuccess }) {
  const { t } = useLanguage();
  const [selectedCv, setSelectedCv] = useState(null);
  const [selectedJd, setSelectedJd] = useState(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleMatch = async () => {
    if (!selectedCv || !selectedJd) {
      setError(t('match.requireBoth'));
      return;
    }
    setMatching(true);
    setError('');
    setLoading(true);
    try {
      const { data } = await matchAPI.create(selectedCv.id, selectedJd.id);
      onSuccess?.(data);
    } catch (err) {
      setError(err.response?.data?.error || t('match.failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="space-y-4">
      <h3 className="text-lg font-bold text-gray-800">{t('match.selectTitle')}</h3>
      <p className="text-sm text-gray-500">{t('match.selectDesc')}</p>

      <div className="grid grid-cols-2 gap-4">
        {/* CV selection */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-gray-700">{t('match.selectCv')}</label>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {cvs?.length > 0 ? cvs.map((cv) => (
              <button
                key={cv.id}
                onClick={() => setSelectedCv(cv)}
                className={`w-full text-left px-3 py-2 rounded-xl border transition-all text-sm
                  ${selectedCv?.id === cv.id ? 'border-primary bg-blue-50 text-primary font-semibold' : 'border-gray-200 hover:border-gray-400'}`}
              >
                {cv.title}
              </button>
            )) : <p className="text-gray-400 text-sm">{t('match.noCv')}</p>}
          </div>
        </div>

        {/* JD selection */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-gray-700">{t('match.selectJd')}</label>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {jds?.length > 0 ? jds.map((jd) => (
              <button
                key={jd.id}
                onClick={() => setSelectedJd(jd)}
                className={`w-full text-left px-3 py-2 rounded-xl border transition-all text-sm
                  ${selectedJd?.id === jd.id ? 'border-primary bg-blue-50 text-primary font-semibold' : 'border-gray-200 hover:border-gray-400'}`}
              >
                {jd.title}
              </button>
            )) : <p className="text-gray-400 text-sm">{t('match.noJd')}</p>}
          </div>
        </div>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <Button onClick={handleMatch} loading={loading} disabled={!selectedCv || !selectedJd} className="w-full">
        {loading ? t('match.running') : t('match.start')}
      </Button>
    </Card>
  );
}
