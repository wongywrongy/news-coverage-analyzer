'use client';

import Link from 'next/link';
import { getGap, getCategoryColor, getPrimaryCategory } from '../lib/constants';

export default function CoverageBar({ story, index }) {
  const g = getGap(story);
  const ag = Math.abs(g);
  const isPos = g >= 20;
  const isNeg = g <= -20;
  const catColor = getCategoryColor(story.category);

  const barColor = isPos ? '#2563EB' : isNeg ? '#D97706' : '#94A3B8';
  const barGradient = isPos
    ? 'linear-gradient(to right, rgba(37,99,235,0.08), rgba(37,99,235,0.3))'
    : isNeg
    ? 'linear-gradient(to right, rgba(217,119,6,0.06), rgba(217,119,6,0.25))'
    : 'linear-gradient(to right, rgba(148,163,184,0.04), rgba(148,163,184,0.12))';

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', padding: '16px 24px',
          cursor: 'pointer', borderBottom: '1px solid #F3F4F6',
          transition: 'all 0.15s ease',
          animation: `fadeIn 0.2s ease ${index * 0.03}s both`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = '#F8FAFC';
          e.currentTarget.style.borderLeftColor = catColor;
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = 'white';
          e.currentTarget.style.borderLeftColor = 'transparent';
        }}
      >
        {/* Category dot */}
        <div style={{ width: 4, height: 32, background: catColor, marginRight: 16, flexShrink: 0, opacity: 0.6 }} />

        <div style={{ width: 380, paddingRight: 24, flexShrink: 0 }}>
          <div style={{ fontSize: 15, color: '#111827', fontFamily: "'Source Serif 4',Georgia,serif", fontWeight: 600, lineHeight: 1.4, marginBottom: 4 }}>
            {story.topic}
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#9CA3AF', fontFamily: "'JetBrains Mono',monospace" }}>
            <span>{story.article_count} articles</span>
            <span>{story.source_count} sources</span>
            <span style={{ color: catColor, fontWeight: 600 }}>{getPrimaryCategory(story.category)}</span>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ flex: 1, height: 28, background: '#F8FAFC', overflow: 'hidden', position: 'relative', border: '1px solid #F1F5F9' }}>
            <div style={{
              height: '100%',
              width: `${Math.max(ag, 3)}%`,
              background: barGradient,
              transition: 'width 0.3s ease',
            }} />
            {ag >= 5 && (
              <span style={{
                position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
                fontSize: 11, fontWeight: 700,
                color: barColor,
                fontFamily: "'JetBrains Mono',monospace",
              }}>
                {g}
              </span>
            )}
          </div>

          {/* Score pills */}
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono',monospace", color: '#64748B', padding: '3px 8px', background: '#F1F5F9' }}>
              {Math.round(story.impact_score || 0)}i
            </span>
            <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono',monospace", color: '#64748B', padding: '3px 8px', background: '#F1F5F9' }}>
              {Math.round(story.attention_score || 0)}a
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
