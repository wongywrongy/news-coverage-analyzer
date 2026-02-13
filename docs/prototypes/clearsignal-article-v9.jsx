import { useState, useEffect, useRef } from "react";

function Counter({ target, duration }) {
  var _val = useState(0), val = _val[0], setVal = _val[1];
  var ref = useRef(null);
  useEffect(function() {
    var startTime = null;
    var dur = duration || 1200;
    function step(ts) {
      if (!startTime) startTime = ts;
      var p = Math.min((ts - startTime) / dur, 1);
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) ref.current = requestAnimationFrame(step);
    }
    ref.current = requestAnimationFrame(step);
    return function() { if (ref.current) cancelAnimationFrame(ref.current); };
  }, [target, duration]);
  return val;
}

function FadeIn({ delay, children }) {
  var _vis = useState(false), vis = _vis[0], setVis = _vis[1];
  useEffect(function() { var t = setTimeout(function() { setVis(true); }, delay || 0); return function() { clearTimeout(t); }; }, [delay]);
  return <div style={{ opacity: vis ? 1 : 0, transform: vis ? "translateY(0)" : "translateY(10px)", transition: "opacity 0.5s ease, transform 0.5s ease" }}>{children}</div>;
}

function FactorRow({ label, value, max }) {
  var _vis = useState(false), vis = _vis[0], setVis = _vis[1];
  useEffect(function() { var t = setTimeout(function() { setVis(true); }, 500); return function() { clearTimeout(t); }; }, []);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6B7280", width: 48, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 6, background: "#E8E4DA", borderRadius: 3 }}>
        <div style={{ height: "100%", borderRadius: 3, background: "#4A6FA5", width: vis ? (value / max * 100) + "%" : "0%", transition: "width 0.8s cubic-bezier(0.16,1,0.3,1)" }} />
      </div>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#374151", fontWeight: 600, width: 36, textAlign: "right", flexShrink: 0 }}>{value}/{max}</span>
    </div>
  );
}

var S = {
  headline: "US Iran Nuclear Talks Resume in Oman With Economic Stakes Rising",
  lede: "The United States and Iran have returned to the negotiating table in Muscat, Oman, entering a critical phase of discussions over nuclear enrichment limits and sanctions relief that could reshape global energy markets.",
  category: "DIPLOMACY",
  group: "Economy & Business",
  groupColor: "#8B7520",
  articles: 38,
  sources: 14,
  impactScore: 72,
  attentionScore: 58,
  days: [3,4,5,6,7,8,9,10,11,12,13],
  firstTracked: "Jan 28",
  lastArticle: "Feb 8",
  activeDays: 11,
  context: [
    "Diplomatic negotiations between the United States and Iran resumed in Oman on February 5, marking the third round of indirect talks since channels reopened in late 2025. The discussions center on Iran's uranium enrichment program, which Tehran has expanded to 60% purity, and the potential easing of economic sanctions that have constrained Iran's oil exports since 2018.",
    "The talks come amid shifting geopolitical dynamics in the Middle East. According to Reuters, Oman was chosen as a neutral venue due to its longstanding role as a back-channel mediator between Washington and Tehran. The Wall Street Journal reported that European allies have pressed for a framework agreement before the U.S. election cycle intensifies, while Iranian state media emphasized that any deal must include full sanctions relief.",
    "Economic analysts note the talks carry significant market implications. Oil futures fluctuated by 3% during the first day of negotiations, as reported by Bloomberg. The Congressional Budget Office estimated that renewed Iranian oil exports could reduce global crude prices by $8 to $12 per barrel, affecting energy markets worldwide.",
    "Both sides face domestic political constraints. According to the New York Times, the administration is navigating opposition from lawmakers who argue any agreement would be insufficient without addressing Iran's ballistic missile program. Iranian negotiators, as reported by Al Jazeera, must contend with hardliners who view sanctions relief as a prerequisite rather than a concession.",
  ],
  contrasts: [
    { angle: "Framing of U.S. negotiating position", descriptions: [
      { framing: "Emphasize diplomatic pragmatism and willingness to pursue incremental agreements on enrichment limits", sources: ["NYT", "AP", "Reuters"] },
      { framing: "Characterize the approach as making concessions to a hostile regime without adequate security guarantees", sources: ["Fox News", "WSJ Editorial", "NY Post"] },
    ]},
    { angle: "Economic impact emphasis", descriptions: [
      { framing: "Focus on potential oil price reduction and consumer benefit from increased Iranian supply", sources: ["Bloomberg", "CNBC", "Reuters"] },
      { framing: "Highlight risk of sanctions relief funding Iranian military programs and regional proxy activities", sources: ["Fox News", "Daily Wire", "Wash. Examiner"] },
    ]},
    { angle: "Role of regional actors", descriptions: [
      { framing: "Frame Gulf states, particularly Oman and Qatar, as constructive mediators advancing stability", sources: ["Al Jazeera", "BBC", "AP"] },
      { framing: "Focus on Israeli and Saudi concerns about any rapprochement with Tehran", sources: ["CNN", "WSJ", "Times of Israel"] },
    ]},
  ],
  facts: [
    "Talks resumed in Muscat, Oman on February 5, 2026",
    "Iran has enriched uranium to 60% purity",
    "Oil futures moved 3% during the first day of negotiations",
    "This is the third round of indirect talks since late 2025",
    "CBO estimates Iranian exports could reduce crude prices by $8-12/barrel",
  ],
  bottomLine: "Negotiations are in a critical phase with both sides signaling flexibility on enrichment limits and sanctions, though domestic political opposition in both countries could derail progress. The next round is expected within two weeks.",
  spectrum: "This story received broad coverage across the political spectrum, with 38 articles from 14 sources. Wire services and centrist outlets focused on diplomatic mechanics, while outlets on both ends emphasized the risks of the other side's position. Economic framing was most prevalent among business-focused sources.",
  sourceList: [
    { name: "Reuters", n: 5 }, { name: "AP", n: 4 }, { name: "NYT", n: 3 }, { name: "WSJ", n: 3 },
    { name: "Bloomberg", n: 3 }, { name: "Fox News", n: 3 }, { name: "CNN", n: 2 }, { name: "Al Jazeera", n: 2 },
    { name: "BBC", n: 2 }, { name: "CNBC", n: 2 }, { name: "NY Post", n: 2 }, { name: "Wash. Examiner", n: 2 },
    { name: "Daily Wire", n: 1 }, { name: "Times of Israel", n: 1 },
  ],
  factors: [
    { label: "Pop.", value: 25, max: 30 },
    { label: "Econ.", value: 20, max: 25 },
    { label: "Policy", value: 15, max: 20 },
    { label: "Dur.", value: 9, max: 15 },
    { label: "Irrev.", value: 3, max: 10 },
  ],
};

function ContrastBlock({ contrast }) {
  var a = contrast.descriptions[0];
  var b = contrast.descriptions[1];
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 17, fontWeight: 700, color: "#111827", marginBottom: 16 }}>{contrast.angle}</div>
      <div style={{ position: "relative", display: "flex" }}>
        <div style={{ flex: 1, padding: "20px 24px", background: "rgba(74,111,165,0.04)", borderLeft: "4px solid #4A6FA5", borderTop: "1px solid rgba(74,111,165,0.12)", borderBottom: "1px solid rgba(74,111,165,0.12)" }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4A6FA5", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10, fontWeight: 600 }}>Framing A</div>
          <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#1F2937", lineHeight: 1.7, marginBottom: 14 }}>{a.framing}</p>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#4A6FA5", fontWeight: 500 }}>{a.sources.join(" · ")}</div>
        </div>
        <div style={{ width: 44, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div style={{ color: "#4A6FA5", fontSize: 14, lineHeight: 1, marginBottom: 2 }}>◂</div>
          <div style={{ width: 1, height: 24, background: "#D0D0D0" }} />
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#F0ECE2", border: "2px solid #D0D0D0", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'JetBrains Mono', monospace", fontSize: 9, fontWeight: 700, color: "#6B7280" }}>vs</div>
          <div style={{ width: 1, height: 24, background: "#D0D0D0" }} />
          <div style={{ color: "#C8A84E", fontSize: 14, lineHeight: 1, marginTop: 2 }}>▸</div>
        </div>
        <div style={{ flex: 1, padding: "20px 24px", background: "rgba(200,168,78,0.04)", borderRight: "4px solid #C8A84E", borderTop: "1px solid rgba(200,168,78,0.12)", borderBottom: "1px solid rgba(200,168,78,0.12)" }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#A08520", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10, fontWeight: 600 }}>Framing B</div>
          <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#1F2937", lineHeight: 1.7, marginBottom: 14 }}>{b.framing}</p>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#A08520", fontWeight: 500 }}>{b.sources.join(" · ")}</div>
        </div>
      </div>
    </div>
  );
}

export default function StoryDetail() {
  return (
    <div style={{ background: "#F0ECE2", minHeight: "100vh" }}>
      <style>{"@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;500;600;700;800&display=swap'); @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }"}</style>

      {/* Header */}
      <div style={{ background: "#FFFFFF", padding: "14px 44px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #E5E5E5" }}>
        <div style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 21, fontWeight: 700, cursor: "pointer" }}>
          <span style={{ color: "#111827" }}>Clear</span><span style={{ color: "#4A6FA5" }}>Signal</span>
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#4A6FA5", cursor: "pointer" }}>← Back to stories</div>
      </div>

      {/* ====== WHITE HEADER ZONE ====== */}
      <div style={{ background: "#FFFFFF", borderBottom: "2px solid #3D5F8F" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 44px 36px" }}>

          <FadeIn delay={100}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 20 }}>
              <span style={{ background: S.groupColor + "14", border: "1px solid " + S.groupColor + "30", color: S.groupColor, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, padding: "3px 10px", fontWeight: 600, letterSpacing: "0.04em" }}>{S.category}</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6B7280" }}>{S.group}</span>
            </div>
          </FadeIn>

          <FadeIn delay={200}>
            <h1 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 44, fontWeight: 800, color: "#111827", lineHeight: 1.08, letterSpacing: "-0.02em", marginBottom: 18, maxWidth: 820 }}>{S.headline}</h1>
          </FadeIn>

          <FadeIn delay={300}>
            <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 19, color: "#4B5563", lineHeight: 1.65, marginBottom: 24, maxWidth: 780 }}>{S.lede}</p>
          </FadeIn>

          <FadeIn delay={380}>
            <div style={{ marginBottom: 32 }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: "2px 0" }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#9CA3AF", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 10, fontWeight: 600 }}>Sources</span>
                {S.sourceList.map(function(src, i) {
                  return (
                    <span key={i} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, lineHeight: 2 }}>
                      <span style={{ color: "#111827" }}>{src.name}</span>
                      <span style={{ color: "#9CA3AF", fontSize: 11 }}>&thinsp;{src.n}</span>
                      {i < S.sourceList.length - 1 ? <span style={{ color: "#D0D0D0", margin: "0 6px" }}>·</span> : null}
                    </span>
                  );
                })}
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#9CA3AF", marginLeft: 10 }}>— {S.articles} articles total</span>
              </div>
            </div>
          </FadeIn>

          <FadeIn delay={450}>
            <div style={{ borderTop: "1px solid #E8E4DA", paddingTop: 24, display: "flex", gap: 32, alignItems: "flex-start" }}>
              <div style={{ flexShrink: 0, width: 220 }}>
                <div style={{ display: "flex", gap: 28, marginBottom: 16 }}>
                  <div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Impact</div>
                    <div style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 36, fontWeight: 700, color: "#111827", lineHeight: 1 }}><Counter target={S.impactScore} /></div>
                  </div>
                  <div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Coverage</div>
                    <div style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 36, fontWeight: 700, color: "#111827", lineHeight: 1 }}><Counter target={S.attentionScore} /></div>
                  </div>
                </div>
                <div>
                  <div style={{ height: 10, borderRadius: 2, overflow: "hidden", display: "flex", background: "#E8E4DA" }}>
                    {(function() { var segs = []; for (var i = 0; i < 14; i++) { segs.push(<div key={i} style={{ flex: 1, background: S.days.indexOf(i) >= 0 ? "#5578A8" : "transparent" }} />); } return segs; })()}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#9CA3AF" }}>{S.firstTracked}</span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#9CA3AF" }}>Today</span>
                  </div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#9CA3AF", marginTop: 6 }}>Active {S.activeDays} of 14 days</div>
                </div>
              </div>
              <div style={{ width: 1, background: "#E8E4DA", alignSelf: "stretch", flexShrink: 0 }} />
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 7, minWidth: 0 }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Impact factors</div>
                {S.factors.map(function(f) { return <FactorRow key={f.label} label={f.label} value={f.value} max={f.max} />; })}
              </div>
            </div>
          </FadeIn>
        </div>
      </div>

      {/* ====== ARTICLE BODY ====== */}
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "44px 24px 80px" }}>

        {/* ====== AGREED FACTS — first thing in the body, styled block ====== */}
        <FadeIn delay={550}>
          <div style={{ marginBottom: 36 }}>
            <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>What sources agree on</h2>
            <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#6B7280", lineHeight: 1.6, marginBottom: 18 }}>
              Undisputed facts reported across multiple outlets
            </p>
            <div style={{
              padding: "22px 26px",
              background: "rgba(74,111,165,0.03)",
              borderLeft: "4px solid #4A6FA5",
              borderTop: "1px solid rgba(74,111,165,0.10)",
              borderBottom: "1px solid rgba(74,111,165,0.10)",
              borderRight: "1px solid rgba(74,111,165,0.10)",
            }}>
              {S.facts.map(function(f, i) {
                return (
                  <div key={i} style={{ display: "flex", gap: 14, marginBottom: i < S.facts.length - 1 ? 14 : 0, alignItems: "flex-start" }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#4A6FA5", marginTop: 8, flexShrink: 0, opacity: 0.5 }} />
                    <span style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 16, color: "#1F2937", lineHeight: 1.65 }}>{f}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </FadeIn>

        <div style={{ height: 1, background: "#DDD7C5", margin: "36px 0" }} />

        {/* Context paragraphs */}
        <FadeIn delay={650}>
          {S.context.map(function(p, i) {
            return <p key={i} style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 18, color: "#1F2937", lineHeight: 1.85, marginBottom: 22 }}>{p}</p>;
          })}
        </FadeIn>

        <div style={{ height: 1, background: "#DDD7C5", margin: "40px 0" }} />

        {/* Contrasts */}
        <FadeIn delay={750}>
          <div style={{ marginBottom: 44 }}>
            <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>How coverage differs</h2>
            <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#6B7280", lineHeight: 1.6, marginBottom: 28 }}>Where sources diverge in their framing of this story</p>
            {S.contrasts.map(function(c, ci) { return <ContrastBlock key={ci} contrast={c} />; })}
          </div>
        </FadeIn>

        <div style={{ height: 1, background: "#DDD7C5", margin: "40px 0" }} />

        {/* Bottom line + spectrum */}
        <FadeIn delay={850}>
          <div style={{ marginBottom: 44 }}>
            <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 8 }}>Bottom line</h2>
            <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#6B7280", lineHeight: 1.6, marginBottom: 20 }}>What is known, what is uncertain, what to watch</p>

            <div>
              <div style={{
                padding: "24px 28px", background: "rgba(74,111,165,0.03)",
                borderLeft: "4px solid #4A6FA5", borderTop: "1px solid rgba(74,111,165,0.10)",
                borderBottom: "1px solid rgba(74,111,165,0.10)", borderRight: "1px solid rgba(74,111,165,0.10)",
              }}>
                <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 17, color: "#1F2937", lineHeight: 1.85, fontWeight: 500 }}>{S.bottomLine}</p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "12px 0" }}>
                <div style={{ width: 1, height: 20, background: "#D0D0D0" }} />
                <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#F0ECE2", border: "2px solid #D0D0D0", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'JetBrains Mono', monospace", fontSize: 8, fontWeight: 700, color: "#9CA3AF", textTransform: "uppercase" }}>···</div>
                <div style={{ width: 1, height: 20, background: "#D0D0D0" }} />
              </div>

              <div style={{
                padding: "22px 28px", background: "rgba(200,168,78,0.03)",
                borderRight: "4px solid #C8A84E", borderTop: "1px solid rgba(200,168,78,0.10)",
                borderBottom: "1px solid rgba(200,168,78,0.10)", borderLeft: "1px solid rgba(200,168,78,0.10)",
              }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#A08520", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10, fontWeight: 600 }}>Coverage spectrum</div>
                <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 15, color: "#374151", lineHeight: 1.75 }}>{S.spectrum}</p>
              </div>
            </div>
          </div>
        </FadeIn>

        <div style={{ padding: "22px 0", borderTop: "1px solid #DDD7C5", display: "flex", justifyContent: "space-between" }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#4A6FA5", cursor: "pointer" }}>← Back to all stories</div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#9CA3AF" }}>ClearSignal · methodology</div>
        </div>
      </div>

      <div style={{ borderTop: "1px solid #DED8CA", padding: "20px 44px", display: "flex", justifyContent: "space-between" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#9CA3AF" }}>© 2026 ClearSignal</div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#9CA3AF" }}>5-factor impact model · <span style={{ textDecoration: "underline", cursor: "pointer" }}>Learn more</span></div>
      </div>
    </div>
  );
}
