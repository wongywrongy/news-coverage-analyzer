'use client';

import { useMemo, useEffect, useRef, useState } from 'react';
import Link from 'next/link';

const CATEGORIES = [
  { label: 'Politics & Law', color: '#C0392B' },
  { label: 'World & Security', color: '#2B4C7E' },
  { label: 'Economy & Business', color: '#C8963E' },
  { label: 'Science & Health', color: '#27AE60' },
];

export default function CoverageSection({ categorySummary }) {
  const [visible, setVisible] = useState(false);
  const chartRef = useRef(null);

  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const categoryData = useMemo(() => {
    const result = {};
    const cats = categorySummary?.categories || [];
    for (const cat of cats) {
      result[cat.name] = {
        avgImpact: cat.avg_impact || 0,
        avgCoverage: cat.avg_coverage || 0,
      };
    }
    return result;
  }, [categorySummary]);

  return (
    <section className="hp-coverage" style={{
      padding: '72px 48px',
      background: '#F4F1EB',
      borderBottom: '1px solid #E8E6E1',
    }}>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {/* Top row: narrative + legend */}
        <div className="coverage-top" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 48,
          gap: 48,
        }}>
          <div style={{ maxWidth: 560 }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '2px',
              color: '#C8963E',
              display: 'block',
              marginBottom: 8,
            }}>
              THE COVERAGE GAP
            </span>
            <h2 style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 32,
              lineHeight: 1.2,
              color: '#1A1A1A',
              marginBottom: 12,
            }}>
              What&rsquo;s important vs. what gets covered
            </h2>
            <p style={{
              fontSize: 15,
              lineHeight: 1.6,
              color: '#5A5A5A',
            }}>
              Every topic is scored for real-world impact and measured against actual
              media coverage. The gap between the two reveals what&rsquo;s being overlooked.
            </p>
          </div>

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            flexShrink: 0,
            paddingTop: 36,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 12, height: 12, borderRadius: 2,
                background: '#D1D5DB', display: 'inline-block',
              }} />
              <span style={{ fontSize: 12, color: '#5A5A5A' }}>Estimated Impact</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 12, height: 12, borderRadius: 2,
                background: '#1B3155', display: 'inline-block',
              }} />
              <span style={{ fontSize: 12, color: '#5A5A5A' }}>Observed Coverage</span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div ref={chartRef} style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
          marginBottom: 48,
        }}>
          {CATEGORIES.map((cat, i) => {
            const data = categoryData[cat.label] || { avgImpact: 0, avgCoverage: 0 };
            const gap = data.avgImpact - data.avgCoverage;
            return (
              <div key={cat.label} className="coverage-row" style={{
                display: 'grid',
                gridTemplateColumns: '180px 1fr 60px',
                alignItems: 'center',
                gap: 20,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: cat.color, flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: 13, fontWeight: 600, color: '#1A1A1A',
                    whiteSpace: 'nowrap',
                  }}>
                    {cat.label}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ height: 20, borderRadius: 3 }}>
                    <div style={{
                      height: '100%',
                      width: visible ? `${data.avgImpact}%` : '0%',
                      background: '#D1D5DB',
                      borderRadius: 3,
                      transition: `width 0.8s cubic-bezier(0.22, 1, 0.36, 1) ${0.1 + i * 0.1}s`,
                    }} />
                  </div>
                  <div style={{ height: 20, borderRadius: 3 }}>
                    <div style={{
                      height: '100%',
                      width: visible ? `${data.avgCoverage}%` : '0%',
                      background: '#1B3155',
                      borderRadius: 3,
                      transition: `width 0.8s cubic-bezier(0.22, 1, 0.36, 1) ${0.15 + i * 0.1}s`,
                    }} />
                  </div>
                </div>

                <div style={{
                  textAlign: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13,
                  fontWeight: 600,
                  color: gap > 0 ? '#C8963E' : '#767676',
                }}>
                  {gap > 0 ? `+${gap}` : String(gap)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom CTAs */}
        <div className="coverage-ctas" style={{ display: 'flex', gap: 16 }}>
          <Link href="/methodology" style={{
            padding: '14px 24px',
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            borderRadius: 6,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            background: '#1B3155',
            color: '#fff',
          }}>
            <strong style={{ fontSize: 14, fontWeight: 700 }}>Methodology</strong>
            <span style={{ fontSize: 12, opacity: 0.7 }}>Our 9-stage AI pipeline, explained</span>
          </Link>
          <Link href="/archive" style={{
            padding: '14px 24px',
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            borderRadius: 6,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            background: 'transparent',
            color: '#1B3155',
            border: '1.5px solid #1B3155',
          }}>
            <strong style={{ fontSize: 14, fontWeight: 700 }}>Archive</strong>
            <span style={{ fontSize: 12, color: '#767676' }}>Browse every topic we&rsquo;ve analyzed</span>
          </Link>
        </div>
      </div>
    </section>
  );
}
