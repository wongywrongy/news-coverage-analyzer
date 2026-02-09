'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import ContrastCard from './ContrastCard';
import { getPrimaryCategory, getGroupLabel, getGroupColor, computeActivityDays } from '../lib/constants';

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
      transform: vis ? 'translateY(0)' : 'translateY(10px)',
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
        color: '#6B7280',
        width: 40,
        flexShrink: 0,
      }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 5, background: '#E8E4DA', borderRadius: 3 }}>
        <div style={{
          height: '100%',
          borderRadius: 3,
          background: '#4A6FA5',
          width: `${(value / max) * 100}%`,
          transition: 'width 0.4s ease',
        }} />
      </div>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: '#374151',
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

/** Hover tooltip wrapper — shows content on mouseenter, hides on mouseleave. */
function ScoreTooltip({ children, tooltip }) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef(null);

  const handleEnter = () => {
    clearTimeout(timeoutRef.current);
    setShow(true);
  };
  const handleLeave = () => {
    timeoutRef.current = setTimeout(() => setShow(false), 150);
  };

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
            background: '#FFFFFF',
            border: '1px solid #E8E4DA',
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
            borderRadius: 8,
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

/* ── Factor definitions ── */

const FACTOR_DEFS = [
  { key: 'population_affected', label: 'Pop.', max: 30 },
  { key: 'economic_magnitude', label: 'Econ.', max: 25 },
  { key: 'policy_change', label: 'Policy', max: 20 },
  { key: 'duration', label: 'Dur.', max: 15 },
  { key: 'irreversibility', label: 'Irrev.', max: 10 },
];

/* ── Main component ── */

export default function StoryDetail({ story, analysis, sourceList = [] }) {
  const a = analysis;
  const cat = getPrimaryCategory(story.category);
  const groupLabel = getGroupLabel(story.category);
  const groupColor = getGroupColor(story.category);
  const activityDays = computeActivityDays(story);
  const activeDayCount = activityDays.filter(Boolean).length;
  const spectrumNote = a?.coverage_note || a?.spectrum || '';

  // Parse significance factors
  let factors = null;
  if (story.significance_factors && typeof story.significance_factors === 'object') {
    factors = FACTOR_DEFS.map(def => {
      const f = story.significance_factors[def.key];
      return {
        label: def.label,
        value: f?.score || 0,
        max: def.max,
      };
    });
  }

  // Context paragraphs: split on double newline
  const contextParagraphs = a?.context
    ? a.context.split(/\n\n+/).filter(p => p.trim())
    : [];

  // Compute timeline dates client-side to avoid hydration issues
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const now = mounted ? new Date() : null;
  const windowStart = mounted ? (() => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    d.setDate(d.getDate() - 13);
    return d;
  })() : null;
  const startDateLabel = windowStart
    ? windowStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '';

  // Coverage velocity label
  const velocity = story.coverage_velocity;
  const velocityLabel = velocity != null ? `${velocity} articles/day` : null;

  return (
    <div style={{ background: '#F0ECE2', minHeight: '100vh' }}>
      {/* ── Sticky Header ── */}
      <div className="sd-nav" style={{
        background: '#FFFFFF',
        padding: '14px 44px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #E5E5E5',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <div className="sd-logo" style={{
            fontFamily: "'Source Serif 4', Georgia, serif",
            fontSize: 21,
            fontWeight: 700,
            cursor: 'pointer',
          }}>
            <span style={{ color: '#111827' }}>Clear</span>
            <span style={{ color: '#4A6FA5' }}>Signal</span>
          </div>
        </Link>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <span className="sd-back" style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: '#4A6FA5',
            cursor: 'pointer',
          }}>
            &larr; Back to stories
          </span>
        </Link>
      </div>

      {a ? (
        <>
          {/* ====== WHITE HEADER ZONE ====== */}
          <div style={{ background: '#FFFFFF', borderBottom: '2px solid #3D5F8F' }}>
            <div className="sd-header-inner" style={{ maxWidth: 1100, margin: '0 auto', padding: '48px 44px 36px' }}>

              {/* Category pill */}
              <FadeIn delay={100}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20 }}>
                  <span style={{
                    background: groupColor + '14',
                    border: `1px solid ${groupColor}30`,
                    color: groupColor,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    padding: '3px 10px',
                    fontWeight: 600,
                    letterSpacing: '0.04em',
                  }}>
                    {cat}
                  </span>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12,
                    color: '#6B7280',
                  }}>
                    {groupLabel}
                  </span>
                </div>
              </FadeIn>

              {/* Headline */}
              <FadeIn delay={200}>
                <h1 className="sd-headline" style={{
                  fontFamily: "'Source Serif 4', Georgia, serif",
                  fontSize: 44,
                  fontWeight: 800,
                  color: '#111827',
                  lineHeight: 1.08,
                  letterSpacing: '-0.02em',
                  marginBottom: 18,
                  maxWidth: 820,
                }}>
                  {a.headline}
                </h1>
              </FadeIn>

              {/* Lede */}
              <FadeIn delay={300}>
                <p className="sd-lede" style={{
                  fontFamily: "'Source Serif 4', Georgia, serif",
                  fontSize: 19,
                  color: '#4B5563',
                  lineHeight: 1.65,
                  marginBottom: 24,
                  maxWidth: 780,
                }}>
                  {a.lede}
                </p>
              </FadeIn>

              {/* Sources inline */}
              {sourceList.length > 0 && (
                <FadeIn delay={380}>
                  <div style={{ marginBottom: 32 }}>
                    <div className="sd-sources" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '2px 0' }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11,
                        color: '#9CA3AF',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginRight: 10,
                        fontWeight: 600,
                      }}>
                        Sources
                      </span>
                      {sourceList.map((src, i) => (
                        <span key={i} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, lineHeight: 2 }}>
                          <span style={{ color: '#111827' }}>{src.name}</span>
                          <span style={{ color: '#9CA3AF', fontSize: 11 }}>&thinsp;{src.n}</span>
                          {i < sourceList.length - 1 && (
                            <span style={{ color: '#D0D0D0', margin: '0 6px' }}>&middot;</span>
                          )}
                        </span>
                      ))}
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12,
                        color: '#9CA3AF',
                        marginLeft: 10,
                      }}>
                        &mdash; {story.article_count || 0} articles total
                      </span>
                    </div>
                  </div>
                </FadeIn>
              )}

              {/* Score strip */}
              <FadeIn delay={450} style={{ position: 'relative', zIndex: 10 }}>
                <div style={{ borderTop: '1px solid #E8E4DA', paddingTop: 24 }}>
                  {/* Row: Impact | Coverage | Timeline */}
                  <div className="sd-score-row" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0,
                  }}>
                    {/* Scores pair */}
                    <div className="sd-score-pair" style={{ display: 'flex', alignItems: 'center', gap: 0, flexShrink: 0 }}>
                      {/* Impact — with hover tooltip */}
                      <ScoreTooltip tooltip={
                        factors ? (
                          <div>
                            <div style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 10,
                              color: '#6B7280',
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
                            color: '#9CA3AF',
                          }}>
                            5-factor significance model
                          </div>
                        )
                      }>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginRight: 20 }}>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11,
                            color: '#6B7280',
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                            fontWeight: 600,
                          }}>
                            Impact
                          </span>
                          <span style={{
                            fontFamily: "'Source Serif 4', Georgia, serif",
                            fontSize: 32,
                            fontWeight: 700,
                            color: '#4A6FA5',
                            lineHeight: 1,
                          }}>
                            <Counter target={Math.round(story.impact_score || 0)} />
                          </span>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 9,
                            color: '#B0B0B0',
                            marginLeft: -4,
                          }}>
                            &#9432;
                          </span>
                        </div>
                      </ScoreTooltip>

                      <div className="sd-score-divider" style={{ width: 1, height: 32, background: '#E8E4DA', flexShrink: 0, marginRight: 20 }} />

                      {/* Coverage — with hover tooltip */}
                      <ScoreTooltip tooltip={
                        <div>
                          <div style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10,
                            color: '#6B7280',
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
                            { label: 'Active', value: `${activeDayCount}/14 days` },
                            ...(story.bias_spread != null ? [{ label: 'Bias spread', value: story.bias_spread.toFixed(1) }] : []),
                            { label: 'Status', value: story.status || 'unknown' },
                          ].map((row, i) => (
                            <div key={i} style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '3px 0',
                              borderBottom: i < 5 ? '1px solid #F0EDE6' : 'none',
                            }}>
                              <span style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: 11,
                                color: '#6B7280',
                              }}>
                                {row.label}
                              </span>
                              <span style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: 11,
                                color: '#374151',
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
                            color: '#6B7280',
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                            fontWeight: 600,
                          }}>
                            Coverage
                          </span>
                          <span style={{
                            fontFamily: "'Source Serif 4', Georgia, serif",
                            fontSize: 32,
                            fontWeight: 700,
                            color: '#C8A84E',
                            lineHeight: 1,
                          }}>
                            <Counter target={Math.round(story.coverage_score || story.attention_score || 0)} />
                          </span>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 9,
                            color: '#B0B0B0',
                            marginLeft: -4,
                          }}>
                            &#9432;
                          </span>
                        </div>
                      </ScoreTooltip>
                    </div>

                    <div className="sd-timeline-divider" style={{ width: 1, height: 32, background: '#E8E4DA', flexShrink: 0, marginRight: 24 }} />

                    {/* 14-segment timeline */}
                    <div className="sd-timeline" style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        height: 10,
                        borderRadius: 2,
                        overflow: 'hidden',
                        display: 'flex',
                        background: '#E8E4DA',
                      }}>
                        {activityDays.map((active, i) => (
                          <div key={i} style={{
                            flex: 1,
                            background: active ? '#5578A8' : 'transparent',
                          }} />
                        ))}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#9CA3AF' }}>
                          {startDateLabel}
                        </span>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#9CA3AF' }}>
                          Today &middot; {activeDayCount}/14 active
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </FadeIn>
            </div>
          </div>

          {/* ====== ARTICLE BODY ====== */}
          <div className="sd-body" style={{ maxWidth: 720, margin: '0 auto', padding: '44px 24px 80px' }}>

            {/* ── What sources agree on (facts) ── */}
            {a.facts?.length > 0 && (
              <FadeIn delay={550}>
                <div style={{ marginBottom: 36 }}>
                  <h2 className="sd-section-heading" style={{
                    fontFamily: "'Source Serif 4', Georgia, serif",
                    fontSize: 24,
                    fontWeight: 700,
                    color: '#111827',
                    marginBottom: 8,
                  }}>
                    What sources agree on
                  </h2>
                  <p style={{
                    fontFamily: "'Source Serif 4', Georgia, serif",
                    fontSize: 15,
                    color: '#6B7280',
                    lineHeight: 1.6,
                    marginBottom: 18,
                  }}>
                    Undisputed facts reported across multiple outlets
                  </p>
                  <div className="sd-facts-block" style={{
                    padding: '22px 26px',
                    background: 'rgba(74,111,165,0.03)',
                    borderLeft: '4px solid #4A6FA5',
                    borderTop: '1px solid rgba(74,111,165,0.10)',
                    borderBottom: '1px solid rgba(74,111,165,0.10)',
                    borderRight: '1px solid rgba(74,111,165,0.10)',
                  }}>
                    {a.facts.map((f, i) => {
                      const text = typeof f === 'string' ? f : f.claim;
                      return (
                        <div key={i} style={{
                          display: 'flex',
                          gap: 14,
                          marginBottom: i < a.facts.length - 1 ? 14 : 0,
                          alignItems: 'flex-start',
                        }}>
                          <div style={{
                            width: 6,
                            height: 6,
                            borderRadius: '50%',
                            background: '#4A6FA5',
                            marginTop: 8,
                            flexShrink: 0,
                            opacity: 0.5,
                          }} />
                          <span style={{
                            fontFamily: "'Source Serif 4', Georgia, serif",
                            fontSize: 16,
                            color: '#1F2937',
                            lineHeight: 1.65,
                          }}>
                            {text}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </FadeIn>
            )}

            {a.facts?.length > 0 && <div style={{ height: 1, background: '#DDD7C5', margin: '36px 0' }} />}

            {/* ── Context paragraphs ── */}
            {contextParagraphs.length > 0 && (
              <FadeIn delay={650}>
                {contextParagraphs.map((p, i) => (
                  <p key={i} className="sd-context-p" style={{
                    fontFamily: "'Source Serif 4', Georgia, serif",
                    fontSize: 18,
                    color: '#1F2937',
                    lineHeight: 1.85,
                    marginBottom: 22,
                  }}>
                    {p}
                  </p>
                ))}
              </FadeIn>
            )}

            {contextParagraphs.length > 0 && <div style={{ height: 1, background: '#DDD7C5', margin: '40px 0' }} />}

            {/* ── How coverage differs ── */}
            {a.contrasts?.length > 0 ? (
              <FadeIn delay={750}>
                <div style={{ marginBottom: 44 }}>
                  <h2 className="sd-section-heading" style={{
                    fontFamily: "'Source Serif 4', Georgia, serif",
                    fontSize: 24,
                    fontWeight: 700,
                    color: '#111827',
                    marginBottom: 8,
                  }}>
                    How coverage differs
                  </h2>
                  <p style={{
                    fontFamily: "'Source Serif 4', Georgia, serif",
                    fontSize: 15,
                    color: '#6B7280',
                    lineHeight: 1.6,
                    marginBottom: 28,
                  }}>
                    Where sources diverge in their framing of this story
                  </p>
                  {a.contrasts.map((c, i) => (
                    <ContrastCard key={i} contrast={c} />
                  ))}
                </div>
              </FadeIn>
            ) : (
              <FadeIn delay={750}>
                <div style={{ marginBottom: 44 }}>
                  <div style={{
                    padding: '22px 26px',
                    background: 'rgba(74,111,165,0.03)',
                    borderLeft: '4px solid #4A6FA5',
                    borderTop: '1px solid rgba(74,111,165,0.10)',
                    borderBottom: '1px solid rgba(74,111,165,0.10)',
                    borderRight: '1px solid rgba(74,111,165,0.10)',
                  }}>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: '#4A6FA5',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      marginBottom: 8,
                      fontWeight: 600,
                    }}>
                      Similar framing across sources
                    </div>
                    <p style={{
                      fontFamily: "'Source Serif 4', Georgia, serif",
                      fontSize: 15,
                      color: '#374151',
                      lineHeight: 1.7,
                    }}>
                      Sources covering this story used similar framing. No significant differences in angle were identified.
                    </p>
                  </div>
                </div>
              </FadeIn>
            )}

            <div style={{ height: 1, background: '#DDD7C5', margin: '40px 0' }} />

            {/* ── Bottom line + spectrum ── */}
            <FadeIn delay={850}>
              <div style={{ marginBottom: 44 }}>
                <h2 className="sd-section-heading" style={{
                  fontFamily: "'Source Serif 4', Georgia, serif",
                  fontSize: 24,
                  fontWeight: 700,
                  color: '#111827',
                  marginBottom: 8,
                }}>
                  Bottom line
                </h2>
                <p style={{
                  fontFamily: "'Source Serif 4', Georgia, serif",
                  fontSize: 15,
                  color: '#6B7280',
                  lineHeight: 1.6,
                  marginBottom: 20,
                }}>
                  What is known, what is uncertain, what to watch
                </p>

                <div>
                  {/* Blue block: bottom line */}
                  <div className="sd-bl-block" style={{
                    padding: '24px 28px',
                    background: 'rgba(74,111,165,0.03)',
                    borderLeft: '4px solid #4A6FA5',
                    borderTop: '1px solid rgba(74,111,165,0.10)',
                    borderBottom: '1px solid rgba(74,111,165,0.10)',
                    borderRight: '1px solid rgba(74,111,165,0.10)',
                  }}>
                    <p style={{
                      fontFamily: "'Source Serif 4', Georgia, serif",
                      fontSize: 17,
                      color: '#1F2937',
                      lineHeight: 1.85,
                      fontWeight: 500,
                    }}>
                      {a.bottom_line}
                    </p>
                  </div>

                  {/* Connector dots */}
                  {spectrumNote && (
                    <>
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        padding: '12px 0',
                      }}>
                        <div style={{ width: 1, height: 20, background: '#D0D0D0' }} />
                        <div style={{
                          width: 28,
                          height: 28,
                          borderRadius: '50%',
                          background: '#F0ECE2',
                          border: '2px solid #D0D0D0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 8,
                          fontWeight: 700,
                          color: '#9CA3AF',
                        }}>
                          &middot;&middot;&middot;
                        </div>
                        <div style={{ width: 1, height: 20, background: '#D0D0D0' }} />
                      </div>

                      {/* Gold block: coverage spectrum */}
                      <div className="sd-bl-block" style={{
                        padding: '22px 28px',
                        background: 'rgba(200,168,78,0.03)',
                        borderRight: '4px solid #C8A84E',
                        borderTop: '1px solid rgba(200,168,78,0.10)',
                        borderBottom: '1px solid rgba(200,168,78,0.10)',
                        borderLeft: '1px solid rgba(200,168,78,0.10)',
                      }}>
                        <div style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 10,
                          color: '#A08520',
                          textTransform: 'uppercase',
                          letterSpacing: '0.06em',
                          marginBottom: 10,
                          fontWeight: 600,
                        }}>
                          Coverage spectrum
                        </div>
                        <p style={{
                          fontFamily: "'Source Serif 4', Georgia, serif",
                          fontSize: 15,
                          color: '#374151',
                          lineHeight: 1.75,
                        }}>
                          {spectrumNote}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </FadeIn>

            {/* ── Bottom nav ── */}
            <div style={{
              padding: '22px 0',
              borderTop: '1px solid #DDD7C5',
              display: 'flex',
              justifyContent: 'space-between',
            }}>
              <Link href="/" style={{ textDecoration: 'none' }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  color: '#4A6FA5',
                  cursor: 'pointer',
                }}>
                  &larr; Back to all stories
                </span>
              </Link>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: '#9CA3AF',
              }}>
                ClearSignal &middot; methodology
              </span>
            </div>
          </div>

          {/* ── Footer ── */}
          <div className="sd-footer" style={{
            borderTop: '1px solid #DED8CA',
            padding: '20px 44px',
            display: 'flex',
            justifyContent: 'space-between',
          }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#9CA3AF' }}>
              &copy; 2026 ClearSignal
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#9CA3AF' }}>
              5-factor impact model
            </span>
          </div>
        </>
      ) : (
        /* ── No analysis state ── */
        <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px' }}>
          <h1 style={{
            fontSize: 28,
            fontFamily: "'Source Serif 4', Georgia, serif",
            fontWeight: 600,
            color: '#111827',
            marginBottom: 20,
          }}>
            {story.topic}
          </h1>
          <div style={{
            padding: 32,
            background: '#FAFAFA',
            border: '1px solid #E8E8E8',
            textAlign: 'center',
          }}>
            <p style={{
              fontSize: 14,
              color: '#9CA3AF',
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
