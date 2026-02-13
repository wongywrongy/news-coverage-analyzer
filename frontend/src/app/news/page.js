import { getStories, getHeadlineStories, getDashboardStats } from '../../lib/queries';
import TopStories from '../../components/TopStories';
import TopicList from '../../components/TopicList';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function NewsPage() {
  const defaults = [[], [], { analyzedCount: 0, articleCount: 0, totalTracked: 0 }];

  const results = await Promise.allSettled([
    getStories(),
    getHeadlineStories(),
    getDashboardStats(),
  ]);

  const [stories, headlineStories, stats] = results.map((r, i) =>
    r.status === 'fulfilled' ? r.value : defaults[i],
  );

  const excludeIds = new Set(headlineStories.map(s => s.id));

  return (
    <div style={{ background: 'var(--bg)' }}>
      <TopStories stories={headlineStories} stats={stats} storyCount={stories.length} />
      <TopicList stories={stories} excludeIds={excludeIds} />
      <div style={{
        maxWidth: 1080,
        margin: '0 auto',
        padding: '0 48px 60px',
        textAlign: 'center',
      }}>
        <Link href="/archive" style={{
          display: 'inline-block',
          padding: '12px 28px',
          border: '1px solid var(--border)',
          borderRadius: 6,
          fontSize: 13,
          fontWeight: 500,
          fontFamily: "'DM Sans', sans-serif",
          color: 'var(--accent-blue)',
          textDecoration: 'none',
          transition: 'all 0.2s',
        }}>
          View all in archive
        </Link>
      </div>
    </div>
  );
}
