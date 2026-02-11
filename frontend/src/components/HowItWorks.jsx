'use client';

import Link from 'next/link';

export default function HowItWorks() {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      {/* Nav */}
      <nav className="hiw-nav" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 48px', borderBottom: '1px solid var(--border)',
        background: 'rgba(250,250,247,0.95)', backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)', position: 'sticky', top: 0,
        zIndex: 100, height: 58,
      }}>
        <Link href="/" style={{ textDecoration: 'none', color: 'var(--ink)' }}>
          <div style={{
            fontFamily: "'Playfair Display', serif", fontWeight: 800,
            fontSize: 22, letterSpacing: '-0.5px',
          }}>
            Clear<span style={{ color: 'var(--accent-gold)' }}>Signal</span>
          </div>
        </Link>
        <Link href="/" style={{
          fontSize: 14, color: 'var(--ink-muted)', textDecoration: 'none',
        }}>
          &larr; Back to stories
        </Link>
      </nav>

      {/* Cinematic Dark Hero */}
      <section className="hiw-hero" style={{
        background: 'var(--bg-dark)', color: '#fff',
        padding: '80px 48px 64px', position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          content: '', position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
          background: 'radial-gradient(ellipse at 20% 80%, rgba(200,150,62,0.06) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(43,76,126,0.08) 0%, transparent 50%)',
          pointerEvents: 'none',
        }} />
        <div style={{ position: 'relative', maxWidth: 1080, margin: '0 auto' }}>
          <h1 style={{
            fontFamily: "'Playfair Display', serif", fontWeight: 900,
            fontSize: 52, lineHeight: 1.05, letterSpacing: '-2px',
            marginBottom: 'var(--space-md)', maxWidth: 600,
          }}>
            From raw feeds to<br />
            <em style={{ fontStyle: 'normal', color: 'var(--accent-gold)' }}>structured clarity</em>
          </h1>
          <p style={{
            fontSize: 17, lineHeight: 1.6, color: 'rgba(255,255,255,0.6)',
            maxWidth: 480, marginBottom: 'var(--space-xl)',
          }}>
            9 stages turn the noise of 40+ sources into a map of who's saying what — and what's being left out.
          </p>

          {/* Pipeline Grid */}
          <div className="hiw-pipeline">
            {PIPELINE.map((cell) => (
              <div key={cell.num} className={`hp-cell${cell.final ? ' final' : ''}`}>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, color: 'rgba(255,255,255,0.3)', marginBottom: 6,
                }}>{cell.num}</div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12, fontWeight: 500,
                  color: cell.final ? 'var(--accent-gold)' : 'rgba(255,255,255,0.7)',
                }}>{cell.name}</div>
                {cell.model && (
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, marginTop: 4,
                    color: cell.final ? 'rgba(200,150,62,0.5)' : 'rgba(255,255,255,0.25)',
                  }}>{cell.model}</div>
                )}
              </div>
            ))}
          </div>

          {/* Principles */}
          <div className="hiw-principles">
            {PRINCIPLES.map((p) => (
              <div key={p.title} style={{ flex: 1 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700,
                  color: 'rgba(255,255,255,0.9)', marginBottom: 4,
                }}>{p.title}</div>
                <div style={{
                  fontSize: 12, lineHeight: 1.5, color: 'rgba(255,255,255,0.4)',
                }}>{p.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stage 01: Ingest */}
      <StageSection num="Stage 01" title="Ingest"
        desc="Concurrent RSS fetcher pulls from 40+ feeds across the political spectrum every 15 minutes. URLs are normalized, deduplicated, and stored with source metadata including editorial lean ratings.">
        <div className="feed-cascade">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {FEEDS.map((f, i) => (
              <div key={i} className="feed-row" style={f.faded ? { opacity: 0.4, borderStyle: 'dashed' } : undefined}>
                <span className={`feed-lean ${f.lean}`}>{f.leanLabel}</span>
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.domain}</span>
                <span style={{ color: 'var(--ink-secondary)', fontSize: 10, flexShrink: 0 }}>{f.count}</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', justifyContent: 'center' }}>
            <div style={{
              border: '2px solid var(--accent-blue-deep)', borderRadius: 8,
              padding: 20, textAlign: 'center',
            }}>
              <div style={{
                fontFamily: "'Playfair Display', serif", fontWeight: 800,
                fontSize: 32, color: 'var(--accent-blue-deep)',
              }}>477</div>
              <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginTop: 2 }}>articles this cycle</div>
            </div>
            <div style={{
              background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: 8,
              padding: 'var(--space-md)', fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, lineHeight: 2, color: 'var(--ink-secondary)',
            }}>
              <span style={{ color: 'var(--accent-blue-deep)' }}>title:</span> <span style={{ color: 'var(--ink)' }}>"Trump Freezes Foreign Aid..."</span><br />
              <span style={{ color: 'var(--accent-blue-deep)' }}>source:</span> <span style={{ color: 'var(--ink)' }}>"reuters.com"</span><br />
              <span style={{ color: 'var(--accent-blue-deep)' }}>published:</span> <span style={{ color: 'var(--ink)' }}>"2025-02-09T14:23:00Z"</span><br />
              <span style={{ color: 'var(--accent-blue-deep)' }}>lean:</span> <span style={{ color: 'var(--ink)' }}>"center"</span><br />
              <span style={{ color: 'var(--accent-blue-deep)' }}>url:</span> <span style={{ color: 'var(--ink)' }}>"reuters.com/world/us/..."</span>
            </div>
          </div>
        </div>
      </StageSection>

      {/* Stage 02 and 03: Embed and Cluster */}
      <StageSection num="Stage 02 and 03" title="Embed and Cluster" warm
        modelTag="OpenAI embeddings"
        desc="Each article headline is embedded into a 384-dimensional vector. HDBSCAN density-based clustering discovers story groups by cosine similarity. Scattered articles find each other in semantic space.">
        <div className="cluster-viz">
          {/* Before: scattered */}
          <div className="cluster-panel">
            <div style={{
              position: 'absolute', top: 12, left: 14,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, textTransform: 'uppercase',
              letterSpacing: '1px', color: 'var(--ink-secondary)',
            }}>477 scattered articles</div>
            {SCATTERED_DOTS.map((d, i) => (
              <div key={i} style={{
                position: 'absolute', width: 8, height: 8, borderRadius: '50%',
                opacity: 0.6, top: d.top, left: d.left,
                background: `var(--cat-${d.cat})`,
              }} />
            ))}
          </div>

          <div className="hiw-arrow" style={{ fontSize: 28, color: 'var(--border)' }}>&rarr;</div>
          <div className="hiw-connector" />

          {/* After: clustered */}
          <div className="cluster-panel">
            <div style={{
              position: 'absolute', top: 12, left: 14,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, textTransform: 'uppercase',
              letterSpacing: '1px', color: 'var(--ink-secondary)',
            }}>46 story clusters</div>
            {CLUSTERS.map((c) => (
              <div key={c.label}>
                <div className={`cluster-ring ${c.cat}`} style={{
                  top: c.ring.top, left: c.ring.left,
                  width: c.ring.w, height: c.ring.h,
                }} />
                {c.dots.map((d, i) => (
                  <div key={i} style={{
                    position: 'absolute', width: 8, height: 8, borderRadius: '50%',
                    opacity: 0.9, top: d.top, left: d.left,
                    background: `var(--cat-${c.catFull})`,
                  }} />
                ))}
                <div style={{
                  position: 'absolute', top: c.labelPos.top, left: c.labelPos.left,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, fontWeight: 500, padding: '2px 6px', borderRadius: 3,
                  whiteSpace: 'nowrap', color: `var(--cat-${c.catFull})`,
                  background: c.labelBg,
                }}>{c.label}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{
          textAlign: 'center', padding: 'var(--space-md) 0 0',
          fontFamily: "'JetBrains Mono', monospace", fontSize: 13,
          color: 'var(--ink-secondary)',
        }}>
          <strong style={{ color: 'var(--accent-blue-deep)' }}>"Trump freezes aid"</strong>
          {' '}&rarr; [0.023, -0.187, 0.441, ... ] &rarr; cosine similarity &rarr; cluster assignment
        </div>
      </StageSection>

      {/* Stage 04: Label */}
      <StageSection num="Stage 04" title="Label" modelTag="Claude Haiku"
        desc="Different outlets write different headlines for the same event. Claude Haiku reads them all and generates one neutral, wire-service-style topic label. No editorializing — just the facts.">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div className="label-inputs">
            {HEADLINES.map((h, i) => (
              <div key={i} className={`label-headline ${h.lean}`}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                  color: 'var(--ink-muted)', display: 'block', marginBottom: 4,
                }}>{h.src}</span>
                {h.text}
              </div>
            ))}
          </div>
          <div style={{
            border: '2px solid var(--accent-blue-deep)', borderRadius: 8,
            padding: 'var(--space-md) var(--space-lg)', textAlign: 'center',
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
              color: 'var(--accent-gold)', textTransform: 'uppercase',
              letterSpacing: '1px', marginBottom: 'var(--space-xs)',
            }}>Neutral Topic Label</div>
            <div style={{
              fontFamily: "'Playfair Display', serif", fontWeight: 800,
              fontSize: 22, lineHeight: 1.3,
            }}>Trump Administration Freezes Foreign Aid Pending Policy Review</div>
          </div>
        </div>
      </StageSection>

      {/* Stage 05: Score */}
      <StageSection num="Stage 05" title="Score" warm modelTag="Claude Haiku"
        desc="Every topic receives an impact score from a 5-factor model that measures real-world significance — not clickbait potential, not engagement, not controversy. A separate coverage score is computed from signal data alone.">
        <div className="score-viz">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {FACTORS.map((f) => (
              <div key={f.label} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <span style={{ fontSize: 13, fontWeight: 600, minWidth: 160, flexShrink: 0 }}>{f.label}</span>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: f.pct }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, fontWeight: 500, color: '#fff',
                    }}>{f.score}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', textAlign: 'center',
          }}>
            <div style={{
              fontFamily: "'Playfair Display', serif", fontWeight: 900,
              fontSize: 72, color: 'var(--accent-blue-deep)', lineHeight: 1,
            }}>80</div>
            <div style={{ fontSize: 14, color: 'var(--ink-muted)', marginTop: 'var(--space-xs)' }}>Impact Score</div>
            <div style={{
              fontSize: 12, color: 'var(--ink-secondary)', marginTop: 'var(--space-sm)',
              fontStyle: 'italic', maxWidth: 240,
            }}>"We do not score based on how interesting or clickable the story is"</div>
          </div>
        </div>
      </StageSection>

      {/* Stage 08: Frame */}
      <StageSection num="Stage 08" title="Frame" modelTag="Claude Haiku"
        desc="Each article's editorial framing is classified into one of 7 categories from its language alone. The model never sees source names, political lean labels, or any metadata about who published the article.">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {/* Firewall banner */}
          <div style={{
            textAlign: 'center', padding: 'var(--space-sm)',
            border: '1px dashed var(--accent-gold)', borderRadius: 6,
            fontSize: 13, color: 'var(--accent-gold)', fontWeight: 600,
          }}>
            Source identity is hidden from the AI. Framing is classified from text alone.
          </div>

          {/* Event label */}
          <div style={{
            textAlign: 'center', padding: 'var(--space-sm)',
            background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: 6,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
            color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '1px',
          }}>Same event: Foreign Aid Freeze</div>

          {/* Three frame cards */}
          <div className="frame-cards">
            {FRAMES.map((f) => (
              <div key={f.src} className={`frame-card ${f.lean}`}>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                  color: 'var(--ink-secondary)', marginBottom: 6,
                }}>{f.src}</div>
                <div style={{
                  fontSize: 14, lineHeight: 1.5, color: 'var(--ink-secondary)',
                  marginBottom: 'var(--space-sm)',
                }} dangerouslySetInnerHTML={{ __html: f.html }} />
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                  letterSpacing: '0.5px', padding: '3px 8px', borderRadius: 4,
                  display: 'inline-block', color: f.tagColor, background: f.tagBg,
                }}>{f.tag}</span>
              </div>
            ))}
          </div>
        </div>
      </StageSection>

      {/* Stage 09: Analyze */}
      <StageSection num="Stage 09" title="Analyze" warm modelTag="Claude Sonnet"
        desc="The most capable model synthesizes everything — headlines, article bodies, framing classifications, impact scores — into a structured analysis that reads like a senior editor's briefing. Not a summary. A map of how the story is being told differently.">
        <div className="analyze-viz">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            {INPUTS.map((inp) => (
              <div key={inp.icon} style={{
                padding: '10px 14px', background: '#F9FAFB',
                border: '1px solid #E5E7EB', borderRadius: 6,
                fontSize: 12, color: 'var(--ink-secondary)',
                display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
              }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                  color: 'var(--ink-secondary)', background: '#f0eeea',
                  padding: '2px 6px', borderRadius: 3, flexShrink: 0,
                }}>{inp.icon}</span>
                {inp.text}
              </div>
            ))}
          </div>

          <div className="hiw-arrow" style={{
            fontSize: 28, color: 'var(--border)',
            display: 'flex', alignItems: 'center',
          }}>&rarr;</div>
          <div className="hiw-connector" />

          <div className="analyze-output">
            <div style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
              textTransform: 'uppercase', letterSpacing: '1px',
              color: 'rgba(255,255,255,0.5)', marginBottom: 'var(--space-sm)',
            }}>Structured Analysis Output</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              {ANALYSIS_SECTIONS.map((s) => (
                <div key={s.label} className="analyze-output-section">
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                    color: 'var(--accent-gold)', textTransform: 'uppercase',
                    letterSpacing: '0.5px', display: 'block', marginBottom: 4,
                  }}>{s.label}</span>
                  {s.text}
                </div>
              ))}
            </div>
          </div>
        </div>
      </StageSection>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: 'var(--space-lg) 48px',
        borderTop: '1px solid var(--border)',
      }}>
        <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
          &copy; 2025 ClearSignal — Tracking media coverage across the political spectrum.
        </p>
      </footer>
    </div>
  );
}

/* ── Sub-components ── */

function StageSection({ num, title, desc, warm, modelTag, children }) {
  return (
    <div className={`hiw-stage${warm ? ' warm' : ''}`}>
      <div className="hiw-stage-inner">
        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
            fontWeight: 500, color: 'var(--accent-gold)',
            textTransform: 'uppercase', letterSpacing: '1.5px',
            marginBottom: 'var(--space-xs)',
            display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
          }}>
            {num}
            {modelTag && (
              <span style={{
                fontSize: 10, color: 'var(--ink-muted)',
                background: 'rgba(0,0,0,0.04)', padding: '2px 8px',
                borderRadius: 3, letterSpacing: '0.5px',
              }}>{modelTag}</span>
            )}
          </div>
          <div style={{
            fontFamily: "'Playfair Display', serif", fontWeight: 800,
            fontSize: 32, letterSpacing: '-0.5px',
            marginBottom: 'var(--space-xs)',
          }}>{title}</div>
          <div style={{
            fontSize: 16, lineHeight: 1.65, color: 'var(--ink-secondary)',
            maxWidth: 640,
          }}>{desc}</div>
        </div>
        <div className={`hiw-visual`}>
          {children}
        </div>
      </div>
    </div>
  );
}

/* ── Data ── */

const PIPELINE = [
  { num: '01', name: 'Ingest' },
  { num: '02', name: 'Embed', model: 'OpenAI' },
  { num: '03', name: 'Cluster', model: 'HDBSCAN' },
  { num: '04', name: 'Label', model: 'Haiku' },
  { num: '05', name: 'Validate', model: 'GPT-4o' },
  { num: '06', name: 'Score', model: 'Haiku' },
  { num: '07', name: 'Select', model: 'GPT-4o' },
  { num: '08', name: 'Frame', model: 'Haiku' },
  { num: '09', name: 'Analyze', model: 'Sonnet', final: true },
];

const PRINCIPLES = [
  { title: 'Source-Blind Framing', desc: 'Framing classified from language, not source identity. The AI never sees outlet names.' },
  { title: 'Coverage Gap Detection', desc: 'Impact vs coverage delta reveals what the media is overlooking.' },
  { title: 'Multi-Model Architecture', desc: 'Fast models triage. The best model analyzes. Cost, speed, depth — balanced.' },
];

const FEEDS = [
  { lean: 'left', leanLabel: 'Left', domain: 'nytimes.com/rss', count: '12 articles' },
  { lean: 'left', leanLabel: 'Left', domain: 'washingtonpost.com/rss', count: '9 articles' },
  { lean: 'center', leanLabel: 'Center', domain: 'apnews.com/feed', count: '18 articles' },
  { lean: 'center', leanLabel: 'Center', domain: 'reuters.com/rss', count: '15 articles' },
  { lean: 'right', leanLabel: 'Right', domain: 'foxnews.com/rss', count: '11 articles' },
  { lean: 'right', leanLabel: 'Right', domain: 'dailywire.com/rss', count: '8 articles' },
  { lean: 'center', leanLabel: '...', domain: '34 more feeds', count: '', faded: true },
];

const SCATTERED_DOTS = [
  { top: '25%', left: '18%', cat: 'politics' },
  { top: '42%', left: '12%', cat: 'world' },
  { top: '33%', left: '25%', cat: 'politics' },
  { top: '68%', left: '45%', cat: 'economy' },
  { top: '55%', left: '52%', cat: 'world' },
  { top: '22%', left: '72%', cat: 'science' },
  { top: '78%', left: '20%', cat: 'politics' },
  { top: '45%', left: '78%', cat: 'economy' },
  { top: '62%', left: '32%', cat: 'world' },
  { top: '38%', left: '58%', cat: 'science' },
  { top: '82%', left: '65%', cat: 'politics' },
  { top: '18%', left: '42%', cat: 'economy' },
  { top: '72%', left: '82%', cat: 'world' },
  { top: '52%', left: '22%', cat: 'science' },
  { top: '15%', left: '55%', cat: 'politics' },
  { top: '85%', left: '38%', cat: 'economy' },
  { top: '28%', left: '88%', cat: 'world' },
  { top: '65%', left: '68%', cat: 'science' },
];

const CLUSTERS = [
  {
    cat: 'p', catFull: 'politics',
    ring: { top: '15%', left: '10%', w: 100, h: 80 },
    dots: [
      { top: '28%', left: '18%' },
      { top: '22%', left: '26%' },
      { top: '32%', left: '22%' },
      { top: '26%', left: '14%' },
    ],
    label: 'FBI Director Vote',
    labelPos: { top: '48%', left: '10%' },
    labelBg: 'rgba(192,57,43,0.08)',
  },
  {
    cat: 'w', catFull: 'world',
    ring: { top: '10%', left: '55%', w: 110, h: 85 },
    dots: [
      { top: '22%', left: '62%' },
      { top: '18%', left: '72%' },
      { top: '28%', left: '68%' },
      { top: '24%', left: '58%' },
      { top: '16%', left: '66%' },
    ],
    label: 'Foreign Aid Freeze',
    labelPos: { top: '44%', left: '55%' },
    labelBg: 'rgba(43,76,126,0.08)',
  },
  {
    cat: 'e', catFull: 'economy',
    ring: { top: '58%', left: '30%', w: 90, h: 75 },
    dots: [
      { top: '68%', left: '38%' },
      { top: '72%', left: '45%' },
      { top: '65%', left: '42%' },
    ],
    label: 'Fed Rate Pause',
    labelPos: { top: '84%', left: '30%' },
    labelBg: 'rgba(200,150,62,0.08)',
  },
];

const HEADLINES = [
  { lean: 'left', src: 'NYT', text: '"Trump\'s Aid Freeze Threatens Millions Abroad, Critics Warn"' },
  { lean: 'left', src: 'MSNBC', text: '"Devastating Foreign Aid Cuts Leave Allies Scrambling"' },
  { lean: 'center', src: 'AP', text: '"US Halts Foreign Aid Disbursements Pending Review"' },
  { lean: 'center', src: 'Reuters', text: '"Trump Administration Pauses Foreign Assistance Programs"' },
  { lean: 'right', src: 'Fox News', text: '"Trump Puts America First, Freezes Wasteful Foreign Aid"' },
  { lean: 'right', src: 'Daily Wire', text: '"Trump Delivers on Promise to Review Bloated Aid Programs"' },
];

const FACTORS = [
  { label: 'Policy Scope', pct: '85%', score: '17/20' },
  { label: 'Population Affected', pct: '90%', score: '27/30' },
  { label: 'Economic Magnitude', pct: '80%', score: '20/25' },
  { label: 'Institutional Precedent', pct: '73%', score: '11/15' },
  { label: 'Irreversibility', pct: '50%', score: '5/10' },
];

const FRAMES = [
  {
    lean: 'left', src: 'Source A (identity hidden)',
    html: '"The freeze <em style="font-style:normal;background:rgba(200,150,62,0.15);padding:1px 4px;border-radius:2px">threatens millions</em> of vulnerable people who depend on U.S. assistance programs, aid workers say"',
    tag: 'Alarmist', tagColor: '#B45309', tagBg: 'rgba(180,83,9,0.08)',
  },
  {
    lean: 'center', src: 'Source B (identity hidden)',
    html: '"The administration <em style="font-style:normal;background:rgba(200,150,62,0.15);padding:1px 4px;border-radius:2px">announced a review</em> of all foreign assistance programs, pausing disbursements"',
    tag: 'Factual / Wire', tagColor: 'var(--ink-muted)', tagBg: 'rgba(0,0,0,0.04)',
  },
  {
    lean: 'right', src: 'Source C (identity hidden)',
    html: '"The president <em style="font-style:normal;background:rgba(200,150,62,0.15);padding:1px 4px;border-radius:2px">delivered on his promise</em> to ensure taxpayer dollars serve American interests first"',
    tag: 'Policy / Regulatory', tagColor: 'var(--accent-blue-deep)', tagBg: 'rgba(27,49,85,0.08)',
  },
];

const INPUTS = [
  { icon: 'HDLN', text: '38 headlines from 22 sources' },
  { icon: 'BODY', text: 'Full text from 8 selected articles' },
  { icon: 'FRAME', text: '7 framing classifications per article' },
  { icon: 'SCORE', text: 'Impact: 80 / Coverage: 72' },
  { icon: 'LEAN', text: '3 left, 2 center, 3 right sources' },
];

const ANALYSIS_SECTIONS = [
  { label: 'Lede', text: 'The Trump administration has frozen foreign aid disbursements across multiple agencies pending a comprehensive policy review...' },
  { label: 'Narrative', text: 'Left-leaning outlets frame the freeze as a humanitarian crisis, while conservative sources cast it as fiscal responsibility...' },
  { label: 'Source Spectrum', text: 'NYT and WaPo emphasize impact on recipients. AP and Reuters report procedural details. Fox and Daily Wire highlight cost savings...' },
  { label: 'Bottom Line', text: 'The freeze is real, the scope is disputed, and the framing reveals more about each outlet than about the policy itself.' },
];
