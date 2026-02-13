'use client';

import AnimatedCounter from './AnimatedCounter';

export default function StatsStrip({ stats }) {
  const storiesAnalyzed = stats?.analyzedCount || 0;
  const articlesCollected = stats?.articleCount || 0;

  const items = [
    { value: storiesAnalyzed, label: 'Topics Analyzed' },
    { value: articlesCollected, label: 'Articles Collected' },
    { value: '100+', label: 'Sources Monitored', isString: true },
  ];

  return (
    <section style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 56,
      padding: '32px 48px',
      borderBottom: '1px solid var(--border)',
    }}>
      {items.map((s, i) => (
        <div key={i} style={{ position: 'relative', textAlign: 'center' }}>
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
              right: -28,
              top: 4,
              height: 36,
              width: 1,
              background: 'var(--border)',
            }} />
          )}
        </div>
      ))}
    </section>
  );
}
