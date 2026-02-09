import { getStory } from '../../../lib/queries';
import StoryDetail from '../../../components/StoryDetail';

export const dynamic = 'force-dynamic';

export default async function StoryDetailPage({ params }) {
  const { id } = params;
  const { story, analysis, sourceList } = await getStory(id);

  if (!story) {
    return (
      <div style={{ minHeight: '100vh', background: '#F0ECE2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ fontSize: 14, color: '#9CA3AF', fontFamily: "'JetBrains Mono', monospace" }}>Story not found.</p>
      </div>
    );
  }

  return <StoryDetail story={story} analysis={analysis} sourceList={sourceList} />;
}
