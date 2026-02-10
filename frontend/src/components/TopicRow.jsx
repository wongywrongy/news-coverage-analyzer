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

  // Compare dates in local time
  const dDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const nowDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.round((nowDate - dDate) / 86400000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';

  // Same year: "Feb 9"
  if (d.getFullYear() === now.getFullYear()) {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Different year: "Dec 3 '24"
  const month = d.toLocaleDateString('en-US', { month: 'short' });
  const day = d.getDate();
  const year = String(d.getFullYear()).slice(2);
  return `${month} ${day} '${year}`;
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
          borderBottom: '1px solid var(--border)',
          transition: 'all 0.2s ease',
          cursor: 'pointer',
          opacity: 0,
          animation: `fadeUp 0.35s ease ${0.05 + index * 0.03}s both`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderLeftWidth = '5px';
          e.currentTarget.style.background = 'rgba(0,0,0,0.015)';
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
            {badge && (
              <>
                <span>&middot;</span>
                {badge}
              </>
            )}
          </div>
        </div>

        {/* Date column */}
        <div className="topic-row-date" style={{
          minWidth: 72,
          textAlign: 'right',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: 'var(--ink-muted)',
          flexShrink: 0,
        }}>
          {formatDate(story)}
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
