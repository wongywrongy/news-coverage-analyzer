'use client';

import { CATEGORY_GROUPS } from '../lib/constants';

const ALL_COLOR = '#4A6FA5';

export default function CategoryNav({ selected, onSelect }) {
  const groups = [
    { key: null, label: 'ALL', color: ALL_COLOR },
    ...CATEGORY_GROUPS.map(g => ({ key: g.key, label: g.label.toUpperCase(), color: g.color })),
  ];

  return (
    <div style={{
      background: '#FFFFFF',
      borderBottom: '1px solid #E5E5E5',
    }}>
      <div className="cat-nav" style={{
        maxWidth: 1288,
        margin: '0 auto',
        padding: '0 44px',
        display: 'flex',
      }}>
        {groups.map(g => {
          const isActive = selected === g.key;
          return (
            <button
              key={g.key || 'all'}
              className="cat-tab"
              onClick={() => onSelect(g.key)}
              style={{
                flex: 1,
                padding: '14px 16px',
                background: isActive ? g.color : 'transparent',
                color: isActive ? '#FFFFFF' : '#111827',
                border: 'none',
                borderBottom: isActive ? `3px solid ${g.color}` : '3px solid transparent',
                fontSize: 11,
                fontWeight: 600,
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                cursor: 'pointer',
                transition: 'all 0.25s ease',
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              {g.label}
            </button>
          );
        })}
      </div>

      <style>{`
        .cat-tab:hover {
          opacity: 0.85;
        }
        @media (max-width: 767px) {
          .cat-nav { overflow-x: auto; -webkit-overflow-scrolling: touch; }
          .cat-tab { min-width: 130px; flex: 0 0 auto !important; }
        }
      `}</style>
    </div>
  );
}
