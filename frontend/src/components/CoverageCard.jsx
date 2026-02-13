'use client';

import { useState } from 'react';
import Link from 'next/link';
import CoverageTimeline from './CoverageTimeline';
import { getGap, getCategoryColor, getPrimaryCategory, getCoverageRelationship, computeActivityDays } from '../lib/constants';

const TOOLTIP_TEXT =
  'Impact score estimates real-world significance using population affected, ' +
  'economic magnitude, policy change, duration, and irreversibility. Coverage ' +
  'score reflects article volume from our tracked sources. The relationship ' +
  'between these scores is descriptive, not a judgment of media performance.';

const RELATIONSHIP_LABELS = {
  'less-covered': {
    text: 'Less covered than expected',
    color: '#C2B280',
    bg: 'rgba(194, 178, 128, 0.10)',
    border: 'rgba(194, 178, 128, 0.25)',
  },
  'more-covered': {
    text: 'More covered than expected',
    color: '#D4A054',
    bg: 'rgba(217, 119, 6, 0.08)',
    border: 'rgba(217, 119, 6, 0.25)',
  },
  'proportional': null,
};

const CARD_BG = '#1A1F2B';
const CARD_BG_HOVER = '#222838';

export default function CoverageCard({ story, index }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const gap = getGap(story);
  const catColor = getCategoryColor(story.category);
  const relationship = getCoverageRelationship(gap);
  const label = RELATIONSHIP_LABELS[relationship];
  const activityDays = computeActivityDays(story);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div
        style={{
          background: CARD_BG,
          border: '1px solid #2E3440',
          padding: 16,
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          animation: `fadeIn 0.25s ease ${index * 0.04}s both`,
          position: 'relative',
          minHeight: 180,
          display: 'flex',
          flexDirection: 'column',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = CARD_BG_HOVER;
          e.currentTarget.style.borderColor = '#3E4550';
          e.currentTarget.style.transform = 'translateY(-1px)';
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.4)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = CARD_BG;
          e.currentTarget.style.borderColor = '#2E3440';
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        {/* Top row: category + article count */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            color: catColor,
            fontFamily: "'JetBrains Mono',monospace",
            letterSpacing: '0.04em',
            padding: '2px 8px',
            background: catColor + '26',
            border: `1px solid ${catColor}4D`,
            textTransform: 'uppercase',
          }}>
            {getPrimaryCategory(story.category)}
          </span>
          <span style={{
            fontSize: 11,
            color: '#9B958C',
            fontFamily: "'JetBrains Mono',monospace",
          }}>
            {story.article_count} articles
          </span>
        </div>

        {/* Headline — 2-line clamp */}
        <h3 style={{
          fontSize: 16,
          fontWeight: 700,
          fontFamily: "'Source Serif 4',Georgia,serif",
          color: '#EEECE7',
          lineHeight: 1.35,
          letterSpacing: '-0.01em',
          marginBottom: 14,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}>
          {story.topic}
        </h3>

        {/* Coverage timeline */}
        <div style={{ marginBottom: 12 }}>
          <CoverageTimeline
            activityDays={activityDays}
            barHeight={14}
            firstSeen={story.first_seen}
          />
        </div>

        {/* Bottom row: coverage indicator + scores */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 'auto' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            {label ? (
              <span
                style={{
                  fontSize: 10,
                  color: label.color,
                  fontFamily: "'JetBrains Mono',monospace",
                  padding: '3px 10px',
                  background: label.bg,
                  border: `1px solid ${label.border}`,
                  cursor: 'help',
                  display: 'inline-block',
                  letterSpacing: '0.02em',
                }}
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onClick={e => { e.preventDefault(); e.stopPropagation(); setShowTooltip(v => !v); }}
              >
                {label.text}
              </span>
            ) : (
              <span style={{ display: 'inline-block', height: 22 }} />
            )}

            {showTooltip && (
              <div style={{
                position: 'absolute',
                bottom: '100%',
                left: 0,
                marginBottom: 8,
                width: 280,
                padding: '12px 14px',
                background: '#0B0F18',
                color: '#D5CFC5',
                fontSize: 11,
                fontFamily: "'Source Serif 4',Georgia,serif",
                lineHeight: 1.6,
                zIndex: 20,
                border: '1px solid #2E3440',
                boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
              }}>
                {TOOLTIP_TEXT}
              </div>
            )}
          </div>

          <span style={{
            fontSize: 11,
            fontFamily: "'JetBrains Mono',monospace",
            color: '#706B63',
            flexShrink: 0,
          }}>
            i:{Math.round(story.impact_score || 0)} a:{Math.round(story.attention_score || 0)}
          </span>
        </div>
      </div>
    </Link>
  );
}
