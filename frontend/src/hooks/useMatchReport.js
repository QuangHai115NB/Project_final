import { useState } from 'react';
import { matchAPI } from '../api/auth';

export function useMatchReport() {
  const [report, setReport] = useState(null);
  const [matchDetail, setMatchDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = async (matchId) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await matchAPI.get(matchId);
      setMatchDetail(data);
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

  const saveReview = async (matchId, userReview) => {
    const { data } = await matchAPI.updateReview(matchId, userReview);
    setMatchDetail((prev) => prev ? { ...prev, user_review: data.user_review } : prev);
    return data;
  };

  const downloadDocx = async (matchId, filename = 'report.docx') => {
    const { data: blob } = await matchAPI.download(matchId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return { report, matchDetail, loading, error, fetchReport, saveReview, downloadDocx };
}
