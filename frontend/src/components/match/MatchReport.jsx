import { useEffect } from 'react';
import { useMatchReport } from '../../hooks/useMatchReport';
import { LoadingSpinner, Card, Button } from '../shared';

const TONES = {
  green: {
    text: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    fill: '#10B981',
  },
  amber: {
    text: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    fill: '#F59E0B',
  },
  red: {
    text: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    fill: '#EF4444',
  },
};

function getTone(score, color) {
  if (color && TONES[color]) return TONES[color];
  const val = Number(score) || 0;
  if (val >= 70) return TONES.green;
  if (val >= 55) return TONES.amber;
  return TONES.red;
}

function formatScore(score) {
  return `${(Number(score) || 0).toFixed(0)}/100`;
}

function ScoreBar({ label, score, weight }) {
  const val = Math.max(0, Math.min(100, Number(score) || 0));
  const tone = getTone(val);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="shrink-0 font-bold text-gray-800">
          {formatScore(val)}
          {weight != null && (
            <span className="ml-2 text-xs font-medium text-gray-500">
              weight {Number(weight).toFixed(0)}%
            </span>
          )}
        </span>
      </div>
      <div className="h-2.5 w-full rounded bg-gray-200">
        <div
          className="h-2.5 rounded transition-all duration-700"
          style={{ width: `${val}%`, backgroundColor: tone.fill }}
        />
      </div>
    </div>
  );
}

function EvidenceItem({ item }) {
  if (item == null) return null;

  if (typeof item === 'object') {
    const location = [item.section, item.bullet_index ? `bullet #${item.bullet_index}` : null]
      .filter(Boolean)
      .join(' - ');

    return (
      <li className="rounded border border-gray-200 bg-white p-3">
        {location && (
          <div className="mb-1 text-xs font-semibold uppercase text-gray-500">
            {location}
          </div>
        )}
        <p className="text-sm text-gray-800">{item.excerpt || JSON.stringify(item)}</p>
        {item.reason && <p className="mt-1 text-xs text-gray-500">{item.reason}</p>}
      </li>
    );
  }

  return (
    <li className="rounded border border-gray-200 bg-white p-3 text-sm text-gray-800">
      {String(item)}
    </li>
  );
}

function IssueCard({ issue }) {
  const severityStyles = {
    high: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      badge: 'bg-red-100 text-red-700',
      label: 'HIGH',
    },
    medium: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      badge: 'bg-amber-100 text-amber-700',
      label: 'MEDIUM',
    },
    low: {
      bg: 'bg-gray-50',
      border: 'border-gray-200',
      badge: 'bg-gray-100 text-gray-600',
      label: 'LOW',
    },
  };
  const style = severityStyles[issue.severity] || severityStyles.low;
  const evidence = issue.evidence || issue.details || [];

  return (
    <div className={`${style.bg} border ${style.border} rounded p-4`}>
      <div className="mb-2 flex flex-wrap items-start gap-2">
        <span className={`${style.badge} rounded px-2 py-0.5 text-xs font-bold`}>
          {style.label}
        </span>
        <h4 className="font-semibold text-gray-800">
          {issue.title || issue.code?.replace(/_/g, ' ')}
        </h4>
        {issue.section && (
          <span className="rounded bg-white px-2 py-0.5 text-xs text-gray-500">
            {issue.section}
          </span>
        )}
      </div>

      {issue.explanation && <p className="mb-3 text-sm text-gray-700">{issue.explanation}</p>}

      {evidence.length > 0 && (
        <div className="mb-3">
          <p className="mb-2 text-xs font-semibold uppercase text-gray-500">Dẫn chứng</p>
          <ul className="space-y-2">
            {evidence.slice(0, 4).map((item, index) => (
              <EvidenceItem key={index} item={item} />
            ))}
          </ul>
        </div>
      )}

      {issue.suggested_fix && (
        <div className="rounded border border-gray-200 bg-white p-3">
          <p className="mb-1 text-xs font-semibold uppercase text-blue-700">Cách sửa</p>
          <p className="text-sm text-gray-700">{issue.suggested_fix}</p>
        </div>
      )}

      {issue.optional_rewrite && (
        <div className="mt-3 rounded border border-blue-200 bg-blue-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase text-blue-700">Gợi ý viết lại</p>
          <p className="text-sm text-gray-800">{issue.optional_rewrite}</p>
        </div>
      )}
    </div>
  );
}

function PillList({ items = [], colorClass = 'bg-gray-100 text-gray-700' }) {
  if (!items.length) return <p className="text-sm text-gray-500">Không có dữ liệu.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span key={`${item}-${index}`} className={`${colorClass} rounded px-2 py-1 text-xs font-medium`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function SectionAnalysis({ sectionAnalysis }) {
  if (!sectionAnalysis) return null;
  return (
    <Card>
      <h3 className="mb-4 font-bold text-gray-800">Cấu trúc CV</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-2 text-sm font-semibold text-green-700">Đã nhận diện</p>
          <PillList items={sectionAnalysis.sections_found || []} colorClass="bg-green-100 text-green-700" />
        </div>
        <div>
          <p className="mb-2 text-sm font-semibold text-red-700">Còn thiếu</p>
          <PillList
            items={sectionAnalysis.missing_required_sections || []}
            colorClass="bg-red-100 text-red-700"
          />
        </div>
      </div>
    </Card>
  );
}

function RewriteExamples({ examples = [] }) {
  if (!examples.length) return null;
  return (
    <Card>
      <h3 className="mb-4 font-bold text-gray-800">Mẫu viết lại</h3>
      <div className="space-y-3">
        {examples.slice(0, 3).map((example, index) => (
          <div key={index} className="rounded border border-gray-200 p-3">
            <div className="mb-1 flex flex-wrap gap-2">
              <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                {example.target_section || 'CV'}
              </span>
              <span className="text-sm font-semibold text-gray-800">{example.label}</span>
            </div>
            <p className="text-sm text-gray-700">{example.template}</p>
          </div>
        ))}
      </div>
    </Card>
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
      <div className="rounded border border-red-200 bg-red-50 p-4 text-red-600">
        {error}
      </div>
    );
  }

  if (!report) return null;

  const {
    summary = {},
    score_breakdown: scoreBreakdown = {},
    score_weights: scoreWeights = {},
    skills_summary: skillsSummary,
    section_analysis: sectionAnalysis,
    semantic_analysis: semanticAnalysis,
    rewrite_examples: rewriteExamples = [],
    issues = [],
  } = report;

  const finalScore = Number(summary.final_score) || 0;
  const scoreTone = getTone(finalScore, summary.color);

  if (compact) {
    return (
      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <h3 className="font-bold text-gray-800">Báo cáo #{matchId}</h3>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${scoreTone.text}`}>{finalScore.toFixed(0)}</span>
            <span className="text-gray-400">/100</span>
          </div>
        </div>
        {issues.length > 0 && (
          <p className="text-sm text-gray-500">{issues.length} vấn đề được phát hiện</p>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className={`${scoreTone.bg} ${scoreTone.border} rounded border p-8 text-center`}>
        <div className={`text-6xl font-black ${scoreTone.text}`}>{finalScore.toFixed(0)}</div>
        <div className="mt-1 text-xl font-bold text-gray-700">/ 100</div>
        <div className={`mt-2 text-sm font-bold uppercase ${scoreTone.text}`}>
          {summary.label || 'N/A'}
        </div>
        <p className="mt-3 text-sm text-gray-600">
          Điểm cuối được tính trực tiếp từ breakdown và weight bên dưới.
        </p>
      </div>

      <Card className="space-y-4">
        <h3 className="font-bold text-gray-800">Chi tiết điểm số</h3>
        <div className="grid gap-3 md:grid-cols-2">
          <ScoreBar label="Cấu trúc CV" score={scoreBreakdown.section_score} weight={scoreWeights.section_score} />
          <ScoreBar label="Skill Coverage" score={scoreBreakdown.skill_score} weight={scoreWeights.skill_score} />
          <ScoreBar label="Semantic Match" score={scoreBreakdown.semantic_score} weight={scoreWeights.semantic_score} />
          <ScoreBar label="Keyword Match" score={scoreBreakdown.keyword_score} weight={scoreWeights.keyword_score} />
          <ScoreBar label="Experience" score={scoreBreakdown.experience_score} weight={scoreWeights.experience_score} />
          <ScoreBar
            label="Bullet Quality"
            score={scoreBreakdown.jd_structure_score ?? scoreBreakdown.structure_score}
            weight={scoreWeights.jd_structure_score}
          />
        </div>
      </Card>

      {skillsSummary && (
        <Card>
          <h3 className="mb-4 font-bold text-gray-800">Skills Summary</h3>
          <div className="mb-4 text-sm text-gray-600">
            Required coverage: <span className="font-bold">{Number(skillsSummary.required_coverage_pct || 0).toFixed(0)}%</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-semibold text-green-700">
                Matched required ({skillsSummary.matched_required?.length || 0})
              </p>
              <PillList items={skillsSummary.matched_required || []} colorClass="bg-green-100 text-green-700" />
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold text-red-700">
                Missing required ({skillsSummary.missing_required?.length || 0})
              </p>
              <PillList items={skillsSummary.missing_required || []} colorClass="bg-red-100 text-red-700" />
            </div>
          </div>
        </Card>
      )}

      <SectionAnalysis sectionAnalysis={sectionAnalysis} />

      {semanticAnalysis?.unmatched_jd_lines?.length > 0 && (
        <Card>
          <h3 className="mb-4 font-bold text-gray-800">JD chưa được CV cover</h3>
          <ul className="space-y-2">
            {semanticAnalysis.unmatched_jd_lines.slice(0, 3).map((item, index) => (
              <EvidenceItem key={index} item={item.jd_line || item} />
            ))}
          </ul>
        </Card>
      )}

      {issues.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-bold text-gray-800">Vấn đề cần sửa ({issues.length})</h3>
          {issues.map((issue, index) => (
            <IssueCard key={`${issue.code}-${index}`} issue={issue} />
          ))}
        </div>
      )}

      <RewriteExamples examples={rewriteExamples} />

      <Button
        variant="outline"
        className="w-full"
        onClick={() => downloadDocx(matchId, `report_${matchId}.docx`)}
      >
        Tải báo cáo Word (.docx)
      </Button>
    </div>
  );
}
