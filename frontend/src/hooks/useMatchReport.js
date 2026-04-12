import { useState } from 'react';
import { matchAPI } from '../api/auth';

export function useMatchReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = async (matchId) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await matchAPI.get(matchId);
      setReport(data);
      return data;
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load report');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = async (matchId, filename = 'report.docx') => {
    const { data } = await matchAPI.download(matchId);
    const url = URL.createObjectURL(new Blob([data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return { report, loading, error, fetchReport, downloadDocx };
}