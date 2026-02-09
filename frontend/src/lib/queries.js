import { supabase } from './supabase';

// Select all columns — the app handles missing fields gracefully via defaults.
const STORY_COLUMNS = '*';

/** Return story_ids that have a completed analysis (non-null headline). */
async function getAnalyzedIds() {
  const { data: rows, error } = await supabase
    .from('analyses')
    .select('story_id, headline')
    .not('headline', 'is', null);

  if (error) throw error;
  if (!rows || rows.length === 0) return [];

  return [...new Set(rows.map(r => r.story_id))];
}

export async function getStories() {
  const analyzedIds = await getAnalyzedIds();
  if (analyzedIds.length === 0) return [];

  const { data, error } = await supabase
    .from('stories')
    .select(STORY_COLUMNS)
    .in('id', analyzedIds)
    .eq('active', true);

  if (error) throw error;
  if (!data) return [];

  // 30-day rolling window
  const since = new Date();
  since.setDate(since.getDate() - 30);
  const sinceMs = since.getTime();

  const recent = data.filter(s => {
    const ts = s.first_seen || s.created_at;
    return ts && new Date(ts).getTime() >= sinceMs;
  });

  // Sort by rank_score (from backend ranking), fallback to weighted formula
  recent.sort((a, b) => {
    const rankA = a.rank_score || 0;
    const rankB = b.rank_score || 0;
    if (rankA !== rankB) return rankB - rankA;
    // Fallback: 60% impact + 40% coverage
    const covA = a.coverage_score || a.attention_score || 0;
    const covB = b.coverage_score || b.attention_score || 0;
    const scoreA = (a.impact_score || 0) * 0.6 + covA * 0.4;
    const scoreB = (b.impact_score || 0) * 0.6 + covB * 0.4;
    return scoreB - scoreA;
  });

  // Cap at 50
  return recent.slice(0, 50);
}

export async function getStory(id) {
  const numericId = Number(id);

  // Fetch story
  const { data: story, error: storyError } = await supabase
    .from('stories')
    .select(STORY_COLUMNS)
    .eq('id', numericId)
    .single();

  if (storyError || !story) {
    console.error('Story fetch error:', storyError);
    return { story: null, analysis: null, sourceList: [] };
  }

  // Parse significance_factors JSONB
  if (story.significance_factors) {
    if (typeof story.significance_factors === 'string') {
      try { story.significance_factors = JSON.parse(story.significance_factors); }
      catch { story.significance_factors = null; }
    }
  }

  // Fetch analysis — use select + limit instead of maybeSingle
  const { data: analyses, error: analysisError } = await supabase
    .from('analyses')
    .select('*')
    .eq('story_id', numericId)
    .order('created_at', { ascending: false })
    .limit(1);

  if (analysisError) {
    console.error('Analysis fetch error:', analysisError);
  }

  let analysis = analyses?.[0] || null;

  // Parse JSONB fields if they come back as strings
  if (analysis) {
    if (typeof analysis.contrasts === 'string') {
      try { analysis.contrasts = JSON.parse(analysis.contrasts); }
      catch { analysis.contrasts = []; }
    }
    if (typeof analysis.facts === 'string') {
      try { analysis.facts = JSON.parse(analysis.facts); }
      catch { analysis.facts = []; }
    }
    if (!Array.isArray(analysis.contrasts)) analysis.contrasts = [];
    if (!Array.isArray(analysis.facts)) analysis.facts = [];
  }

  // Fetch article source list: group by source_name with count
  let sourceList = [];
  try {
    const { data: articles, error: artErr } = await supabase
      .from('articles')
      .select('source_name')
      .eq('story_id', numericId);

    if (!artErr && articles) {
      const counts = {};
      for (const a of articles) {
        const name = a.source_name || 'Unknown';
        counts[name] = (counts[name] || 0) + 1;
      }
      sourceList = Object.entries(counts)
        .map(([name, n]) => ({ name, n }))
        .sort((a, b) => b.n - a.n);
    }
  } catch (e) {
    console.error('Source list fetch error:', e);
  }

  console.log('getStory', numericId, '→ analysis:', analysis ? 'found' : 'null',
    analysis ? `headline="${analysis.headline}", contrasts=${analysis.contrasts?.length}, facts=${analysis.facts?.length}` : '',
    `sources=${sourceList.length}`);

  return { story, analysis, sourceList };
}

export async function getDashboardStats() {
  const analyzedIds = await getAnalyzedIds();

  let analyzedStories = [];
  if (analyzedIds.length > 0) {
    const { data, error } = await supabase
      .from('stories')
      .select('id, impact_score, attention_score, coverage_score, article_count')
      .in('id', analyzedIds)
      .eq('active', true);
    if (error) throw error;
    analyzedStories = data || [];
  }

  const { count: totalTracked, error: cErr } = await supabase
    .from('stories')
    .select('id', { count: 'exact', head: true })
    .eq('active', true);
  if (cErr) throw cErr;

  const totalArticles = analyzedStories.reduce((sum, s) => sum + (s.article_count || 0), 0);

  return {
    analyzedCount: analyzedStories.length,
    articleCount: totalArticles,
    totalTracked: totalTracked || 0,
  };
}

/** Read cached insights from insights_cache table (populated by backend pipeline). */
export async function getInsights() {
  try {
    const { data, error } = await supabase
      .from('insights_cache')
      .select('insights, computed_at')
      .eq('id', 1)
      .single();

    if (error || !data) return [];

    let insights = data.insights || [];
    if (typeof insights === 'string') {
      try { insights = JSON.parse(insights); }
      catch { insights = []; }
    }
    return Array.isArray(insights) ? insights : [];
  } catch {
    return [];
  }
}

const CATEGORY_GROUP_MEMBERS = {
  'Politics & Law': ['POLITICS', 'LAW', 'GOVERNMENT', 'LEGAL', 'ELECTIONS'],
  'World & Security': ['WORLD', 'MILITARY', 'INTERNATIONAL-RELATIONS', 'SECURITY', 'DEFENSE', 'INTERNATIONAL', 'INTERNATIONAL DIPLOMACY', 'CONFLICT', 'FOREIGN POLICY', 'DIPLOMACY', 'FOREIGN-POLICY'],
  'Economy & Business': ['ECONOMY', 'BUSINESS', 'TECHNOLOGY', 'FINANCE', 'TRADE', 'MARKETS', 'ENERGY'],
  'Science & Health': ['SCIENCE', 'HEALTHCARE', 'HEALTH', 'ENVIRONMENT', 'CLIMATE', 'MEDICAL'],
};

/**
 * Server-side category aggregation.
 * Returns { categories: [{ name, avg_impact, avg_coverage, topic_count, article_count }] }
 */
export async function getCategorySummary() {
  const { data, error } = await supabase
    .from('stories')
    .select('category, impact_score, coverage_score, attention_score, article_count')
    .eq('active', true);

  if (error) throw error;
  if (!data) return { categories: [] };

  const groups = {};
  for (const [name, members] of Object.entries(CATEGORY_GROUP_MEMBERS)) {
    groups[name] = { impact_sum: 0, coverage_sum: 0, topic_count: 0, article_count: 0 };
  }

  for (const story of data) {
    const cat = (story.category || '').trim();
    let matched = false;

    // Try matching full group label first (new format: "Politics & Law")
    if (groups[cat]) {
      const g = groups[cat];
      g.impact_sum += story.impact_score || 0;
      g.coverage_sum += story.coverage_score || story.attention_score || 0;
      g.topic_count += 1;
      g.article_count += story.article_count || 0;
      matched = true;
    }

    // Fall back to legacy uppercase member matching
    if (!matched) {
      const raw = cat.split('/')[0].trim().toUpperCase();
      for (const [name, members] of Object.entries(CATEGORY_GROUP_MEMBERS)) {
        if (members.includes(raw)) {
          const g = groups[name];
          g.impact_sum += story.impact_score || 0;
          g.coverage_sum += story.coverage_score || story.attention_score || 0;
          g.topic_count += 1;
          g.article_count += story.article_count || 0;
          matched = true;
          break;
        }
      }
    }

    if (!matched) {
      const g = groups['Economy & Business'];
      g.impact_sum += story.impact_score || 0;
      g.coverage_sum += story.coverage_score || story.attention_score || 0;
      g.topic_count += 1;
      g.article_count += story.article_count || 0;
    }
  }

  const categories = Object.entries(groups)
    .filter(([, g]) => g.topic_count > 0)
    .map(([name, g]) => ({
      name,
      avg_impact: Math.round(g.impact_sum / g.topic_count),
      avg_coverage: Math.round(g.coverage_sum / g.topic_count),
      topic_count: g.topic_count,
      article_count: g.article_count,
    }));

  return { categories };
}

const TOPICS_PER_CATEGORY = 8;

/**
 * Structured homepage data: top-ranked topics per category.
 * Returns {
 *   categories: [{
 *     name: string,
 *     topic_count_total: number,
 *     topics: [{ id, topic, article_count, impact_score, coverage_score,
 *                rank_score, featured_reason, trend, status }]
 *   }]
 * }
 */
export async function getHomepageData() {
  const analyzedIds = await getAnalyzedIds();
  if (analyzedIds.length === 0) return { categories: [] };

  const { data, error } = await supabase
    .from('stories')
    .select(STORY_COLUMNS)
    .in('id', analyzedIds)
    .eq('active', true);

  if (error) throw error;
  if (!data) return { categories: [] };

  // 30-day rolling window
  const since = new Date();
  since.setDate(since.getDate() - 30);
  const sinceMs = since.getTime();

  const recent = data.filter(s => {
    const ts = s.first_seen || s.created_at;
    return ts && new Date(ts).getTime() >= sinceMs;
  });

  // Group by category
  const groupMap = {};
  for (const [name, members] of Object.entries(CATEGORY_GROUP_MEMBERS)) {
    groupMap[name] = [];
  }

  for (const story of recent) {
    const cat = (story.category || '').trim();
    let matched = false;

    if (groupMap[cat]) {
      groupMap[cat].push(story);
      matched = true;
    }

    if (!matched) {
      const raw = cat.split('/')[0].trim().toUpperCase();
      for (const [name, members] of Object.entries(CATEGORY_GROUP_MEMBERS)) {
        if (members.includes(raw)) {
          groupMap[name].push(story);
          matched = true;
          break;
        }
      }
    }

    if (!matched) {
      groupMap['Economy & Business'].push(story);
    }
  }

  // Sort each group by rank_score, take top N
  const categories = Object.entries(groupMap)
    .filter(([, stories]) => stories.length > 0)
    .map(([name, stories]) => {
      stories.sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0));

      return {
        name,
        topic_count_total: stories.length,
        topics: stories.slice(0, TOPICS_PER_CATEGORY).map(s => ({
          id: s.id,
          topic: s.topic,
          article_count: s.article_count || 0,
          impact_score: s.impact_score || 0,
          coverage_score: s.coverage_score || s.attention_score || 0,
          rank_score: s.rank_score || 0,
          featured_reason: s.featured_reason || 'notable',
          trend: s.trend,
          status: s.status || 'developing',
        })),
      };
    });

  return { categories };
}
