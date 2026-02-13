'use client';

import Link from 'next/link';
import {
  getGap,
  getGroupLabel,
  getGroupColor,
  getCoverageRelationship,
  getCoverageScore,
  parseTrend,
  computeTrendDirection,
  getPrimaryCategory,
} from '../lib/constants';

/** Map a single day count to a visual state. */
function getDayState(count) {
  if (count === 0) return 'empty';
  if (count <= 4) return 'active';
  return 'hot';
}

/** Format a date string (YYYY-MM-DD) to short display (e.g., "Jan 26"). */
function formatShortDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}

const TREND_LABELS = {
  trending: '\u2191 trending',
  steady: '\u25A0 steady',
  cooling: '\u2193 cooling',
};

export default function TopicCard({ story, index = 0 }) {
  const gap = getGap(story);
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);
  const relationship = getCoverageRelationship(gap);
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);
  const primaryCat = getPrimaryCategory(story.category);

  // Get the category CSS class for the left border
  const catClass =
    groupLabel === 'Politics & Law' ? 'politics' :
    groupLabel === 'World & Security' ? 'world' :
    groupLabel === 'Economy & Business' ? 'economy' :
    'science';

  // Timeline dates
  const startDate = trend.length > 0 ? formatShortDate(trend[0].date) : '';

  // "More covered" badge
  const showMoreCovered = relationship === 'more-covered';

  const impactScore = Math.round(story.impact_score || 0);
  const coverageScore = Math.round(getCoverageScore(story));

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div
        className="topic-card"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '24px 28px',
          display: 'grid',
          gridTemplateColumns: '1fr auto',
          gap: 24,
          alignItems: 'center',
          transition: 'all 0.25s',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          opacity: 0,
          animation: `fadeUp 0.4s ease ${0.1 + index * 0.05}s both`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = '#ccc';
          e.currentTarget.style.boxShadow = 'var(--shadow-md)';
          e.currentTarget.style.transform = 'translateY(-2px)';
          const bar = e.currentTarget.querySelector('.card-left-bar');
          if (bar) bar.style.width = '6px';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.boxShadow = 'none';
          e.currentTarget.style.transform = 'translateY(0)';
          const bar = e.currentTarget.querySelector('.card-left-bar');
          if (bar) bar.style.width = '4px';
        }}
      >
        {/* Left color bar */}
        <div
          className="card-left-bar"
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: 4,
            background: groupColor,
            borderRadius: '12px 0 0 12px',
            transition: 'width 0.25s',
          }}
        />

        {/* Left content */}
        <div style={{ paddingLeft: 4 }}>
          {/* Meta row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
              padding: '3px 10px',
              borderRadius: 4,
              color: groupColor,
              background: `${groupColor}14`,
            }}>
              {primaryCat}
            </span>
            <span style={{
              fontSize: 13,
              color: 'var(--ink-muted)',
            }}>
              {story.article_count || 0} articles
            </span>
            {showMoreCovered && (
              <span style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--accent-gold)',
                background: 'var(--accent-gold-light)',
                padding: '2px 8px',
                borderRadius: 4,
              }}>
                &uarr; More covered
              </span>
            )}
          </div>

          {/* Title */}
          <div className="topic-title" style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 700,
            fontSize: 20,
            lineHeight: 1.3,
            marginBottom: 10,
            letterSpacing: '-0.3px',
          }}>
            {story.topic}
          </div>

          {/* Timeline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 11,
              color: 'var(--ink-muted)',
              fontFamily: "'JetBrains Mono', monospace",
              minWidth: 36,
            }}>
              {startDate}
            </span>
            <div style={{
              display: 'flex',
              gap: 2,
              alignItems: 'center',
              flex: 1,
              maxWidth: 200,
            }}>
              {trend.map((d, i) => {
                const state = getDayState(d.count);
                return (
                  <div
                    key={i}
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 2,
                      transition: 'all 0.2s',
                      ...(state === 'empty' && {
                        background: 'var(--border)',
                      }),
                      ...(state === 'active' && {
                        background: 'var(--accent-blue)',
                      }),
                      ...(state === 'hot' && {
                        background: 'var(--accent-blue-deep)',
                        transform: 'scaleY(1.4)',
                      }),
                    }}
                  />
                );
              })}
            </div>
            <span style={{
              fontSize: 11,
              color: 'var(--ink-muted)',
              fontFamily: "'JetBrains Mono', monospace",
              minWidth: 36,
            }}>
              Today
            </span>
            {trendDir && (
              <span style={{
                fontSize: 10,
                color: 'var(--ink-muted)',
                fontStyle: 'italic',
                marginLeft: 8,
              }}>
                {TREND_LABELS[trendDir]}
              </span>
            )}
          </div>
        </div>

        {/* Right: Scores */}
        <div className="topic-scores" style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
          {/* Impact */}
          <div style={{ textAlign: 'center', minWidth: 56 }}>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 28,
              lineHeight: 1,
              color: '#6B6B6B',
            }}>
              {impactScore}
            </div>
            <div style={{
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '1px',
              color: 'var(--ink-muted)',
              marginTop: 4,
            }}>
              Impact
            </div>
            <div style={{
              width: '100%',
              height: 3,
              background: 'var(--border)',
              borderRadius: 2,
              marginTop: 6,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${impactScore}%`,
                borderRadius: 2,
                background: '#AEAEAE',
                transition: 'width 0.5s ease',
              }} />
            </div>
          </div>

          {/* Coverage */}
          <div style={{ textAlign: 'center', minWidth: 56 }}>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 28,
              lineHeight: 1,
              color: '#6B6B6B',
            }}>
              {coverageScore}
            </div>
            <div style={{
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '1px',
              color: 'var(--ink-muted)',
              marginTop: 4,
            }}>
              Coverage
            </div>
            <div style={{
              width: '100%',
              height: 3,
              background: 'var(--border)',
              borderRadius: 2,
              marginTop: 6,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${coverageScore}%`,
                borderRadius: 2,
                background: '#AEAEAE',
                transition: 'width 0.5s ease',
              }} />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
