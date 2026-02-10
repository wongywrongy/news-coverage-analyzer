'use client';

import Link from 'next/link';

export default function HowItWorks() {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      {/* ── Nav ── */}
      <nav className="hiw-nav" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '18px 48px',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(250,250,247,0.95)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 58,
      }}>
        <Link href="/" style={{ textDecoration: 'none', color: 'var(--ink)' }}>
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: '-0.5px',
          }}>
            Clear<span style={{ color: 'var(--accent-gold)' }}>Signal</span>
          </div>
        </Link>
        <Link href="/" style={{
          fontSize: 14,
          color: 'var(--ink-muted)',
          textDecoration: 'none',
          transition: 'color 0.2s',
        }}>
          &larr; Back to stories
        </Link>
      </nav>

      {/* ── Hero ── */}
      <section className="hiw-hero" style={{
        padding: 'var(--space-xl) 48px var(--space-lg)',
        textAlign: 'center',
      }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <h1 className="hiw-hero-title" style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 900,
            fontSize: 44,
            lineHeight: 1.1,
            letterSpacing: '-1.5px',
            marginBottom: 'var(--space-sm)',
          }}>
            How{' '}
            <em style={{
              fontStyle: 'normal',
              background: 'linear-gradient(135deg, var(--accent-gold), #D4A853)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              ClearSignal
            </em>
            {' '}works
          </h1>
          <p style={{
            fontSize: 17,
            lineHeight: 1.65,
            color: 'var(--ink-secondary)',
          }}>
            A 9-stage AI pipeline that ingests raw RSS feeds, discovers story clusters
            through semantic similarity, and generates neutral AP-style analyses —
            without human editorial input.
          </p>
        </div>

        {/* Pipeline strip */}
        <div className="hiw-pipeline" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          flexWrap: 'wrap',
          marginTop: 'var(--space-lg)',
          padding: 'var(--space-md) var(--space-lg)',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          maxWidth: 920,
          marginLeft: 'auto',
          marginRight: 'auto',
        }}>
          {PIPELINE_NODES.map((node, i) => (
            <span key={node.label} style={{ display: 'contents' }}>
              <PipelineNode label={node.label} type={node.type} />
              {i < PIPELINE_NODES.length - 1 && (
                <>
                  <span className="hiw-arrow" style={{ color: '#ccc', fontSize: 16, flexShrink: 0 }}>&rarr;</span>
                  <Connector />
                </>
              )}
            </span>
          ))}
        </div>

        {/* Stats row */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-md)',
          marginTop: 'var(--space-md)',
        }}>
          {HERO_STATS.map((stat, i) => (
            <span key={stat.label} style={{ display: 'contents' }}>
              <div style={{ textAlign: 'center' }}>
                <span style={{
                  fontFamily: "'Playfair Display', serif",
                  fontWeight: 800,
                  fontSize: 20,
                  color: 'var(--accent-blue-deep)',
                  display: 'block',
                }}>
                  {stat.value}
                </span>
                <span style={{
                  fontSize: 11,
                  color: 'var(--ink-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                }}>
                  {stat.label}
                </span>
              </div>
              {i < HERO_STATS.length - 1 && (
                <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
              )}
            </span>
          ))}
        </div>
      </section>

      {/* ── Principle Cards ── */}
      <div className="hiw-principles" style={{
        maxWidth: 1080,
        margin: '0 auto',
        padding: 'var(--space-xl) 48px var(--space-lg)',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 'var(--space-md)',
      }}>
        {PRINCIPLES.map((p) => (
          <div key={p.title} style={{
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: 'var(--space-md)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, marginBottom: 'var(--space-sm)' }}>{p.icon}</div>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontWeight: 800,
              fontSize: 18,
              marginBottom: 'var(--space-xs)',
            }}>
              {p.title}
            </div>
            <div style={{
              fontSize: 14,
              lineHeight: 1.5,
              color: 'var(--ink-secondary)',
            }}>
              {p.desc}
            </div>
          </div>
        ))}
      </div>

      {/* ── Phase 1: Collection and Discovery ── */}
      <PhaseSection
        num="Phase 1"
        title="Collection and Discovery"
        sub="Raw articles are pulled from 40+ feeds, embedded into vector space, and grouped into stories by semantic similarity."
      >
        <FlowDiagram>
          <div className="hiw-flow-h">
            {PHASE1_COLS.map((col, i) => (
              <span key={col.label} style={{ display: 'contents' }}>
                <FlowCol boxType={col.boxType} label={col.label} desc={col.desc} isLast={i === PHASE1_COLS.length - 1} />
                {i < PHASE1_COLS.length - 1 && <Connector />}
              </span>
            ))}
          </div>
        </FlowDiagram>
      </PhaseSection>

      {/* ── Phase 2: Evaluation and Triage ── */}
      <PhaseSection
        num="Phase 2"
        title="Evaluation and Triage"
        sub="Every topic is validated for recency, scored for real-world impact, and triaged by an editorial selection model that decides what gets deep analysis."
        warm
      >
        <FlowDiagram warm>
          <div className="hiw-flow-h">
            {PHASE2_COLS.map((col, i) => (
              <span key={col.label} style={{ display: 'contents' }}>
                <FlowCol boxType={col.boxType} label={col.label} desc={col.desc} isLast={i === PHASE2_COLS.length - 1} />
                {i < PHASE2_COLS.length - 1 && <Connector />}
              </span>
            ))}
          </div>
        </FlowDiagram>
      </PhaseSection>

      {/* ── Phase 3: Deep Analysis ── */}
      <PhaseSection
        num="Phase 3"
        title="Deep Analysis"
        sub="Selected stories get full article extraction, source-blind framing classification, and a structured editorial analysis from the most capable model."
      >
        <FlowDiagram>
          <div className="hiw-flow-split">
            {/* Left path */}
            <div className="hiw-split-left" style={{ gap: 12 }}>
              <SplitBox
                borderColor="var(--accent-blue)"
                bg="rgba(43,76,126,0.04)"
                labelColor="var(--accent-blue-deep)"
                label="Scrape"
                desc="Full article body text extracted via trafilatura content-aware parsing. Only runs for selected stories — no unnecessary load on source sites."
              />
              <div className="hiw-arrow" style={{ textAlign: 'center', color: 'var(--border)', fontSize: 18 }}>&darr;</div>
              <Connector />
              <SplitBox
                borderColor="var(--accent-gold)"
                bg="rgba(200,150,62,0.04)"
                labelColor="var(--accent-gold)"
                label="Frame · Haiku"
                desc="Each article classified into 1 of 7 framing categories from its language alone — source identity is hidden. Alarmist, reassuring, adversarial, institutional, human-interest, investigative, or neutral."
              />
            </div>

            {/* Merge arrow */}
            <div className="hiw-split-merge hiw-arrow">
              &rarr;
            </div>

            {/* Right: final analysis */}
            <div className="hiw-split-right">
              <Connector />
              <div style={{
                background: 'var(--accent-blue-deep)',
                color: '#fff',
                borderRadius: 8,
                padding: '20px 24px',
                minHeight: 168,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
              }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 14,
                  fontWeight: 500,
                  letterSpacing: '0.3px',
                  color: '#fff',
                  display: 'block',
                  marginBottom: 6,
                }}>
                  Analyze · Sonnet
                </span>
                <div style={{
                  fontSize: 13,
                  color: 'rgba(255,255,255,0.6)',
                  lineHeight: 1.5,
                  marginTop: 8,
                }}>
                  AP-style lede, flowing editorial narrative with inline framing contrasts, source spectrum across the political divide, and a concrete bottom line. Output as structured JSON.
                </div>
              </div>
            </div>
          </div>
        </FlowDiagram>
      </PhaseSection>

      {/* ── Footer ── */}
      <footer style={{
        textAlign: 'center',
        padding: 'var(--space-lg) 48px',
        borderTop: '1px solid var(--border)',
      }}>
        <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
          &copy; 2025 ClearSignal — Tracking media coverage across the political spectrum.
        </p>
      </footer>
    </div>
  );
}

/* ── Data ── */

const PIPELINE_NODES = [
  { label: 'Ingest', type: 'src' },
  { label: 'Cluster', type: 'proc' },
  { label: 'Label', type: 'proc' },
  { label: 'Validate', type: 'ai-light' },
  { label: 'Score', type: 'proc' },
  { label: 'Select', type: 'ai-light' },
  { label: 'Scrape', type: 'proc' },
  { label: 'Frame', type: 'proc' },
  { label: 'Analyze', type: 'ai-heavy' },
];

const HERO_STATS = [
  { value: '40+', label: 'RSS feeds' },
  { value: '9', label: 'stages' },
  { value: '15m', label: 'cycle interval' },
];

const PRINCIPLES = [
  {
    icon: '\u25C7',
    title: 'Source-Blind Framing',
    desc: "Framing is classified from language patterns, not source identity. The system doesn\u2019t know which outlet is \u201Cleft\u201D or \u201Cright\u201D until after analysis.",
  },
  {
    icon: '\u25C8',
    title: 'Coverage Gap Detection',
    desc: 'Every topic gets an impact score and a coverage score. The delta between them reveals what the media ecosystem is over- or under-covering.',
  },
  {
    icon: '\u25C6',
    title: 'Multi-Model Architecture',
    desc: 'Fast models handle ingestion and triage. The most capable model is reserved for final analysis — balancing cost, speed, and depth.',
  },
];

const PHASE1_COLS = [
  { boxType: 'source', label: '40+ RSS Feeds', desc: 'Left, center, and right outlets pulled concurrently via httpx async and feedparser every 15 minutes.' },
  { boxType: 'process', label: 'Normalize and Dedup', desc: 'URLs are canonicalized and duplicates dropped before storage.' },
  { boxType: 'process', label: 'Embed \u2192 384d Vectors', desc: 'Each headline is embedded into 384-dimensional semantic space using text-embedding-3-small, stored in pgvector.' },
  { boxType: 'ai', label: 'HDBSCAN Cluster', desc: 'Density-based clustering discovers story groups by cosine similarity. Oversized clusters are split, near-duplicates merged.' },
  { boxType: 'ai', label: 'Label \u00B7 Haiku', desc: 'Each cluster gets a neutral wire-service headline. Vague or truncated labels are caught and rewritten.' },
];

const PHASE2_COLS = [
  { boxType: 'ai', label: 'Validate \u00B7 GPT-4o-mini', desc: 'Two-step filter with a 30-day recency window. Regex pre-filter catches historical events; the model handles ambiguous cases. Only current topics advance.' },
  { boxType: 'process', label: 'Score: Impact 0-100', desc: '5-factor weighted model: policy scope, population affected, economic magnitude, institutional precedent, and irreversibility. Scored by Claude Haiku.' },
  { boxType: 'process', label: 'Score: Coverage 0-100', desc: 'Computed from signal data: article volume, source diversity, recency, velocity, VADER sentiment, and attention percentile. No AI needed.' },
  { boxType: 'ai', label: 'Select \u00B7 GPT-4o-mini', desc: 'Editorial triage. Picks up to 10 stories per cycle, prioritizing high impact with multi-source coverage, increasing velocity, and framing divergence. Also flags stale analyses for re-generation.' },
];

/* ── Sub-components ── */

function Connector() {
  return <div className="hiw-connector" />;
}

function PipelineNode({ label, type }) {
  const styles = {
    src: { background: '#F3F4F6', color: 'var(--ink-muted)' },
    proc: { background: 'rgba(43,76,126,0.08)', color: 'var(--accent-blue-deep)' },
    'ai-light': { background: 'rgba(200,150,62,0.08)', color: 'var(--accent-gold)' },
    'ai-heavy': { background: 'var(--accent-blue-deep)', color: '#fff' },
  };
  return (
    <div className="hiw-pipe-node" style={{
      padding: '10px 16px',
      borderRadius: 6,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 12,
      fontWeight: 500,
      textAlign: 'center',
      whiteSpace: 'nowrap',
      ...styles[type],
    }}>
      {label}
    </div>
  );
}

function PhaseSection({ num, title, sub, warm, children }) {
  return (
    <div className={`hiw-phase${warm ? ' hiw-phase-warm' : ''}`} style={{
      padding: '72px 48px',
      background: warm ? 'var(--bg-warm)' : undefined,
    }}>
      <div style={{ maxWidth: 1080, margin: '0 auto' }}>
        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            fontWeight: 500,
            color: 'var(--accent-gold)',
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            marginBottom: 'var(--space-xs)',
          }}>
            {num}
          </div>
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 800,
            fontSize: 32,
            letterSpacing: '-0.5px',
            marginBottom: 'var(--space-xs)',
          }}>
            {title}
          </div>
          <div style={{
            fontSize: 16,
            lineHeight: 1.6,
            color: 'var(--ink-secondary)',
            maxWidth: 640,
          }}>
            {sub}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function FlowDiagram({ warm, children }) {
  return (
    <div className="hiw-flow-diagram" style={{
      background: warm ? '#fff' : 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: 'var(--space-xl) var(--space-lg)',
    }}>
      {children}
    </div>
  );
}

function FlowCol({ boxType, label, desc, isLast }) {
  const BOX_STYLES = {
    source: { borderColor: '#D1D5DB', background: '#F9FAFB', labelColor: 'var(--ink-muted)' },
    process: { borderColor: 'var(--accent-blue)', background: 'rgba(43,76,126,0.04)', labelColor: 'var(--accent-blue-deep)' },
    ai: { borderColor: 'var(--accent-gold)', background: 'rgba(200,150,62,0.04)', labelColor: 'var(--accent-gold)' },
  };
  const s = BOX_STYLES[boxType] || BOX_STYLES.process;

  return (
    <div className={`hiw-flow-col${isLast ? ' hiw-flow-col-last' : ''}`}>
      <div style={{
        border: `1px solid ${s.borderColor}`,
        background: s.background,
        borderRadius: 8,
        padding: '16px 18px',
        width: '100%',
        marginBottom: 12,
        minHeight: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13,
          fontWeight: 500,
          letterSpacing: '0.3px',
          color: s.labelColor,
        }}>
          {label}
        </span>
      </div>
      <div style={{
        fontSize: 13,
        color: 'var(--ink-muted)',
        lineHeight: 1.5,
      }}>
        {desc}
      </div>
    </div>
  );
}

function SplitBox({ borderColor, bg, labelColor, label, desc }) {
  return (
    <div style={{
      border: `1px solid ${borderColor}`,
      background: bg,
      borderRadius: 8,
      padding: '20px 24px',
    }}>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 13,
        fontWeight: 500,
        letterSpacing: '0.3px',
        color: labelColor,
        display: 'block',
        marginBottom: 6,
      }}>
        {label}
      </span>
      <div style={{ fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.5 }}>
        {desc}
      </div>
    </div>
  );
}
