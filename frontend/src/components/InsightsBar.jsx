export default function InsightsBar({ insights }) {
  if (!insights || insights.length === 0) return null;

  return (
    <div style={{
      width: '100%',
      background: 'var(--bg-warm)',
      borderBottom: '1px solid var(--border)',
      padding: '10px 0',
      overflow: 'hidden',
    }}>
      <div className="insights-inner" style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '0 48px',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-lg)',
      }}>
        {insights.map((insight, i) => (
          <div key={i} style={{ display: 'contents' }}>
            {i > 0 && (
              <span className="insights-sep" style={{
                color: 'var(--border)',
                fontSize: 18,
                flexShrink: 0,
              }}>
                &middot;
              </span>
            )}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-xs)',
              flexShrink: 0,
            }}>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                flexShrink: 0,
                color: insight.type === 'undercovered' ? 'var(--accent-gold)' : 'var(--accent-blue)',
              }}>
                {insight.type === 'undercovered' ? 'Undercovered' : 'Surging'}
              </span>
              <span style={{
                fontSize: 13,
                color: 'var(--ink-secondary)',
              }}>
                {insight.text || insight.description}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
