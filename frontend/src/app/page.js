import { getDashboardStats, getCategorySummary, getHeadlineStories } from '../lib/queries';
import Hero from '../components/Hero';
import CoverageSection from '../components/CoverageSection';
import MethodologyTeaser from '../components/MethodologyTeaser';
import FeaturedStories from '../components/FeaturedStories';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const defaults = [
    { analyzedCount: 0, articleCount: 0, totalTracked: 0 },
    { categories: [] },
    [],
  ];

  const results = await Promise.allSettled([
    getDashboardStats(),
    getCategorySummary(),
    getHeadlineStories(),
  ]);

  const [stats, categorySummary, headlineStories] = results.map((r, i) =>
    r.status === 'fulfilled' ? r.value : defaults[i],
  );

  return (
    <div style={{ background: 'var(--bg)' }}>
      <Hero stats={stats} />
      <CoverageSection categorySummary={categorySummary} />
      <MethodologyTeaser />
      <FeaturedStories stories={headlineStories} />
    </div>
  );
}
