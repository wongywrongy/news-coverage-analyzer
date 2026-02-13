'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/news', label: 'News' },
  { href: '/archive', label: 'Archive' },
  { href: '/methodology', label: 'Methodology' },
];

export default function NavBar() {
  const pathname = usePathname();

  function isActive(href) {
    if (pathname.startsWith('/topic/')) return false;
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  }

  return (
    <nav className="navbar" style={{
      height: 58,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 48px',
      borderBottom: '1px solid var(--border)',
      background: 'rgba(250,250,247,0.9)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <Link href="/" style={{ textDecoration: 'none' }}>
        <div style={{
          fontFamily: "'Playfair Display', serif",
          fontWeight: 800,
          fontSize: 22,
          letterSpacing: '-0.5px',
        }}>
          <span style={{ color: 'var(--ink)' }}>Clear</span>
          <span style={{ color: 'var(--accent-gold)' }}>Signal</span>
        </div>
      </Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
        {NAV_LINKS.map(link => {
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 14,
                fontWeight: active ? 600 : 500,
                color: active ? 'var(--ink)' : 'var(--ink-muted)',
                textDecoration: 'none',
                transition: 'color 0.2s',
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
