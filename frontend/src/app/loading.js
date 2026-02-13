export default function Loading() {
  const shimmerBg = {
    background: 'linear-gradient(90deg, #F0EDE8 25%, #E8E5E0 50%, #F0EDE8 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s ease-in-out infinite',
    borderRadius: 6,
  };

  return (
    <div style={{ background: 'var(--bg, #FAFAF7)' }}>
      {/* Hero skeleton */}
      <section style={{ padding: '60px 48px', textAlign: 'center' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <div style={{ width: '60%', height: 56, margin: '0 auto 12px', ...shimmerBg }} />
          <div style={{ width: '40%', height: 56, margin: '0 auto 28px', ...shimmerBg }} />
          <div style={{ width: '80%', height: 16, margin: '0 auto 8px', ...shimmerBg }} />
          <div style={{ width: '70%', height: 16, margin: '0 auto 32px', ...shimmerBg }} />
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <div style={{ width: 160, height: 44, ...shimmerBg }} />
            <div style={{ width: 140, height: 44, ...shimmerBg }} />
          </div>
        </div>
      </section>

      {/* Stats skeleton */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 56, padding: '32px 48px', borderTop: '1px solid #E0DED8', borderBottom: '1px solid #E0DED8' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{ textAlign: 'center' }}>
            <div style={{ width: 48, height: 32, margin: '0 auto 4px', ...shimmerBg }} />
            <div style={{ width: 100, height: 12, margin: '0 auto', ...shimmerBg }} />
          </div>
        ))}
      </div>

      {/* Cards skeleton */}
      <div style={{ maxWidth: 1080, margin: '40px auto 0', padding: '0 48px' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            background: '#FFFFFF',
            border: '1px solid #E0DED8',
            borderRadius: 12,
            padding: '24px 28px',
            marginBottom: 12,
          }}>
            <div style={{ width: 70, height: 14, marginBottom: 12, ...shimmerBg }} />
            <div style={{ width: '75%', height: 22, marginBottom: 12, ...shimmerBg }} />
            <div style={{ width: '50%', height: 14, ...shimmerBg }} />
          </div>
        ))}
      </div>
    </div>
  );
}
