'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

/* ── Utility: FadeIn on scroll ── */

function FadeIn({ children, style: extraStyle }) {
  const ref = useRef(null);
  const [vis, setVis] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVis(true); obs.disconnect(); } },
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{
        opacity: vis ? 1 : 0,
        transform: vis ? 'translateY(0)' : 'translateY(20px)',
        transition: 'opacity 0.55s ease, transform 0.55s ease',
        ...extraStyle,
      }}
    >
      {children}
    </div>
  );
}

/* ── Shared visual label style ── */

const vizLabel = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 10,
  color: 'var(--ink-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  fontWeight: 600,
  marginBottom: 12,
};

/* ── Shared warm container ── */

const warmBox = {
  background: 'var(--warm-bg)',
  borderRadius: 'var(--radius)',
  padding: 'var(--space-md)',
};

/* ── Stage data ── */

const STAGES = [
  {
    id: 'ingest',
    num: '01',
    title: 'Ingest',
    body: `Every cycle starts by pulling from 100+ news sources — wire services like Reuters and AP, major outlets like CNN and Fox News, and publications across the political spectrum. Each URL is deduplicated and cleaned so the same article is never counted twice, regardless of how many feeds carry it.`,
  },
  {
    id: 'embed',
    num: '02',
    title: 'Embed',
    body: `Each article becomes a 384-dimensional vector — a mathematical fingerprint of its meaning. Articles about the same event naturally land near each other in this vector space, regardless of how the headline spins it. An embedding model processes articles in batches, with a local model as fallback if the API is ever unreachable.`,
  },
  {
    id: 'cluster',
    num: '03',
    title: 'Cluster',
    body: `Instead of relying on keywords or categories, ClearSignal groups articles by semantic similarity — how close their meaning vectors are in 384-dimensional space. Articles from Fox News, NPR, and Reuters about the same event cluster together, even when their headlines tell completely different stories. Articles that don't fit any group are held back and retried as more coverage arrives.`,
  },
  {
    id: 'label',
    num: '04',
    title: 'Label',
    body: `Each cluster of articles needs a single, neutral name. A language model reads every headline in the group and generates a wire-service-style label — factual, 3–8 words, no editorial spin. The prompt explicitly instructs: describe what happened, not how to feel about it.`,
    promptQuote: `"Generate a neutral, wire-service-style topic label. No articles (a/an/the). 3-8 words. Describe the event, not the reaction."`,
  },
  {
    id: 'score',
    num: '05',
    title: 'Score',
    body: `Not every story matters equally. A language model evaluates each topic against a 5-factor significance model, scoring real-world impact out of 100. The factors are deliberately weighted to prioritize things that affect people's lives over things that generate clicks.`,
    promptQuote: `"Do not score based on how interesting or clickable a story is. Score based on real-world impact."`,
    factors: [
      { label: 'Pop. Affected', value: 21, max: 30 },
      { label: 'Econ. Magnitude', value: 18, max: 25 },
      { label: 'Policy Change', value: 20, max: 20 },
      { label: 'Duration', value: 8, max: 15 },
      { label: 'Irreversibility', value: 4, max: 10 },
    ],
  },
  {
    id: 'select',
    num: '06',
    title: 'Select',
    body: `Not every story needs deep analysis on every cycle. A fast, lightweight model triages all scored topics and picks the 8 most important for full analysis — flagging new stories for first-time analysis and evolving stories for re-analysis. Everything else is skipped until the next run.`,
  },
  {
    id: 'scrape',
    num: '07',
    title: 'Scrape',
    body: `RSS feeds only provide headlines and snippets. For real analysis, we need the full article. A content extractor pulls the body text from each URL, stripping away ads, navigation, and boilerplate. Paywalled sites are detected and skipped gracefully. Requests are throttled to one per second to respect publishers. The result: roughly 300 words of clean text per article.`,
    paywalled: ['WSJ', 'Bloomberg', 'FT', 'NYT (some)'],
  },
  {
    id: 'frame',
    num: '08',
    title: 'Frame',
    body: `This is the stage that defines ClearSignal. A language model reads each article's full text and classifies how the journalist frames the story — accountability reporting, economic impact, human interest, conflict, policy analysis, crisis framing, or neutral wire copy.`,
    callout: 'The model sees only the text. It never receives the source name, the outlet\'s political lean, or any bias label. Framing is determined purely from language.',
    framingCategories: ['Accountability', 'Economic', 'Human Interest', 'Conflict', 'Policy', 'Crisis/Alarm', 'Neutral/Wire'],
  },
  {
    id: 'analyze',
    num: '09',
    title: 'Analyze',
    body: `The final stage brings everything together. A more capable language model receives a diversity-weighted selection of articles — one from each perspective across the political spectrum, so no single viewpoint dominates. The model is instructed to attribute every claim, distinguish verified facts from editorial assertions, and note what sources omit.`,
    promptQuote: `"You are a media analysis engine. Attribute every claim. Distinguish verified facts from editorial assertions. Note what sources omit."`,
  },
];

/* ── FactorBar ── */

function FactorBar({ label, value, max }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color: 'var(--ink-muted)',
        width: 110,
        flexShrink: 0,
      }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 3 }}>
        <div style={{
          height: '100%',
          borderRadius: 3,
          background: 'var(--accent-blue)',
          width: `${(value / max) * 100}%`,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color: 'var(--ink)',
        fontWeight: 600,
        width: 40,
        textAlign: 'right',
        flexShrink: 0,
      }}>
        {value}/{max}
      </span>
    </div>
  );
}

/* ── Main component ── */

export default function HowItWorks() {
  const stageRefs = useRef([]);

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      {/* ── Sticky Nav ── */}
      <div className="hiw-nav" style={{
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
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 21,
            fontWeight: 700,
            cursor: 'pointer',
          }}>
            <span style={{ color: 'var(--ink)' }}>Clear</span>
            <span style={{ color: 'var(--accent-gold)' }}>Signal</span>
          </div>
        </Link>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          color: 'var(--ink-muted)',
        }}>
          Methodology
        </span>
      </div>


      {/* ── Hero ── */}
      <section style={{
        maxWidth: 960,
        margin: '0 auto',
        padding: '80px 48px 60px',
        textAlign: 'center',
      }}>
        <FadeIn>
          <h1 className="hiw-hero-title" style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 900,
            fontSize: 48,
            lineHeight: 1.1,
            letterSpacing: '-1px',
            marginBottom: 20,
            color: 'var(--ink)',
          }}>
            From{' '}
            <em style={{
              fontStyle: 'normal',
              background: 'linear-gradient(135deg, var(--accent-gold), #D4A853)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              100+ feeds
            </em>
            {' '}to one clear picture
          </h1>
          <p style={{
            fontFamily: "'DM Sans', sans-serif",
            fontSize: 17,
            lineHeight: 1.7,
            color: 'var(--ink-secondary)',
            maxWidth: 620,
            margin: '0 auto 48px',
          }}>
            Every topic on ClearSignal passes through a 9-stage AI pipeline &mdash;
            analyzed by multiple language models, scored for real-world impact,
            and checked for framing bias before you ever see it.
          </p>
        </FadeIn>

        {/* 3-column flow */}
        <FadeIn>
          <div className="hiw-flow" style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr auto 1fr',
            gap: 0,
            alignItems: 'center',
            maxWidth: 780,
            margin: '0 auto 32px',
          }}>
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '28px 24px',
              textAlign: 'center',
            }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: 'var(--ink)', marginBottom: 8 }}>
                100+ Sources
              </div>
              <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14, color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
                RSS feeds from across the political spectrum
              </div>
            </div>
            <div className="hiw-flow-arrow" style={{ padding: '0 12px', color: 'var(--ink-muted)', fontSize: 20, flexShrink: 0 }}>&rarr;</div>
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '28px 24px',
              textAlign: 'center',
            }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: 'var(--ink)', marginBottom: 8 }}>
                AI Pipeline
              </div>
              <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14, color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
                9 stages of LLM-powered processing
              </div>
            </div>
            <div className="hiw-flow-arrow" style={{ padding: '0 12px', color: 'var(--ink-muted)', fontSize: 20, flexShrink: 0 }}>&rarr;</div>
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '28px 24px',
              textAlign: 'center',
            }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: 'var(--ink)', marginBottom: 8 }}>
                Your Analysis
              </div>
              <div style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14, color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
                Framing contrasts, agreed facts, and a clear bottom line
              </div>
            </div>
          </div>
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: 'var(--ink-muted)',
            letterSpacing: '0.02em',
          }}>
            Framing is classified from language, not source identity
          </p>
        </FadeIn>
      </section>

      <div style={{ maxWidth: 'var(--content-width)', margin: '0 auto', height: 1, background: 'var(--border)' }} />

      {/* ── 9 Stage Sections ── */}
      <div style={{ maxWidth: 'var(--content-width)', margin: '0 auto', padding: '0 24px' }}>
        {STAGES.map((stage, idx) => (
          <section
            key={stage.id}
            ref={el => { stageRefs.current[idx] = el; }}
            style={{
              paddingTop: 'var(--space-section)',
              paddingBottom: 'var(--space-section)',
              borderBottom: idx < STAGES.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <FadeIn>
              {/* Stage label */}
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: 'var(--ink-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                fontWeight: 500,
                marginBottom: 'var(--space-xs)',
              }}>
                STAGE {stage.num}
              </div>

              {/* Title (no badge) */}
              <h2 style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 28,
                fontWeight: 800,
                color: 'var(--ink)',
                marginBottom: 'var(--space-sm)',
              }}>
                {stage.title}
              </h2>

              {/* Body */}
              <p style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 16,
                lineHeight: 1.8,
                color: 'var(--ink-secondary)',
                marginBottom: 'var(--space-md)',
              }}>
                {stage.body}
              </p>

              {/* ── Stage 01: Ingest — Grouped sources ── */}
              {stage.id === 'ingest' && (
                <div style={warmBox}>
                  <div style={vizLabel}>Sources Monitored</div>
                  {[
                    { group: 'Wire Services', sources: ['Reuters', 'AP News'] },
                    { group: 'Major Outlets', sources: ['CNN', 'Fox News', 'NPR', 'BBC'] },
                    { group: 'Print & Digital', sources: ['WSJ', 'Bloomberg', 'Politico', 'The Guardian', 'Forbes'] },
                  ].map((row, ri) => (
                    <div key={ri} style={{ marginBottom: 12 }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 9,
                        color: 'var(--ink-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 6,
                      }}>
                        {row.group}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {row.sources.map((s, si) => (
                          <span key={si} style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11,
                            padding: '5px 12px',
                            borderRadius: 4,
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border)',
                            color: 'var(--ink-secondary)',
                          }}>
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: 'var(--ink-muted)',
                    fontStyle: 'italic',
                  }}>
                    + 30 more across the political spectrum
                  </span>
                  <div style={{
                    marginTop: 16,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: 'var(--ink-muted)',
                    padding: '8px 12px',
                    background: 'var(--bg)',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                  }}>
                    Every URL is cleaned and deduplicated &mdash; same article from 5 feeds = 1 record
                  </div>
                </div>
              )}

              {/* ── Stage 02: Embed — Vector flow + structured cluster viz ── */}
              {stage.id === 'embed' && (
                <div style={warmBox}>
                  <div style={vizLabel}>How Embedding Works</div>
                  <div className="hiw-embed-flow" style={{
                    display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 24,
                  }}>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
                      padding: '8px 14px', background: 'var(--bg-card)',
                      border: '1px solid var(--border)', borderRadius: 6,
                    }}>
                      &quot;Senate passes budget...&quot;
                    </div>
                    <span style={{ color: 'var(--ink-muted)', fontSize: 18 }}>&rarr;</span>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                      padding: '8px 14px', background: 'var(--bg-card)',
                      border: '1px solid var(--border)', borderRadius: 6, color: 'var(--ink-secondary)',
                    }}>
                      [0.023, &minus;0.156, 0.089, ... ] <span style={{ color: 'var(--ink-muted)' }}>384 dims</span>
                    </div>
                  </div>

                  <div style={vizLabel}>Similar Meaning = Nearby Vectors</div>
                  <div style={{
                    background: 'var(--bg-card)', border: '1px solid var(--border)',
                    borderRadius: 8, padding: 20,
                    display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap',
                  }}>
                    {/* Cluster A */}
                    <div style={{
                      flex: '1 1 280px',
                      background: 'rgba(43,76,126,0.05)',
                      border: '1px dashed rgba(43,76,126,0.25)',
                      borderRadius: 10, padding: 16,
                    }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                        color: 'var(--accent-blue)', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10,
                      }}>
                        Same event &mdash; clustered together
                      </div>
                      {[
                        { headline: '"Senate passes budget deal"', source: 'Reuters' },
                        { headline: '"Budget compromise heads to vote"', source: 'Fox News' },
                        { headline: '"Bipartisan budget advances"', source: 'AP' },
                      ].map((a, i) => (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          marginBottom: i < 2 ? 8 : 0,
                        }}>
                          <div style={{
                            width: 8, height: 8, borderRadius: '50%',
                            background: 'var(--accent-blue)', flexShrink: 0,
                          }} />
                          <div>
                            <div style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 11, color: 'var(--ink-secondary)',
                            }}>
                              {a.headline}
                            </div>
                            <div style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 9, color: 'var(--ink-muted)',
                            }}>
                              {a.source}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Cluster B */}
                    <div style={{
                      flex: '0 1 180px',
                      background: 'rgba(200,150,62,0.05)',
                      border: '1px dashed rgba(200,150,62,0.25)',
                      borderRadius: 10, padding: 16,
                    }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                        color: 'var(--accent-gold)', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10,
                      }}>
                        Different event
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 8, height: 8, borderRadius: '50%',
                          background: 'var(--accent-gold)', flexShrink: 0,
                        }} />
                        <div>
                          <div style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11, color: 'var(--ink-secondary)',
                          }}>
                            &ldquo;Fed holds rates steady&rdquo;
                          </div>
                          <div style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 9, color: 'var(--ink-muted)',
                          }}>
                            Bloomberg
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11, color: 'var(--ink-muted)',
                    marginTop: 12, textAlign: 'center',
                  }}>
                    Articles about the same event cluster together automatically
                  </div>
                </div>
              )}

              {/* ── Stage 03: Cluster — Cards with neutral pills + noise card ── */}
              {stage.id === 'cluster' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div className="hiw-cluster-viz" style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                    gap: 12,
                  }}>
                    {[
                      { label: 'Budget Deal', sources: ['Reuters', 'Fox News', 'NPR', 'CNN', 'WSJ', 'AP', 'Politico'], count: 7 },
                      { label: 'Trade Policy', sources: ['Bloomberg', 'CNBC', 'BBC', 'Forbes', 'Guardian'], count: 5 },
                      { label: 'Tech Hearing', sources: ['NYT', 'Wired', 'Politico', 'CNN'], count: 4 },
                    ].map((cluster, ci) => (
                      <div key={ci} style={{
                        ...warmBox,
                        display: 'flex', flexDirection: 'column', gap: 10,
                      }}>
                        <div style={{
                          fontFamily: "'Playfair Display', serif",
                          fontSize: 15, fontWeight: 700, color: 'var(--ink)',
                        }}>
                          {cluster.label}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {cluster.sources.map((src, si) => (
                            <span key={si} style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 10, padding: '3px 8px', borderRadius: 4,
                              background: 'var(--bg-card)', color: 'var(--ink-secondary)',
                              border: '1px solid var(--border)',
                            }}>
                              {src}
                            </span>
                          ))}
                        </div>
                        <div style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 10, color: 'var(--ink-muted)',
                        }}>
                          {cluster.count} articles
                        </div>
                      </div>
                    ))}

                    {/* Noise card */}
                    <div style={{
                      background: 'transparent',
                      borderRadius: 'var(--radius)',
                      padding: 'var(--space-md)',
                      border: '1px dashed var(--border)',
                      display: 'flex', flexDirection: 'column', gap: 10,
                      opacity: 0.7,
                    }}>
                      <div style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: 15, fontWeight: 700, color: 'var(--ink-muted)',
                      }}>
                        Unclustered
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {['Local sports recap', 'Op-ed: why I changed my mind'].map((s, si) => (
                          <span key={si} style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: '3px 8px', borderRadius: 4,
                            background: 'transparent', color: 'var(--ink-muted)',
                            border: '1px dashed var(--border)',
                          }}>
                            {s}
                          </span>
                        ))}
                      </div>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, color: 'var(--ink-muted)', fontStyle: 'italic',
                      }}>
                        Retried next cycle
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Stage 04: Label — Styled divider + blue-bordered output ── */}
              {stage.id === 'label' && (
                <div style={warmBox}>
                  <div style={vizLabel}>Example</div>
                  <div style={{ marginBottom: 16 }}>
                    {[
                      '"Senate Advances Bipartisan Budget Deal" — Reuters',
                      '"GOP, Dems Strike Budget Compromise" — Fox News',
                      '"Budget Agreement Reached After Months of Gridlock" — NPR',
                      '"New Budget Deal Draws Criticism From Both Flanks" — Politico',
                      '"Federal Budget Compromise Heads to Full Senate" — AP',
                    ].map((h, i) => (
                      <div key={i} style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11, color: 'var(--ink-secondary)',
                        padding: '4px 0',
                        borderBottom: i < 4 ? '1px solid var(--border)' : 'none',
                      }}>
                        {h}
                      </div>
                    ))}
                  </div>

                  {/* Styled divider with label */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    margin: '16px 0',
                  }}>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: 'var(--ink-muted)',
                      textTransform: 'uppercase', letterSpacing: '0.06em',
                    }}>
                      Language model generates label
                    </span>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                  </div>

                  {/* Output with blue left border */}
                  <div style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: 20, fontWeight: 700, color: 'var(--ink)',
                    padding: '12px 16px',
                    background: 'var(--bg-card)',
                    borderLeft: '4px solid var(--accent-blue)',
                    borderRadius: '0 6px 6px 0',
                  }}>
                    Senate Bipartisan Budget Deal Advances
                  </div>
                  {stage.promptQuote && (
                    <div style={{
                      marginTop: 16,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, color: 'var(--ink-muted)',
                      fontStyle: 'italic', lineHeight: 1.6,
                    }}>
                      {stage.promptQuote}
                    </div>
                  )}
                </div>
              )}

              {/* ── Stage 05: Score — Realistic values ── */}
              {stage.id === 'score' && (
                <>
                  <div style={{
                    background: 'rgba(200,150,62,0.08)',
                    borderLeft: '4px solid var(--accent-gold)',
                    borderRadius: '0 var(--radius) var(--radius) 0',
                    padding: '20px 24px',
                    marginBottom: 'var(--space-md)',
                  }}>
                    <p style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontSize: 17, color: 'var(--ink)', lineHeight: 1.6,
                      fontWeight: 500, fontStyle: 'italic',
                    }}>
                      &ldquo;Do not score based on how interesting or clickable a story is. Score based on real-world impact.&rdquo;
                    </p>
                    <p style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: 'var(--ink-muted)', marginTop: 8,
                    }}>
                      &mdash; from the actual scoring prompt
                    </p>
                  </div>

                  <div style={warmBox}>
                    <div style={{ ...vizLabel, marginBottom: 16 }}>
                      Example: Senate Bipartisan Budget Deal
                    </div>
                    {stage.factors.map(f => (
                      <FactorBar key={f.label} label={f.label} value={f.value} max={f.max} />
                    ))}
                    <div style={{
                      marginTop: 12,
                      display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline', gap: 8,
                    }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11, color: 'var(--ink-muted)',
                      }}>
                        Total
                      </span>
                      <span style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: 28, fontWeight: 800, color: 'var(--ink)',
                      }}>
                        71
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11, color: 'var(--ink-muted)',
                      }}>
                        / 100
                      </span>
                    </div>
                  </div>
                </>
              )}

              {/* ── Stage 06: Select — Cutoff line ── */}
              {stage.id === 'select' && (
                <div style={warmBox}>
                  <div style={vizLabel}>Triage Output</div>
                  {[
                    { topic: 'Senate Budget Deal', action: 'analyze_new', active: true },
                    { topic: 'Trade War Escalation', action: 'analyze_new', active: true },
                    { topic: 'Fed Rate Decision', action: 're_analyze', active: true },
                    { topic: 'Tech Antitrust Hearing', action: 'analyze_new', active: true },
                    { topic: 'Climate Summit Progress', action: 'analyze_new', active: true },
                    { topic: 'Border Policy Shift', action: 're_analyze', active: true },
                    { topic: 'Healthcare Reform Bill', action: 'analyze_new', active: true },
                    { topic: 'Housing Market Data', action: 'analyze_new', active: true },
                  ].map((item, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '6px 0',
                      borderBottom: '1px solid var(--border)',
                    }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12, color: 'var(--ink-secondary)',
                      }}>
                        {i + 1}. {item.topic}
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, padding: '2px 8px', borderRadius: 4,
                        background: item.action === 'analyze_new' ? 'rgba(43,76,126,0.1)' : 'rgba(200,150,62,0.1)',
                        color: item.action === 'analyze_new' ? 'var(--accent-blue)' : 'var(--accent-gold)',
                        fontWeight: 500,
                      }}>
                        {item.action}
                      </span>
                    </div>
                  ))}

                  {/* Cutoff line */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    margin: '8px 0',
                  }}>
                    <div style={{ flex: 1, height: 1, borderTop: '1px dashed var(--ink-muted)' }} />
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 9, color: 'var(--ink-muted)',
                      textTransform: 'uppercase', letterSpacing: '0.04em',
                      whiteSpace: 'nowrap',
                    }}>
                      analysis limit
                    </span>
                    <div style={{ flex: 1, height: 1, borderTop: '1px dashed var(--ink-muted)' }} />
                  </div>

                  {[
                    { topic: 'Celebrity Interview', action: 'skip' },
                    { topic: 'Sports Recap', action: 'skip' },
                  ].map((item, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '6px 0', opacity: 0.4,
                      borderBottom: i < 1 ? '1px solid var(--border)' : 'none',
                    }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12, color: 'var(--ink-muted)',
                      }}>
                        {i + 9}. {item.topic}
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, padding: '2px 8px', borderRadius: 4,
                        background: 'rgba(0,0,0,0.05)', color: 'var(--ink-muted)', fontWeight: 500,
                      }}>
                        skip
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* ── Stage 07: Scrape — Before/after panels ── */}
              {stage.id === 'scrape' && (
                <div style={warmBox}>
                  <div style={vizLabel}>Content Extraction</div>
                  <div className="hiw-scrape-flow" style={{
                    display: 'grid', gridTemplateColumns: '1fr auto 1fr',
                    gap: 12, alignItems: 'stretch', marginBottom: 16,
                  }}>
                    {/* Before panel */}
                    <div style={{
                      background: 'var(--bg-card)', border: '1px solid var(--border)',
                      borderRadius: 6, padding: 14, overflow: 'hidden',
                    }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 9, color: 'var(--ink-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8,
                      }}>
                        Raw Webpage
                      </div>
                      {/* Mini page mockup */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <div style={{ height: 8, background: 'var(--border)', borderRadius: 2 }} />
                        <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                          <div style={{ width: '30%', height: 6, background: 'var(--border)', borderRadius: 2 }} />
                          <div style={{ width: '20%', height: 6, background: 'var(--border)', borderRadius: 2 }} />
                          <div style={{ width: '25%', height: 6, background: 'var(--border)', borderRadius: 2 }} />
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
                            <div style={{ height: 4, background: 'var(--accent-blue)', borderRadius: 1, opacity: 0.3 }} />
                            <div style={{ height: 4, background: 'var(--accent-blue)', borderRadius: 1, opacity: 0.3 }} />
                            <div style={{ height: 4, background: 'var(--accent-blue)', borderRadius: 1, opacity: 0.3, width: '70%' }} />
                          </div>
                          <div style={{ width: '35%', height: 30, background: 'var(--border)', borderRadius: 2 }} />
                        </div>
                        <div style={{ height: 14, background: 'var(--border)', borderRadius: 2, opacity: 0.5, marginTop: 4 }} />
                      </div>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 9, color: 'var(--ink-muted)', marginTop: 8, textAlign: 'center',
                      }}>
                        Ads, nav, sidebars, boilerplate
                      </div>
                    </div>

                    {/* Arrow */}
                    <div style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center',
                      justifyContent: 'center', gap: 4,
                    }}>
                      <span style={{ color: 'var(--ink-muted)', fontSize: 18 }}>&rarr;</span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 8, color: 'var(--ink-muted)',
                        writingMode: 'vertical-lr',
                        textTransform: 'uppercase', letterSpacing: '0.06em',
                      }}>
                        extract
                      </span>
                    </div>

                    {/* After panel */}
                    <div style={{
                      background: 'var(--bg-card)', border: '1px solid var(--border)',
                      borderRadius: 6, padding: 14,
                    }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 9, color: 'var(--ink-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8,
                      }}>
                        ~300 Words of Clean Text
                      </div>
                      <div style={{
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: 11, color: 'var(--ink-secondary)', lineHeight: 1.6,
                      }}>
                        The Senate advanced a bipartisan budget agreement on Thursday, marking the end of months of negotiations between party leaders. The deal includes provisions for...
                      </div>
                    </div>
                  </div>
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11, color: 'var(--ink-muted)',
                  }}>
                    Paywalled (skipped): {stage.paywalled.join(', ')}
                  </div>
                </div>
              )}

              {/* ── Stage 08: Frame — Dominant callout + comparison ── */}
              {stage.id === 'frame' && (
                <>
                  <div style={{
                    background: 'var(--accent-blue)',
                    borderRadius: 'var(--radius)',
                    padding: '32px 28px',
                    marginBottom: 'var(--space-lg)',
                    textAlign: 'center',
                  }}>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: 'rgba(255,255,255,0.6)',
                      textTransform: 'uppercase', letterSpacing: '0.1em',
                      fontWeight: 600, marginBottom: 12,
                    }}>
                      Key Design Decision
                    </div>
                    <p style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: 22, fontWeight: 800, color: '#fff',
                      lineHeight: 1.4, maxWidth: 520, margin: '0 auto 12px',
                    }}>
                      The AI never knows which outlet published the article.
                    </p>
                    <p style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontSize: 15, color: 'rgba(255,255,255,0.8)',
                      lineHeight: 1.6, maxWidth: 480, margin: '0 auto',
                    }}>
                      {stage.callout}
                    </p>
                  </div>

                  <div style={{ ...warmBox, padding: 'var(--space-md) var(--space-md) var(--space-sm)' }}>
                    <div style={vizLabel}>Same Event, Different Frames</div>
                    {[
                      {
                        source: 'Reuters', framing: 'Neutral/Wire', framingColor: '#767676',
                        headline: '"Senate passes bipartisan budget deal in 62-38 vote"',
                        angle: 'Straight facts: who, what, when, outcome.',
                      },
                      {
                        source: 'Fox News', framing: 'Economic', framingColor: 'var(--accent-gold)',
                        headline: '"Budget deal raises concerns over fiscal impact on taxpayers"',
                        angle: 'Leads with economic consequences.',
                      },
                      {
                        source: 'NPR', framing: 'Policy', framingColor: 'var(--accent-blue)',
                        headline: '"What the new federal budget means for social programs"',
                        angle: 'Focuses on policy implications and who is affected.',
                      },
                      {
                        source: 'CNN', framing: 'Conflict', framingColor: 'var(--accent-red)',
                        headline: '"Budget fight exposes deep rifts within both parties"',
                        angle: 'Emphasizes political tensions and disagreement.',
                      },
                    ].map((ex, i) => (
                      <div key={i} style={{
                        padding: '16px 0',
                        borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 12, color: 'var(--ink)', fontWeight: 600,
                          }}>
                            {ex.source}
                          </span>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: '2px 8px', borderRadius: 4,
                            background: `${ex.framingColor}18`,
                            color: ex.framingColor,
                            border: `1px solid ${ex.framingColor}30`,
                            fontWeight: 500,
                          }}>
                            {ex.framing}
                          </span>
                        </div>
                        <div style={{
                          fontFamily: "'DM Sans', sans-serif",
                          fontSize: 15, color: 'var(--ink)', lineHeight: 1.5, marginBottom: 4,
                        }}>
                          {ex.headline}
                        </div>
                        <div style={{
                          fontFamily: "'DM Sans', sans-serif",
                          fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.5,
                        }}>
                          {ex.angle}
                        </div>
                      </div>
                    ))}
                    <div style={{
                      marginTop: 12, paddingTop: 12,
                      borderTop: '1px solid var(--border)',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: 'var(--ink-muted)',
                    }}>
                      7 framing categories: {stage.framingCategories.join(' · ')}
                    </div>
                  </div>
                </>
              )}

              {/* ── Stage 09: Analyze — Redacted input + wireframe output ── */}
              {stage.id === 'analyze' && (
                <div style={warmBox}>
                  <div style={vizLabel}>Diversity-Weighted Input</div>
                  <div style={{ marginBottom: 20 }}>
                    {[
                      { source: 'washingtonexaminer.com' },
                      { source: 'pbs.org' },
                      { source: 'bloomberg.com' },
                      { source: 'foxnews.com' },
                      { source: 'apnews.com' },
                    ].map((row, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '6px 0',
                        borderBottom: i < 4 ? '1px solid var(--border)' : 'none',
                      }}>
                        <span style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 11, color: 'var(--ink-secondary)',
                          width: 180, flexShrink: 0,
                        }}>
                          {row.source}
                        </span>
                        <div style={{
                          flex: 1, height: 6, background: 'var(--border)', borderRadius: 3,
                        }}>
                          <div style={{
                            height: '100%', width: `${55 + (i * 7) % 30}%`,
                            background: 'var(--accent-blue)', borderRadius: 3, opacity: 0.3,
                          }} />
                        </div>
                        <span style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 10, color: 'var(--ink-muted)',
                          background: 'var(--bg)',
                          padding: '2px 8px', borderRadius: 4,
                          border: '1px solid var(--border)',
                          textDecoration: 'line-through',
                          textDecorationColor: 'var(--ink-muted)',
                        }}>
                          lean: &#x2014;&#x2014;
                        </span>
                      </div>
                    ))}
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: 'var(--accent-blue)',
                      marginTop: 8, fontWeight: 500,
                    }}>
                      Bias labels withheld from the model &mdash; it sees only the article text
                    </div>
                  </div>

                  {/* Divider */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, margin: '4px 0 16px',
                  }}>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 9, color: 'var(--ink-muted)',
                      textTransform: 'uppercase', letterSpacing: '0.04em',
                    }}>
                      produces
                    </span>
                    <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                  </div>

                  <div style={vizLabel}>Structured Output</div>
                  {/* Wireframe mockup */}
                  <div style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 8, overflow: 'hidden',
                  }}>
                    {/* Headline + lede */}
                    <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
                      <div style={{
                        fontFamily: "'Playfair Display', serif",
                        fontSize: 16, fontWeight: 700, color: 'var(--ink)', marginBottom: 4,
                      }}>
                        Headline
                      </div>
                      <div style={{
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: 12, color: 'var(--ink-secondary)', lineHeight: 1.5,
                      }}>
                        Lede paragraph summarizing the event across all sources...
                      </div>
                    </div>
                    {/* Facts */}
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
                      {['Agreed fact from all sources', 'Second verified fact'].map((f, i) => (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'center', gap: 6, marginBottom: i < 1 ? 4 : 0,
                        }}>
                          <div style={{
                            width: 14, height: 14, borderRadius: '50%',
                            background: 'var(--accent-green)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                          }}>
                            <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                              <path d="M1 3L3 5L7 1" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </div>
                          <span style={{
                            fontFamily: "'DM Sans', sans-serif",
                            fontSize: 11, color: 'var(--ink-secondary)',
                          }}>
                            {f}
                          </span>
                        </div>
                      ))}
                    </div>
                    {/* Framings */}
                    <div style={{
                      padding: '10px 16px', borderBottom: '1px solid var(--border)',
                      display: 'flex', gap: 6, flexWrap: 'wrap',
                    }}>
                      {['Neutral/Wire', 'Economic', 'Policy', 'Conflict'].map(fr => (
                        <span key={fr} style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 9, padding: '2px 8px', borderRadius: 4,
                          background: 'rgba(43,76,126,0.08)', color: 'var(--accent-blue)',
                        }}>
                          {fr}
                        </span>
                      ))}
                    </div>
                    {/* Bottom line */}
                    <div style={{
                      padding: '10px 16px',
                      borderLeft: '3px solid var(--accent-blue)',
                    }}>
                      <div style={{
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: 11, color: 'var(--ink-secondary)', lineHeight: 1.5, fontWeight: 500,
                      }}>
                        Bottom line: what is known, what is uncertain, what to watch...
                      </div>
                    </div>
                  </div>
                  {stage.promptQuote && (
                    <div style={{
                      marginTop: 16,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, color: 'var(--ink-muted)',
                      fontStyle: 'italic', lineHeight: 1.6,
                    }}>
                      {stage.promptQuote}
                    </div>
                  )}
                </div>
              )}
            </FadeIn>
          </section>
        ))}
      </div>

      {/* ── The Result ── */}
      <div style={{ maxWidth: 'var(--content-width)', margin: '0 auto', padding: 'var(--space-section) 24px' }}>
        <FadeIn>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, color: 'var(--ink-muted)',
            textTransform: 'uppercase', letterSpacing: '0.08em',
            fontWeight: 500, marginBottom: 'var(--space-xs)',
          }}>
            The Result
          </div>
          <h2 style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 28, fontWeight: 800, color: 'var(--ink)',
            marginBottom: 'var(--space-md)',
          }}>
            Three principles, every cycle
          </h2>
          <div style={{
            ...warmBox,
            padding: 'var(--space-lg)',
            borderLeft: '4px solid var(--accent-gold)',
          }}>
            {[
              {
                num: '1',
                title: 'The AI never knows which outlet published an article',
                desc: 'No source names, no political labels, no bias ratings are ever included in framing prompts. The model classifies purely from text.',
              },
              {
                num: '2',
                title: 'Seven framing categories, assigned purely from language',
                desc: 'Accountability, economic, human interest, conflict, policy, crisis, and neutral wire — determined by structure and emphasis, not source identity.',
              },
              {
                num: '3',
                title: 'Fully transparent pipeline',
                desc: 'Every model call, every prompt, every design decision is documented on this page. You can trace how any analysis was produced.',
              },
            ].map((p, i) => (
              <div key={i} style={{
                display: 'flex', gap: 16, alignItems: 'flex-start',
                padding: '16px 0',
                borderBottom: i < 2 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'var(--accent-gold)', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12, fontWeight: 600, flexShrink: 0,
                }}>
                  {p.num}
                </div>
                <div>
                  <div style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontSize: 16, fontWeight: 600, color: 'var(--ink)', marginBottom: 4,
                  }}>
                    {p.title}
                  </div>
                  <div style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontSize: 14, color: 'var(--ink-secondary)', lineHeight: 1.6,
                  }}>
                    {p.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </FadeIn>
      </div>

      {/* ── Footer ── */}
      <footer style={{
        maxWidth: 1280, margin: '40px auto 0', padding: '32px 48px',
        borderTop: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
          &copy; 2025 ClearSignal &mdash; Tracking media coverage across the political spectrum.
        </p>
        <p style={{ fontSize: 13 }}>
          <Link href="/" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>Home</Link>
          {' \u00B7 '}
          <a href="#about" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>About</a>
          {' \u00B7 '}
          <a href="#api" style={{ color: 'var(--accent-blue)', textDecoration: 'none', fontWeight: 500 }}>API</a>
        </p>
      </footer>
    </div>
  );
}
