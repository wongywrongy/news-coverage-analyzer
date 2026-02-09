export default function Header({ stats }) {
  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '18px 48px',
      borderBottom: '1px solid var(--border)',
      background: 'rgba(250,250,247,0.9)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div style={{
        fontFamily: "'Playfair Display', serif",
        fontWeight: 800,
        fontSize: 22,
        letterSpacing: '-0.5px',
      }}>
        <span style={{ color: '#1A1A1A' }}>Clear</span>
        <span style={{ color: 'var(--accent-gold)' }}>Signal</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          color: 'var(--ink-muted)',
          letterSpacing: '0.5px',
        }}>
          <strong style={{ color: 'var(--ink)', fontSize: 14 }}>
            {stats?.totalTracked || 0}
          </strong>{' '}
          topics tracked
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          color: 'var(--ink-muted)',
          letterSpacing: '0.5px',
        }}>
          <strong style={{ color: 'var(--ink)', fontSize: 14 }}>100+</strong>{' '}
          sources
        </span>
      </div>
    </nav>
  );
}
