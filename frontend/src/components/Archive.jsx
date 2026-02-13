'use client';

import { useState, useMemo, useCallback } from 'react';
import TopicRow from './TopicRow';
import {
  CATEGORY_GROUPS,
  getPrimaryCategory,
  getGroupForCategory,
} from '../lib/constants';

const PAGE_SIZE = 15;

const SORT_OPTIONS = [
  { value: 'hottest', label: 'Hottest first' },
  { value: 'coverage_gap', label: 'Coverage gap' },
  { value: 'newest', label: 'Newest first' },
  { value: 'impact', label: 'Impact: high to low' },
  { value: 'articles', label: 'Most articles' },
];

const TABS = [
  { key: null, label: 'All' },
  ...CATEGORY_GROUPS.map(g => ({ key: g.key, label: g.label.replace(/&/g, 'and') })),
];

function sortStories(stories, sortKey) {
  const sorted = [...stories];
  switch (sortKey) {
    case 'hottest':
      sorted.sort((a, b) => (b.heat || 0) - (a.heat || 0));
      break;
    case 'coverage_gap':
      sorted.sort((a, b) => {
        const gapA = (a.impact_score || 0) - (a.coverage_score || a.attention_score || 0);
        const gapB = (b.impact_score || 0) - (b.coverage_score || b.attention_score || 0);
        return gapB - gapA;
      });
      break;
    case 'impact':
      sorted.sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0));
      break;
    case 'articles':
      sorted.sort((a, b) => (b.article_count || 0) - (a.article_count || 0));
      break;
    case 'newest':
    default:
      sorted.sort((a, b) => new Date(b.first_seen || 0) - new Date(a.first_seen || 0));
      break;
  }
  return sorted;
}

export default function Archive({ stories }) {
  const [selGroup, setSelGroup] = useState(null);
  const [sort, setSort] = useState('hottest');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    let result = stories;

    if (selGroup) {
      result = result.filter(s =>
        getGroupForCategory(getPrimaryCategory(s.category)) === selGroup
      );
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(s => (s.topic || '').toLowerCase().includes(q));
    }

    return sortStories(result, sort);
  }, [stories, selGroup, sort, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safeP = Math.min(page, totalPages);
  const visible = filtered.slice((safeP - 1) * PAGE_SIZE, safeP * PAGE_SIZE);

  const handleSearch = useCallback((e) => {
    setSearch(e.target.value);
    setPage(1);
  }, []);

  const handleCategoryChange = useCallback((groupKey) => {
    setSelGroup(groupKey);
    setPage(1);
  }, []);

  const handleSortChange = useCallback((e) => {
    setSort(e.target.value);
    setPage(1);
  }, []);

  const hasFilters = selGroup || search.trim();

  return (
    <div style={{ background: 'var(--bg)' }}>
      {/* Header */}
      <div style={{ padding: '0 48px' }}>
        <div style={{ maxWidth: 1080, margin: '0 auto' }}>
          <div className="archive-header" style={{
            paddingTop: 12,
            marginBottom: 'var(--space-md)',
            paddingBottom: 'var(--space-sm)',
            borderBottom: '2px solid var(--ink)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}>
            {/* Left: title + count */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <span style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '1.5px',
                color: 'var(--ink)',
              }}>
                Archive
              </span>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: 'var(--ink-muted)',
              }}>
                {stories.length} topics
              </span>
            </div>

            {/* Right: sort + search */}
            <div className="archive-controls" style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}>
              <select
                value={sort}
                onChange={handleSortChange}
                style={{
                  padding: '5px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg)',
                  color: 'var(--ink)',
                  fontSize: 12,
                  fontFamily: "'DM Sans', sans-serif",
                  cursor: 'pointer',
                  outline: 'none',
                }}
                onFocus={e => {
                  e.currentTarget.style.borderColor = 'var(--accent-gold)';
                  e.currentTarget.style.boxShadow = '0 0 0 2px rgba(200,150,62,0.1)';
                }}
                onBlur={e => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {SORT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>

              <div style={{ position: 'relative', width: 180 }}>
                <svg
                  style={{
                    position: 'absolute', left: 8, top: '50%',
                    transform: 'translateY(-50%)', width: 13, height: 13,
                    color: 'var(--ink-muted)',
                  }}
                  fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
                >
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <input
                  type="text"
                  placeholder="Search topics..."
                  value={search}
                  onChange={handleSearch}
                  style={{
                    width: '100%',
                    padding: '5px 10px 5px 26px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg)',
                    color: 'var(--ink)',
                    fontSize: 12,
                    fontFamily: "'DM Sans', sans-serif",
                    outline: 'none',
                  }}
                  onFocus={e => {
                    e.currentTarget.style.borderColor = 'var(--accent-gold)';
                    e.currentTarget.style.boxShadow = '0 0 0 2px rgba(200,150,62,0.1)';
                  }}
                  onBlur={e => {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Category tabs */}
      <div style={{
        maxWidth: 1080,
        margin: '0 auto',
        padding: '0 48px',
      }}>
        <div className="archive-tabs" style={{
          display: 'flex',
          gap: 4,
          borderBottom: '2px solid var(--border)',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
        }}>
          {TABS.map(tab => {
            const isActive = selGroup === tab.key;
            return (
              <button
                key={tab.key ?? 'all'}
                onClick={() => handleCategoryChange(tab.key)}
                style={{
                  padding: '14px 24px',
                  fontSize: 13,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  color: isActive ? 'var(--accent-blue-deep)' : 'var(--ink-muted)',
                  cursor: 'pointer',
                  marginBottom: -2,
                  transition: 'all 0.2s',
                  background: 'none',
                  border: 'none',
                  borderBottomWidth: 2,
                  borderBottomStyle: 'solid',
                  borderBottomColor: isActive ? 'var(--accent-blue-deep)' : 'transparent',
                  fontFamily: "'DM Sans', sans-serif",
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Results */}
      <main style={{
        maxWidth: 1080,
        margin: '0 auto',
        padding: 'var(--space-md) 48px 80px',
      }}>
        {/* Results count when filtered */}
        {hasFilters && (
          <div style={{
            fontSize: 13, color: 'var(--ink-muted)',
            padding: '16px 0 0',
          }}>
            {filtered.length} {filtered.length === 1 ? 'result' : 'results'}
          </div>
        )}

        {filtered.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '64px 24px',
            animation: 'fadeUp 0.4s ease both',
          }}>
            <p style={{
              color: 'var(--ink-secondary)',
              fontSize: 15,
              fontWeight: 500,
              marginBottom: 6,
            }}>
              {hasFilters ? 'No topics match your filters.' : 'No topics analyzed yet.'}
            </p>
            <p style={{
              color: 'var(--ink-muted)',
              fontSize: 13,
              marginBottom: hasFilters ? 20 : 0,
            }}>
              {hasFilters
                ? 'Try adjusting your search or category filter.'
                : 'Topics will appear here after the first analysis cycle.'}
            </p>
            {hasFilters && (
              <button
                onClick={() => { setSelGroup(null); setSearch(''); setPage(1); }}
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
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {visible.map((story, i) => (
                <TopicRow key={story.id} story={story} index={i} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 6,
                paddingTop: 24,
                borderTop: '1px solid var(--border)',
                marginTop: 0,
              }}>
                {buildPageNumbers(safeP, totalPages).map((p, i) => {
                  if (p === '...') {
                    return (
                      <span key={`ellipsis-${i}`} style={{
                        width: 36, height: 36,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 13, color: 'var(--ink-muted)',
                      }}>...</span>
                    );
                  }
                  const isActive = p === safeP;
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      style={{
                        width: 36, height: 36,
                        borderRadius: 6,
                        border: isActive ? 'none' : '1px solid var(--border)',
                        background: isActive ? 'var(--ink)' : 'var(--bg-card)',
                        color: isActive ? '#fff' : 'var(--ink-secondary)',
                        fontSize: 13,
                        fontFamily: "'DM Sans', sans-serif",
                        fontWeight: 500,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {p}
                    </button>
                  );
                })}
                {safeP < totalPages && (
                  <button
                    onClick={() => setPage(safeP + 1)}
                    style={{
                      width: 36, height: 36,
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      background: 'var(--bg-card)',
                      color: 'var(--ink-secondary)',
                      fontSize: 13,
                      fontFamily: "'DM Sans', sans-serif",
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    &rarr;
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function buildPageNumbers(current, total) {
  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages = [];
  pages.push(1);

  if (current > 3) pages.push('...');

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) pages.push('...');

  pages.push(total);
  return pages;
}
