import { getStory } from '../../../lib/queries';
import StoryDetail from '../../../components/StoryDetail';

export const dynamic = 'force-dynamic';

export default async function TopicDetailPage({ params }) {
  const { id } = params;
  let story = null, analysis = null, sourceList = [], biasCounts = {};
  try {
    ({ story, analysis, sourceList, biasCounts } = await getStory(id));
  } catch (e) {
    console.error('TopicDetailPage fetch error:', e);
  }

  if (!story) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ fontSize: 14, color: 'var(--ink-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Topic not found.</p>
      </div>
    );
  }

  return <StoryDetail story={story} analysis={analysis} sourceList={sourceList} biasCounts={biasCounts} />;
}
