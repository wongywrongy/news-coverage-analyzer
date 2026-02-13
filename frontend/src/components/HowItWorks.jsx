'use client';

import Link from 'next/link';

/* ── Score node positions for the orbital diagram ── */
const SCORE_NODES = [
  { top: '18%', left: '50%', pip: 'ai', icon: 'AI', name: 'Impact', sub: 'Real-world significance' },
  { top: '68%', left: '22%', pip: '', icon: 'C', name: 'Coverage', sub: 'Source breadth and diversity' },
  { top: '68%', left: '78%', pip: '', icon: 'C', name: 'Attention', sub: 'Volume of articles' },
  { top: '6%', left: '22%', pip: '', icon: 'NLP', name: 'Sentiment', sub: 'Emotional temp by lean' },
  { top: '6%', left: '78%', pip: '', icon: 'C', name: 'Timeline', sub: 'Story lifecycle stage' },
  { top: '42%', left: '4%', pip: '', icon: 'C', name: 'Gaps', sub: 'Who is not covering this' },
  { top: '42%', left: '96%', pip: '', icon: 'F', name: 'Heat', sub: 'Front-page prominence' },
  { top: '88%', left: '6%', pip: '', icon: 'A', name: 'Insights', sub: 'Category-level patterns' },
  { top: '88%', left: '94%', pip: '', icon: 'S', name: 'Ranking', sub: 'Final sort order' },
];

/* ── Document preview bar widths ── */
const DOC_LEAD_BARS = [
  { h: 8, w: '100%' }, { h: 8, w: '88%' }, { h: 8, w: '62%' },
];
const DOC_BODY_BARS = [
  { h: 6, w: '100%' }, { h: 6, w: '96%' }, { h: 6, w: '100%' }, { h: 6, w: '92%' },
  { h: 6, w: '100%' }, { h: 6, w: '87%' }, { h: 6, w: '100%' }, { h: 6, w: '44%' },
];

/* ── Sidebar fields ── */
const DOC_FIELDS = [
  { name: 'headline', desc: 'Neutral, AP-style headline' },
  { name: 'lead', desc: 'Opening paragraph with key facts' },
  { name: 'body', desc: 'Flowing analysis with woven framing contrasts' },
  { name: 'framing_cards', desc: 'Source-by-source comparisons' },
  { name: 'bottom_line', desc: 'Single key takeaway' },
  { name: 'source_coverage', desc: 'Per-outlet framing, inclusions, omissions' },
];

/* ── Framing categories ── */
const FRAMES = [
  'Accountability', 'Alarmist', 'Contextual', 'Dismissive',
  'Empathetic', 'Investigative', 'Neutral / Wire',
];

/* ── Model tier data ── */
const MODEL_TIERS = [
  {
    cls: 'tier-fast', label: 'Speed Tier',
    models: [
      { name: 'text-embedding-3-small', task: 'Embeddings', why: '384-dim vectors at scale' },
      { name: 'VADER', task: 'Sentiment analysis', why: 'Per-article tone, grouped by lean' },
    ],
  },
  {
    cls: 'tier-reason', label: 'Reasoning Tier',
    models: [
      { name: 'Claude Haiku', task: 'Labeling, scoring, framing', why: 'Hundreds of calls per cycle' },
      { name: 'GPT-4o-mini', task: 'Validation and selection', why: 'Structured editorial reasoning' },
    ],
  },
  {
    cls: 'tier-gen', label: 'Generation Tier',
    models: [
      { name: 'Claude Sonnet', task: 'Full analysis generation', why: 'Long-form editorial quality' },
    ],
  },
];

/* ── Principles data ── */
const PRINCIPLES = [
  {
    num: '01', title: 'Source-Blind Framing',
    desc: 'Analyses never say "the liberal take" or "the conservative view." Framing contrasts are attributed to specific outlets. CNN emphasized X while Fox focused on Y. Readers see what each source actually reported. No shorthand. No labels.',
  },
  {
    num: '02', title: 'Coverage Gap Detection',
    desc: 'Every story is checked for who is not covering it. If fifteen right-leaning outlets cover a congressional hearing but only two left-leaning outlets mention it, that silence is surfaced as data. What is missing is often as revealing as what is there.',
  },
  {
    num: '03', title: 'Separation of Concerns',
    desc: 'No single model makes all the decisions. No single formula drives all the scores. Fast models handle volume. Powerful models handle nuance. Deterministic formulas handle ranking. This prevents any single point of failure or bias amplification.',
  },
];

export default function HowItWorks() {
  return (
    <div style={{ background: 'var(--bg)' }}>
      {/* ═══ HERO ═══ */}
      <section className="meth-hero">
        <div className="meth-hero-inner">
          <h1>From raw feeds to<br />structured clarity</h1>
          <p className="meth-hero-sub">
            Four interconnected pipelines. Six specialized AI models. Twenty-seven
            stages of processing. Zero editorial bias. Here is how ClearSignal turns
            the noise of modern media into signal.
          </p>

          {/* Pipeline strip */}
          <div className="pipeline-strip">
            <div className="pipeline-block">
              <div className="pipeline-name">Ingest</div>
              <div className="pipeline-stages">5 stages</div>
            </div>
            <div className="pipeline-arrow">&#9656;</div>
            <div className="pipeline-block">
              <div className="pipeline-name">Cluster</div>
              <div className="pipeline-stages">9 stages</div>
            </div>
            <div className="pipeline-arrow">&#9656;</div>
            <div className="pipeline-block">
              <div className="pipeline-name">Score</div>
              <div className="pipeline-stages">9 stages</div>
            </div>
            <div className="pipeline-arrow">&#9656;</div>
            <div className="pipeline-block final">
              <div className="pipeline-name">Analyze</div>
              <div className="pipeline-stages">4 stages</div>
            </div>
          </div>

          <div className="meth-principles-row">
            Source-Blind Framing <span className="sep">&middot;</span>
            Coverage Gap Detection <span className="sep">&middot;</span>
            Multi-Model Architecture
          </div>
        </div>
      </section>

      {/* ═══ PIPELINE 01: INGEST ═══ */}
      <section className="meth-section">
        <div className="meth-section-inner">
          <span className="meth-section-label">Pipeline 01</span>
          <div className="meth-section-header">
            <div className="meth-section-number">01</div>
            <h2 className="meth-section-title">Ingest</h2>
          </div>
          <p className="meth-section-desc">
            Every cycle, ClearSignal pulls from over a hundred sources spanning
            the full political spectrum, from Fox News to NPR, Wall Street Journal
            to The Guardian, Reuters to Daily Wire. Articles are normalized,
            deduplicated against both URL and semantic similarity, transformed into
            high-dimensional vector embeddings, and stored for downstream analysis.
            Nothing gets through twice. Nothing gets missed.
          </p>

          <Conveyor nodes={[
            { num: 1, label: 'Fetch', detail: 'RSS feeds and news APIs', key: true },
            { num: 2, label: 'Normalize', detail: 'URL resolution and cleanup' },
            { num: 3, label: 'Dedup', detail: 'URL and semantic similarity' },
            { num: 4, label: 'Embed', detail: '384-dimension vectors', key: true },
            { num: 5, label: 'Store', detail: 'Supabase pgvector' },
          ]} />

          <div className="meth-callout">
            <div>
              <div className="callout-label">Source Spectrum Tagging</div>
              <div className="callout-text">
                Every feed is tagged with its editorial lean using AllSides and
                Ad Fontes Media ratings: left, left-center, center, right-center,
                right, and wire service. This is not cosmetic. It powers coverage
                gap detection downstream. When ClearSignal says a story is
                &ldquo;undercovered on the right,&rdquo; that is a measured claim
                backed by tagged source data.
              </div>
            </div>
            <div>
              <div className="callout-label">Semantic Deduplication</div>
              <div className="callout-text">
                URL matching catches the obvious duplicates. But when a wire
                service publishes a story and dozens of outlets run slightly
                rewritten versions, URL matching fails. ClearSignal uses cosine
                similarity on title embeddings to catch syndicated rewrites,
                ensuring each story is counted once regardless of how many outlets
                picked it up.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ PIPELINE 02: CLUSTER ═══ */}
      <section className="meth-section alt">
        <div className="meth-section-inner">
          <span className="meth-section-label">Pipeline 02</span>
          <div className="meth-section-header">
            <div className="meth-section-number">02</div>
            <h2 className="meth-section-title">Cluster</h2>
          </div>
          <p className="meth-section-desc">
            Raw articles become stories. ClearSignal groups semantically related
            articles using density-based clustering on their vector embeddings,
            with no predefined topic count and no forced grouping. Each cluster
            receives an AI-generated neutral headline, named entities are
            extracted, and a knowledge graph connects people, organizations, and
            legislation across stories.
          </p>

          <div className="conveyor-group">
            <Conveyor nodes={[
              { num: 1, label: 'Assign', detail: 'Fast-path matching', key: true },
              { num: 2, label: 'Discover', detail: 'HDBSCAN clustering', key: true },
              { num: 3, label: 'Split', detail: 'Oversized clusters' },
              { num: 4, label: 'Label', detail: 'AI topic naming', key: true },
              { num: 5, label: 'Rename', detail: 'Headline polish' },
            ]} />
            <Conveyor nodes={[
              { num: 6, label: 'Entities', detail: 'NER extraction', key: true },
              { num: 7, label: 'Graph', detail: 'PageRank scoring', key: true },
              { num: 8, label: 'Merge', detail: 'Converged stories' },
              { num: 9, label: 'Validate', detail: 'Currency and relevance' },
            ]} />
          </div>

          <div className="meth-callout">
            <div>
              <div className="callout-label">Why HDBSCAN</div>
              <div className="callout-text">
                Most clustering algorithms require a predefined number of clusters.
                That is impossible with news. HDBSCAN finds natural density
                boundaries in the embedding space and handles noise gracefully.
                Articles that do not belong to any story become outliers, not
                forced matches.
              </div>
            </div>
            <div>
              <div className="callout-label">Entity Knowledge Graph</div>
              <div className="callout-text">
                People, organizations, legislation, and court cases are extracted
                from every topic and connected by co-occurrence. PageRank-style
                importance scoring means a senator appearing across 12 stories
                alongside the Supreme Court carries more weight than a name
                appearing in 10 unrelated local stories.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ PIPELINE 03: SCORE ═══ */}
      <section className="meth-section">
        <div className="meth-section-inner">
          <span className="meth-section-label">Pipeline 03</span>
          <div className="meth-section-header">
            <div className="meth-section-number">03</div>
            <h2 className="meth-section-title">Score</h2>
          </div>
          <p className="meth-section-desc">
            Every story is measured across nine dimensions. Not just &ldquo;is this
            important?&rdquo; but how much attention is it getting, who is covering
            it, what is the emotional temperature across the spectrum, and crucially:
            what are people missing? These scores drive the homepage ranking, trending
            indicators, and coverage gap alerts.
          </p>

          {/* Orbital scoring visual (desktop) */}
          <div className="scoring-visual">
            <div className="orbit-ring inner" />
            <div className="orbit-ring outer" />
            <div className="scoring-hub">
              <div className="scoring-hub-label">Each Story</div>
              <div className="scoring-hub-title">9 Scores</div>
            </div>
            {SCORE_NODES.map((n) => (
              <div key={n.name} className="score-node" style={{ top: n.top, left: n.left }}>
                <div className={`score-pip${n.pip === 'ai' ? ' ai-pip' : ''}`}>
                  <span className="score-pip-icon">{n.icon}</span>
                </div>
                <div className="score-node-name">{n.name}</div>
                <div className="score-node-sub">{n.sub}</div>
              </div>
            ))}
          </div>

          {/* Mobile fallback grid */}
          <div className="scoring-fallback" style={{
            gridTemplateColumns: 'repeat(3, 1fr)', gap: 16,
            marginBottom: 48,
          }}>
            {SCORE_NODES.map((n) => (
              <div key={n.name} style={{
                textAlign: 'center', padding: 16,
                border: '1px solid var(--border)', borderRadius: 8,
              }}>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                  fontWeight: 600, color: n.pip === 'ai' ? 'var(--accent-gold)' : 'var(--ink-muted)',
                  marginBottom: 4,
                }}>{n.icon}</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{n.name}</div>
                <div style={{ fontSize: 10, color: '#8A8A82', marginTop: 2 }}>{n.sub}</div>
              </div>
            ))}
          </div>

          <div className="meth-callout">
            <div>
              <div className="callout-label">Sentiment by Lean</div>
              <div className="callout-text">
                Sentiment analysis runs per article, then results are grouped by
                outlet political lean. This surfaces editorial divergence
                quantitatively: when left-leaning outlets cover a story with alarm
                while right-leaning outlets dismiss it, that pattern is captured as
                measured framing data, not opinion.
              </div>
            </div>
            <div>
              <div className="callout-label">Deterministic Ranking</div>
              <div className="callout-text">
                The final homepage ranking uses a weighted formula with no AI in
                the loop. Impact, source breadth, publishing velocity, and editorial
                divergence are combined with time-decay factors. Rankings are
                reproducible, auditable, and fast.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ PIPELINE 04: ANALYZE ═══ */}
      <section className="meth-section alt">
        <div className="meth-section-inner">
          <span className="meth-section-label">Pipeline 04</span>
          <div className="meth-section-header">
            <div className="meth-section-number">04</div>
            <h2 className="meth-section-title">Analyze</h2>
          </div>
          <p className="meth-section-desc">
            The final and most sophisticated stage. An AI editorial triage selects
            which stories warrant deep analysis. Full article bodies are scraped.
            Per-article editorial framing is classified across seven categories.
            Then a dedicated analysis model generates a complete structured
            breakdown: neutral, editorial-quality prose with source-specific framing
            contrasts, coverage comparisons, and verified claims.
          </p>

          <Conveyor nodes={[
            { num: 1, label: 'Select', detail: 'Editorial triage' },
            { num: 2, label: 'Scrape', detail: 'Full article body' },
            { num: 3, label: 'Frame', detail: '7 framing categories', key: true },
            { num: 4, label: 'Analyze', detail: 'Structured generation', key: true },
          ]} />

          {/* Document preview card */}
          <div className="doc-preview-wrapper">
            <div className="doc-preview">
              <div className="doc-main">
                <span className="doc-badge">Analysis Output</span>

                <div className="doc-line">
                  <div className="doc-line-label">headline</div>
                  <div className="doc-line-bar">
                    <div className="doc-line-bar-fill" style={{ width: '75%' }} />
                  </div>
                </div>

                <div className="doc-line">
                  <div className="doc-line-label">lead</div>
                  {DOC_LEAD_BARS.map((b, i) => (
                    <div key={i} className="doc-line-bar" style={{
                      height: b.h, marginBottom: i < DOC_LEAD_BARS.length - 1 ? 4 : 0,
                    }}>
                      <div className="doc-line-bar-fill" style={{ width: b.w }} />
                    </div>
                  ))}
                </div>

                <div className="doc-line">
                  <div className="doc-line-label">body</div>
                  {DOC_BODY_BARS.map((b, i) => (
                    <div key={i} className="doc-line-bar" style={{
                      height: b.h, marginBottom: i < DOC_BODY_BARS.length - 1 ? 3 : 0,
                    }}>
                      <div className="doc-line-bar-fill" style={{ width: b.w }} />
                    </div>
                  ))}
                </div>

                <div className="doc-line" style={{ marginTop: 20 }}>
                  <div className="doc-line-label">framing_cards</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {[1, 2, 3].map((n) => (
                      <div key={n} style={{
                        flex: 1, height: 40, borderRadius: 4,
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.08)',
                      }} />
                    ))}
                  </div>
                </div>

                <div className="doc-line">
                  <div className="doc-line-label">bottom_line</div>
                  <div className="doc-line-bar" style={{ height: 8 }}>
                    <div className="doc-line-bar-fill" style={{ width: '70%' }} />
                  </div>
                </div>
              </div>

              <div className="doc-sidebar">
                {DOC_FIELDS.map((f) => (
                  <div key={f.name} className="doc-field">
                    <div className="doc-field-name">{f.name}</div>
                    <div className="doc-field-desc">{f.desc}</div>
                  </div>
                ))}
              </div>

              <div className="doc-footer-row">
                <span><strong>Reads</strong> 8 to 30 full articles per story</span>
                <span><strong>Generates</strong> 2,000 to 4,000 words of structured analysis</span>
              </div>
            </div>
          </div>

          <div className="meth-callout single-col">
            <div>
              <div className="callout-label">Seven Editorial Frames</div>
              <div className="callout-text">
                Every article is classified before the final analysis begins. This
                gives the analysis model structured framing data to work with,
                concrete categorization rather than asking it to detect bias from
                raw text.
                <div className="framing-pills">
                  {FRAMES.map((f) => (
                    <span key={f} className="framing-pill">{f}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ MULTI-MODEL ARCHITECTURE ═══ */}
      <section className="meth-section-dark">
        <div className="meth-section-inner">
          <h2>Six models, each chosen for the job</h2>
          <p className="lead">
            ClearSignal does not route everything through one model and hope for
            the best. Fast models handle volume. Reasoning models handle editorial
            decisions. The most capable model is reserved for the final analysis,
            where nuance and quality matter most.
          </p>

          <div className="model-tiers">
            {MODEL_TIERS.map((tier) => (
              <div key={tier.cls} className={`model-tier ${tier.cls}`}>
                <div className="tier-label">{tier.label}</div>
                <ul className="tier-model-list">
                  {tier.models.map((m) => (
                    <li key={m.name} className="tier-model-item">
                      <div className="tier-model-name">{m.name}</div>
                      <div className="tier-model-task">{m.task}</div>
                      <div className="tier-model-why">{m.why}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ PRINCIPLES ═══ */}
      <section className="meth-section">
        <div className="meth-section-inner">
          <span className="meth-section-label">Core Principles</span>
          <div style={{ marginBottom: 48 }} />
          <div className="meth-principles-grid">
            {PRINCIPLES.map((p) => (
              <div key={p.num} className="principle">
                <div className="principle-number">{p.num}</div>
                <div className="principle-title">{p.title}</div>
                <div className="principle-desc">{p.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ FOOTER CTA ═══ */}
      <div className="meth-footer-cta">
        <Link href="/news">See today&#39;s analysis &rarr;</Link>
      </div>
    </div>
  );
}

/* ── Conveyor sub-component ── */

function Conveyor({ nodes }) {
  return (
    <div className="conveyor">
      {nodes.map((n) => (
        <div key={n.num} className={`conveyor-node${n.key ? ' key' : ''}`}>
          <div className="node-circle">
            <div className="node-fill">{n.num}</div>
          </div>
          <div className="node-label">{n.label}</div>
          <div className="node-detail">{n.detail}</div>
        </div>
      ))}
    </div>
  );
}
