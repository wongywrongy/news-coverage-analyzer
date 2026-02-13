'use client';

import { useState } from 'react';
import Link from 'next/link';
import { getGroupLabel, getGroupColor, parseTrend, computeTrendDirection } from '../lib/constants';

function getTag(story) {
  if (story.featured_reason === 'undercovered') return 'undercovered';
  const biasSpread = story.bias_spread || 0;
  if (biasSpread >= 1.5) return 'divergent';
  const trend = parseTrend(story);
  const trendDir = computeTrendDirection(trend);
  if (trendDir === 'trending') return 'trending';
  return null;
}

function TagPill({ tag }) {
  if (!tag) return null;
  const config = {
    trending: { label: 'Trending', bg: 'rgba(200,150,62,0.12)', color: 'var(--accent-gold)' },
    divergent: { label: 'High divergence', bg: 'rgba(192,57,43,0.08)', color: 'var(--cat-politics)' },
    undercovered: { label: 'Undercovered', bg: 'rgba(43,76,126,0.10)', color: 'var(--accent-blue)' },
  };
  const c = config[tag];
  if (!c) return null;
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 9,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      padding: '2px 8px',
      borderRadius: 8,
      background: c.bg,
      color: c.color,
    }}>
      {c.label}
    </span>
  );
}

export default function FeaturedStories({ stories }) {
  if (!stories || stories.length === 0) return null;

  const featured = stories.slice(0, 3);

  return (
    <section style={{
      padding: 'var(--space-xl) 48px',
      background: 'var(--bg)',
    }}>
      <div style={{ maxWidth: 1080, margin: '0 auto' }}>
        {/* Header row */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 'var(--space-md)',
          paddingBottom: 'var(--space-sm)',
          borderBottom: '2px solid var(--ink)',
        }}>
          <span style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            color: 'var(--ink)',
          }}>
            Recent Analysis
          </span>
          <Link href="/news" style={{
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--accent-blue)',
            textDecoration: 'none',
          }}>
            See today's full briefing &rarr;
          </Link>
        </div>

        {/* Card grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--space-md)',
        }}>
          {featured.map(story => (
            <FeaturedCard key={story.id} story={story} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeaturedCard({ story }) {
  const [hovered, setHovered] = useState(false);
  const label = getGroupLabel(story.category).replace(/&/g, 'and');
  const color = getGroupColor(story.category);
  const tag = getTag(story);

  return (
    <Link href={`/topic/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 'var(--space-md)',
          cursor: 'pointer',
          transition: 'box-shadow 0.2s, transform 0.2s',
          boxShadow: hovered ? 'var(--shadow-md)' : 'var(--shadow-sm)',
          transform: hovered ? 'translateY(-2px)' : 'none',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Category + tag */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color,
          }}>
            {label}
          </span>
          <TagPill tag={tag} />
        </div>

        {/* Title */}
        <h3 style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 700,
          fontSize: 20,
          lineHeight: 1.25,
          letterSpacing: '-0.3px',
          color: 'var(--ink)',
          marginBottom: 8,
        }}>
          {story.headline || story.topic}
        </h3>

        {/* Lede */}
        {story.lede && (
          <p style={{
            fontSize: 14,
            lineHeight: 1.5,
            color: 'var(--ink-secondary)',
            marginBottom: 'var(--space-sm)',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            flex: 1,
          }}>
            {story.lede}
          </p>
        )}

        {/* Meta */}
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: 'var(--ink-muted)',
          marginTop: 'auto',
        }}>
          {story.article_count} articles &middot; {story.source_count || '\u2014'} sources
        </div>
      </div>
    </Link>
  );
}
