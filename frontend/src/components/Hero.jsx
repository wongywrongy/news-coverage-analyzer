'use client';

import Link from 'next/link';

export default function Hero() {
  return (
    <section className="hero-section" style={{
      padding: 'var(--space-xl) 48px var(--space-lg)',
      textAlign: 'center',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        maxWidth: 720,
        margin: '0 auto',
      }}>
        <h1 className="hero-title" style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 900,
          fontSize: 52,
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
          We track how outlets across the political spectrum frame the same stories,
          score what matters, and surface what's being overlooked.
        </p>

        {/* CTA buttons */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 12,
          animation: 'fadeUp 0.6s ease 0.2s both',
        }}>
          <Link href="/news" style={{
            padding: '12px 28px',
            background: 'var(--accent-blue-deep)',
            color: '#fff',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}>
            See Today's Analysis
          </Link>
          <Link href="/methodology" style={{
            padding: '12px 28px',
            background: 'transparent',
            color: 'var(--accent-blue-deep)',
            border: '1.5px solid var(--accent-blue-deep)',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}>
            How It Works
          </Link>
        </div>
      </div>
    </section>
  );
}
