export default function Footer() {
  return (
    <footer style={{
      maxWidth: 1280,
      margin: '40px auto 0',
      padding: '32px 48px',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
        &copy; 2025 ClearSignal &mdash; Tracking media coverage across the political spectrum.
      </p>
      <p style={{ fontSize: 13 }}>
        <a href="/methodology" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>Methodology</a>
        {' \u00B7 '}
        <a href="#about" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>About</a>
        {' \u00B7 '}
        <a href="#api" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>API</a>
      </p>
    </footer>
  );
}
