'use client';

import { useState, useEffect, useRef } from 'react';

export default function TypewriterText({ text, delay = 0, speed = 50, style = {}, onComplete }) {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);
  const [started, setStarted] = useState(false);
  const prefersReduced = useRef(false);

  useEffect(() => {
    prefersReduced.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced.current) {
      setDisplayed(text);
      setDone(true);
      setStarted(true);
      onComplete?.();
      return;
    }

    const startTimer = setTimeout(() => {
      setStarted(true);
      let i = 0;
      const interval = setInterval(() => {
        i++;
        setDisplayed(text.slice(0, i));
        if (i >= text.length) {
          clearInterval(interval);
          setDone(true);
          onComplete?.();
        }
      }, speed);
      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(startTimer);
  }, [text, delay, speed, onComplete]);

  if (!started) {
    return <span style={{ ...style, visibility: 'hidden' }}>{text}</span>;
  }

  return (
    <span style={style}>
      {displayed}
      {!done && (
        <span
          style={{
            display: 'inline-block',
            width: 2,
            height: '0.85em',
            background: '#111827',
            marginLeft: 2,
            verticalAlign: 'text-bottom',
            animation: 'cursorBlink 0.8s step-end infinite',
          }}
        />
      )}
    </span>
  );
}
