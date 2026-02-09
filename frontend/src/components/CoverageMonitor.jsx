'use client';

import { useState, useMemo, useRef } from 'react';
import CategoryTabs from './CategoryTabs';
import InsightsBar from './InsightsBar';
import TopicCard from './TopicCard';
import { CATEGORY_GROUPS, getGap, getCoverageScore, getPrimaryCategory, getGroupForCategory, computeInsights } from '../lib/constants';

const MAX_VISIBLE = 8;

export default function CoverageMonitor({ stories, insights: serverInsights }) {
  const [selGroup, setSelGroup] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const sectionRefs = useRef({});

  // Prefer backend-cached insights; fall back to client-side computation
  const insights = serverInsights && serverInsights.length > 0
    ? serverInsights
    : computeInsights(stories);

  const sections = useMemo(() => {
    let filtered = stories;

    if (selGroup) {
      filtered = filtered.filter(s =>
        getGroupForCategory(getPrimaryCategory(s.category)) === selGroup
      );
    }

    const groups = {};
    for (const story of filtered) {
      const cat = getPrimaryCategory(story.category);
      const groupKey = getGroupForCategory(cat);
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(story);
    }

    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => {
        const rankA = a.rank_score || 0;
        const rankB = b.rank_score || 0;
        if (rankA !== rankB) return rankB - rankA;
        const scoreA = (a.impact_score || 0) * 0.6 + getCoverageScore(a) * 0.4;
        const scoreB = (b.impact_score || 0) * 0.6 + getCoverageScore(b) * 0.4;
        return scoreB - scoreA || a.id - b.id;
      });
    }

    return CATEGORY_GROUPS
      .filter(g => groups[g.key]?.length > 0)
      .map(g => ({
        key: g.key,
        label: g.label,
        color: g.color,
        stories: groups[g.key],
      }));
  }, [stories, selGroup]);

  const handleGroupSelect = (groupKey) => {
    setSelGroup(groupKey);
    if (groupKey && sectionRefs.current[groupKey]) {
      setTimeout(() => {
        sectionRefs.current[groupKey]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    }
  };

  const toggleShowAll = (sectionKey) => {
    setExpandedSections(prev => ({ ...prev, [sectionKey]: !prev[sectionKey] }));
  };

  let runningIndex = 0;

  return (
    <>
      <CategoryTabs selected={selGroup} onSelect={handleGroupSelect} />
      <InsightsBar insights={insights} />

      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '0 48px 80px' }}>
        {sections.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '64px 24px',
            animation: 'fadeUp 0.4s ease both',
          }}>
            <div style={{
              width: 48,
              height: 48,
              margin: '0 auto 16px',
              borderRadius: '50%',
              background: selGroup
                ? (CATEGORY_GROUPS.find(g => g.key === selGroup)?.color || 'var(--border)') + '14'
                : 'var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              opacity: 0.7,
            }}>
              {selGroup ? (
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: CATEGORY_GROUPS.find(g => g.key === selGroup)?.color || 'var(--ink-muted)',
                }} />
              ) : (
                <span style={{ color: 'var(--ink-muted)' }}>—</span>
              )}
            </div>
            <p style={{
              color: 'var(--ink-secondary)',
              fontSize: 15,
              fontWeight: 500,
              marginBottom: 6,
            }}>
              {selGroup
                ? `No topics in ${CATEGORY_GROUPS.find(g => g.key === selGroup)?.label || 'this category'} yet`
                : 'No topics available'}
            </p>
            <p style={{
              color: 'var(--ink-muted)',
              fontSize: 13,
              marginBottom: selGroup ? 20 : 0,
            }}>
              {selGroup
                ? 'Topics will appear here once articles in this category are collected and analyzed.'
                : 'The pipeline hasn\u2019t run yet. Topics will appear after the first analysis cycle.'}
            </p>
            {selGroup && (
              <button
                onClick={() => handleGroupSelect(null)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 20px',
                  fontSize: 13,
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 500,
                  color: 'var(--accent-blue)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--accent-blue)';
                  e.currentTarget.style.background = 'rgba(43,76,126,0.04)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                View all categories
              </button>
            )}
          </div>
        ) : (
          sections.map(section => {
            const showAll = expandedSections[section.key];
            const visibleStories = showAll ? section.stories : section.stories.slice(0, MAX_VISIBLE);
            const hasMore = section.stories.length > MAX_VISIBLE;
            const startIdx = runningIndex;
            runningIndex += visibleStories.length;

            return (
              <div
                key={section.key}
                ref={el => { sectionRefs.current[section.key] = el; }}
                style={{ marginBottom: 48 }}
              >
                {/* Section header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  marginBottom: 20,
                }}>
                  <div style={{
                    width: 4,
                    height: 24,
                    borderRadius: 2,
                    background: section.color,
                  }} />
                  <h2 style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: 700,
                    fontSize: 14,
                    textTransform: 'uppercase',
                    letterSpacing: '1.2px',
                    color: 'var(--ink-secondary)',
                  }}>
                    {section.label}
                  </h2>
                  <span style={{
                    fontSize: 13,
                    color: 'var(--ink-muted)',
                    fontWeight: 400,
                  }}>
                    {section.stories.length} {section.stories.length === 1 ? 'topic' : 'topics'}
                  </span>
                </div>

                {/* Story cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {visibleStories.map((story, i) => (
                    <TopicCard
                      key={story.id}
                      story={story}
                      index={startIdx + i}
                    />
                  ))}
                </div>

                {/* Show all button */}
                {hasMore && !showAll && (
                  <button
                    onClick={(e) => { e.preventDefault(); toggleShowAll(section.key); }}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: 14,
                      marginTop: 8,
                      background: 'transparent',
                      border: '1px dashed var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--ink-muted)',
                      fontSize: 12,
                      fontFamily: "'DM Sans', sans-serif",
                      fontWeight: 500,
                      letterSpacing: '0.03em',
                      cursor: 'pointer',
                      textAlign: 'center',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'var(--accent-blue)';
                      e.currentTarget.style.color = 'var(--accent-blue)';
                      e.currentTarget.style.background = 'rgba(43,76,126,0.03)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = 'var(--border)';
                      e.currentTarget.style.color = 'var(--ink-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    Show all {section.stories.length} topics
                  </button>
                )}
              </div>
            );
          })
        )}
      </main>
    </>
  );
}
