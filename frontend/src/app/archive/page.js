import { getArchiveStories } from '../../lib/queries';
import Archive from '../../components/Archive';

export const dynamic = 'force-dynamic';

export default async function ArchivePage() {
  let stories = [];
  try {
    stories = await getArchiveStories();
  } catch (e) {
    console.error('ArchivePage fetch error:', e);
  }
  return <Archive stories={stories} />;
}
