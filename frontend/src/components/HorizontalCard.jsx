'use client';

import Link from 'next/link';
import CoverageTimeline from './CoverageTimeline';
import {
  getGap,
  getPrimaryCategory,
  getGroupLabel,
  getGroupColor,
  getCoverageRelationship,
  computeActivityDays,
} from '../lib/constants';

export default function HorizontalCard({ story, index = 0 }) {
  const gap = getGap(story);
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);
  const relationship = getCoverageRelationship(gap);
  const activityDays = computeActivityDays(story);
  const primaryCat = getPrimaryCategory(story.category);

  // Lede: first sentence of analysis context, lede, or bottom_line
  const lede = story.analysis?.lede
    || story.analysis?.context?.split(/(?<=[.!?])\s/)?.[0]
    || story.analysis?.bottom_line?.split(/(?<=[.!?])\s/)?.[0]
    || '';

  // Source names from articles or source_names field
  let sourceNames = [];
  if (story.articles && Array.isArray(story.articles)) {
    sourceNames = [...new Set(story.articles.map(a => a.source?.name).filter(Boolean))];
  } else if (story.source_names) {
    try {
      const parsed = typeof story.source_names === 'string' ? JSON.parse(story.source_names) : story.source_names;
      if (Array.isArray(parsed)) sourceNames = parsed;
    } catch { /* ignore */ }
  }
  const displaySources = sourceNames.slice(0, 4).join(', ');
  const moreCount = sourceNames.length - 4;
  const sourceText = moreCount > 0 ? `${displaySources} +${moreCount} more` : displaySources;

  const coverageLabel = relationship === 'less-covered'
    ? { text: '\u2193 Less covered', color: '#4A6FA5', bg: 'rgba(74,111,165,0.06)', border: 'rgba(74,111,165,0.18)' }
    : relationship === 'more-covered'
    ? { text: '\u2191 More covered', color: '#A06B20', bg: 'rgba(180,100,20,0.06)', border: 'rgba(180,100,20,0.16)' }
    : null;

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div
        className="h-card"
        style={{
          display: 'flex',
          background: '#FAFAFA',
          border: '1px solid #E8E8E8',
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          opacity: 0,
          transform: 'translateY(20px)',
          animation: `fadeUpCard 500ms ease ${index * 120}ms forwards`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = '#FFFFFF';
          e.currentTarget.style.borderColor = '#D0D0D0';
          e.currentTarget.style.boxShadow = '0 6px 24px rgba(0,0,0,0.08)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = '#FAFAFA';
          e.currentTarget.style.borderColor = '#E8E8E8';
          e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.02)';
        }}
      >
        {/* Left color bar */}
        <div style={{
          width: 4,
          flexShrink: 0,
          background: groupColor,
          borderRadius: '2px 0 0 2px',
        }} />

        {/* Content */}
        <div style={{ flex: 1, padding: '16px 20px', minWidth: 0 }}>
          {/* Row 1: category · article count · coverage label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 9,
              fontWeight: 600,
              color: groupColor,
              fontFamily: "'JetBrains Mono', monospace",
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}>
              {primaryCat}
            </span>
            <span style={{
              fontSize: 10,
              color: '#9CA3AF',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              &middot; {story.article_count || 0} articles
            </span>
            {coverageLabel && (
              <span style={{
                fontSize: 10,
                color: coverageLabel.color,
                fontFamily: "'JetBrains Mono', monospace",
                padding: '2px 8px',
                background: coverageLabel.bg,
                border: `1px solid ${coverageLabel.border}`,
              }}>
                {coverageLabel.text}
              </span>
            )}
          </div>

          {/* Row 2: headline */}
          <h3 style={{
            fontSize: 17,
            fontWeight: 700,
            fontFamily: "'Source Serif 4', Georgia, serif",
            color: '#111827',
            lineHeight: 1.35,
            letterSpacing: '-0.01em',
            marginBottom: 6,
          }}>
            {story.topic}
          </h3>

          {/* Row 3: lede */}
          {lede && (
            <p style={{
              fontSize: 13,
              color: '#6B7280',
              fontFamily: "'Source Serif 4', Georgia, serif",
              lineHeight: 1.55,
              marginBottom: 12,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {lede}
            </p>
          )}

          {/* Row 4: timeline + sources */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ maxWidth: 200, flex: '0 0 200px' }}>
              <CoverageTimeline
                activityDays={activityDays}
                barHeight={8}
                firstSeen={story.first_seen}
                animated
              />
            </div>
            {sourceText && (
              <span style={{
                fontSize: 9,
                color: '#B5B5B5',
                fontFamily: "'JetBrains Mono', monospace",
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {sourceText}
              </span>
            )}
          </div>
        </div>

        {/* Right: Impact & Coverage scores */}
        <div style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '16px 20px 16px 0',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: 20,
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
              color: '#4A6FA5',
              lineHeight: 1,
            }}>
              {Math.round(story.impact_score || 0)}
            </div>
            <div style={{
              fontSize: 8,
              fontWeight: 600,
              fontFamily: "'JetBrains Mono', monospace",
              color: '#9CA3AF',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginTop: 4,
            }}>
              Impact
            </div>
          </div>
          <div style={{ width: 1, height: 28, background: '#E8E8E8' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: 20,
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
              color: '#C8A84E',
              lineHeight: 1,
            }}>
              {Math.round(story.attention_score || 0)}
            </div>
            <div style={{
              fontSize: 8,
              fontWeight: 600,
              fontFamily: "'JetBrains Mono', monospace",
              color: '#9CA3AF',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginTop: 4,
            }}>
              Coverage
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
