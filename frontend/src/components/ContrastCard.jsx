'use client';

export default function ContrastCard({ contrast }) {
  const framingA = contrast.framingA || '';
  const framingB = contrast.framingB || '';

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Angle / theme heading */}
      <div style={{
        fontFamily: "'Source Serif 4', Georgia, serif",
        fontSize: 17,
        fontWeight: 700,
        color: '#111827',
        marginBottom: 16,
      }}>
        {contrast.theme}
      </div>

      {/* Side-by-side cards with vs connector */}
      <div className="contrast-layout" style={{ position: 'relative', display: 'flex' }}>
        {/* Left: blue tint — Framing A */}
        <div className="contrast-a" style={{
          flex: 1,
          padding: '20px 24px',
          background: 'rgba(74,111,165,0.04)',
          borderLeft: '4px solid #4A6FA5',
          borderTop: '1px solid rgba(74,111,165,0.12)',
          borderBottom: '1px solid rgba(74,111,165,0.12)',
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: '#4A6FA5',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 10,
            fontWeight: 600,
          }}>
            Framing A
          </div>
          <p style={{
            fontFamily: "'Source Serif 4', Georgia, serif",
            fontSize: 15,
            color: '#1F2937',
            lineHeight: 1.7,
            marginBottom: 14,
          }}>
            {contrast.claimA}
          </p>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: '#4A6FA5',
            fontWeight: 500,
          }}>
            {contrast.sourceA}
            {framingA && <span style={{ color: '#9CA3AF', fontWeight: 400, marginLeft: 6 }}>({framingA})</span>}
          </div>
        </div>

        {/* Center connector — desktop */}
        <div className="contrast-connector-desktop" style={{
          width: 44,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{ color: '#4A6FA5', fontSize: 14, lineHeight: 1, marginBottom: 2 }}>&#9668;</div>
          <div style={{ width: 1, height: 24, background: '#D0D0D0' }} />
          <div style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: '#F0ECE2',
            border: '2px solid #D0D0D0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            fontWeight: 700,
            color: '#6B7280',
          }}>
            vs
          </div>
          <div style={{ width: 1, height: 24, background: '#D0D0D0' }} />
          <div style={{ color: '#C8A84E', fontSize: 14, lineHeight: 1, marginTop: 2 }}>&#9658;</div>
        </div>

        {/* Center connector — mobile (hidden by default, shown at ≤640px) */}
        <div className="contrast-connector-mobile" style={{
          display: 'none',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '8px 0',
        }}>
          <div style={{ width: 1, height: 12, background: '#D0D0D0' }} />
          <div style={{
            width: 26,
            height: 26,
            borderRadius: '50%',
            background: '#F0ECE2',
            border: '2px solid #D0D0D0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            fontWeight: 700,
            color: '#6B7280',
          }}>
            vs
          </div>
          <div style={{ width: 1, height: 12, background: '#D0D0D0' }} />
        </div>

        {/* Right: gold tint — Framing B */}
        <div className="contrast-b" style={{
          flex: 1,
          padding: '20px 24px',
          background: 'rgba(200,168,78,0.04)',
          borderRight: '4px solid #C8A84E',
          borderTop: '1px solid rgba(200,168,78,0.12)',
          borderBottom: '1px solid rgba(200,168,78,0.12)',
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: '#A08520',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginBottom: 10,
            fontWeight: 600,
          }}>
            Framing B
          </div>
          <p style={{
            fontFamily: "'Source Serif 4', Georgia, serif",
            fontSize: 15,
            color: '#1F2937',
            lineHeight: 1.7,
            marginBottom: 14,
          }}>
            {contrast.claimB}
          </p>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: '#A08520',
            fontWeight: 500,
          }}>
            {contrast.sourceB}
            {framingB && <span style={{ color: '#9CA3AF', fontWeight: 400, marginLeft: 6 }}>({framingB})</span>}
          </div>
        </div>
      </div>

    </div>
  );
}
