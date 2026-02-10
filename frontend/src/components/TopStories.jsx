'use client';

import Link from 'next/link';
import { getGroupLabel, getGroupColor, parseTrend, computeTrendDirection } from '../lib/constants';

function getCatClass(category) {
  const label = getGroupLabel(category);
  if (label === 'Politics & Law') return 'politics';
  if (label === 'World & Security') return 'world';
  if (label === 'Economy & Business') return 'economy';
  return 'science';
}

function BadgePill({ story }) {
  const biasSpread = story.bias_spread || 0;
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);

  if (biasSpread >= 1.5) {
    return (
      <span className="ts-badge ts-badge-divergent">
        High framing divergence
      </span>
    );
  }

  if (trendDir === 'trending') {
    return (
      <span className="ts-badge ts-badge-trending">
        Trending
      </span>
    );
  }

  return null;
}

function MetaDivider() {
  return <span className="ts-divider" />;
}

export default function TopStories({ stories }) {
  if (!stories || stories.length < 2) return null;

  const lead = stories[0];
  const sides = stories.slice(1, 3);

  return (
    <section className="ts" style={{
      background: 'var(--bg)',
      padding: '0 48px var(--space-md)',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {/* Header */}
        <div className="ts-header" style={{
          paddingTop: 12,
          marginBottom: 'var(--space-sm)',
        }}>
          <span className="ts-label" style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            color: 'var(--ink)',
          }}>
            Top Stories Right Now
          </span>
        </div>

        {/* Grid */}
        <div className="ts-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1.4fr 1fr',
          animation: 'fadeUp 0.5s ease both',
        }}>
          {/* Lead story */}
          <LeadStory story={lead} />

          {/* Side stories */}
          <div className="ts-side" style={{
            borderLeft: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
          }}>
            {sides.map((s, i) => (
              <SideStory key={s.id} story={s} isLast={i === sides.length - 1} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function LeadStory({ story }) {
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="ts-lead" style={{
        paddingRight: 'var(--space-md)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}>
        <div style={{
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: groupColor,
          marginBottom: 'var(--space-xs)',
        }}>
          {groupLabel}
        </div>

        <h2 style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 800,
          fontSize: 30,
          lineHeight: 1.2,
          letterSpacing: '-0.5px',
          color: 'var(--ink)',
          marginBottom: 'var(--space-xs)',
        }}>
          {story.headline || story.topic}
        </h2>

        {story.lede && (
          <p style={{
            fontSize: 15,
            lineHeight: 1.55,
            color: 'var(--ink-secondary)',
            marginBottom: 'var(--space-sm)',
          }}>
            {story.lede}
          </p>
        )}

        <div className="meta-row" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm)',
          marginTop: 'auto',
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
          </span>
          <MetaDivider />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            Impact <strong style={{ color: 'var(--ink-secondary)', fontSize: 13 }}>{story.impact_score}</strong>
          </span>
          <MetaDivider />
          <BadgePill story={story} />
        </div>
      </div>
    </Link>
  );
}

function SideStory({ story, isLast }) {
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', flex: 1, display: 'flex' }}>
      <div className="ts-side-item" style={{
        padding: 'var(--space-sm) var(--space-sm) var(--space-sm) var(--space-md)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        borderBottom: isLast ? 'none' : '1px solid var(--border)',
      }}>
        <div style={{
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: groupColor,
          marginBottom: 'var(--space-xs)',
        }}>
          {groupLabel}
        </div>

        <h3 style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 800,
          fontSize: 18,
          lineHeight: 1.25,
          letterSpacing: '-0.2px',
          color: 'var(--ink)',
          marginBottom: 'auto',
        }}>
          {story.headline || story.topic}
        </h3>

        <div className="meta-row" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm)',
          marginTop: 'var(--space-sm)',
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
          </span>
          <MetaDivider />
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            Impact <strong style={{ color: 'var(--ink-secondary)', fontSize: 13 }}>{story.impact_score}</strong>
          </span>
          <BadgePill story={story} />
        </div>
      </div>
    </Link>
  );
}
