'use client';

import { useState } from 'react';
import CoverageCard from './CoverageCard';

const MAX_VISIBLE = 6;

export default function CategorySection({ categoryKey, categoryLabel, categoryColor, stories, startIndex }) {
  const [collapsed, setCollapsed] = useState(false);
  const [showAll, setShowAll] = useState(false);

  if (!stories || stories.length === 0) return null;

  const visibleStories = showAll ? stories : stories.slice(0, MAX_VISIBLE);
  const hasMore = stories.length > MAX_VISIBLE;

  return (
    <section style={{ marginBottom: 40 }}>
      {/* Section header */}
      <button
        onClick={() => setCollapsed(v => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          width: '100%',
          background: 'none',
          border: 'none',
          borderLeft: `4px solid ${categoryColor}`,
          padding: '10px 16px',
          cursor: 'pointer',
          marginBottom: collapsed ? 0 : 20,
        }}
      >
        <span style={{
          fontSize: 13,
          fontWeight: 700,
          color: '#D5CFC5',
          fontFamily: "'JetBrains Mono',monospace",
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          {categoryLabel}
        </span>
        <span style={{
          fontSize: 11,
          color: '#9B958C',
          fontFamily: "'JetBrains Mono',monospace",
        }}>
          {stories.length} {stories.length === 1 ? 'story' : 'stories'}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: 10,
          color: '#9B958C',
          fontFamily: "'JetBrains Mono',monospace",
          transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          transition: 'transform 0.15s ease',
        }}>
          &#9660;
        </span>
      </button>

      {/* Card grid */}
      {!collapsed && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: 12,
          }}>
            {visibleStories.map((story, i) => (
              <CoverageCard key={story.id} story={story} index={startIndex + i} />
            ))}
          </div>

          {hasMore && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              style={{
                display: 'block',
                width: '100%',
                padding: 12,
                marginTop: 8,
                background: 'transparent',
                border: '1px dashed #2E3440',
                color: '#9B958C',
                fontSize: 11,
                fontFamily: "'JetBrains Mono',monospace",
                letterSpacing: '0.03em',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#C2B280';
                e.currentTarget.style.color = '#C2B280';
                e.currentTarget.style.background = 'rgba(194, 178, 128, 0.04)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#2E3440';
                e.currentTarget.style.color = '#9B958C';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              Show all {stories.length} stories &rarr;
            </button>
          )}
        </>
      )}
    </section>
  );
}
