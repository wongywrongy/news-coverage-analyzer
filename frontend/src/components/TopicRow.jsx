'use client';

import Link from 'next/link';
import {
  getGroupLabel,
  getGroupColor,
  getCoverageScore,
  parseTrend,
  computeTrendDirection,
} from '../lib/constants';

function getCatClass(category) {
  const label = getGroupLabel(category);
  if (label === 'Politics & Law') return 'politics';
  if (label === 'World & Security') return 'world';
  if (label === 'Economy & Business') return 'economy';
  return 'science';
}

function formatDate(story) {
  const raw = story.last_article_at || story.last_updated || story.first_seen;
  if (!raw) return '\u2014';

  const d = new Date(raw);
  const now = new Date();

  // Determine start of the current week (Monday)
  const dayOfWeek = now.getDay();
  const mondayOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const weekStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - mondayOffset);

  // If topic date is within the current week: "Feb 9"
  if (d >= weekStart) {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Older than current week: "Feb 9, 2026"
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function BadgeInline({ story }) {
  const biasSpread = story.bias_spread || 0;
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);

  if (biasSpread >= 1.5) {
    return <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>divergent</span>;
  }
  if (trendDir === 'trending') {
    return <span style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>trending</span>;
  }
  return null;
}

function Separator() {
  return (
    <span style={{
      display: 'inline-block',
      width: 1,
      height: 10,
      background: 'var(--border)',
      flexShrink: 0,
      verticalAlign: 'middle',
    }} />
  );
}

export default function TopicRow({ story, index = 0 }) {
  const groupColor = getGroupColor(story.category);
  const catClass = getCatClass(story.category);
  const impactScore = Math.round(story.impact_score || 0);
  const coverageScore = Math.round(getCoverageScore(story));
  const badge = <BadgeInline story={story} />;

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div
        className={`topic-row topic-row-${catClass}`}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          padding: '18px 0 18px 16px',
          borderLeft: `3px solid ${groupColor}`,
          borderBottom: '1px solid #f0eeea',
          transition: 'all 0.2s ease',
          cursor: 'pointer',
          opacity: 0,
          animation: `fadeUp 0.35s ease ${0.05 + index * 0.03}s both`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderLeftWidth = '5px';
          e.currentTarget.style.background = 'rgba(0,0,0,0.012)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderLeftWidth = '3px';
          e.currentTarget.style.background = 'transparent';
        }}
      >
        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="topic-row-title" style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 700,
            fontSize: 17,
            lineHeight: 1.3,
            letterSpacing: '-0.2px',
            color: 'var(--ink)',
            marginBottom: 4,
          }}>
            {story.topic}
          </div>
          <div style={{
            fontSize: 12,
            color: 'var(--ink-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            flexWrap: 'wrap',
          }}>
            <span>{story.article_count || 0} articles</span>
            <span>&middot;</span>
            <span>{story.source_count || '\u2014'} sources</span>
            <Separator />
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
            }}>
              {formatDate(story)}
            </span>
            {badge && (
              <>
                <Separator />
                {badge}
              </>
            )}
          </div>
        </div>

        {/* Score columns */}
        <div className="topic-row-scores" style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
          <div style={{ textAlign: 'center', minWidth: 48 }}>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 20,
              lineHeight: 1,
              color: '#6B6B6B',
            }}>
              {impactScore}
            </div>
            <div style={{
              fontSize: 9,
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
              color: 'var(--ink-muted)',
              marginTop: 3,
            }}>
              Impact
            </div>
          </div>

          <div style={{ textAlign: 'center', minWidth: 48 }}>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 20,
              lineHeight: 1,
              color: '#6B6B6B',
            }}>
              {coverageScore}
            </div>
            <div style={{
              fontSize: 9,
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
              color: 'var(--ink-muted)',
              marginTop: 3,
            }}>
              Coverage
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
