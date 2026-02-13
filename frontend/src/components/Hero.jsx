'use client';

import Link from 'next/link';
import AnimatedCounter from './AnimatedCounter';

export default function Hero({ stats }) {
  const storiesAnalyzed = stats?.analyzedCount || 0;
  const articlesCollected = stats?.articleCount || 0;

  const statItems = [
    { value: storiesAnalyzed, label: 'Topics Analyzed' },
    { value: articlesCollected, label: 'Articles Collected' },
    { value: '100+', label: 'Sources Monitored', isString: true },
  ];

  return (
    <section className="hero-section" style={{
      background: 'linear-gradient(170deg, #1B3155 0%, #11213A 65%, #0D1825 100%)',
      padding: '96px 48px 72px',
      textAlign: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle radial glow */}
      <div style={{
        position: 'absolute',
        top: '-30%',
        right: '-10%',
        width: 600,
        height: 600,
        background: 'radial-gradient(circle, rgba(200,150,62,0.04) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      <div style={{ maxWidth: 680, margin: '0 auto', position: 'relative' }}>
        <h1 className="hero-title" style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontWeight: 900,
          fontSize: 52,
          lineHeight: 1.1,
          letterSpacing: '-1.5px',
          color: '#fff',
          marginBottom: 20,
          animation: 'fadeUp 0.6s ease both',
        }}>
          Same event.<br />
          <em style={{
            fontStyle: 'normal',
            background: 'linear-gradient(135deg, #C8963E, #D4A853)',
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
          color: 'rgba(255,255,255,0.6)',
          marginBottom: 32,
          animation: 'fadeUp 0.6s ease 0.08s both',
        }}>
          We track how outlets across the political spectrum frame the same stories,
          score what matters, and surface what&rsquo;s being overlooked.
        </p>

        {/* CTA buttons */}
        <div className="hero-ctas" style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 12,
          marginBottom: 48,
          animation: 'fadeUp 0.6s ease 0.14s both',
        }}>
          <Link href="/news" style={{
            padding: '12px 28px',
            background: '#C8963E',
            color: '#fff',
            borderRadius: 5,
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}>
            See Today&rsquo;s Analysis
          </Link>
          <Link href="/methodology" style={{
            padding: '12px 28px',
            background: 'transparent',
            color: 'rgba(255,255,255,0.6)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 5,
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}>
            How It Works
          </Link>
        </div>

        {/* Stats row */}
        <div className="hero-stats" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 48,
          animation: 'fadeUp 0.6s ease 0.2s both',
        }}>
          {statItems.map((s, i) => (
            <div key={i} style={{ position: 'relative', textAlign: 'center' }}>
              <div style={{
                fontFamily: "'Playfair Display', serif",
                fontWeight: 800,
                fontSize: 28,
                color: '#fff',
              }}>
                {s.isString ? s.value : (
                  <AnimatedCounter target={s.value} duration={1800} delay={400} />
                )}
              </div>
              <div style={{
                fontSize: 11,
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: 'rgba(255,255,255,0.4)',
                marginTop: 2,
              }}>
                {s.label}
              </div>
              {/* Vertical divider */}
              {i < 2 && (
                <div style={{
                  position: 'absolute',
                  right: -24,
                  top: 4,
                  height: 36,
                  width: 1,
                  background: 'rgba(255,255,255,0.12)',
                }} />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
