'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const STAGES = [
  { name: 'Ingest', key: true },
  { name: 'Embed' },
  { name: 'Cluster', key: true },
  { name: 'Validate' },
  { name: 'Label' },
  { name: 'Select' },
  { name: 'Scrape' },
  { name: 'Score', key: true },
  { name: 'Analyze', final: true },
];

const PRINCIPLES = [
  {
    num: '01',
    title: 'Source-Blind Framing',
    desc: 'Contrasts attributed to specific outlets. No \u201Cliberal take\u201D or \u201Cconservative view\u201D \u2014 just who reported what.',
  },
  {
    num: '02',
    title: 'Coverage Gap Detection',
    desc: 'Every story checked for who\u2019s not covering it. Silence is surfaced as data, not overlooked.',
  },
  {
    num: '03',
    title: 'Multi-Model Architecture',
    desc: 'Fast models for volume. Powerful models for nuance. Deterministic formulas for ranking. No single point of failure.',
  },
];

export default function MethodologyTeaser() {
  const [visible, setVisible] = useState(false);
  const sectionRef = useRef(null);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="hp-meth" style={{
      background: 'linear-gradient(175deg, #1B3155, #11213A)',
      padding: '80px 48px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Gold glow top-right */}
      <div style={{
        position: 'absolute', top: '-20%', right: '-5%',
        width: 500, height: 500,
        background: 'radial-gradient(circle, rgba(200,150,62,0.04) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        maxWidth: 1080,
        margin: '0 auto',
        position: 'relative',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(20px)',
        transition: 'opacity 0.6s ease, transform 0.6s ease',
      }}>
        {/* Top row */}
        <div className="meth-teaser-top" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 56,
          gap: 32,
        }}>
          <div style={{ maxWidth: 560 }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '2px',
              color: '#C8963E',
              display: 'block',
              marginBottom: 12,
            }}>
              METHODOLOGY
            </span>
            <h2 style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 32,
              color: '#fff',
              lineHeight: 1.2,
              marginBottom: 12,
            }}>
              From raw feeds to structured clarity
            </h2>
            <p style={{
              fontSize: 15,
              lineHeight: 1.65,
              color: 'rgba(255,255,255,0.5)',
            }}>
              Four pipelines. Six AI models. Twenty-seven stages. Zero editorial bias.
              Here&rsquo;s how 100+ sources become signal.
            </p>
          </div>

          <Link href="/methodology" style={{
            padding: '12px 24px',
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 6,
            color: 'rgba(255,255,255,0.7)',
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "'DM Sans', sans-serif",
            textDecoration: 'none',
            whiteSpace: 'nowrap',
            flexShrink: 0,
            transition: 'all 0.2s',
          }}>
            See the full pipeline &rarr;
          </Link>
        </div>

        {/* Pipeline track */}
        <div className="pipeline-track" style={{
          position: 'relative',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          padding: '0 8px',
          marginBottom: 56,
        }}>
          {/* Rail line */}
          <div className="pipeline-rail" style={{
            position: 'absolute',
            top: 24,
            left: 32,
            right: 32,
            height: 2,
            background: 'linear-gradient(90deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.15) 40%, #C8963E 100%)',
            borderRadius: 1,
          }} />

          {STAGES.map((stage, i) => {
            const isFinal = !!stage.final;
            const isKey = !!stage.key;
            let bg, borderColor, textColor, labelColor;
            if (isFinal) {
              bg = '#C8963E';
              borderColor = '#C8963E';
              textColor = '#fff';
              labelColor = '#C8963E';
            } else if (isKey) {
              bg = 'rgba(255,255,255,0.08)';
              borderColor = 'rgba(255,255,255,0.25)';
              textColor = '#fff';
              labelColor = '#fff';
            } else {
              bg = '#11213A';
              borderColor = 'rgba(255,255,255,0.1)';
              textColor = 'rgba(255,255,255,0.4)';
              labelColor = 'rgba(255,255,255,0.4)';
            }

            return (
              <div key={stage.name} className="pipeline-node" style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                position: 'relative',
                zIndex: 1,
              }}>
                <div className="pipeline-circle" style={{
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  background: bg,
                  border: `1.5px solid ${borderColor}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 10,
                  boxShadow: isFinal ? '0 0 20px rgba(200,150,62,0.2)' : 'none',
                  transition: 'transform 0.2s, border-color 0.2s',
                  cursor: 'default',
                }}>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    fontWeight: 600,
                    color: textColor,
                  }}>
                    {String(i + 1).padStart(2, '0')}
                  </span>
                </div>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: labelColor,
                  textAlign: 'center',
                }}>
                  {stage.name}
                </span>
              </div>
            );
          })}
        </div>

        {/* Principle cards */}
        <div className="principle-cards" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
        }}>
          {PRINCIPLES.map(p => (
            <div key={p.num} style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8,
              padding: 24,
            }}>
              <div style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 24,
                fontWeight: 800,
                color: 'rgba(200,150,62,0.5)',
                marginBottom: 8,
              }}>
                {p.num}
              </div>
              <div style={{
                fontSize: 15,
                fontWeight: 700,
                color: '#fff',
                marginBottom: 8,
              }}>
                {p.title}
              </div>
              <div style={{
                fontSize: 13,
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.45)',
              }}>
                {p.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
