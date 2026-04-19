import { useEffect, useState } from 'react';
import { useMatchReport } from '../../hooks/useMatchReport';
import { LoadingSpinner, Card, Button, Modal } from '../shared';
import { useLanguage } from '../../i18n/LanguageContext';

const TONES = {
  green: {
    text: 'text-green-700 dark:text-emerald-300',
    bg: 'bg-green-50',
    border: 'border-green-200',
    fill: '#059669',
  },
  amber: {
    text: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    fill: '#D97706',
  },
  red: {
    text: 'text-red-700 dark:text-rose-300',
    bg: 'bg-red-50',
    border: 'border-red-200',
    fill: '#DC2626',
  },
};

const SCORE_ROWS = [
  ['section_score', 'report.cvStructure'],
  ['skill_score', 'report.skillCoverage'],
  ['semantic_score', 'report.semanticMatch'],
  ['keyword_score', 'report.keywordMatch'],
  ['experience_score', 'report.experience'],
  ['jd_structure_score', 'report.bulletQuality'],
];

function getTone(score, color) {
  if (color && TONES[color]) return TONES[color];
  const val = Number(score) || 0;
  if (val >= 70) return TONES.green;
  if (val >= 55) return TONES.amber;
  return TONES.red;
}

function scoreValue(score) {
  return Math.max(0, Math.min(100, Number(score) || 0));
}

function getLocalizedValue(item, language, viKey, enKey, fallbackKey) {
  if (!item) return '';
  if (language === 'vi') {
    return item[viKey] || item[fallbackKey] || item[enKey] || '';
  }
  return item[enKey] || item[fallbackKey] || item[viKey] || '';
}

function localizeSectionLabel(value, language) {
  if (language !== 'vi') return value;
  const sectionMap = {
    Summary: 'Tóm tắt',
    Skills: 'Kỹ năng',
    Experience: 'Kinh nghiệm',
    Projects: 'Dự án',
    Education: 'Học vấn',
    Certifications: 'Chứng chỉ',
    Contact: 'Liên hệ',
  };
  return String(value || '')
    .split('/')
    .map((part) => sectionMap[part.trim()] || part.trim())
    .join(' / ');
}

function localizeEvidenceItem(item, issueCode, language) {
  if (issueCode === 'missing_metrics' && typeof item === 'string') {
    if (language === 'en' && /Không|số liệu|bullet/.test(item)) {
      return { excerpt: 'No Experience/Projects bullet contains measurable metrics.' };
    }
    if (language === 'vi') {
      return item.replaceAll('bullet', 'dòng mô tả');
    }
  }

  if (issueCode === 'contact_info' && typeof item === 'string') {
    return item;
  }

  if (
    language === 'vi'
    && ['missing_sections', 'missing_recommended_sections'].includes(issueCode)
    && typeof item === 'string'
  ) {
    return localizeSectionLabel(item, language);
  }
  return item;
}

function localizeContactItem(item, language, t) {
  const key = String(item || '').trim();
  const label = t(`contact.${key}`);
  if (label !== `contact.${key}`) return label;
  return language === 'vi' ? key.replace(/^has_/, '').replaceAll('_', ' ') : key.replace(/^has_/, '').replaceAll('_', ' ');
}

function cleanDisplayLine(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[\s\-*•●▪–—]+/, '')
    .replace(/^\(?\s*(?:\d+|[a-zA-Z])[\).:-]\s*/, '')
    .replace(/^[\s([{:;,.]+/, '')
    .replace(/[\s)\]}:;,.]+$/, '')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')');
}

function normalizeUnmatchedJdLines(items = []) {
  const seen = new Set();
  return items
    .map((item) => {
      const rawLine = typeof item === 'object' ? item.jd_line || item.excerpt || '' : item;
      const line = cleanDisplayLine(rawLine);
      return {
        jd_line: line,
        best_cv_score: typeof item === 'object' ? item.best_cv_score : undefined,
      };
    })
    .filter((item) => {
      if (!/[A-Za-zÀ-ỹ0-9]/.test(item.jd_line)) return false;
      if (item.jd_line.split(/\s+/).length < 4) return false;
      const key = item.jd_line.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 5);
}

function removeEducationRequirement(items = []) {
  return items.filter((item) => String(item).trim().toLowerCase() !== 'education');
}

function normalizeVisibleIssues(issues = []) {
  return issues
    .map((issue) => {
      if (issue.code !== 'missing_sections') return issue;
      const evidence = removeEducationRequirement(issue.evidence || []);
      const details = removeEducationRequirement(issue.details || []);
      return { ...issue, evidence, details };
    })
    .filter((issue) => {
      if (issue.code !== 'missing_sections') return true;
      return (issue.evidence || issue.details || []).length > 0;
    });
}

function ScoreBar({ label, score, weight, t }) {
  const val = scoreValue(score);
  const tone = getTone(val);

  return (
    <div className="ui-surface rounded-lg p-4">
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="font-semibold text-gray-800 dark:text-slate-200">{label}</span>
        <span className="shrink-0 font-bold text-gray-900 dark:text-white">{val.toFixed(0)}/100</span>
      </div>
      <div className="h-2.5 w-full rounded bg-gray-100 dark:bg-slate-800">
        <div
          className="h-2.5 rounded transition-all duration-700"
          style={{ width: `${val}%`, backgroundColor: tone.fill }}
        />
      </div>
      {weight != null && (
        <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
          {t('report.weight', { value: Number(weight).toFixed(0) })}
        </p>
      )}
    </div>
  );
}

function EvidenceItem({ item, language, t }) {
  if (item == null) return null;

  if (typeof item === 'object') {
    const location = [
      item.section ? localizeSectionLabel(item.section, language) : null,
      item.bullet_index ? t('evidence.itemLine', { index: item.bullet_index }) : null,
    ]
      .filter(Boolean)
      .join(' - ');

    return (
      <li className="ui-muted-surface rounded-lg p-3">
        {location && (
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            {location}
          </div>
        )}
        <p className="text-sm text-gray-800 dark:text-slate-100">{item.excerpt || item.jd_line || JSON.stringify(item)}</p>
        {item.reason && (
          <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
            {language === 'vi' && item.reason === 'No measurable result or scale found.'
              ? t('evidence.metricReason')
              : item.reason}
          </p>
        )}
      </li>
    );
  }

  return (
    <li className="ui-muted-surface rounded-lg p-3 text-sm">
      {String(item)}
    </li>
  );
}

function PillList({ items = [], colorClass = 'bg-gray-100 text-gray-700', t, formatItem }) {
  if (!items.length) return <p className="text-sm text-gray-500 dark:text-slate-400">{t('common.noData')}</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span key={`${item}-${index}`} className={`${colorClass} rounded px-2 py-1 text-xs font-medium`}>
          {formatItem ? formatItem(item) : item}
        </span>
      ))}
    </div>
  );
}

function IssueCard({ issue, language, t }) {
  const severityStyles = {
    high: 'ui-soft-red',
    medium: 'ui-soft-amber',
    low: 'ui-muted-surface',
  };
  const severityLabel = {
    high: t('report.high'),
    medium: t('report.medium'),
    low: t('report.low'),
  };
  const rawEvidence = issue.evidence || issue.details || [];
  const evidence = issue.code === 'uncovered_responsibilities'
    ? normalizeUnmatchedJdLines(rawEvidence).map((item) => item.jd_line)
    : rawEvidence.map((item) => (
      issue.code === 'contact_info' ? localizeContactItem(item, language, t) : item
    ));
  const title = t(`issue.${issue.code}.title`) || issue.title || issue.code?.replace(/_/g, ' ');
  const explanation = getLocalizedValue(issue, language, 'explanation_vi', 'explanation_en', 'explanation');
  const cvWording = issue.optional_rewrite || issue.suggested_fix_en || '';
  const meaning = issue.optional_rewrite
    ? getLocalizedValue(issue, language, 'optional_rewrite_meaning_vi', 'optional_rewrite_meaning_en', 'fix_meaning_vi')
    : getLocalizedValue(issue, language, 'fix_meaning_vi', 'fix_meaning_en', 'suggested_fix');

  return (
    <div className="ui-surface rounded-lg p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-1 text-xs font-bold ${severityStyles[issue.severity] || severityStyles.low}`}>
          {severityLabel[issue.severity] || severityLabel.low}
        </span>
        {issue.section && (
          <span className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-500 dark:border-slate-700 dark:text-slate-400">
            {localizeSectionLabel(issue.section, language)}
          </span>
        )}
      </div>

      <h4 className="text-base font-bold text-gray-900 dark:text-white">{title}</h4>
      {explanation && <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-slate-300">{explanation}</p>}

      {evidence.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            {issue.code === 'contact_info' ? t('report.addSuggestion') : t('report.evidence')}
          </p>
          <ul className="space-y-2">
            {evidence.slice(0, 4).map((item, index) => (
              <EvidenceItem
                key={index}
                item={localizeEvidenceItem(item, issue.code, language)}
                language={language}
                t={t}
              />
            ))}
          </ul>
        </div>
      )}

      {(cvWording || meaning) && (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {cvWording && (
            <div className="ui-soft-blue rounded-lg p-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-wide">{t('report.fix')}</p>
              <p className="text-sm leading-6 text-gray-900 dark:text-sky-100">{cvWording}</p>
            </div>
          )}
          {meaning && (
            <div className="ui-muted-surface rounded-lg p-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-600 dark:text-slate-300">{t('report.meaning')}</p>
              <p className="text-sm leading-6 text-gray-700 dark:text-slate-200">{meaning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoringGuide({ isOpen, onClose, t }) {
  const items = [
    'guide.section',
    'guide.skill',
    'guide.semantic',
    'guide.keyword',
    'guide.experience',
    'guide.structure',
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('guide.title')} size="lg">
      <div className="space-y-4">
        <p className="text-sm leading-6 text-gray-600 dark:text-slate-300">{t('guide.intro')}</p>
        <div className="space-y-3">
          {items.map((key) => (
            <div key={key} className="ui-muted-surface rounded-lg p-4 text-sm leading-6">
              {t(key)}
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}

function RewriteExamples({ examples = [], language, t }) {
  if (!examples.length) return null;
  return (
    <Card>
      <h3 className="mb-4 font-bold text-gray-900 dark:text-white">{t('report.rewriteExamples')}</h3>
      <div className="space-y-3">
        {examples.slice(0, 3).map((example, index) => (
          <div key={index} className="ui-surface rounded-lg p-4">
            <div className="mb-2 flex flex-wrap gap-2">
              <span className="ui-soft-blue rounded px-2 py-1 text-xs font-bold">
                {localizeSectionLabel(example.target_section || 'CV', language)}
              </span>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">{example.label}</span>
            </div>
            <p className="text-sm leading-6 text-gray-900 dark:text-slate-100">{example.template}</p>
            <div className="ui-muted-surface mt-3 rounded-lg p-3">
              <p className="mb-1 text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-slate-400">{t('report.meaning')}</p>
              <p className="text-sm leading-6 text-gray-600 dark:text-slate-300">
                {language === 'vi' ? example.meaning_vi : example.meaning_en}
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function UnmatchedJdRequirements({ items = [], t }) {
  const cleanItems = normalizeUnmatchedJdLines(items);
  if (!cleanItems.length) return null;

  return (
    <Card className="border-l-4 border-l-amber-500">
      <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="font-bold text-gray-900 dark:text-white">{t('report.uncoveredJd')}</h3>
          <p className="mt-1 text-sm leading-6 text-gray-600 dark:text-slate-300">{t('report.uncoveredJdHelp')}</p>
        </div>
        <span className="ui-soft-amber w-fit rounded px-2 py-1 text-xs font-bold">
          {t('report.needsEvidence')}
        </span>
      </div>

      <div className="space-y-3">
        {cleanItems.map((item, index) => (
          <div key={`${item.jd_line}-${index}`} className="ui-soft-amber rounded-lg p-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="rounded bg-white px-2 py-1 text-xs font-bold text-amber-800 dark:bg-amber-950/50 dark:text-amber-100">
                JD #{index + 1}
              </span>
              {item.best_cv_score != null && (
                <span className="text-xs font-medium">
                  {t('report.closestCvMatch', { value: Number(item.best_cv_score).toFixed(0) })}
                </span>
              )}
            </div>
            <p className="text-sm leading-6 text-gray-900 dark:text-amber-50">{item.jd_line}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function MatchReport({ matchId, compact = false }) {
  const { report, loading, error, fetchReport, downloadDocx } = useMatchReport();
  const { language, t } = useLanguage();
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    if (matchId) {
      fetchReport(matchId);
    }
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner text={t('report.loading')} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="ui-soft-red rounded-lg p-4">
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
  const visibleIssues = normalizeVisibleIssues(issues);
  const visibleMissingSections = removeEducationRequirement(
    sectionAnalysis?.missing_required_sections || [],
  );

  const scoreRows = SCORE_ROWS.filter(
    ([key]) => scoreWeights[key] != null || scoreBreakdown[key] != null,
  );

  if (compact) {
    return (
      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <h3 className="font-bold text-gray-900 dark:text-white">{t('report.title', { id: matchId })}</h3>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${scoreTone.text}`}>{finalScore.toFixed(0)}</span>
            <span className="text-gray-400 dark:text-slate-500">/100</span>
          </div>
        </div>
        {visibleIssues.length > 0 && (
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('report.issuesFound', { count: visibleIssues.length })}</p>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className={`rounded-lg border ${scoreTone.border} ${scoreTone.bg} p-6 dark:border-slate-700 dark:bg-slate-900/80`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">{t('dashboard.matchReport')}</p>
            <div className="mt-2 flex items-end gap-3">
              <span className={`text-6xl font-black ${scoreTone.text}`}>{finalScore.toFixed(0)}</span>
              <span className="pb-2 text-xl font-bold text-gray-700 dark:text-slate-300">/100</span>
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-slate-300">{t('report.scoreNote')}</p>
          </div>
          <Button variant="outline" onClick={() => setShowGuide(true)} className="bg-white dark:bg-slate-950">
            {t('report.scoringGuide')}
          </Button>
        </div>
      </div>

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-bold text-gray-900 dark:text-white">{t('report.scoreBreakdown')}</h3>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {scoreRows.map(([key, labelKey]) => (
            <ScoreBar
              key={key}
              label={t(labelKey)}
              score={scoreBreakdown[key]}
              weight={scoreWeights[key]}
              t={t}
            />
          ))}
        </div>
      </Card>

      {skillsSummary && (
        <Card>
          <h3 className="mb-2 font-bold text-gray-900 dark:text-white">{t('report.skillsSummary')}</h3>
          <p className="mb-4 text-sm text-gray-600 dark:text-slate-300">
            {t('report.requiredCoverage')}: <span className="font-bold">{Number(skillsSummary.required_coverage_pct || 0).toFixed(0)}%</span>
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="ui-soft-green rounded-lg p-4">
              <p className="mb-2 text-sm font-bold">
                {t('report.matchedRequired', { count: skillsSummary.matched_required?.length || 0 })}
              </p>
              <PillList items={skillsSummary.matched_required || []} colorClass="bg-white text-green-700 border border-green-200 dark:bg-emerald-950/50 dark:text-emerald-100 dark:border-emerald-700/50" t={t} />
            </div>
            <div className="ui-soft-red rounded-lg p-4">
              <p className="mb-2 text-sm font-bold">
                {t('report.missingRequired', { count: skillsSummary.missing_required?.length || 0 })}
              </p>
              <PillList items={skillsSummary.missing_required || []} colorClass="bg-white text-red-700 border border-red-200 dark:bg-rose-950/50 dark:text-rose-100 dark:border-rose-700/50" t={t} />
            </div>
          </div>
        </Card>
      )}

      {sectionAnalysis && (
        <Card>
          <h3 className="mb-4 font-bold text-gray-900 dark:text-white">{t('report.sections')}</h3>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-bold text-gray-700 dark:text-slate-200">{t('report.sectionsFound')}</p>
              <PillList
                items={sectionAnalysis.sections_found || []}
                colorClass="bg-blue-50 text-blue-700 border border-blue-200 dark:bg-sky-950/40 dark:text-sky-100 dark:border-sky-700/50"
                t={t}
                formatItem={(item) => localizeSectionLabel(item, language)}
              />
            </div>
            <div>
              <p className="mb-2 text-sm font-bold text-gray-700 dark:text-slate-200">{t('report.sectionsMissing')}</p>
              <PillList
                items={visibleMissingSections}
                colorClass="bg-red-50 text-red-700 border border-red-200 dark:bg-rose-950/40 dark:text-rose-100 dark:border-rose-700/50"
                t={t}
                formatItem={(item) => localizeSectionLabel(item, language)}
              />
            </div>
          </div>
        </Card>
      )}

      <UnmatchedJdRequirements items={semanticAnalysis?.unmatched_jd_lines || []} t={t} />

      {visibleIssues.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-bold text-gray-900 dark:text-white">{t('report.issues', { count: visibleIssues.length })}</h3>
          {visibleIssues.map((issue, index) => (
            <IssueCard key={`${issue.code}-${index}`} issue={issue} language={language} t={t} />
          ))}
        </div>
      )}

      <RewriteExamples examples={rewriteExamples} language={language} t={t} />

      <Button
        variant="outline"
        className="w-full bg-white dark:bg-slate-950"
        onClick={() => downloadDocx(matchId, `report_${matchId}.docx`)}
      >
        {t('common.downloadWord')}
      </Button>

      <ScoringGuide isOpen={showGuide} onClose={() => setShowGuide(false)} t={t} />
    </div>
  );
}
