'use client';

import { useMemo } from 'react';
import AnimatedCounter from './AnimatedCounter';
import BarChart from './BarChart';

export default function Hero({ stats, categorySummary }) {
  // Transform getCategorySummary() output into BarChart format
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

  const storiesAnalyzed = stats?.analyzedCount || 0;
  const articlesCollected = stats?.articleCount || 0;

  return (
    <section style={{
      position: 'relative',
      padding: '80px 48px 60px',
      overflow: 'hidden',
    }}>
      {/* Decorative radial gradients */}
      <div style={{
        position: 'absolute',
        top: -100,
        right: -200,
        width: 800,
        height: 800,
        background: 'radial-gradient(ellipse, rgba(43,76,126,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        bottom: -100,
        left: -100,
        width: 600,
        height: 600,
        background: 'radial-gradient(ellipse, rgba(200,150,62,0.05) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div className="hero-inner" style={{
        maxWidth: 1280,
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1.1fr',
        gap: 60,
        alignItems: 'center',
        position: 'relative',
      }}>
        {/* Left column */}
        <div>
          <h1 style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 900,
            fontSize: 58,
            lineHeight: 1.1,
            letterSpacing: '-1.5px',
            marginBottom: 20,
            animation: 'fadeUp 0.6s ease both',
          }}>
            Same event.<br />
            <em style={{
              fontStyle: 'normal',
              background: 'linear-gradient(135deg, var(--accent-gold), #D4A853)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              Different realities.
            </em>
          </h1>

          <p style={{
            fontSize: 17,
            lineHeight: 1.65,
            color: 'var(--ink-secondary)',
            maxWidth: 480,
            marginBottom: 32,
            animation: 'fadeUp 0.6s ease 0.1s both',
          }}>
            The same topic can look completely different depending on who covers it.
            We track how outlets across the political spectrum frame the same subjects,
            score what matters, and surface what&rsquo;s being overlooked.
          </p>

          {/* Text links */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 48,
            animation: 'fadeUp 0.6s ease 0.2s both',
          }}>
            <a href="#methodology" style={{
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--accent-blue-deep)',
              textDecoration: 'none',
            }}>
              How It Works
            </a>
            <span style={{ width: 1, height: 16, background: 'var(--border)' }} />
            <a href="#archive" style={{
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--accent-blue-deep)',
              textDecoration: 'none',
            }}>
              Archive
            </a>
          </div>

          {/* Stats row */}
          <div className="hero-stats" style={{
            display: 'flex',
            gap: 40,
            animation: 'fadeUp 0.6s ease 0.3s both',
          }}>
            {[
              { value: storiesAnalyzed, label: 'Topics Analyzed' },
              { value: articlesCollected, label: 'Articles Collected' },
              { value: '100+', label: 'Sources Monitored', isString: true },
            ].map((s, i) => (
              <div key={i} className="hero-stat" style={{ position: 'relative' }}>
                <div style={{
                  fontFamily: "'Playfair Display', serif",
                  fontWeight: 800,
                  fontSize: 32,
                  color: 'var(--accent-blue-deep)',
                }}>
                  {s.isString ? s.value : (
                    <AnimatedCounter target={s.value} duration={1800} delay={400} />
                  )}
                </div>
                <div style={{
                  fontSize: 12,
                  color: 'var(--ink-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  marginTop: 2,
                }}>
                  {s.label}
                </div>
                {/* Vertical divider after first two stats */}
                {i < 2 && (
                  <div style={{
                    position: 'absolute',
                    right: -20,
                    top: 4,
                    height: 36,
                    width: 1,
                    background: 'var(--border)',
                  }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right column — Bar Chart */}
        <div className="hero-chart-area" style={{
          animation: 'fadeUp 0.6s ease 0.4s both',
        }}>
          <BarChart categoryData={categoryData} />
        </div>
      </div>
    </section>
  );
}
