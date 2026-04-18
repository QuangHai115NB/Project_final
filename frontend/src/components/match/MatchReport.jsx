import { useEffect } from 'react';
import { useMatchReport } from '../../hooks/useMatchReport';
import { LoadingSpinner, Card, Button } from '../shared';

function ScoreBar({ label, score }) {
  const val = score ?? 0;
  const color = val >= 75 ? '#10B981' : val >= 55 ? '#F59E0B' : '#EF4444';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="font-bold text-gray-800">{val.toFixed(0)}/100</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="h-2.5 rounded-full transition-all duration-700"
          style={{ width: `${val}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function IssueCard({ issue }) {
  const severityStyles = {
    high: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', text: '🔴 HIGH' },
    medium: { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-100 text-amber-700', text: '🟡 MEDIUM' },
    low: { bg: 'bg-gray-50', border: 'border-gray-200', badge: 'bg-gray-100 text-gray-600', text: '🟢 LOW' },
  };
  const s = severityStyles[issue.severity] || severityStyles.low;
  return (
    <div className={`${s.bg} border ${s.border} rounded-xl p-4`}>
      <div className="flex items-start gap-2 mb-2">
        <span className={`${s.badge} text-xs font-bold px-2 py-0.5 rounded-full`}>{s.text}</span>
        <h4 className="font-semibold text-gray-800">{issue.title}</h4>
      </div>
      {issue.explanation && <p className="text-sm text-gray-600 mb-2">{issue.explanation}</p>}
      {issue.suggested_fix && (
        <div className="bg-white rounded-lg p-3 border border-gray-200">
          <p className="text-xs font-semibold text-primary mb-1">💡 Đề xuất:</p>
          <p className="text-sm text-gray-700">{issue.suggested_fix}</p>
        </div>
      )}
    </div>
  );
}

export default function MatchReport({ matchId, compact = false }) {
  const { report, loading, error, fetchReport, downloadDocx } = useMatchReport();

  useEffect(() => {
    if (matchId) {
      fetchReport(matchId);
    }
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner text="Đang tải báo cáo..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl">
        {error}
      </div>
    );
  }

  if (!report) return null;

  const { summary, score_breakdown, skills_summary, issues } = report;
  const finalScore = summary?.final_score ?? 0;
  const scoreColor = finalScore >= 75 ? 'text-success' : finalScore >= 55 ? 'text-warning' : 'text-danger';
  const scoreBg = finalScore >= 75 ? 'bg-green-50' : finalScore >= 55 ? 'bg-amber-50' : 'bg-red-50';

  if (compact) {
    return (
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-gray-800">Báo cáo #{matchId}</h3>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${scoreColor}`}>{finalScore.toFixed(0)}</span>
            <span className="text-gray-400">/100</span>
          </div>
        </div>
        {issues?.length > 0 && (
          <p className="text-sm text-gray-500">{issues.length} vấn đề được phát hiện</p>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <div className={`${scoreBg} rounded-2xl p-8 text-center`}>
        <div className={`text-6xl font-black ${scoreColor}`}>{finalScore.toFixed(0)}</div>
        <div className="text-xl font-bold text-gray-700 mt-1">/ 100</div>
        <div className={`text-sm font-bold uppercase tracking-wider mt-2 ${scoreColor}`}>
          {summary?.label ?? '—'}
        </div>
      </div>

      {/* Score Breakdown */}
      {score_breakdown && (
        <Card className="space-y-4">
          <h3 className="font-bold text-gray-800">📊 Chi tiết điểm số</h3>
          <div className="grid grid-cols-2 gap-3">
            <ScoreBar label="Skill Coverage" score={score_breakdown.skill_score} />
            <ScoreBar label="Semantic Match" score={score_breakdown.semantic_score} />
            <ScoreBar label="Keyword Match" score={score_breakdown.keyword_score} />
            <ScoreBar label="Experience" score={score_breakdown.experience_score} />
            <ScoreBar label="Structure" score={score_breakdown.structure_score ?? score_breakdown.jd_structure_score} />
            <ScoreBar label="Language" score={score_breakdown.language_score ?? 100} />
          </div>
        </Card>
      )}

      {/* Skills Summary */}
      {skills_summary && (
        <Card>
          <h3 className="font-bold text-gray-800 mb-4">🎯 Skills Summary</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-semibold text-green-600 mb-2">
                ✅ Matched ({skills_summary.matched_required?.length ?? 0})
              </p>
              <div className="space-y-1">
                {(skills_summary.matched_required ?? []).map((s, i) => (
                  <div key={i} className="text-sm text-gray-700">• {s}</div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-red-600 mb-2">
                ❌ Missing ({skills_summary.missing_required?.length ?? 0})
              </p>
              <div className="space-y-1">
                {(skills_summary.missing_required ?? []).map((s, i) => (
                  <div key={i} className="text-sm text-red-600">• {s}</div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Issues */}
      {issues?.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-bold text-gray-800">⚠️ Issues ({issues.length})</h3>
          {issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} />
          ))}
        </div>
      )}

      {/* Download Button */}
      <Button
        variant="outline"
        className="w-full"
        onClick={() => downloadDocx(matchId, `report_${matchId}.docx`)}
      >
        📥 Tải báo cáo Word (.docx)
      </Button>
    </div>
  );
}
