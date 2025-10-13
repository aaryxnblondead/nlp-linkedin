import React from 'react';

function Pill({ children, tone = 'default' }) {
  const className = `pill pill-${tone}`;
  return <span className={className}>{children}</span>;
}

function meterColor(v) {
  if (v >= 0.75) return 'good';
  if (v >= 0.5) return 'medium';
  return 'low';
}

export default function SummaryCell({ insights }) {
  if (!insights) return <span className="muted">No summary</span>;
  const rating = insights.rating ?? null;
  const ratingLabel = (insights.rating_label || '').toLowerCase();
  const exp = insights.experience_years ?? null;
  const summaryText = insights.summary || '';
  const ed = typeof insights.education_score === 'number' ? insights.education_score : null;
  const act = typeof insights.activity_score === 'number' ? insights.activity_score : null;
  const sent = typeof insights.sentiment_score === 'number' ? insights.sentiment_score : null;

  // Extract newly added resume-quality signals from summary if present
  let projectQuality = null;
  let confidenceTone = null;
  try {
    const pqMatch = summaryText.match(/Project quality \(resume\):\s*([0-9.]+)/i);
    if (pqMatch) projectQuality = parseFloat(pqMatch[1]);
  } catch {}
  try {
    const toneMatch = summaryText.match(/Confidence tone:\s*([0-9.]+)/i);
    if (toneMatch) confidenceTone = parseFloat(toneMatch[1]);
  } catch {}

  // Try to extract a few skill hints from the summary string
  const skillsMatch = summaryText.match(/Skills\s*\((?:[^)]*)\):\s*([^|]+)/i);
  const skillsBlock = skillsMatch ? String(skillsMatch[1]) : '';
  // Split by common delimiters first; if none found, fall back to whitespace tokenization
  let skillsTokens = [];
  if (skillsBlock) {
    const normalized = skillsBlock.replace(/\s+/g, ' ').trim();
    const hasDelims = /[;,|•·]/.test(normalized);
    if (hasDelims) {
      skillsTokens = normalized.split(/[;,|•·]/g);
    } else if (normalized.includes(',')) {
      skillsTokens = normalized.split(',');
    } else {
      // Fallback: split by spaces to avoid huddling multiple skills into one chip
      skillsTokens = normalized.split(/\s+/g);
    }
  }
  // Clean up tokens, drop trivial connectors, dedupe
  const STOPWORDS = new Set(['and','or','with','for','of','the','to','in','on','at','a','an','&']);
  const skillsList = Array.from(
    new Set(
      skillsTokens
        .map((s) => s.trim())
        .filter((s) => s && !STOPWORDS.has(s.toLowerCase()))
    )
  );
  const maxSkills = 4;
  const shownSkills = skillsList.slice(0, maxSkills);
  const moreCount = Math.max(0, skillsList.length - maxSkills);

  const rateTone = rating >= 75 ? 'good' : rating >= 60 ? 'medium' : 'low';

  return (
    <div className="summary-cell" aria-label="Candidate summary">
      {/* Header pills */}
      <div className="summary-row">
        <Pill tone={rateTone}>Rating {rating ?? 'N/A'}</Pill>
        {ratingLabel && <Pill tone="soft">{insights.rating_label}</Pill>}
        {typeof exp === 'number' && <Pill tone="soft">{exp} yrs exp</Pill>}
      </div>

      {/* Top skills (compact) */}
      {(shownSkills.length > 0 || moreCount > 0) && (
        <div className="summary-row chips" aria-label="Top skills">
          {shownSkills.map((s, i) => (
            <span key={i} className="chip chip-sm" title={s}>{s}</span>
          ))}
          {moreCount > 0 && (
            <span className="chip chip-sm chip-more" title={`${moreCount} more skills`}>+{moreCount} more</span>
          )}
        </div>
      )}

      {/* KPI meters in a responsive grid */}
      <div className="summary-meters">
        <div className="meter-row">
          <div className="meter-label">Education</div>
          <div className={`meter meter-${meterColor(ed ?? 0)}`}>
            <div className="bar" style={{ width: `${Math.max(0, Math.min(1, ed ?? 0)) * 100}%` }} />
          </div>
        </div>
        <div className="meter-row">
          <div className="meter-label">Activity</div>
          <div className={`meter meter-${meterColor(act ?? 0)}`}>
            <div className="bar" style={{ width: `${Math.max(0, Math.min(1, act ?? 0)) * 100}%` }} />
          </div>
        </div>
        <div className="meter-row">
          <div className="meter-label">Sentiment</div>
          <div className={`meter meter-${meterColor(((sent ?? 0) + 1) / 2)}`}>
            <div className="bar" style={{ width: `${Math.max(0, Math.min(2, (sent ?? 0) + 1)) * 50}%` }} />
          </div>
        </div>
      </div>

      {/* Additional signals (compact chips) */}
      {(projectQuality !== null || confidenceTone !== null) && (
        <div className="summary-row chips" style={{ marginTop: 6 }}>
          {projectQuality !== null && (
            <span className="chip chip-sm" title="Resume projects signal">Project quality: {projectQuality.toFixed(2)}</span>
          )}
          {confidenceTone !== null && (
            <span className="chip chip-sm" title="Ownership/confidence tone">Confidence tone: {confidenceTone.toFixed(2)}</span>
          )}
        </div>
      )}
    </div>
  );
}
