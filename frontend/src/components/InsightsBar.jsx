export default function InsightsBar({ insights }) {
  if (!insights || insights.length === 0) return null;

  return (
    <div style={{
      width: '100%',
      background: '#F4F1EB',
      borderBottom: '1px solid var(--border)',
      padding: '20px 0',
      marginBottom: 40,
    }}>
      <div className="insights-inner" style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '0 48px',
        display: 'flex',
        alignItems: 'stretch',
      }}>
        {insights.map((insight, i) => (
          <div key={i} style={{ display: 'contents' }}>
            {i > 0 && (
              <div className="insights-divider" style={{
                width: 1,
                background: 'var(--border)',
                margin: '0 32px',
                flexShrink: 0,
              }} />
            )}
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
            }}>
              <p style={{
                fontSize: 13,
                color: 'var(--ink-secondary)',
                lineHeight: 1.4,
                display: 'flex',
                alignItems: 'center',
              }}>
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  padding: '3px 8px',
                  borderRadius: 3,
                  flexShrink: 0,
                  marginRight: 10,
                  ...(insight.type === 'undercovered'
                    ? { color: 'var(--accent-gold)', background: 'rgba(200,150,62,0.12)' }
                    : { color: 'var(--accent-blue)', background: 'rgba(43,76,126,0.1)' }
                  ),
                }}>
                  {insight.type === 'undercovered' ? 'Undercovered' : 'Surging'}
                </span>
                {insight.text || insight.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
