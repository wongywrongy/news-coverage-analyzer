'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { getCategoryColor, getPrimaryCategory } from '../lib/constants';

const LEAN_POSITIONS = {
  'far-left': 0.08,
  'left': 0.15,
  'left-center': 0.32,
  'center': 0.50,
  'right-center': 0.68,
  'right': 0.85,
  'far-right': 0.92,
};

const BAND_LABELS = [
  { label: 'LEFT', y: 0.115 },
  { label: 'LEFT-CENTER', y: 0.32 },
  { label: 'CENTER', y: 0.50 },
  { label: 'RIGHT-CENTER', y: 0.68 },
  { label: 'RIGHT', y: 0.885 },
];

const BAND_DIVIDERS = [0.23, 0.41, 0.59, 0.77];

const PAD = { top: 10, right: 20, bottom: 30, left: 80 };
const W = 500;
const H = 280;
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

function seededRandom(seed) {
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function timeToX(publishedAt, windowStart, range) {
  const pos = (new Date(publishedAt) - windowStart) / range;
  return PAD.left + Math.max(0, Math.min(1, pos)) * PLOT_W;
}

function leanToY(bias) {
  const norm = LEAN_POSITIONS[bias] || 0.5;
  return PAD.top + norm * PLOT_H;
}

function getDateLabels(windowStart) {
  const labels = [];
  for (let i = 0; i < 7; i += 2) {
    const d = new Date(windowStart);
    d.setDate(d.getDate() + i);
    labels.push({
      date: d,
      label: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      frac: i / 7,
    });
  }
  return labels;
}

export default function DotStripPlot({ articles, storyMap }) {
  const [hovered, setHovered] = useState(null);

  const { dots, windowStart, range, dateLabels, dayFractions } = useMemo(() => {
    const now = new Date();
    const ws = new Date(now);
    ws.setDate(ws.getDate() - 7);
    ws.setHours(0, 0, 0, 0);
    const r = now - ws;

    const mapped = articles.map((a, i) => {
      const story = storyMap[a.story_id];
      const cat = story ? getPrimaryCategory(story.category) : 'OTHER';
      const jitterY = (seededRandom(a.id || i) - 0.5) * 16;
      return {
        ...a,
        cx: timeToX(a.published_at, ws, r),
        cy: leanToY(a.source_bias) + jitterY,
        color: getCategoryColor(cat),
        storyTopic: story?.topic || 'Unknown story',
        storyId: a.story_id,
        cat,
        dateLabel: new Date(a.published_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', year: 'numeric',
        }),
      };
    });

    const dl = getDateLabels(ws);
    const dayFracs = Array.from({ length: 8 }, (_, i) => i / 7);

    return { dots: mapped, windowStart: ws, range: r, dateLabels: dl, dayFractions: dayFracs };
  }, [articles, storyMap]);

  return (
    <div style={{ width: '100%' }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        role="img"
        aria-label={`Dot strip plot showing ${dots.length} articles over 7 days by source perspective`}
      >
        {/* Band divider lines */}
        {BAND_DIVIDERS.map((frac, i) => (
          <line
            key={`div-${i}`}
            x1={PAD.left}
            x2={W - PAD.right}
            y1={PAD.top + frac * PLOT_H}
            y2={PAD.top + frac * PLOT_H}
            stroke="rgba(51, 65, 85, 0.3)"
            strokeWidth={1}
          />
        ))}

        {/* Vertical day gridlines */}
        {dayFractions.map((frac, i) => (
          <line
            key={`vg-${i}`}
            x1={PAD.left + frac * PLOT_W}
            x2={PAD.left + frac * PLOT_W}
            y1={PAD.top}
            y2={PAD.top + PLOT_H}
            stroke="rgba(51, 65, 85, 0.2)"
            strokeWidth={1}
          />
        ))}

        {/* Band labels */}
        {BAND_LABELS.map((b, i) => (
          <text
            key={`bl-${i}`}
            x={PAD.left - 8}
            y={PAD.top + b.y * PLOT_H}
            textAnchor="end"
            dominantBaseline="central"
            fill="#8A857D"
            fontSize={8}
            fontFamily="'JetBrains Mono',monospace"
          >
            {b.label}
          </text>
        ))}

        {/* Date labels */}
        {dateLabels.map((d, i) => (
          <text
            key={`dl-${i}`}
            x={PAD.left + d.frac * PLOT_W}
            y={H - 6}
            textAnchor="middle"
            fill="#8A857D"
            fontSize={9}
            fontFamily="'JetBrains Mono',monospace"
          >
            {d.label}
          </text>
        ))}

        {/* Article dots */}
        {dots.map((dot, i) => (
          <circle
            key={dot.id || i}
            cx={dot.cx}
            cy={dot.cy}
            r={4}
            fill={dot.color}
            opacity={hovered === i ? 1.0 : 0.6}
            style={{
              cursor: 'pointer',
              transition: 'opacity 0.1s, r 0.1s',
              transform: hovered === i ? `scale(1.5)` : 'scale(1)',
              transformOrigin: `${dot.cx}px ${dot.cy}px`,
              animation: `dotFadeIn 0.2s ease ${i * 10}ms both`,
            }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}

        {/* Tooltip */}
        {hovered !== null && dots[hovered] && (() => {
          const d = dots[hovered];
          const tipW = 220;
          const tipH = 52;
          let tx = d.cx + 10;
          let ty = d.cy - tipH - 8;
          if (tx + tipW > W - PAD.right) tx = d.cx - tipW - 10;
          if (ty < PAD.top) ty = d.cy + 12;
          return (
            <g style={{ pointerEvents: 'none' }}>
              <rect x={tx} y={ty} width={tipW} height={tipH} rx={0} fill="#0F172A" stroke="#3D4455" strokeWidth={1} />
              <text x={tx + 10} y={ty + 16} fill="#F1F0EB" fontSize={11} fontFamily="'Source Serif 4',Georgia,serif">
                {d.storyTopic.length > 32 ? d.storyTopic.slice(0, 32) + '\u2026' : d.storyTopic}
              </text>
              <text x={tx + 10} y={ty + 30} fill="#A8A49C" fontSize={9} fontFamily="'JetBrains Mono',monospace">
                {d.source_name} &middot; {d.dateLabel}
              </text>
              <text x={tx + 10} y={ty + 43} fill={d.color} fontSize={9} fontFamily="'JetBrains Mono',monospace" fontWeight={700}>
                {d.cat}
              </text>
            </g>
          );
        })()}
      </svg>

      <style>{`
        @keyframes dotFadeIn {
          from { opacity: 0; }
          to { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}
