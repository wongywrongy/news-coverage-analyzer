'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';
import ContrastCard from './ContrastCard';
import { getPrimaryCategory, getGroupLabel, getGroupColor, parseTrend } from '../lib/constants';

/* ── Utility components ── */

function FadeIn({ delay = 0, style: extraStyle, children }) {
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVis(true), delay);
    return () => clearTimeout(t);
  }, [delay]);
  return (
    <div style={{
      opacity: vis ? 1 : 0,
      transform: vis ? 'translateY(0)' : 'translateY(16px)',
      transition: 'opacity 0.5s ease, transform 0.5s ease',
      ...extraStyle,
    }}>
      {children}
    </div>
  );
}

function Counter({ target, duration = 1200 }) {
  const [val, setVal] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVal(target);
      return;
    }
    let startTime = null;
    function step(ts) {
      if (!startTime) startTime = ts;
      const p = Math.min((ts - startTime) / duration, 1);
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) ref.current = requestAnimationFrame(step);
    }
    ref.current = requestAnimationFrame(step);
    return () => { if (ref.current) cancelAnimationFrame(ref.current); };
  }, [target, duration]);
  return val;
}

function FactorBar({ label, value, max }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: 'var(--ink-muted)',
        width: 40,
        flexShrink: 0,
      }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 5, background: 'var(--border)', borderRadius: 3 }}>
        <div style={{
          height: '100%',
          borderRadius: 3,
          background: 'var(--accent-blue)',
          width: `${(value / max) * 100}%`,
          transition: 'width 0.4s ease',
        }} />
      </div>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: 'var(--ink)',
        fontWeight: 600,
        width: 32,
        textAlign: 'right',
        flexShrink: 0,
      }}>
        {value}/{max}
      </span>
    </div>
  );
}

function ScoreTooltip({ children, tooltip }) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef(null);

  const handleEnter = () => { clearTimeout(timeoutRef.current); setShow(true); };
  const handleLeave = () => { timeoutRef.current = setTimeout(() => setShow(false), 150); };

  return (
    <div
      style={{ position: 'relative', cursor: 'default', zIndex: show ? 999 : 'auto' }}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      {children}
      {show && (
        <div
          onMouseEnter={handleEnter}
          onMouseLeave={handleLeave}
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginTop: 8,
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-md)',
            borderRadius: 'var(--radius-sm)',
            padding: '14px 16px',
            minWidth: 220,
            zIndex: 9999,
            animation: 'fadeUp 0.2s ease both',
          }}
        >
          {tooltip}
        </div>
      )}
    </div>
  );
}

/* ── Section heading pattern ── */

function SectionHeading({ label, title, subtitle }) {
  return (
    <div style={{ marginBottom: 'var(--space-md)' }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color: 'var(--ink-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        fontWeight: 500,
        marginBottom: 'var(--space-xs)',
      }}>
        {label}
      </div>
      <h2 className="sd-section-heading" style={{
        fontFamily: "'Playfair Display', serif",
        fontSize: 26,
        fontWeight: 800,
        color: 'var(--ink)',
        marginBottom: subtitle ? 6 : 0,
      }}>
        {title}
      </h2>
      {subtitle && (
        <p style={{
          fontSize: 14,
          color: 'var(--ink-muted)',
          lineHeight: 1.5,
        }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

/* ── Factor definitions ── */

const FACTOR_DEFS = [
  { key: 'population_affected', label: 'Pop.', max: 30 },
  { key: 'economic_magnitude', label: 'Econ.', max: 25 },
  { key: 'policy_change', label: 'Policy', max: 20 },
  { key: 'duration', label: 'Dur.', max: 15 },
  { key: 'irreversibility', label: 'Irrev.', max: 10 },
];

/* ── Spectrum bar config ── */

const SPECTRUM_GROUPS = [
  { key: 'left', labels: ['far-left', 'left'], color: '#2B4C7E', name: 'Left' },
  { key: 'left-center', labels: ['left-center'], color: '#5B8CB5', name: 'Left-Center' },
  { key: 'center', labels: ['center'], color: '#9A9A9A', name: 'Center' },
  { key: 'right-center', labels: ['right-center'], color: '#D4A853', name: 'Right-Center' },
  { key: 'right', labels: ['right', 'far-right'], color: '#C0392B', name: 'Right' },
];

/* ── Main component ── */

export default function StoryDetail({ story, analysis, sourceList = [], biasCounts = {} }) {
  const a = analysis;
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);

  // Parse significance factors
  let factors = null;
  if (story.significance_factors && typeof story.significance_factors === 'object') {
    factors = FACTOR_DEFS.map(def => {
      const f = story.significance_factors[def.key];
      return { label: def.label, value: f?.score || 0, max: def.max };
    });
  }

  // Context paragraphs
  const contextParagraphs = a?.context
    ? a.context.split(/\n\n+/).filter(p => p.trim())
    : [];

  // Timeline from trend data
  const trendData = useMemo(() => {
    const raw = parseTrend(story);
    return raw.slice(-14);
  }, [story]);

  const startDateLabel = trendData.length > 0 ? trendData[0].date : '';
  const activeDayCount = trendData.filter(d => (d.count || 0) > 0).length;

  function barHeight(count) {
    if (!count || count === 0) return 6;
    if (count <= 4) return 12;
    return 22;
  }

  // Coverage velocity label
  const velocity = story.coverage_velocity;
  const velocityLabel = velocity != null ? `${velocity} articles/day` : null;

  // Spectrum segments
  const spectrumSegments = useMemo(() => {
    const total = Object.values(biasCounts).reduce((s, n) => s + n, 0);
    if (total === 0) return [];
    return SPECTRUM_GROUPS
      .map(g => {
        const count = g.labels.reduce((s, l) => s + (biasCounts[l] || 0), 0);
        return { ...g, count, pct: (count / total) * 100 };
      })
      .filter(s => s.count > 0);
  }, [biasCounts]);

  // Source framings
  const sourceFramings = a?.source_framings || [];
  const spectrumNote = a?.spectrum || '';
  const coverageNote = a?.coverage_note || '';

  // Footer date
  const lastUpdated = a?.generated_at || story.last_updated || story.created_at;
  const formattedDate = lastUpdated
    ? new Date(lastUpdated).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '';

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      {/* ── Sticky Nav ── */}
      <div className="sd-nav" style={{
        background: 'rgba(250,250,247,0.9)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        padding: '14px 48px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid var(--border)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <div className="sd-logo" style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 21,
            fontWeight: 700,
            cursor: 'pointer',
          }}>
            <span style={{ color: 'var(--ink)' }}>Clear</span>
            <span style={{ color: 'var(--accent-gold)' }}>Signal</span>
          </div>
        </Link>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <span className="sd-back" style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: 'var(--ink-muted)',
            cursor: 'pointer',
          }}>
            &larr; Back to topics
          </span>
        </Link>
      </div>

      {a ? (
        <div className="sd-body" style={{
          maxWidth: 'var(--content-width)',
          margin: '0 auto',
          padding: 'var(--space-xl) var(--space-md) 0',
        }}>

          {/* ── Article Header ── */}
          <FadeIn delay={0}>
            {/* Category badge */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
              <span style={{
                background: groupColor + '14',
                border: `1px solid ${groupColor}30`,
                color: groupColor,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                padding: '3px 10px',
                fontWeight: 600,
                letterSpacing: '0.04em',
                borderRadius: 4,
              }}>
                {groupLabel}
              </span>
            </div>

            {/* Headline */}
            <h1 className="sd-headline" style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 42,
              fontWeight: 900,
              color: 'var(--ink)',
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              marginBottom: 'var(--space-sm)',
            }}>
              {a.headline || story.topic}
            </h1>

            {/* Lede */}
            {a.lede && (
              <p className="sd-lede" style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 18,
                color: 'var(--ink-secondary)',
                lineHeight: 1.7,
                marginBottom: 'var(--space-md)',
              }}>
                {a.lede}
              </p>
            )}

            {/* Sources row */}
            {sourceList.length > 0 && (
              <div className="sd-sources" style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: 'var(--space-xs)',
                marginBottom: 'var(--space-lg)',
              }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: 'var(--ink-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  fontWeight: 600,
                  marginRight: 4,
                }}>
                  Sources
                </span>
                {sourceList.map((src, i) => (
                  <span key={i} style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12,
                    background: 'var(--warm-bg)',
                    padding: '4px 10px',
                    borderRadius: 4,
                    color: 'var(--ink-secondary)',
                  }}>
                    {src.name}
                    <span style={{ color: 'var(--ink-muted)', fontSize: 11, marginLeft: 4 }}>{src.n}</span>
                  </span>
                ))}
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  color: 'var(--ink-muted)',
                  marginLeft: 4,
                }}>
                  &mdash; {story.article_count || 0} articles total
                </span>
              </div>
            )}
          </FadeIn>

          {/* ── Scores + Timeline ── */}
          <FadeIn delay={100} style={{ position: 'relative', zIndex: 10 }}>
            <div style={{
              borderTop: '1px solid var(--border)',
              borderBottom: '1px solid var(--border)',
              padding: 'var(--space-md) 0',
              marginBottom: 'var(--space-section)',
            }}>
              <div className="sd-score-row" style={{
                display: 'flex',
                alignItems: 'center',
                gap: 0,
              }}>
                {/* Scores pair */}
                <div className="sd-score-pair" style={{ display: 'flex', alignItems: 'center', gap: 0, flexShrink: 0 }}>
                  {/* Impact */}
                  <ScoreTooltip tooltip={
                    factors ? (
                      <div>
                        <div style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 10,
                          color: 'var(--ink-muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                          marginBottom: 10,
                          fontWeight: 600,
                        }}>
                          Impact factors
                        </div>
                        {factors.map(f => (
                          <FactorBar key={f.label} label={f.label} value={f.value} max={f.max} />
                        ))}
                      </div>
                    ) : (
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11,
                        color: 'var(--ink-muted)',
                      }}>
                        5-factor significance model
                      </div>
                    )
                  }>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginRight: 20 }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11,
                        color: 'var(--ink-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        fontWeight: 600,
                      }}>
                        Impact
                      </span>
                      <span style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: 28,
                        fontWeight: 800,
                        color: '#6B6B6B',
                        lineHeight: 1,
                      }}>
                        <Counter target={Math.round(story.impact_score || 0)} />
                      </span>
                    </div>
                  </ScoreTooltip>

                  <div className="sd-score-divider" style={{ width: 1, height: 32, background: 'var(--border)', flexShrink: 0, marginRight: 20 }} />

                  {/* Coverage */}
                  <ScoreTooltip tooltip={
                    <div>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10,
                        color: 'var(--ink-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        marginBottom: 10,
                        fontWeight: 600,
                      }}>
                        Coverage breakdown
                      </div>
                      {[
                        { label: 'Articles', value: story.article_count || 0 },
                        { label: 'Sources', value: story.source_count || 0 },
                        ...(velocityLabel ? [{ label: 'Velocity', value: velocityLabel }] : []),
                        { label: 'Active', value: `${activeDayCount}/${trendData.length || 14} days` },
                        ...(story.bias_spread != null ? [{ label: 'Bias spread', value: story.bias_spread.toFixed(1) }] : []),
                        { label: 'Status', value: story.status || 'unknown' },
                      ].map((row, i) => (
                        <div key={i} style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '3px 0',
                          borderBottom: i < 5 ? '1px solid var(--border)' : 'none',
                        }}>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11,
                            color: 'var(--ink-muted)',
                          }}>
                            {row.label}
                          </span>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11,
                            color: 'var(--ink)',
                            fontWeight: 600,
                          }}>
                            {row.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  }>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginRight: 24 }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11,
                        color: 'var(--ink-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        fontWeight: 600,
                      }}>
                        Coverage
                      </span>
                      <span style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: 28,
                        fontWeight: 800,
                        color: '#6B6B6B',
                        lineHeight: 1,
                      }}>
                        <Counter target={Math.round(story.coverage_score || story.attention_score || 0)} />
                      </span>
                    </div>
                  </ScoreTooltip>
                </div>

                <div className="sd-timeline-divider" style={{ width: 1, height: 32, background: 'var(--border)', flexShrink: 0, marginRight: 24 }} />

                {/* Variable-height timeline */}
                <div className="sd-timeline" style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    height: 22,
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: 2,
                  }}>
                    {trendData.length > 0 ? trendData.map((d, i) => {
                      const count = d.count || 0;
                      const h = barHeight(count);
                      const bg = count === 0
                        ? 'var(--border)'
                        : count >= 5
                          ? 'var(--accent-blue-deep)'
                          : 'var(--accent-blue)';
                      return (
                        <div key={i} style={{
                          flex: 1,
                          height: h,
                          background: bg,
                          borderRadius: 2,
                          transition: 'height 0.3s ease',
                        }} />
                      );
                    }) : (
                      // Fallback: 14 empty bars
                      Array.from({ length: 14 }).map((_, i) => (
                        <div key={i} style={{
                          flex: 1,
                          height: 6,
                          background: 'var(--border)',
                          borderRadius: 2,
                        }} />
                      ))
                    )}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: 'var(--ink-muted)' }}>
                      {startDateLabel}
                    </span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: 'var(--ink-muted)' }}>
                      Today &middot; {activeDayCount}/{trendData.length || 14} active
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>

          {/* ── Consensus: What sources agree on ── */}
          {a.facts?.length > 0 && (
            <FadeIn delay={150}>
              <SectionHeading
                label="Consensus"
                title="What is known"
              />
              <div style={{ marginBottom: 'var(--space-section)' }}>
                {a.facts.map((f, i) => {
                  const text = typeof f === 'string' ? f : f.claim;
                  return (
                    <div key={i} style={{
                      display: 'flex',
                      gap: 14,
                      alignItems: 'flex-start',
                      padding: '14px 0',
                      borderBottom: i < a.facts.length - 1 ? '1px solid #f0eeea' : 'none',
                    }}>
                      {/* Green checkmark circle */}
                      <div style={{
                        width: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: 'var(--accent-green)',
                        flexShrink: 0,
                        marginTop: 2,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                          <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <span style={{
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: 15,
                        color: 'var(--ink)',
                        lineHeight: 1.6,
                      }}>
                        {text}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div style={{ height: 1, background: 'var(--border)', margin: `var(--space-section) 0` }} />
            </FadeIn>
          )}

          {/* ── Context: Background ── */}
          {contextParagraphs.length > 0 && (
            <FadeIn delay={200}>
              <SectionHeading
                label="Background"
                title="Context"
              />
              <div style={{ marginBottom: 'var(--space-section)' }}>
                {contextParagraphs.map((p, i) => (
                  <p key={i} className="sd-context-p" style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontSize: 16,
                    color: 'var(--ink-secondary)',
                    lineHeight: 1.8,
                    marginBottom: 'var(--space-sm)',
                  }}>
                    {p}
                  </p>
                ))}
              </div>
              <div style={{ height: 1, background: 'var(--border)', margin: `var(--space-section) 0` }} />
            </FadeIn>
          )}

          {/* ── Framing Analysis: Where sources diverge ── */}
          <FadeIn delay={250}>
            <SectionHeading
              label="Framing Analysis"
              title="Where sources diverge"
              subtitle="How different outlets frame the same facts"
            />
            {a.contrasts?.length > 0 ? (
              <div style={{ marginBottom: 'var(--space-section)' }}>
                {a.contrasts.map((c, i) => (
                  <ContrastCard key={i} contrast={c} />
                ))}
              </div>
            ) : (
              <div style={{
                padding: 'var(--space-md)',
                background: 'var(--warm-bg)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: 'var(--space-section)',
              }}>
                <p style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 15,
                  color: 'var(--ink-secondary)',
                  lineHeight: 1.6,
                }}>
                  All sources framed this topic similarly. No significant differences in angle or emphasis were identified.
                </p>
              </div>
            )}
            <div style={{ height: 1, background: 'var(--border)', margin: `var(--space-section) 0` }} />
          </FadeIn>

          {/* ── Bottom Line ── */}
          {a.bottom_line && (
            <FadeIn delay={300}>
              <SectionHeading
                label="Summary"
                title="Bottom line"
                subtitle="What is known, what is uncertain, what to watch"
              />
              <div style={{ marginBottom: 'var(--space-section)' }}>
                <p className="sd-context-p" style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 16,
                  color: 'var(--ink-secondary)',
                  lineHeight: 1.8,
                }}>
                  {a.bottom_line}
                </p>
              </div>
              <div style={{ height: 1, background: 'var(--border)', margin: `var(--space-section) 0` }} />
            </FadeIn>
          )}

          {/* ── Source Breakdown ── */}
          <FadeIn delay={350}>
            <SectionHeading
              label="Coverage Overview"
              title="Source breakdown"
              subtitle="How coverage is distributed across the spectrum"
            />

            {/* Spectrum bar */}
            {spectrumSegments.length > 0 && (
              <div style={{ marginBottom: 'var(--space-md)' }}>
                <div style={{
                  height: 8,
                  borderRadius: 4,
                  overflow: 'hidden',
                  display: 'flex',
                }}>
                  {spectrumSegments.map(seg => (
                    <div key={seg.key} style={{
                      width: `${seg.pct}%`,
                      background: seg.color,
                      minWidth: 4,
                    }} />
                  ))}
                </div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: 6,
                }}>
                  {spectrumSegments.map(seg => (
                    <div key={seg.key} style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: 'var(--ink-muted)',
                      textAlign: 'center',
                      width: `${seg.pct}%`,
                      minWidth: 40,
                    }}>
                      {seg.name}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Spectrum note */}
            {(spectrumNote || coverageNote) && (
              <p style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 14,
                color: 'var(--ink-secondary)',
                lineHeight: 1.6,
                marginBottom: 'var(--space-lg)',
              }}>
                {spectrumNote || coverageNote}
              </p>
            )}

            {/* Per-source framing table */}
            {sourceFramings.length > 0 && (
              <div className="sd-framing-table-wrap" style={{ marginBottom: 'var(--space-section)' }}>
              <div className="sd-framing-table" style={{
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
              }}>
                {/* Table header */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '160px 140px 1fr 1fr',
                  gap: 'var(--space-sm)',
                  padding: '12px var(--space-sm)',
                  background: 'var(--warm-bg)',
                  borderBottom: '1px solid var(--border)',
                }}>
                  {['Source', 'Primary Framing', 'Notable Inclusions', 'Notable Omissions'].map(h => (
                    <div key={h} style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      fontWeight: 600,
                      color: 'var(--ink-muted)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                    }}>
                      {h}
                    </div>
                  ))}
                </div>
                {/* Table rows */}
                {sourceFramings.map((sf, i) => (
                  <div key={i} style={{
                    display: 'grid',
                    gridTemplateColumns: '160px 140px 1fr 1fr',
                    gap: 'var(--space-sm)',
                    padding: '12px var(--space-sm)',
                    borderBottom: i < sourceFramings.length - 1 ? '1px solid var(--border)' : 'none',
                    alignItems: 'start',
                  }}>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                      color: 'var(--ink)',
                      fontWeight: 500,
                    }}>
                      {sf.source}
                    </div>
                    <div>
                      {sf.primary_framing && (
                        <span style={{
                          display: 'inline-block',
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 11,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: 'var(--accent-blue)' + '14',
                          color: 'var(--accent-blue)',
                          fontWeight: 500,
                        }}>
                          {sf.primary_framing}
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: 13,
                      color: 'var(--ink-secondary)',
                      lineHeight: 1.5,
                    }}>
                      {sf.notable_inclusions || '\u2014'}
                    </div>
                    <div style={{
                      fontSize: 13,
                      color: 'var(--ink-secondary)',
                      lineHeight: 1.5,
                    }}>
                      {sf.notable_omissions || '\u2014'}
                    </div>
                  </div>
                ))}
              </div>
              </div>
            )}
          </FadeIn>

          {/* ── Footer ── */}
          <div className="sd-footer" style={{
            borderTop: '1px solid var(--border)',
            padding: 'var(--space-lg) 0 var(--space-xl)',
            textAlign: 'center',
          }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              color: 'var(--ink-muted)',
            }}>
              Analysis generated by ClearSignal &middot; Data from {sourceList.length} sources
              {formattedDate && <> &middot; Last updated {formattedDate}</>}
            </span>
          </div>
        </div>
      ) : (
        /* ── No analysis state ── */
        <div style={{
          maxWidth: 'var(--content-width)',
          margin: '0 auto',
          padding: 'var(--space-xl) var(--space-md)',
        }}>
          <h1 style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 28,
            fontWeight: 800,
            color: 'var(--ink)',
            marginBottom: 'var(--space-md)',
          }}>
            {story.topic}
          </h1>
          <div style={{
            padding: 'var(--space-lg)',
            background: 'var(--warm-bg)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
          }}>
            <p style={{
              fontSize: 14,
              color: 'var(--ink-muted)',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              Analysis not yet generated.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
