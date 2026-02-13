'use client';

import Link from 'next/link';

const STAGES = [
  'Ingest', 'Embed', 'Cluster', 'Validate', 'Label', 'Select', 'Scrape', 'Score', 'Analyze',
];

export default function MethodologyTeaser() {
  return (
    <section style={{
      background: 'var(--bg-dark)',
      color: '#fff',
      padding: '80px 48px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        content: '',
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'radial-gradient(ellipse at 20% 80%, rgba(200,150,62,0.06) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(43,76,126,0.08) 0%, transparent 50%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'relative',
        maxWidth: 1080,
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1.2fr',
        gap: 56,
        alignItems: 'center',
      }}>
        {/* Left: copy */}
        <div>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            color: 'var(--accent-gold)',
            display: 'block',
            marginBottom: 'var(--space-sm)',
          }}>
            Methodology
          </span>
          <h2 style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 900,
            fontSize: 36,
            lineHeight: 1.1,
            letterSpacing: '-1px',
            marginBottom: 'var(--space-sm)',
          }}>
            From raw feeds to structured clarity
          </h2>
          <p style={{
            fontSize: 16,
            lineHeight: 1.65,
            color: 'rgba(255,255,255,0.6)',
            marginBottom: 'var(--space-lg)',
          }}>
            9 stages turn the noise of 100+ sources into a map of who is saying what
            and what is being left out. No editorializing. No spin.
          </p>
          <Link href="/methodology" style={{
            display: 'inline-block',
            padding: '12px 28px',
            border: '1.5px solid rgba(255,255,255,0.3)',
            borderRadius: 6,
            color: '#fff',
            fontSize: 14,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            transition: 'border-color 0.2s',
          }}>
            See the full pipeline
          </Link>
        </div>

        {/* Right: mini pipeline grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(9, 1fr)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 8,
          overflow: 'hidden',
        }}>
          {STAGES.map((stage, i) => {
            const isFinal = i === STAGES.length - 1;
            return (
              <div key={stage} style={{
                padding: '18px 8px 14px',
                textAlign: 'center',
                borderRight: i < STAGES.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                background: isFinal ? 'rgba(200,150,62,0.12)' : 'transparent',
                transition: 'background 0.2s',
              }}>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  color: 'rgba(255,255,255,0.3)',
                  marginBottom: 6,
                }}>
                  {String(i + 1).padStart(2, '0')}
                </div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  fontWeight: 500,
                  color: isFinal ? 'var(--accent-gold)' : 'rgba(255,255,255,0.7)',
                }}>
                  {stage}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
