'use client';

import { useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import Footer from './Footer';
import {
  CATEGORY_GROUPS,
  getPrimaryCategory,
  getGroupForCategory,
  getGroupLabel,
  getGroupColor,
  getCoverageScore,
} from '../lib/constants';

const PAGE_SIZE = 50;

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
  { value: 'impact', label: 'Highest impact' },
  { value: 'articles', label: 'Most articles' },
];

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

function sortStories(stories, sortKey) {
  const sorted = [...stories];
  switch (sortKey) {
    case 'oldest':
      sorted.sort((a, b) => new Date(a.first_seen || 0) - new Date(b.first_seen || 0));
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
  const [sort, setSort] = useState('newest');
  const [search, setSearch] = useState('');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const filtered = useMemo(() => {
    let result = stories;

    // Category filter
    if (selGroup) {
      result = result.filter(s =>
        getGroupForCategory(getPrimaryCategory(s.category)) === selGroup
      );
    }

    // Search filter
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(s => (s.topic || '').toLowerCase().includes(q));
    }

    // Sort
    result = sortStories(result, sort);

    return result;
  }, [stories, selGroup, sort, search]);

  const visible = filtered.slice(0, visibleCount);
  const hasMore = visibleCount < filtered.length;

  const handleSearch = useCallback((e) => {
    setSearch(e.target.value);
    setVisibleCount(PAGE_SIZE);
  }, []);

  const handleCategoryChange = useCallback((groupKey) => {
    setSelGroup(groupKey);
    setVisibleCount(PAGE_SIZE);
  }, []);

  const handleSortChange = useCallback((e) => {
    setSort(e.target.value);
    setVisibleCount(PAGE_SIZE);
  }, []);

  const hasFilters = selGroup || search.trim();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Sticky nav */}
      <nav className="archive-nav" style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'rgba(250,250,247,0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border)',
        padding: '14px 48px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <Link href="/" style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 800,
          fontSize: 22,
          color: 'var(--ink)',
          textDecoration: 'none',
          letterSpacing: '-0.5px',
        }}>
          ClearSignal
        </Link>
        <span style={{
          fontSize: 12,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '1.5px',
          color: 'var(--ink-muted)',
        }}>
          Archive
        </span>
      </nav>

      {/* Header */}
      <header style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '48px 48px 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 8 }}>
          <h1 style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 900,
            fontSize: 42,
            letterSpacing: '-1px',
            lineHeight: 1.1,
          }}>
            Archive
          </h1>
          <span style={{
            fontSize: 13,
            color: 'var(--ink-muted)',
            fontFamily: "'JetBrains Mono', monospace",
            background: 'var(--warm-bg)',
            padding: '4px 12px',
            borderRadius: 20,
          }}>
            {stories.length} topics
          </span>
        </div>
        <p style={{
          fontSize: 17,
          lineHeight: 1.5,
          color: 'var(--ink-secondary)',
          maxWidth: 520,
          marginBottom: 32,
        }}>
          Every topic ClearSignal has analyzed.
        </p>
      </header>

      {/* Controls */}
      <div style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '0 48px 24px',
      }}>
        <div className="archive-controls" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
        }}>
          {/* Category pills */}
          <div className="archive-pills" style={{
            display: 'flex',
            gap: 6,
            flex: 1,
            minWidth: 0,
          }}>
            <button
              onClick={() => handleCategoryChange(null)}
              style={{
                padding: '6px 16px',
                borderRadius: 20,
                border: '1px solid',
                borderColor: !selGroup ? 'var(--accent-blue-deep)' : 'var(--border)',
                background: !selGroup ? 'var(--accent-blue-deep)' : 'transparent',
                color: !selGroup ? '#fff' : 'var(--ink-secondary)',
                fontSize: 13,
                fontWeight: 500,
                fontFamily: "'DM Sans', sans-serif",
                cursor: 'pointer',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap',
              }}
            >
              All
            </button>
            {CATEGORY_GROUPS.map(g => {
              const active = selGroup === g.key;
              return (
                <button
                  key={g.key}
                  onClick={() => handleCategoryChange(active ? null : g.key)}
                  style={{
                    padding: '6px 16px',
                    borderRadius: 20,
                    border: '1px solid',
                    borderColor: active ? g.color : 'var(--border)',
                    background: active ? g.color : 'transparent',
                    color: active ? '#fff' : 'var(--ink-secondary)',
                    fontSize: 13,
                    fontWeight: 500,
                    fontFamily: "'DM Sans', sans-serif",
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>

          {/* Sort dropdown */}
          <select
            value={sort}
            onChange={handleSortChange}
            style={{
              padding: '7px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              background: 'var(--bg-card)',
              color: 'var(--ink)',
              fontSize: 13,
              fontFamily: "'DM Sans', sans-serif",
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {SORT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* Search input */}
          <div style={{ position: 'relative', minWidth: 200 }}>
            <svg
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                width: 14,
                height: 14,
                color: 'var(--ink-muted)',
              }}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
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
                padding: '7px 12px 7px 30px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                background: 'var(--bg-card)',
                color: 'var(--ink)',
                fontSize: 13,
                fontFamily: "'DM Sans', sans-serif",
                outline: 'none',
              }}
            />
          </div>
        </div>
      </div>

      {/* Results */}
      <main style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '0 48px 80px',
      }}>
        {/* Results count */}
        {(selGroup || search.trim()) && (
          <div style={{
            fontSize: 13,
            color: 'var(--ink-muted)',
            marginBottom: 16,
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
                onClick={() => { setSelGroup(null); setSearch(''); }}
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {visible.map((story, i) => (
                <ArchiveRow key={story.id} story={story} index={i} />
              ))}
            </div>

            {hasMore && (
              <button
                onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: 14,
                  marginTop: 12,
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
                Show more ({filtered.length - visibleCount} remaining)
              </button>
            )}
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}

function ArchiveRow({ story, index }) {
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);
  const primaryCat = getPrimaryCategory(story.category);
  const impactScore = Math.round(story.impact_score || 0);

  return (
    <Link href={`/story/${story.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      <div
        className="archive-row"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 20px',
          display: 'grid',
          gridTemplateColumns: '1fr auto',
          gap: 16,
          alignItems: 'center',
          transition: 'all 0.2s',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          opacity: 0,
          animation: `fadeUp 0.3s ease ${Math.min(index * 0.02, 0.5)}s both`,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = '#ccc';
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
          e.currentTarget.style.transform = 'translateY(-1px)';
          const bar = e.currentTarget.querySelector('.archive-left-bar');
          if (bar) bar.style.width = '5px';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.boxShadow = 'none';
          e.currentTarget.style.transform = 'translateY(0)';
          const bar = e.currentTarget.querySelector('.archive-left-bar');
          if (bar) bar.style.width = '3px';
        }}
      >
        {/* Left color bar */}
        <div
          className="archive-left-bar"
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: 3,
            background: groupColor,
            borderRadius: '8px 0 0 8px',
            transition: 'width 0.2s',
          }}
        />

        {/* Content */}
        <div className="archive-row-content" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          paddingLeft: 4,
          minWidth: 0,
        }}>
          {/* Category pill */}
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.6px',
            padding: '2px 8px',
            borderRadius: 3,
            color: groupColor,
            background: `${groupColor}14`,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}>
            {primaryCat}
          </span>

          {/* Topic title */}
          <span className="archive-topic-title" style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 600,
            fontSize: 15,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            minWidth: 0,
          }}>
            {story.topic}
          </span>

          {/* Meta: article count + date */}
          <div className="archive-row-meta" style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexShrink: 0,
          }}>
            <span style={{
              fontSize: 12,
              color: 'var(--ink-muted)',
              whiteSpace: 'nowrap',
            }}>
              {story.article_count || 0} articles
            </span>
            <span style={{
              fontSize: 12,
              color: 'var(--ink-muted)',
              fontFamily: "'JetBrains Mono', monospace",
              whiteSpace: 'nowrap',
            }}>
              {formatDate(story.first_seen)}
            </span>
          </div>
        </div>

        {/* Impact score */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexShrink: 0,
        }}>
          <div style={{
            width: 48,
            height: 3,
            background: 'var(--border)',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${impactScore}%`,
              borderRadius: 2,
              background: '#AEAEAE',
              transition: 'width 0.4s ease',
            }} />
          </div>
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 800,
            fontSize: 20,
            lineHeight: 1,
            color: '#6B6B6B',
            minWidth: 28,
            textAlign: 'right',
          }}>
            {impactScore}
          </div>
        </div>
      </div>
    </Link>
  );
}
