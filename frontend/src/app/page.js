import { getStories, getDashboardStats, getCategorySummary, getHeadlineStories } from '../lib/queries';
import Header from '../components/Header';
import Hero from '../components/Hero';
import CoverageSection from '../components/CoverageSection';
import TopStories from '../components/TopStories';
import TopicList from '../components/TopicList';
import Footer from '../components/Footer';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const defaults = [
    [],
    { analyzedCount: 0, articleCount: 0, totalTracked: 0 },
    { categories: [] },
    [],
  ];

  const results = await Promise.allSettled([
    getStories(),
    getDashboardStats(),
    getCategorySummary(),
    getHeadlineStories(),
  ]);

  const [stories, stats, categorySummary, headlineStories] = results.map((r, i) =>
    r.status === 'fulfilled' ? r.value : defaults[i],
  );

  const excludeIds = new Set(headlineStories.map(s => s.id));

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Header stats={stats} />
      <Hero stats={stats} />
      <CoverageSection categorySummary={categorySummary} />
      <TopStories stories={headlineStories} />
      <TopicList stories={stories} excludeIds={excludeIds} />
      <Footer />
    </div>
  );
}
