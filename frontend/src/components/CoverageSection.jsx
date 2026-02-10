'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import BarChart from './BarChart';

export default function CoverageSection({ categorySummary }) {
  const categoryData = useMemo(() => {
    const result = {};
    const cats = categorySummary?.categories || [];
    for (const cat of cats) {
      result[cat.name] = {
        avgImpact: cat.avg_impact || 0,
        avgCoverage: cat.avg_coverage || 0,
        storyCount: cat.topic_count || 0,
      };
    }
    return result;
  }, [categorySummary]);

  return (
    <section className="coverage-section" style={{
      padding: 'var(--space-xl) 48px',
      background: 'var(--bg-warm)',
      borderTop: '1px solid var(--border)',
      borderBottom: '1px solid var(--border)',
    }}>
      <div className="coverage-grid" style={{
        maxWidth: 1280,
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1.4fr',
        gap: 'var(--space-xl)',
        alignItems: 'start',
      }}>
        {/* Left — narrative */}
        <div style={{ paddingTop: 'var(--space-xs)' }}>
          <span style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.2px',
            color: 'var(--accent-gold)',
            display: 'block',
            marginBottom: 'var(--space-xs)',
          }}>
            The Coverage Gap
          </span>

          <h2 style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 800,
            fontSize: 28,
            lineHeight: 1.2,
            letterSpacing: '-0.5px',
            color: 'var(--ink)',
            marginBottom: 'var(--space-sm)',
          }}>
            What&rsquo;s important vs.<br />what gets covered
          </h2>

          <p style={{
            fontSize: 15,
            lineHeight: 1.6,
            color: 'var(--ink-secondary)',
            marginBottom: 'var(--space-lg)',
          }}>
            Every topic is scored for real-world impact and measured against actual
            media coverage. The gap between the two reveals what&rsquo;s being overlooked.
          </p>

          <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
            <Link href="/methodology" style={{
              padding: '14px 24px',
              fontFamily: "'DM Sans', sans-serif",
              textDecoration: 'none',
              borderRadius: 6,
              transition: 'all 0.2s',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              background: 'var(--accent-blue-deep)',
              color: '#fff',
            }}>
              <strong style={{ fontSize: 14, fontWeight: 700 }}>How It Works</strong>
              <span style={{ fontSize: 12, opacity: 0.7 }}>Our 9-stage AI pipeline, explained</span>
            </Link>
            <Link href="/archive" style={{
              padding: '14px 24px',
              fontFamily: "'DM Sans', sans-serif",
              textDecoration: 'none',
              borderRadius: 6,
              transition: 'all 0.2s',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              background: 'transparent',
              color: 'var(--accent-blue-deep)',
              border: '1.5px solid var(--accent-blue-deep)',
            }}>
              <strong style={{ fontSize: 14, fontWeight: 700 }}>Archive</strong>
              <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>Browse every topic we&rsquo;ve analyzed</span>
            </Link>
          </div>
        </div>

        {/* Right — bar chart */}
        <div>
          <BarChart categoryData={categoryData} />
        </div>
      </div>
    </section>
  );
}
