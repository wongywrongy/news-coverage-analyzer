import { supabase } from './supabase';

// Select all columns — the app handles missing fields gracefully via defaults.
const STORY_COLUMNS = '*';

/** Return story_ids that have a completed analysis (non-null headline). */
async function getAnalyzedIds() {
  try {
    const { data: rows, error } = await supabase
      .from('analyses')
      .select('story_id, headline')
      .not('headline', 'is', null);

    if (error) {
      console.error('getAnalyzedIds error:', error.message);
      return [];
    }
    if (!rows || rows.length === 0) return [];

    return [...new Set(rows.map(r => r.story_id))];
  } catch (e) {
    console.error('getAnalyzedIds exception:', e);
    return [];
  }
}

export async function getStories() {
  try {
    const analyzedIds = await getAnalyzedIds();
    if (analyzedIds.length === 0) return [];

    const { data, error } = await supabase
      .from('stories')
      .select(STORY_COLUMNS)
      .in('id', analyzedIds)
      .eq('active', true);

    if (error) {
      console.error('getStories error:', error.message);
      return [];
    }
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
  } catch (e) {
    console.error('getStories exception:', e);
    return [];
  }
}

export async function getStory(id) {
  const numericId = Number(id);

  // Fetch story
  let story = null;
  try {
    const { data, error: storyError } = await supabase
      .from('stories')
      .select(STORY_COLUMNS)
      .eq('id', numericId)
      .single();

    if (storyError || !data) {
      console.error('Story fetch error:', storyError?.message);
      return { story: null, analysis: null, sourceList: [], biasCounts: {} };
    }
    story = data;
  } catch (e) {
    console.error('Story fetch exception:', e);
    return { story: null, analysis: null, sourceList: [], biasCounts: {} };
  }

  // Parse significance_factors JSONB
  if (story.significance_factors) {
    if (typeof story.significance_factors === 'string') {
      try { story.significance_factors = JSON.parse(story.significance_factors); }
      catch { story.significance_factors = null; }
    }
  }

  // Fetch analysis
  let analysis = null;
  try {
    const { data: analyses, error: analysisError } = await supabase
      .from('analyses')
      .select('*')
      .eq('story_id', numericId)
      .order('created_at', { ascending: false })
      .limit(1);

    if (analysisError) {
      console.error('Analysis fetch error:', analysisError.message);
    }
    analysis = analyses?.[0] || null;
  } catch (e) {
    console.error('Analysis fetch exception:', e);
  }

  // Determine if analysis is current (matches latest prompt version)
  const CURRENT_ANALYSIS_VERSION = 2;
  if (analysis) {
    analysis.analysis_is_current = (analysis.analysis_version || 1) >= CURRENT_ANALYSIS_VERSION;
  }

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
    if (typeof analysis.source_framings === 'string') {
      try { analysis.source_framings = JSON.parse(analysis.source_framings); }
      catch { analysis.source_framings = []; }
    }
    if (!Array.isArray(analysis.source_framings)) analysis.source_framings = [];
    if (typeof analysis.body === 'string') {
      try { analysis.body = JSON.parse(analysis.body); }
      catch { analysis.body = []; }
    }
    if (analysis.body && !Array.isArray(analysis.body)) analysis.body = [];
  }

  // Fetch article source list + bias distribution
  let sourceList = [];
  let biasCounts = {};
  try {
    const { data: articles, error: artErr } = await supabase
      .from('articles')
      .select('source_name, source_bias')
      .eq('story_id', numericId);

    if (!artErr && articles) {
      const nameCounts = {};
      for (const a of articles) {
        const name = a.source_name || 'Unknown';
        nameCounts[name] = (nameCounts[name] || 0) + 1;
        const bias = a.source_bias || 'center';
        biasCounts[bias] = (biasCounts[bias] || 0) + 1;
      }
      sourceList = Object.entries(nameCounts)
        .map(([name, n]) => ({ name, n }))
        .sort((a, b) => b.n - a.n);
    }
  } catch (e) {
    console.error('Source list fetch error:', e);
  }

  return { story, analysis, sourceList, biasCounts };
}

export async function getDashboardStats() {
  try {
    const analyzedIds = await getAnalyzedIds();

    let analyzedStories = [];
    if (analyzedIds.length > 0) {
      const { data, error } = await supabase
        .from('stories')
        .select('id, impact_score, attention_score, coverage_score, article_count')
        .in('id', analyzedIds)
        .eq('active', true);
      if (error) {
        console.error('getDashboardStats stories error:', error.message);
      } else {
        analyzedStories = data || [];
      }
    }

    const { count: totalTracked, error: cErr } = await supabase
      .from('stories')
      .select('id', { count: 'exact', head: true })
      .eq('active', true);
    if (cErr) console.error('getDashboardStats count error:', cErr.message);

    const totalArticles = analyzedStories.reduce((sum, s) => sum + (s.article_count || 0), 0);

    return {
      analyzedCount: analyzedStories.length,
      articleCount: totalArticles,
      totalTracked: totalTracked || 0,
    };
  } catch (e) {
    console.error('getDashboardStats exception:', e);
    return { analyzedCount: 0, articleCount: 0, totalTracked: 0 };
  }
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
  try {
    const { data, error } = await supabase
      .from('stories')
      .select('category, impact_score, coverage_score, attention_score, article_count')
      .eq('active', true);

    if (error) {
      console.error('getCategorySummary error:', error.message);
      return { categories: [] };
    }
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
  } catch (e) {
    console.error('getCategorySummary exception:', e);
    return { categories: [] };
  }
}

/**
 * Top 4 headline stories with analysis lede for the Headlines section.
 * Joins stories + analyses; filters high-impact, well-covered, analyzed stories.
 */
export async function getHeadlineStories() {
  try {
    // 30-day rolling window
    const since = new Date();
    since.setDate(since.getDate() - 30);
    const sinceMs = since.getTime();

    // Try strict thresholds first, then relax if too few results
    const thresholds = [
      { impact: 75, articles: 15 },
      { impact: 50, articles: 8 },
      { impact: 30, articles: 5 },
    ];

    for (const { impact, articles } of thresholds) {
      const result = await _fetchHeadlineCandidates(impact, articles, sinceMs);
      if (result.length >= 2) return result.slice(0, 3);
    }

    return [];
  } catch (e) {
    console.error('getHeadlineStories exception:', e);
    return [];
  }
}

async function _fetchHeadlineCandidates(minImpact, minArticles, sinceMs) {
  const { data: stories, error: sErr } = await supabase
    .from('stories')
    .select('id, topic, category, impact_score, article_count, source_count, trend, bias_spread, rank_score, first_seen, created_at')
    .eq('active', true)
    .gte('impact_score', minImpact)
    .gte('article_count', minArticles)
    .order('rank_score', { ascending: false })
    .limit(20);

  if (sErr || !stories || stories.length === 0) return [];

  const recent = stories.filter(s => {
    const ts = s.first_seen || s.created_at;
    return ts && new Date(ts).getTime() >= sinceMs;
  });

  if (recent.length === 0) return [];

  // Fetch analyses for these stories
  const ids = recent.map(s => s.id);
  const { data: analyses, error: aErr } = await supabase
    .from('analyses')
    .select('story_id, headline, lede')
    .in('story_id', ids)
    .not('headline', 'is', null);

  if (aErr || !analyses || analyses.length === 0) return [];

  const analysisMap = {};
  for (const a of analyses) {
    analysisMap[a.story_id] = a;
  }

  return recent
    .filter(s => analysisMap[s.id])
    .map(s => ({
      id: s.id,
      topic: s.topic,
      category: s.category,
      impact_score: s.impact_score,
      article_count: s.article_count,
      source_count: s.source_count,
      trend: s.trend,
      bias_spread: s.bias_spread,
      headline: analysisMap[s.id].headline,
      lede: analysisMap[s.id].lede,
    }));
}

const TOPICS_PER_CATEGORY = 8;

export async function getArchiveStories() {
  try {
    const analyzedIds = await getAnalyzedIds();
    if (analyzedIds.length === 0) return [];

    const { data, error } = await supabase
      .from('stories')
      .select('id, topic, category, impact_score, coverage_score, attention_score, article_count, source_count, first_seen, last_updated, rank_score, trend, status')
      .in('id', analyzedIds)
      .order('first_seen', { ascending: false });

    if (error) {
      console.error('getArchiveStories error:', error.message);
      return [];
    }
    return data || [];
  } catch (e) {
    console.error('getArchiveStories exception:', e);
    return [];
  }
}

/**
 * Structured homepage data: top-ranked topics per category.
 */
export async function getHomepageData() {
  try {
    const analyzedIds = await getAnalyzedIds();
    if (analyzedIds.length === 0) return { categories: [] };

    const { data, error } = await supabase
      .from('stories')
      .select(STORY_COLUMNS)
      .in('id', analyzedIds)
      .eq('active', true);

    if (error) {
      console.error('getHomepageData error:', error.message);
      return { categories: [] };
    }
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
  } catch (e) {
    console.error('getHomepageData exception:', e);
    return { categories: [] };
  }
}
