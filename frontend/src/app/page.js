import { getDashboardStats, getCategorySummary, getHeadlineStories } from '../lib/queries';
import Hero from '../components/Hero';
import StatsStrip from '../components/StatsStrip';
import CoverageSection from '../components/CoverageSection';
import FeaturedStories from '../components/FeaturedStories';
import MethodologyTeaser from '../components/MethodologyTeaser';

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
      <Hero />
      <StatsStrip stats={stats} />
      <CoverageSection categorySummary={categorySummary} />
      <FeaturedStories stories={headlineStories} />
      <MethodologyTeaser />
    </div>
  );
}
