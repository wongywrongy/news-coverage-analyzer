'use client';

import AnimatedCounter from './AnimatedCounter';

export default function Hero({ stats }) {
  const storiesAnalyzed = stats?.analyzedCount || 0;
  const articlesCollected = stats?.articleCount || 0;

  return (
    <section className="hero-section" style={{
      padding: 'var(--space-xl) 48px var(--space-lg)',
      textAlign: 'center',
      borderBottom: 'none',
    }}>
      <div style={{
        maxWidth: 680,
        margin: '0 auto',
      }}>
        <h1 className="hero-title" style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 900,
          fontSize: 48,
          lineHeight: 1.1,
          letterSpacing: '-1.5px',
          marginBottom: 'var(--space-sm)',
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
          fontSize: 16,
          lineHeight: 1.65,
          color: 'var(--ink-secondary)',
          marginBottom: 'var(--space-lg)',
          animation: 'fadeUp 0.6s ease 0.1s both',
        }}>
          We track how outlets across the political spectrum frame the same subjects,
          score what matters, and surface what&rsquo;s being overlooked.
        </p>

        {/* Stats row */}
        <div className="hero-stats" style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 48,
          animation: 'fadeUp 0.6s ease 0.2s both',
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
                fontSize: 28,
                color: 'var(--accent-blue-deep)',
              }}>
                {s.isString ? s.value : (
                  <AnimatedCounter target={s.value} duration={1800} delay={400} />
                )}
              </div>
              <div style={{
                fontSize: 11,
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
                  right: -24,
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
    </section>
  );
}
