'use client';

import { useState, useEffect, useRef } from 'react';

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

function formatNumber(n) {
  // Avoid toLocaleString hydration mismatch between Node.js and browser
  if (typeof n !== 'number') return String(n);
  const s = String(Math.abs(n));
  const parts = [];
  for (let i = s.length; i > 0; i -= 3) {
    parts.unshift(s.slice(Math.max(0, i - 3), i));
  }
  return (n < 0 ? '-' : '') + parts.join(',');
}

export default function AnimatedCounter({ target, duration = 1800, delay = 0, suffix = '', style = {} }) {
  const [value, setValue] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setValue(target);
      return;
    }

    const numTarget = typeof target === 'number' ? target : parseInt(target, 10);
    if (isNaN(numTarget)) {
      setValue(target);
      return;
    }

    const timer = setTimeout(() => {
      const startTime = performance.now();
      const animate = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutCubic(progress);
        setValue(Math.round(easedProgress * numTarget));
        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        }
      };
      rafRef.current = requestAnimationFrame(animate);
    }, delay);

    return () => {
      clearTimeout(timer);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration, delay]);

  const display = typeof target === 'number'
    ? formatNumber(value) + suffix
    : String(target);

  return <span style={style}>{display}</span>;
}
