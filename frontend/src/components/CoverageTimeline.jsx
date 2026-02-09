'use client';

import { useState, useEffect } from 'react';

function getWindowDates(windowDays) {
  const now = new Date();
  return Array.from({ length: windowDays }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    d.setDate(d.getDate() - (windowDays - 1 - i));
    return d;
  });
}

export default function CoverageTimeline({
  activityDays,
  barHeight = 8,
  showDates = true,
  showSummary = false,
  firstSeen,
  lastArticleAt,
  animated = false,
  staggerDelay = 40,
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const [mounted, setMounted] = useState(false);
  const days = activityDays || Array(14).fill(false);
  const windowDays = days.length;
  const activeDayCount = days.filter(Boolean).length;

  useEffect(() => setMounted(true), []);

  // Compute dates only on client to avoid hydration mismatch
  const dates = mounted ? getWindowDates(windowDays) : null;
  const startLabel = dates
    ? dates[0].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '';

  return (
    <div style={{ width: '100%' }}>
      <div
        style={{
          display: 'flex',
          gap: 2,
          borderRadius: 2,
          overflow: 'hidden',
          background: '#E2DDCF',
          height: barHeight,
        }}
        role="img"
        aria-label={`Coverage timeline: active ${activeDayCount} of ${windowDays} days`}
      >
        {days.map((active, i) => {
          const dateLabel = dates
            ? dates[i].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            : '';
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: barHeight,
                background: active ? '#5578A8' : 'transparent',
                borderRadius: 1,
                position: 'relative',
                cursor: 'default',
                ...(animated ? {
                  transform: 'scaleX(0)',
                  transformOrigin: 'left',
                  animation: `barGrow 0.15s ease ${i * staggerDelay}ms forwards`,
                } : {}),
              }}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              {hoveredIdx === i && dateLabel && (
                <div style={{
                  position: 'absolute',
                  bottom: '100%',
                  marginBottom: 6,
                  padding: '4px 8px',
                  background: '#FFFFFF',
                  border: '1px solid #E5E5E5',
                  color: '#6B7280',
                  fontSize: 9,
                  fontFamily: "'JetBrains Mono', monospace",
                  whiteSpace: 'nowrap',
                  zIndex: 30,
                  pointerEvents: 'none',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  ...(i < 3 ? { left: 0 } : i > windowDays - 4 ? { right: 0 } : { left: '50%', transform: 'translateX(-50%)' }),
                }}>
                  {dateLabel} &middot; {active ? 'covered' : 'no coverage'}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showDates && !showSummary && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
          <span style={{ fontSize: 8, color: '#B5AFA0', fontFamily: "'JetBrains Mono', monospace" }}>
            {startLabel}
          </span>
          <span style={{ fontSize: 8, color: '#B5AFA0', fontFamily: "'JetBrains Mono', monospace" }}>
            Today
          </span>
        </div>
      )}

      {showSummary && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 6 }}>
          <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: "'JetBrains Mono', monospace" }}>
            {mounted && firstSeen && <>First tracked {new Date(firstSeen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</>}
            {mounted && firstSeen && lastArticleAt && <> &middot; </>}
            {mounted && lastArticleAt && <>Last article {new Date(lastArticleAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</>}
          </span>
          <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: "'JetBrains Mono', monospace" }}>
            Active {activeDayCount} of {windowDays} days
          </span>
        </div>
      )}
    </div>
  );
}
