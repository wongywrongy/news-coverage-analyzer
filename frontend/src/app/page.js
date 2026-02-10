import { getStories, getDashboardStats, getInsights, getCategorySummary, getHeadlineStories } from '../lib/queries';
import Header from '../components/Header';
import Headlines from '../components/Headlines';
import Hero from '../components/Hero';
import CoverageSection from '../components/CoverageSection';
import CoverageMonitor from '../components/CoverageMonitor';
import Footer from '../components/Footer';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const defaults = [
    [],
    { analyzedCount: 0, articleCount: 0, totalTracked: 0 },
    [],
    { categories: [] },
    [],
  ];

  const results = await Promise.allSettled([
    getStories(),
    getDashboardStats(),
    getInsights(),
    getCategorySummary(),
    getHeadlineStories(),
  ]);

  const [stories, stats, insights, categorySummary, headlineStories] = results.map((r, i) =>
    r.status === 'fulfilled' ? r.value : defaults[i],
  );

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Header stats={stats} />
      <Headlines stories={headlineStories} />
      <Hero stats={stats} />
      <CoverageSection categorySummary={categorySummary} />
      <CoverageMonitor stories={stories} insights={insights} />
      <Footer />
    </div>
  );
}
