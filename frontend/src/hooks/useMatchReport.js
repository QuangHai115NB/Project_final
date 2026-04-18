import { useState } from 'react';
import axios from 'axios';

export function useMatchReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = async (matchId) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('access_token');
      const { data } = await axios.get(`/api/matches/${matchId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      setReport(data.report ?? data);
      return data;
    } catch (err) {
      const msg = err.response?.data?.error || 'Không thể tải báo cáo';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = async (matchId, filename = 'report.docx') => {
    const token = localStorage.getItem('access_token');
    const { data: blob } = await axios.get(`/api/matches/download/${matchId}`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return { report, loading, error, fetchReport, downloadDocx };
}
