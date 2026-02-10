'use client';

import { CATEGORY_GROUPS } from '../lib/constants';

export default function BarChart({ categoryData }) {
  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        marginBottom: 'var(--space-md)',
        paddingBottom: 14,
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{
          fontSize: 13,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: 'var(--ink-muted)',
        }}>
          Coverage Breakdown
        </span>
        <div style={{ display: 'flex', gap: 16 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--ink-muted)', fontWeight: 500 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: '#D1D5DB', display: 'inline-block' }} />
            Estimated Impact
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--ink-muted)', fontWeight: 500 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--accent-blue-deep)', display: 'inline-block' }} />
            Observed Coverage
          </span>
        </div>
      </div>

      {/* Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        {CATEGORY_GROUPS.map((group, i) => {
          const data = categoryData[group.label] || { avgImpact: 0, avgCoverage: 0 };
          return (
            <div key={group.key} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
              {/* Label */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 160, flexShrink: 0 }}>
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: group.color,
                  flexShrink: 0,
                }} />
                <span style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--ink)',
                  whiteSpace: 'nowrap',
                }}>
                  {group.label}
                </span>
              </div>

              {/* Bar pair */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
                {/* Impact bar */}
                <div style={{
                  width: '100%',
                  height: 20,
                  background: 'transparent',
                  borderRadius: 3,
                  position: 'relative',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${data.avgImpact}%`,
                    background: '#D1D5DB',
                    borderRadius: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: 8,
                    transition: 'width 0.8s cubic-bezier(0.22, 1, 0.36, 1)',
                    animation: `barGrow 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${0.1 + i * 0.1}s both`,
                  }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      fontWeight: 500,
                      color: 'var(--ink-secondary)',
                    }}>
                      {data.avgImpact}
                    </span>
                  </div>
                </div>

                {/* Coverage bar */}
                <div style={{
                  width: '100%',
                  height: 20,
                  background: 'transparent',
                  borderRadius: 3,
                  position: 'relative',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${data.avgCoverage}%`,
                    background: 'var(--accent-blue-deep)',
                    borderRadius: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: 8,
                    transition: 'width 0.8s cubic-bezier(0.22, 1, 0.36, 1)',
                    animation: `barGrow 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${0.15 + i * 0.1}s both`,
                  }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      fontWeight: 500,
                      color: '#fff',
                    }}>
                      {data.avgCoverage}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
