'use client';

export default function GlobalError({ error, reset }) {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#FAFAF7',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: 20,
      padding: 40,
    }}>
      <p style={{
        fontFamily: "'Playfair Display', serif",
        fontSize: 28,
        fontWeight: 700,
        color: '#1A1A1A',
      }}>
        Something went wrong
      </p>
      <p style={{
        fontFamily: "'DM Sans', sans-serif",
        fontSize: 15,
        color: '#767676',
        maxWidth: 400,
        textAlign: 'center',
        lineHeight: 1.6,
      }}>
        We couldn't load this page. This is usually temporary — try refreshing.
      </p>
      <button
        onClick={() => reset()}
        style={{
          fontFamily: "'DM Sans', sans-serif",
          fontSize: 13,
          fontWeight: 600,
          color: '#2B4C7E',
          background: 'none',
          border: '1px solid #2B4C7E',
          borderRadius: 8,
          padding: '10px 24px',
          cursor: 'pointer',
        }}
      >
        Try again
      </button>
    </div>
  );
}
