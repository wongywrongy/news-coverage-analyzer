'use client';

import { CATEGORY_GROUPS } from '../lib/constants';

const TABS = [
  { key: null, label: 'All' },
  ...CATEGORY_GROUPS.map(g => ({ key: g.key, label: g.label })),
];

export default function CategoryTabs({ selected, onSelect }) {
  return (
    <div style={{
      maxWidth: 1280,
      margin: '0 auto',
      padding: '0 48px',
    }}>
      <div style={{
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
              onClick={() => onSelect(tab.key)}
              style={{
                padding: '14px 24px',
                fontSize: 13,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.8px',
                color: isActive ? 'var(--accent-blue-deep)' : 'var(--ink-muted)',
                cursor: 'pointer',
                borderBottom: `2px solid ${isActive ? 'var(--accent-blue-deep)' : 'transparent'}`,
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
  );
}
