'use client';

import { useState, useEffect, useRef } from 'react';
import { CATEGORY_GROUPS } from '../lib/constants';

const TABS = [
  { key: null, label: 'All' },
  ...CATEGORY_GROUPS.map(g => ({ key: g.key, label: g.label })),
];

export default function CategoryTabs({ selected, onSelect }) {
  const sentinelRef = useRef(null);
  const [isStuck, setIsStuck] = useState(false);
  const [navH, setNavH] = useState(57);

  // Measure nav height for sticky offset
  useEffect(() => {
    const nav = document.querySelector('.header-nav');
    if (nav) setNavH(nav.offsetHeight);
  }, []);

  // Detect when tabs become stuck
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => setIsStuck(!entry.isIntersecting),
      { threshold: 0 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <>
      <div ref={sentinelRef} style={{ height: 0 }} />
      <div className="tabs-section" style={{
        position: 'sticky',
        top: navH,
        zIndex: 99,
        background: 'var(--bg)',
        boxShadow: isStuck ? '0 1px 3px rgba(0,0,0,0.04)' : 'none',
        transition: 'box-shadow 0.2s',
      }}>
        <div className="tabs-inner" style={{
          maxWidth: 1280,
          margin: '0 auto',
          padding: '0 48px',
        }}>
          <div className="tabs" style={{
            display: 'flex',
            gap: 4,
            borderBottom: '2px solid var(--border)',
            marginBottom: 0,
          }}>
            {TABS.map(tab => {
              const isActive = selected === tab.key;
              return (
                <button
                  key={tab.key ?? 'all'}
                  className="tab"
                  onClick={() => onSelect(tab.key)}
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
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
