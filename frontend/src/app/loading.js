export default function Loading() {
  const shimmerBg = {
    background: 'linear-gradient(90deg, #F0EDE8 25%, #E8E5E0 50%, #F0EDE8 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s ease-in-out infinite',
    borderRadius: 6,
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg, #FAFAF7)' }}>
      {/* Nav skeleton */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '18px 48px',
        borderBottom: '1px solid #E8E6E1',
        background: 'rgba(250,250,247,0.9)',
      }}>
        <div style={{ width: 140, height: 24, ...shimmerBg }} />
        <div style={{ display: 'flex', gap: 24 }}>
          <div style={{ width: 120, height: 16, ...shimmerBg }} />
          <div style={{ width: 90, height: 16, ...shimmerBg }} />
        </div>
      </nav>

      {/* Hero skeleton */}
      <section style={{ padding: '80px 48px 60px' }}>
        <div style={{
          maxWidth: 1280,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: '1fr 1.1fr',
          gap: 60,
          alignItems: 'center',
        }}>
          <div>
            <div style={{ width: '80%', height: 56, marginBottom: 12, ...shimmerBg }} />
            <div style={{ width: '60%', height: 56, marginBottom: 28, ...shimmerBg }} />
            <div style={{ width: '90%', height: 16, marginBottom: 8, ...shimmerBg }} />
            <div style={{ width: '85%', height: 16, marginBottom: 8, ...shimmerBg }} />
            <div style={{ width: '70%', height: 16, marginBottom: 48, ...shimmerBg }} />
            <div style={{ display: 'flex', gap: 40 }}>
              {[0, 1, 2].map(i => (
                <div key={i}>
                  <div style={{ width: 48, height: 32, marginBottom: 4, ...shimmerBg }} />
                  <div style={{ width: 80, height: 12, ...shimmerBg }} />
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ width: '100%', height: 240, ...shimmerBg, borderRadius: 12 }} />
          </div>
        </div>
      </section>

      {/* Tabs skeleton */}
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 48px' }}>
        <div style={{
          display: 'flex',
          gap: 4,
          borderBottom: '2px solid #E8E6E1',
          paddingBottom: 14,
        }}>
          {[60, 100, 110, 120, 100].map((w, i) => (
            <div key={i} style={{ width: w, height: 16, ...shimmerBg }} />
          ))}
        </div>
      </div>

      {/* Cards skeleton */}
      <div style={{ maxWidth: 1280, margin: '40px auto 0', padding: '0 48px' }}>
        {[0, 1, 2, 3].map(i => (
          <div key={i} style={{
            background: '#FFFFFF',
            border: '1px solid #E8E6E1',
            borderRadius: 12,
            padding: '24px 28px',
            marginBottom: 12,
            display: 'grid',
            gridTemplateColumns: '1fr auto',
            gap: 24,
            alignItems: 'center',
          }}>
            <div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                <div style={{ width: 70, height: 20, ...shimmerBg }} />
                <div style={{ width: 80, height: 16, ...shimmerBg }} />
              </div>
              <div style={{ width: '75%', height: 22, marginBottom: 12, ...shimmerBg }} />
              <div style={{ width: '50%', height: 10, ...shimmerBg }} />
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              <div style={{ width: 56, height: 48, ...shimmerBg }} />
              <div style={{ width: 56, height: 48, ...shimmerBg }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
