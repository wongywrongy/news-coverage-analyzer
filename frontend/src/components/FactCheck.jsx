import { VERDICT_STYLES } from '../lib/constants';

export default function FactCheck({ fact }) {
  const v = VERDICT_STYLES[fact.verdict] || VERDICT_STYLES.unverified;

  return (
    <div style={{ marginBottom: 16, border: `1px solid ${v.border}`, overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 12,
        padding: '18px 24px', background: v.bg,
      }}>
        <span style={{
          fontSize: 10, fontWeight: 700, color: v.color,
          background: 'rgba(0,0,0,0.04)', padding: '4px 12px',
          fontFamily: "'JetBrains Mono', monospace", flexShrink: 0,
        }}>
          {fact.verdict.toUpperCase()}
        </span>
        <p style={{
          fontSize: 16, fontWeight: 500, color: '#111827',
          fontFamily: "'Source Serif 4', Georgia, serif", lineHeight: 1.45,
        }}>
          {fact.claim}
        </p>
      </div>
      <div style={{ padding: '16px 24px', background: '#FFFFFF' }}>
        <p style={{
          fontSize: 15, color: '#374151',
          fontFamily: "'Source Serif 4', Georgia, serif", lineHeight: 1.7,
        }}>
          {fact.reality}
        </p>
      </div>
    </div>
  );
}
