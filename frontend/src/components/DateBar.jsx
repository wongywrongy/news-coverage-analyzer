'use client';

export default function DateBar({ stats, storyCount }) {
  const now = new Date();
  const formatted = now.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const topicCount = storyCount || 0;
  const articleCount = stats?.articleCount || 0;

  return (
    <div style={{
      padding: '20px 48px 12px',
    }}>
    <div style={{
      maxWidth: 1080,
      margin: '0 auto',
    }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        color: 'var(--ink-muted)',
        letterSpacing: '0.3px',
      }}>
        {formatted} &middot; {topicCount} topics &middot; {articleCount.toLocaleString()} articles
      </span>
    </div>
    </div>
  );
}
