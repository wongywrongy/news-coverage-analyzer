'use client';

import { useState } from 'react';

const SIZE = 360;
const CX = SIZE / 2;
const CY = SIZE / 2;
const MAX_R = 108;

const QUADRANTS = [
  { label: 'POLITICS & LAW', groupLabel: 'Politics & Law', color: '#C42D3A', startAngle: -90 },
  { label: 'WORLD & SECURITY', groupLabel: 'World & Security', color: '#1D5AD8', startAngle: 0 },
  { label: 'ECONOMY & BIZ', groupLabel: 'Economy & Business', color: '#8B7520', startAngle: 90 },
  { label: 'SCIENCE & HEALTH', groupLabel: 'Science & Health', color: '#046B48', startAngle: 180 },
];

function polar(angleDeg, r) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
}

function wedgePath(startAngle, endAngle, r) {
  if (r < 1) return '';
  const s = polar(startAngle, r);
  const e = polar(endAngle, r);
  const large = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${CX} ${CY} L ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y} Z`;
}

export default function RadialChart({ categoryData }) {
  const [hovered, setHovered] = useState(null);

  return (
    <div style={{ width: '100%', maxWidth: 300, margin: '0 auto' }}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}>
        {/* Guide rings */}
        {[0.33, 0.66, 1].map(f => (
          <circle
            key={f}
            cx={CX} cy={CY} r={MAX_R * f}
            fill="none" stroke="rgba(0,0,0,0.05)"
            strokeWidth={0.5} strokeDasharray="2,4"
            className="rc-grid"
          />
        ))}

        {/* Quadrant dividers */}
        {QUADRANTS.map(q => {
          const end = polar(q.startAngle, MAX_R);
          return (
            <line
              key={q.startAngle}
              x1={CX} y1={CY} x2={end.x} y2={end.y}
              stroke="rgba(0,0,0,0.06)" strokeWidth={0.5}
              className="rc-grid"
            />
          );
        })}

        {/* Quadrants */}
        {QUADRANTS.map((q, i) => {
          const data = categoryData[q.groupLabel];
          const avgImpact = data?.avgImpact || 0;
          const avgCoverage = data?.avgCoverage || 0;

          const impactR = (avgImpact / 100) * MAX_R;
          const coverageR = (avgCoverage / 100) * MAX_R;
          const startA = q.startAngle;
          const endA = startA + 90;

          const isHovered = hovered === i;

          const labelAngle = startA + 45;
          const labelPos = polar(labelAngle, MAX_R + 30);
          const anchor = Math.abs(labelPos.x - CX) < 10
            ? 'middle'
            : labelPos.x > CX ? 'start' : 'end';

          return (
            <g
              key={q.label}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: 'default' }}
              className={`rc-q rc-q-${i}`}
            >
              {/* Impact wedge — background */}
              {impactR >= 1 && (
                <path
                  d={wedgePath(startA, endA, impactR)}
                  fill={q.color}
                  fillOpacity={0.10}
                  stroke="none"
                />
              )}

              {/* Coverage wedge — foreground */}
              {coverageR >= 1 && (
                <path
                  d={wedgePath(startA, endA, coverageR)}
                  fill={q.color}
                  fillOpacity={isHovered ? 0.50 : 0.40}
                  stroke={q.color}
                  strokeOpacity={0.55}
                  strokeWidth={1.5}
                />
              )}

              {/* Invisible hover target */}
              <path
                d={wedgePath(startA, endA, MAX_R)}
                fill="transparent"
                stroke="none"
              />

              {/* Label */}
              <text
                x={labelPos.x} y={labelPos.y}
                textAnchor={anchor}
                dominantBaseline="middle"
                fill="#6B6860"
                fontSize={10}
                fontFamily="'JetBrains Mono', monospace"
                letterSpacing="0.03em"
                className="rc-label"
              >
                {q.label}
              </text>
            </g>
          );
        })}

        {/* Hover tooltip */}
        {hovered !== null && (() => {
          const q = QUADRANTS[hovered];
          const data = categoryData[q.groupLabel];
          if (!data) return null;

          const tipAngle = q.startAngle + 45;
          const tipPos = polar(tipAngle, MAX_R * 0.45);
          const tipW = 160;
          const tipH = 40;
          let tx = tipPos.x - tipW / 2;
          let ty = tipPos.y - tipH / 2;
          tx = Math.max(4, Math.min(tx, SIZE - tipW - 4));
          ty = Math.max(4, Math.min(ty, SIZE - tipH - 4));

          return (
            <g style={{ pointerEvents: 'none' }}>
              <rect x={tx} y={ty} width={tipW} height={tipH}
                rx={2}
                fill="#FFFFFF" stroke="#E5E5E5" strokeWidth={1} />
              <text x={tx + 8} y={ty + 16} fill="#111827" fontSize={10}
                fontFamily="'JetBrains Mono', monospace" fontWeight={600}>
                {q.groupLabel}
              </text>
              <text x={tx + 8} y={ty + 30} fill="#9CA3AF" fontSize={9}
                fontFamily="'JetBrains Mono', monospace">
                {data.storyCount} stories · Imp {Math.round(data.avgImpact)} · Cov {Math.round(data.avgCoverage)}
              </text>
            </g>
          );
        })()}
      </svg>

      {/* Legend */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 16, marginTop: 8,
        fontSize: 9, color: '#6B6860', fontFamily: "'JetBrains Mono', monospace",
      }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <span style={{
            display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
            background: 'rgba(74, 111, 165, 0.10)', border: '1px solid rgba(74, 111, 165, 0.3)',
          }} />
          lighter = estimated impact
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <span style={{
            display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
            background: 'rgba(74, 111, 165, 0.40)', border: '1px solid rgba(74, 111, 165, 0.55)',
          }} />
          solid = observed coverage
        </span>
      </div>

      <style>{`
        @media (prefers-reduced-motion: no-preference) {
          .rc-grid {
            opacity: 0;
            animation: rcFadeIn 300ms ease forwards;
          }
          .rc-q {
            opacity: 0;
          }
          .rc-q-0 { animation: rcFadeIn 500ms ease-out 200ms forwards; }
          .rc-q-1 { animation: rcFadeIn 500ms ease-out 350ms forwards; }
          .rc-q-2 { animation: rcFadeIn 500ms ease-out 500ms forwards; }
          .rc-q-3 { animation: rcFadeIn 500ms ease-out 650ms forwards; }
          .rc-label {
            opacity: 0;
            animation: rcFadeIn 200ms ease 800ms forwards;
          }
        }
      `}</style>
    </div>
  );
}
