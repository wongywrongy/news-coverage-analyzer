import { getStories, getDashboardStats, getInsights, getCategorySummary } from '../lib/queries';
import Header from '../components/Header';
import Hero from '../components/Hero';
import CoverageMonitor from '../components/CoverageMonitor';
import Footer from '../components/Footer';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const [stories, stats, insights, categorySummary] = await Promise.all([
    getStories(),
    getDashboardStats(),
    getInsights(),
    getCategorySummary(),
  ]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Header stats={stats} />
      <Hero stats={stats} categorySummary={categorySummary} />
      <CoverageMonitor stories={stories} insights={insights} />
      <Footer />
    </div>
  );
}
