/* ── Design System Colors ── */

export const CATEGORY_COLORS = {
  'Politics & Law':      '#C0392B',
  'World & Security':    '#2B4C7E',
  'Economy & Business':  '#C8963E',
  'Science & Health':    '#27AE60',
};

export const CATEGORIES = [
  { key: 'POLITICS', label: 'POLITICS', color: '#C0392B' },
  { key: 'WORLD', label: 'WORLD', color: '#2B4C7E' },
  { key: 'BUSINESS', label: 'BUSINESS', color: '#C8963E' },
  { key: 'SCIENCE', label: 'SCIENCE', color: '#27AE60' },
  { key: 'HEALTHCARE', label: 'HEALTHCARE', color: '#27AE60' },
  { key: 'ECONOMY', label: 'ECONOMY', color: '#C8963E' },
  { key: 'TECHNOLOGY', label: 'TECHNOLOGY', color: '#C8963E' },
  { key: 'LAW', label: 'LAW', color: '#C0392B' },
  { key: 'MILITARY', label: 'MILITARY', color: '#2B4C7E' },
];

export const CATEGORY_GROUPS = [
  { key: 'politics-law', label: 'Politics & Law', color: '#C0392B', members: ['POLITICS', 'LAW', 'GOVERNMENT', 'LEGAL', 'ELECTIONS'] },
  { key: 'world-security', label: 'World & Security', color: '#2B4C7E', members: ['WORLD', 'MILITARY', 'INTERNATIONAL-RELATIONS', 'SECURITY', 'DEFENSE', 'INTERNATIONAL', 'INTERNATIONAL DIPLOMACY', 'CONFLICT', 'FOREIGN POLICY', 'DIPLOMACY', 'FOREIGN-POLICY'] },
  { key: 'economy-business', label: 'Economy & Business', color: '#C8963E', members: ['ECONOMY', 'BUSINESS', 'TECHNOLOGY', 'FINANCE', 'TRADE', 'MARKETS', 'ENERGY'] },
  { key: 'science-health', label: 'Science & Health', color: '#27AE60', members: ['SCIENCE', 'HEALTHCARE', 'HEALTH', 'ENVIRONMENT', 'CLIMATE', 'MEDICAL'] },
];

export const BIAS_COLORS = {
  'far-left': '#1D4ED8',
  left: '#2563EB',
  'left-center': '#3B82F6',
  center: '#6B7280',
  'right-center': '#DC2626',
  right: '#B91C1C',
  'far-right': '#991B1B',
};

export const VERDICT_STYLES = {
  confirmed: { bg: '#DCFCE7', color: '#166534', border: '#BBF7D0' },
  misleading: { bg: '#FEE2E2', color: '#991B1B', border: '#FECACA' },
  'lacks context': { bg: '#FEF3C7', color: '#92400E', border: '#FDE68A' },
  unverified: { bg: '#F3F4F6', color: '#4B5563', border: '#E5E7EB' },
};

export const COVERAGE_GAP_THRESHOLD = 15;

/* ── Helper Functions ── */

export function getPrimaryCategory(cat) {
  const trimmed = (cat || '').trim();
  // Full group label → return the first member as primary key
  for (const g of CATEGORY_GROUPS) {
    if (g.label === trimmed) return g.members[0];
  }
  const raw = trimmed.split('/')[0].trim().toUpperCase();
  if (CATEGORIES.some(c => c.key === raw)) return raw;
  return raw || 'OTHER';
}

/** Read the coverage score, preferring coverage_score over attention_score. */
export function getCoverageScore(story) {
  return story.coverage_score || story.attention_score || 0;
}

export function getGap(story) {
  return Math.round((story.impact_score || 0) - getCoverageScore(story));
}

export function getCategoryColor(cat) {
  const p = getPrimaryCategory(cat);
  return CATEGORIES.find(c => c.key === p)?.color || '#6B7280';
}

export function getCoverageRelationship(gap) {
  if (gap > COVERAGE_GAP_THRESHOLD) return 'less-covered';
  if (gap < -COVERAGE_GAP_THRESHOLD) return 'more-covered';
  return 'proportional';
}

/** Map any individual category to its parent group key. */
export function getGroupForCategory(cat) {
  const trimmed = (cat || '').trim();
  // Match full group label (e.g., "Politics & Law")
  for (const g of CATEGORY_GROUPS) {
    if (g.label === trimmed) return g.key;
  }
  // Match legacy uppercase member keys (e.g., "POLITICS")
  const upper = trimmed.toUpperCase();
  for (const g of CATEGORY_GROUPS) {
    if (g.members.includes(upper)) return g.key;
  }
  return 'economy-business';
}

/** Get the parent group label for a category string. */
export function getGroupLabel(cat) {
  const key = getGroupForCategory(getPrimaryCategory(cat));
  return CATEGORY_GROUPS.find(g => g.key === key)?.label || 'Economy & Business';
}

/** Get the parent group color for a category string. */
export function getGroupColor(cat) {
  const key = getGroupForCategory(getPrimaryCategory(cat));
  return CATEGORY_GROUPS.find(g => g.key === key)?.color || '#C8963E';
}

/** Compute 14-day activity array for a story.
 *  Uses UTC dates throughout to avoid hydration mismatches
 *  between server (Node.js) and client (browser) timezones.
 */
export function computeActivityDays(story, windowDays = 14) {
  let raw = story.activity_days;
  if (typeof raw === 'string') {
    try { raw = JSON.parse(raw); } catch { raw = null; }
  }
  if (Array.isArray(raw) && raw.length === windowDays) return raw;

  // Use UTC to guarantee identical results on server and client
  const now = new Date();
  const todayUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const msPerDay = 86400000;
  const windowStartMs = todayUTC - (windowDays - 1) * msPerDay;

  const firstSeen = story.first_seen ? new Date(story.first_seen).getTime() : null;
  const lastArticle = story.last_article_at ? new Date(story.last_article_at).getTime() : null;

  if (!firstSeen && !lastArticle) return Array(windowDays).fill(false);

  const rangeStart = firstSeen && lastArticle ? Math.min(firstSeen, lastArticle) : (firstSeen || lastArticle);
  const rangeEnd = firstSeen && lastArticle ? Math.max(firstSeen, lastArticle) : (firstSeen || lastArticle);

  return Array.from({ length: windowDays }, (_, i) => {
    const dayStartMs = windowStartMs + i * msPerDay;
    const dayEndMs = dayStartMs + msPerDay;
    return rangeStart < dayEndMs && rangeEnd >= dayStartMs;
  });
}

/** Compute aggregate activity for a group of stories over recent days. */
export function computeGroupActivity(groupStories, recentDays = 4) {
  const result = Array(recentDays).fill(false);
  for (const story of groupStories) {
    const activity = computeActivityDays(story);
    const tail = activity.slice(-recentDays);
    for (let i = 0; i < recentDays; i++) {
      if (tail[i]) result[i] = true;
    }
  }
  return result;
}

/* ── New helpers for redesigned dashboard ── */

/** Parse story.trend from JSONB (may come as string from Supabase).
 *  Returns array of {date, count} objects.
 */
export function parseTrend(story) {
  let trend = story.trend;
  if (!trend) return [];
  if (typeof trend === 'string') {
    try { trend = JSON.parse(trend); } catch { return []; }
  }
  if (!Array.isArray(trend)) return [];
  return trend;
}

/** Compute trend direction from last 3 days of daily counts.
 *  Returns "trending", "steady", or "cooling".
 */
export function computeTrendDirection(trend) {
  if (!trend || trend.length < 2) return 'steady';
  const last3 = trend.slice(-3);
  const counts = last3.map(d => d.count || 0);

  if (counts.length < 2) return 'steady';

  // Simple slope: compare last vs first of the window
  const first = counts[0];
  const last = counts[counts.length - 1];
  const diff = last - first;

  if (diff >= 2) return 'trending';
  if (diff <= -2) return 'cooling';
  return 'steady';
}

/** Compute average impact and coverage per category group.
 *  Returns { [groupLabel]: { avgImpact, avgCoverage, storyCount } }
 */
export function computeCategoryAggregates(stories) {
  const result = {};
  for (const group of CATEGORY_GROUPS) {
    const groupStories = stories.filter(s =>
      group.members.includes(getPrimaryCategory(s.category))
    );
    const count = groupStories.length;
    result[group.label] = {
      avgImpact: count > 0
        ? Math.round(groupStories.reduce((sum, s) => sum + (s.impact_score || 0), 0) / count)
        : 0,
      avgCoverage: count > 0
        ? Math.round(groupStories.reduce((sum, s) => sum + getCoverageScore(s), 0) / count)
        : 0,
      storyCount: count,
    };
  }
  return result;
}

/** Compute the two most notable insights:
 *  1. Undercovered — category group with the largest impact-coverage gap
 *  2. Surging — category group with the highest 48h article count increase
 *  Returns [{ type, category, description }]
 */
export function computeInsights(stories) {
  const insights = [];

  // 1. Undercovered: category with highest avg(impact) - avg(coverage)
  const aggregates = computeCategoryAggregates(stories);
  let maxGap = -Infinity;
  let undercoveredCat = null;
  for (const [label, data] of Object.entries(aggregates)) {
    if (data.storyCount === 0) continue;
    const gap = data.avgImpact - data.avgCoverage;
    if (gap > maxGap) {
      maxGap = gap;
      undercoveredCat = label;
    }
  }
  if (undercoveredCat && maxGap > 0) {
    insights.push({
      type: 'undercovered',
      category: undercoveredCat,
      description: `${undercoveredCat} topics show the widest coverage gap this week`,
    });
  }

  // 2. Surging: category with the highest % increase in articles over 48h
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const yesterdayStr = new Date(now.getTime() - 86400000).toISOString().slice(0, 10);
  const twoDaysAgoStr = new Date(now.getTime() - 2 * 86400000).toISOString().slice(0, 10);
  const threeDaysAgoStr = new Date(now.getTime() - 3 * 86400000).toISOString().slice(0, 10);

  let maxSurge = -Infinity;
  let surgingCat = null;
  for (const group of CATEGORY_GROUPS) {
    const groupStories = stories.filter(s =>
      group.members.includes(getPrimaryCategory(s.category))
    );
    let recent48 = 0;
    let prior48 = 0;
    for (const story of groupStories) {
      const trend = parseTrend(story);
      for (const d of trend) {
        if (d.date === todayStr || d.date === yesterdayStr) {
          recent48 += d.count || 0;
        } else if (d.date === twoDaysAgoStr || d.date === threeDaysAgoStr) {
          prior48 += d.count || 0;
        }
      }
    }
    const surge = prior48 > 0 ? ((recent48 - prior48) / prior48) : (recent48 > 0 ? 1 : 0);
    if (surge > maxSurge) {
      maxSurge = surge;
      surgingCat = group.label;
    }
  }
  if (surgingCat && maxSurge > 0) {
    insights.push({
      type: 'surging',
      category: surgingCat,
      description: `${surgingCat} coverage up significantly in the last 48 hours`,
    });
  }

  return insights;
}
