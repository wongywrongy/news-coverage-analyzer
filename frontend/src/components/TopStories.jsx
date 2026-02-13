'use client';

import Link from 'next/link';
import { getGroupLabel, getGroupColor, parseTrend, computeTrendDirection } from '../lib/constants';

function getDisplayLabel(category) {
  return getGroupLabel(category).replace(/&/g, 'and');
}

function getTag(story) {
  if (story.featured_reason === 'undercovered') return 'undercovered';
  const biasSpread = story.bias_spread || 0;
  if (biasSpread >= 1.5) return 'divergent';
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);
  if (trendDir === 'trending') return 'trending';
  return null;
}

function MetaSep() {
  return <span className="meta-sep" />;
}

export default function TopStories({ stories, stats, storyCount }) {
  if (!stories || stories.length < 2) return null;

  const lead = stories[0];
  const sides = stories.slice(1, 3);

  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  const topicCount = storyCount || 0;
  const articleCount = stats?.articleCount || 0;
  const metaParts = [dateStr, `${topicCount} topics`, `${articleCount.toLocaleString()} articles`];

  return (
    <section className="ts" style={{
      background: 'var(--bg)',
      padding: '0 48px var(--space-md)',
    }}>
      <div style={{ maxWidth: 1080, margin: '0 auto' }}>
        {/* Header */}
        <div className="ts-header" style={{
          paddingTop: 12,
          marginBottom: 'var(--space-md)',
          paddingBottom: 'var(--space-sm)',
          borderBottom: '2px solid var(--ink)',
          display: 'flex',
          alignItems: 'baseline',
          gap: 12,
        }}>
          <span className="ts-label" style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            color: 'var(--ink)',
          }}>
            Top Stories
          </span>
          {(topicCount > 0 || articleCount > 0) && (
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: 'var(--ink-muted)',
            }}>
              {metaParts.join(' \u00B7 ')}
            </span>
          )}
        </div>

        {/* Grid */}
        <div className="ts-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1.4fr 1fr',
          animation: 'fadeUp 0.5s ease both',
        }}>
          <LeadStory story={lead} />

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
  const label = getDisplayLabel(story.category);
  const color = getGroupColor(story.category);
  const tag = getTag(story);

  return (
    <Link href={`/topic/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="ts-lead" style={{
        paddingRight: 'var(--space-md)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}>
        {/* Category + tag row */}
        <div className="lead-cat-row">
          <span className="lead-cat" style={{ color }}>{label}</span>
          {tag === 'trending' && (
            <span className="tag-pill trending">Trending</span>
          )}
          {tag === 'divergent' && (
            <span className="tag-pill divergent">High divergence</span>
          )}
          {tag === 'undercovered' && (
            <span className="tag-pill undercovered">Undercovered</span>
          )}
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

        <div className="lead-meta" style={{ marginTop: 'auto' }}>
          <span className="mono">{story.article_count} articles</span>
          <MetaSep />
          <span className="mono">{story.source_count || '\u2014'} sources</span>
        </div>
      </div>
    </Link>
  );
}

function SideStory({ story, isLast }) {
  const label = getDisplayLabel(story.category);
  const color = getGroupColor(story.category);
  const tag = getTag(story);

  return (
    <Link href={`/topic/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', flex: 1, display: 'flex' }}>
      <div className="ts-side-item" style={{
        padding: 'var(--space-sm) var(--space-sm) var(--space-sm) var(--space-md)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        borderBottom: isLast ? 'none' : '1px solid var(--border)',
      }}>
        {/* Category + tag row */}
        <div className="side-cat-row">
          <span className="side-cat" style={{ color }}>{label}</span>
          {tag === 'trending' && (
            <span className="side-tag-pill trending">Trending</span>
          )}
          {tag === 'divergent' && (
            <span className="side-tag-pill divergent">High divergence</span>
          )}
          {tag === 'undercovered' && (
            <span className="side-tag-pill undercovered">Undercovered</span>
          )}
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

        <div className="side-meta">
          {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
        </div>
      </div>
    </Link>
  );
}
