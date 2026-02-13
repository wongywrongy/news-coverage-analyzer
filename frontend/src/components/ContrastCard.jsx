'use client';

export default function ContrastCard({ contrast }) {
  return (
    <div style={{ marginBottom: 'var(--space-lg)' }}>
      {/* Theme heading */}
      <div style={{
        fontFamily: "'DM Sans', sans-serif",
        fontSize: 16,
        fontWeight: 700,
        color: 'var(--ink)',
        marginBottom: 'var(--space-sm)',
      }}>
        {contrast.theme}
      </div>

      {/* Two cards side by side */}
      <div className="contrast-layout" style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'var(--space-sm)',
      }}>
        {/* Framing A — blue left border */}
        <div className="contrast-a" style={{
          padding: 'var(--space-md)',
          background: '#FFFFFF',
          border: '1px solid var(--border)',
          borderLeft: '3px solid var(--accent-blue)',
          borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: 'var(--accent-blue)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 10,
            fontWeight: 600,
          }}>
            Framing A
          </div>
          <p style={{
            fontFamily: "'DM Sans', sans-serif",
            fontSize: 15,
            color: 'var(--ink)',
            lineHeight: 1.6,
            marginBottom: 14,
          }}>
            {contrast.claimA}
          </p>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            {contrast.sourceA}
            {contrast.framingA && (
              <span> &middot; {contrast.framingA}</span>
            )}
          </div>
        </div>

        {/* Framing B — gold left border */}
        <div className="contrast-b" style={{
          padding: 'var(--space-md)',
          background: '#FFFFFF',
          border: '1px solid var(--border)',
          borderLeft: '3px solid var(--accent-gold)',
          borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: 'var(--accent-gold)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 10,
            fontWeight: 600,
          }}>
            Framing B
          </div>
          <p style={{
            fontFamily: "'DM Sans', sans-serif",
            fontSize: 15,
            color: 'var(--ink)',
            lineHeight: 1.6,
            marginBottom: 14,
          }}>
            {contrast.claimB}
          </p>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: 'var(--ink-muted)',
          }}>
            {contrast.sourceB}
            {contrast.framingB && (
              <span> &middot; {contrast.framingB}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
