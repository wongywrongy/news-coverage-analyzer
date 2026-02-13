'use client';

import Link from 'next/link';
import { getGroupLabel, getGroupColor, parseTrend, computeTrendDirection } from '../lib/constants';

/* Brighter category colors for dark backgrounds (WCAG AA on #1B1B1B) */
const DARK_BG_CAT_COLORS = {
  'Politics & Law': '#E8756B',
  'World & Security': '#6B9FD4',
  'Economy & Business': '#C8963E',
  'Science & Health': '#5BC88A',
};

function getCatColorDark(category) {
  const label = getGroupLabel(category);
  return DARK_BG_CAT_COLORS[label] || '#C8963E';
}

function getCatClass(category) {
  const label = getGroupLabel(category);
  if (label === 'Politics & Law') return 'politics';
  if (label === 'World & Security') return 'world';
  if (label === 'Economy & Business') return 'economy';
  return 'science';
}

export default function Headlines({ stories }) {
  if (!stories || stories.length === 0) return null;

  const lead = stories[0];
  const sides = stories.slice(1, 4);

  return (
    <section className="headlines-section" style={{
      background: 'var(--bg-dark)',
      color: '#fff',
      padding: 'var(--space-lg) 48px var(--space-md)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Combined radial gradient overlay */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'radial-gradient(ellipse at 20% 50%, rgba(200,150,62,0.08) 0%, transparent 60%), radial-gradient(ellipse at 80% 50%, rgba(43,76,126,0.08) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      <div style={{ maxWidth: 1280, margin: '0 auto', position: 'relative' }}>
        {/* Header row */}
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-sm)',
        }}>
          <span style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            color: 'var(--accent-gold)',
          }}>
            Top Stories Right Now
          </span>
          <span style={{
            fontSize: 12,
            color: 'rgba(255,255,255,0.4)',
          }}>
            Ranked by impact, coverage, and framing divergence
          </span>
        </div>

        <div className="headlines-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 1fr',
          gap: 'var(--space-sm)',
          animation: 'fadeUp 0.5s ease both',
        }}>
          {/* Lead card */}
          <LeadCard story={lead} />

          {/* Side cards */}
          {sides.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              {sides.map(s => (
                <SideCard key={s.id} story={s} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function BadgePill({ story }) {
  const biasSpread = story.bias_spread || 0;
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);

  if (biasSpread >= 1.5) {
    return (
      <span style={{
        fontSize: 11,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: 3,
        color: '#E8756B',
        background: 'rgba(232,117,107,0.15)',
      }}>
        High framing divergence
      </span>
    );
  }

  if (trendDir === 'trending') {
    return (
      <span style={{
        fontSize: 11,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: 3,
        color: 'var(--accent-gold)',
        background: 'rgba(200,150,62,0.15)',
      }}>
        Trending
      </span>
    );
  }

  return null;
}

function MetaDivider() {
  return (
    <span style={{
      width: 1,
      height: 12,
      background: 'rgba(255,255,255,0.15)',
      flexShrink: 0,
    }} />
  );
}

function LeadCard({ story }) {
  const groupLabel = getGroupLabel(story.category);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div style={{
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 'var(--radius)',
        padding: 'var(--space-md)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'border-color 0.3s',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        height: '100%',
      }}>
        {/* Gold left bar */}
        <div style={{
          position: 'absolute',
          left: 0, top: 0, bottom: 0,
          width: 4,
          background: 'var(--accent-gold)',
          borderRadius: '0 2px 2px 0',
        }} />

        <div>
          <div style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: 'var(--accent-gold)',
            marginBottom: 'var(--space-sm)',
          }}>
            {groupLabel}
          </div>

          <h2 style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 800,
            fontSize: 26,
            lineHeight: 1.2,
            letterSpacing: '-0.5px',
            color: '#FFFFFF',
            marginBottom: 'var(--space-xs)',
          }}>
            {story.headline || story.topic}
          </h2>

          {story.lede && (
            <p style={{
              fontSize: 14,
              lineHeight: 1.55,
              color: 'rgba(255,255,255,0.55)',
              marginBottom: 'var(--space-sm)',
            }}>
              {story.lede}
            </p>
          )}
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm)',
          marginTop: 'auto',
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'rgba(255,255,255,0.4)',
          }}>
            {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
          </span>
          <MetaDivider />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'rgba(255,255,255,0.4)',
          }}>
            Impact <strong style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{story.impact_score}</strong>
          </span>
          <MetaDivider />
          <BadgePill story={story} />
        </div>
      </div>
    </Link>
  );
}

function SideCard({ story }) {
  const groupLabel = getGroupLabel(story.category);
  const catColorDark = getCatColorDark(story.category);
  const groupColor = getGroupColor(story.category);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', flex: 1, display: 'flex' }}>
      <div style={{
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 'var(--radius)',
        padding: 'var(--space-sm) var(--space-md)',
        transition: 'border-color 0.3s',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Category-colored left bar */}
        <div style={{
          position: 'absolute',
          left: 0, top: 0, bottom: 0,
          width: 3,
          borderRadius: '0 2px 2px 0',
          background: groupColor,
        }} />

        <div style={{
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: catColorDark,
          marginBottom: 'var(--space-xs)',
        }}>
          {groupLabel}
        </div>

        <h3 style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 800,
          fontSize: 17,
          lineHeight: 1.25,
          letterSpacing: '-0.2px',
          color: '#FFFFFF',
          marginBottom: 'auto',
        }}>
          {story.headline || story.topic}
        </h3>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm)',
          marginTop: 'var(--space-sm)',
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'rgba(255,255,255,0.4)',
          }}>
            {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
          </span>
          <MetaDivider />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'rgba(255,255,255,0.4)',
          }}>
            Impact <strong style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{story.impact_score}</strong>
          </span>
          <BadgePill story={story} />
        </div>
      </div>
    </Link>
  );
}
