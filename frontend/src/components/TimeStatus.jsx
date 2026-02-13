'use client';

import { useState } from 'react';

const STATUS_CONFIG = {
  breaking: { label: 'BREAKING', color: '#EF4444', pulse: true },
  developing: { label: 'DEVELOPING', color: '#F59E0B', pulse: false },
  ongoing: { label: 'ONGOING', color: '#60A5FA', pulse: false },
  stale: { label: 'STALE', color: '#475569', pulse: false },
  // Legacy status aliases (pre-migration data)
  peak: { label: 'DEVELOPING', color: '#F59E0B', pulse: false },
  fading: { label: 'ONGOING', color: '#60A5FA', pulse: false },
};

function formatRelativeTime(isoDate) {
  if (!isoDate) return null;
  try {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = diffMs / (1000 * 60 * 60);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${Math.round(diffHours)}h ago`;
    const diffDays = diffHours / 24;
    if (diffDays < 7) return `${Math.round(diffDays)}d ago`;
    const diffWeeks = diffDays / 7;
    return `${Math.round(diffWeeks)}w ago`;
  } catch {
    return null;
  }
}

function formatExactDate(isoDate) {
  if (!isoDate) return 'Time data unavailable for older stories';
  try {
    const date = new Date(isoDate);
    return `Last article: ${date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })} ${date.toLocaleTimeString('en-US', {
      hour: 'numeric', minute: '2-digit',
    })}`;
  } catch {
    return 'Time data unavailable';
  }
}

export default function TimeStatus({ story, showVelocity = false }) {
  const [showTooltip, setShowTooltip] = useState(false);

  const status = story.status || 'developing';
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.developing;
  const lastArticle = story.last_article_at;
  const relTime = formatRelativeTime(lastArticle);
  const exactDate = formatExactDate(lastArticle);
  const velocity = story.coverage_velocity;
  const sourceCount = story.source_count;
  const isStale = status === 'stale';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
      {/* Status badge */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        opacity: isStale ? 0.5 : 1,
      }}>
        {/* Status dot */}
        <span style={{
          width: 6,
          height: 6,
          background: config.color,
          display: 'inline-block',
          flexShrink: 0,
          ...(config.pulse ? {
            animation: 'statusPulse 2s ease-in-out infinite',
          } : {}),
        }} />
        <span style={{
          fontSize: 9,
          fontWeight: 700,
          color: config.color,
          fontFamily: "'JetBrains Mono',monospace",
          letterSpacing: '0.06em',
          lineHeight: 1,
        }}>
          {config.label}
        </span>
      </div>

      {/* Relative time with tooltip */}
      {relTime && (
        <div
          style={{ position: 'relative' }}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <span style={{
            fontSize: 10,
            color: '#64748B',
            fontFamily: "'JetBrains Mono',monospace",
            cursor: 'help',
            lineHeight: 1,
          }}>
            {relTime}
          </span>

          {showTooltip && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: 6,
              padding: '6px 10px',
              background: '#0F172A',
              color: '#CBD5E1',
              fontSize: 10,
              fontFamily: "'JetBrains Mono',monospace",
              whiteSpace: 'nowrap',
              zIndex: 20,
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            }}>
              {exactDate}
            </div>
          )}
        </div>
      )}

      {/* Fallback when no time data */}
      {!relTime && (
        <span
          style={{
            fontSize: 10,
            color: '#475569',
            fontFamily: "'JetBrains Mono',monospace",
            cursor: 'help',
          }}
          title="Time data unavailable for older stories"
        >
          &mdash;
        </span>
      )}

      {/* Coverage velocity (detail page only) */}
      {showVelocity && velocity != null && (
        <span style={{
          fontSize: 10,
          color: '#64748B',
          fontFamily: "'JetBrains Mono',monospace",
          lineHeight: 1,
          marginTop: 2,
        }}>
          ~{velocity} articles/day{sourceCount ? ` across ${sourceCount} sources` : ''}
        </span>
      )}

      {/* Inject pulse animation CSS */}
      <style>{`
        @keyframes statusPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
