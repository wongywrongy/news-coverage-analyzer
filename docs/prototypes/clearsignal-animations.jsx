import { useState, useEffect, useRef } from "react";

// ============ ANIMATION SETS ============
// Each set defines a collection of ambient + interactive animations

var ANIM_SETS = {
  breathe: {
    name: "A: Breathing Pulse",
    desc: "Gentle pulsing glow on the radial chart, cards lift softly on scroll, timeline segments fill with a wave.",
  },
  typewriter: {
    name: "B: Typewriter Reveal",
    desc: "Hero text types in letter by letter, stats count up, cards stagger in from below on scroll.",
  },
  inkSpread: {
    name: "C: Ink Spread",
    desc: "Radial chart wedges paint in like ink, section headers wipe in, cards fade up with parallax depth.",
  },
  ambient: {
    name: "D: Ambient Data",
    desc: "Floating particles in hero, live-updating stat counters, timeline segments shimmer, subtle hover ripples.",
  },
};

// ============ RADIAL CHART ============
function RadialChart({ size, animSet }) {
  var s = size || 280;
  var cx = s / 2, cy = s / 2, maxR = s / 2 - 36;
  var labels = ["POLITICS", "WORLD", "ECONOMY", "SCIENCE"];
  var data = [
    { impact: 72, coverage: 55, color: "#C42D3A", sa: -90 },
    { impact: 68, coverage: 61, color: "#1D5AD8", sa: 0 },
    { impact: 61, coverage: 58, color: "#8B7520", sa: 90 },
    { impact: 55, coverage: 42, color: "#046B48", sa: 180 },
  ];

  function p2c(d, r) { return { x: cx + r * Math.cos(d * Math.PI / 180), y: cy + r * Math.sin(d * Math.PI / 180) }; }
  function wp(start, end, r) { var a = p2c(start, r), b = p2c(end, r); return "M " + cx + " " + cy + " L " + a.x + " " + a.y + " A " + r + " " + r + " 0 0 1 " + b.x + " " + b.y + " Z"; }

  // Breathing glow for set A
  var breatheStyle = animSet === "breathe" ? "radial-breathe 4s ease-in-out infinite" : "none";
  // Ink spread for set C
  var inkAnim = animSet === "inkSpread";

  var els = [];
  [0.33, 0.66, 1].forEach(function(f, i) {
    els.push(<circle key={"g" + i} cx={cx} cy={cy} r={maxR * f} fill="none" stroke="rgba(0,0,0,0.05)" strokeWidth={0.5} strokeDasharray="2,4" />);
  });
  [0, 90, 180, 270].forEach(function(a, i) {
    var r = (a - 90) * Math.PI / 180;
    els.push(<line key={"d" + i} x1={cx} y1={cy} x2={cx + Math.cos(r) * maxR} y2={cy + Math.sin(r) * maxR} stroke="rgba(0,0,0,0.06)" strokeWidth={0.5} />);
  });

  data.forEach(function(d, i) {
    var iR = (d.impact / 100) * maxR, cR = (d.coverage / 100) * maxR, eA = d.sa + 90, mA = d.sa + 45, lp = p2c(mA, maxR + 22);
    var delay = inkAnim ? (i * 0.3) + "s" : "0s";
    var inkStyle = inkAnim ? { animation: "ink-fill 1.2s ease-out " + delay + " both" } : {};
    els.push(
      <g key={"w" + i} style={inkStyle}>
        <path d={wp(d.sa, eA, iR)} fill={d.color} fillOpacity={0.10} />
        <path d={wp(d.sa, eA, cR)} fill={d.color} fillOpacity={0.40} stroke={d.color} strokeOpacity={0.55} strokeWidth={1.5} />
        <text x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle" fill="#6B6860" fontSize={8} fontFamily="monospace" letterSpacing="0.05em" fontWeight={500}>{labels[i]}</text>
      </g>
    );
  });

  return (
    <div style={{ position: "relative", display: "flex", justifyContent: "center" }}>
      {animSet === "breathe" && (
        <div style={{
          position: "absolute", top: "50%", left: "50%", width: s * 0.7, height: s * 0.7,
          transform: "translate(-50%, -50%)", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(74,111,165,0.08) 0%, transparent 70%)",
          animation: breatheStyle, pointerEvents: "none",
        }} />
      )}
      <svg viewBox={"0 0 " + s + " " + s} width="100%" style={{ maxWidth: s, position: "relative", zIndex: 1 }}>{els}</svg>
    </div>
  );
}

// ============ ANIMATED COUNTER ============
function Counter({ target, duration, active }) {
  var _val = useState(0), val = _val[0], setVal = _val[1];
  var ref = useRef(null);

  useEffect(function() {
    if (!active) { setVal(target); return; }
    var start = 0;
    var startTime = null;
    var dur = duration || 1500;

    function step(ts) {
      if (!startTime) startTime = ts;
      var progress = Math.min((ts - startTime) / dur, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      setVal(Math.round(eased * target));
      if (progress < 1) ref.current = requestAnimationFrame(step);
    }
    ref.current = requestAnimationFrame(step);
    return function() { if (ref.current) cancelAnimationFrame(ref.current); };
  }, [active, target, duration]);

  return val;
}

// ============ FLOATING PARTICLES (Set D) ============
function Particles() {
  var dots = [];
  for (var i = 0; i < 20; i++) {
    var x = Math.random() * 100;
    var y = Math.random() * 100;
    var size = 2 + Math.random() * 3;
    var dur = 15 + Math.random() * 20;
    var delay = Math.random() * -20;
    dots.push(
      <div key={i} style={{
        position: "absolute",
        left: x + "%", top: y + "%",
        width: size, height: size, borderRadius: "50%",
        background: "rgba(74,111,165,0.12)",
        animation: "float-particle " + dur + "s ease-in-out " + delay + "s infinite",
        pointerEvents: "none",
      }} />
    );
  }
  return <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, overflow: "hidden", pointerEvents: "none" }}>{dots}</div>;
}

// ============ TYPEWRITER TEXT ============
function Typewriter({ text, speed, delay, color, style }) {
  var _shown = useState(0), shown = _shown[0], setShown = _shown[1];
  var _started = useState(false), started = _started[0], setStarted = _started[1];

  useEffect(function() {
    var t1 = setTimeout(function() { setStarted(true); }, delay || 0);
    return function() { clearTimeout(t1); };
  }, [delay]);

  useEffect(function() {
    if (!started) return;
    if (shown >= text.length) return;
    var t = setTimeout(function() { setShown(shown + 1); }, speed || 40);
    return function() { clearTimeout(t); };
  }, [started, shown, text, speed]);

  return (
    <span style={Object.assign({}, style, { color: color })}>
      {text.substring(0, shown)}
      {shown < text.length && <span style={{ borderRight: "2px solid " + (color || "#111"), animation: "blink-cursor 0.8s step-end infinite", marginLeft: 1 }} />}
    </span>
  );
}

// ============ TIMELINE ============
function TL({ days, animSet, delay }) {
  var d = days || [2, 3, 4, 8, 9, 12, 13];
  var _visible = useState(false), vis = _visible[0], setVis = _visible[1];

  useEffect(function() {
    var t = setTimeout(function() { setVis(true); }, delay || 0);
    return function() { clearTimeout(t); };
  }, [delay]);

  var segs = [];
  for (var i = 0; i < 14; i++) {
    var isActive = d.indexOf(i) >= 0;
    var segDelay = animSet === "breathe" ? (i * 40) : 0;
    var shimmer = animSet === "ambient" && isActive;

    segs.push(
      <div key={i} style={{
        flex: 1,
        background: isActive ? (vis || animSet !== "breathe" ? "#5578A8" : "transparent") : "transparent",
        transition: animSet === "breathe" ? "background " + 0.3 + "s ease " + segDelay + "ms" : "none",
        animation: shimmer ? "tl-shimmer 3s ease-in-out " + (i * 0.2) + "s infinite" : "none",
      }} />
    );
  }
  return (
    <div>
      <div style={{ height: 8, borderRadius: 2, overflow: "hidden", display: "flex", background: "#E2DDCF" }}>{segs}</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
        <span style={{ fontFamily: "monospace", fontSize: 8, color: "#B5AFA0" }}>Jan 25</span>
        <span style={{ fontFamily: "monospace", fontSize: 8, color: "#B5AFA0" }}>Today</span>
      </div>
    </div>
  );
}

// ============ HORIZONTAL CARD ============
function HCard({ s, animSet, index }) {
  var _h = useState(false), h = _h[0], setH = _h[1];
  var _vis = useState(false), vis = _vis[0], setVis = _vis[1];

  useEffect(function() {
    var t = setTimeout(function() { setVis(true); }, 100 + index * 120);
    return function() { clearTimeout(t); };
  }, [index]);

  var cardAnim = {};
  if (animSet === "typewriter" || animSet === "inkSpread") {
    cardAnim = {
      opacity: vis ? 1 : 0,
      transform: vis ? "translateY(0)" : "translateY(20px)",
      transition: "opacity 0.5s ease, transform 0.5s ease",
    };
  } else if (animSet === "breathe") {
    cardAnim = {
      opacity: vis ? 1 : 0,
      transform: vis ? "translateY(0) scale(1)" : "translateY(8px) scale(0.99)",
      transition: "all 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
    };
  } else {
    cardAnim = { opacity: 1 };
  }

  var hoverRipple = animSet === "ambient" && h;

  return (
    <div
      onMouseEnter={function(){setH(true);}}
      onMouseLeave={function(){setH(false);}}
      style={Object.assign({}, cardAnim, {
        background: h ? "#FFFFFF" : "#FAFAFA",
        border: "1px solid " + (h ? "#D0D0D0" : "#E8E8E8"),
        padding: 20, cursor: "pointer",
        transition: (cardAnim.transition || "") + ", background 0.2s, border-color 0.2s, box-shadow 0.3s, transform 0.3s",
        boxShadow: h ? "0 6px 24px rgba(0,0,0,0.08)" : "0 1px 3px rgba(0,0,0,0.02)",
        display: "flex", gap: 20,
        position: "relative", overflow: "hidden",
        transform: h && !animSet ? "translateY(-2px)" : (cardAnim.transform || "none"),
      })}
    >
      {/* Hover ripple for ambient set */}
      {hoverRipple && (
        <div style={{
          position: "absolute", top: "50%", left: "50%", width: 300, height: 300,
          borderRadius: "50%", transform: "translate(-50%, -50%)",
          background: "radial-gradient(circle, rgba(74,111,165,0.04) 0%, transparent 60%)",
          animation: "ripple-expand 0.6s ease-out forwards",
          pointerEvents: "none",
        }} />
      )}
      <div style={{ width: 4, background: s.color, borderRadius: 2, flexShrink: 0, position: "relative", zIndex: 1 }} />
      <div style={{ flex: 1, minWidth: 0, position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <span style={{ color: s.color, fontFamily: "monospace", fontSize: 9, fontWeight: 600, letterSpacing: "0.04em" }}>{s.cat}</span>
          <span style={{ color: "#D0D0D0" }}>·</span>
          <span style={{ color: "#9CA3AF", fontFamily: "monospace", fontSize: 10 }}>{s.articles} articles</span>
          {s.label ? <span style={{ color: s.label === "less" ? "#4A6FA5" : "#A06B20", fontFamily: "monospace", fontSize: 9 }}>{s.label === "less" ? "↓ Less covered" : "↑ More covered"}</span> : null}
        </div>
        <div style={{ color: "#111827", fontFamily: "Georgia, serif", fontSize: 17, fontWeight: 700, lineHeight: 1.3, marginBottom: 8 }}>{s.title}</div>
        <div style={{ color: "#6B7280", fontFamily: "Georgia, serif", fontSize: 13, lineHeight: 1.55, marginBottom: 12, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{s.lede}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ flex: 1, maxWidth: 200 }}><TL days={s.days} animSet={animSet} delay={200 + index * 150} /></div>
          <span style={{ color: "#B5B5B5", fontFamily: "monospace", fontSize: 9, whiteSpace: "nowrap" }}>
            {s.sources.split(",").slice(0, 3).join(",")}
            {s.articles > 6 ? " +" + (s.articles - 3) : ""}
          </span>
        </div>
      </div>
    </div>
  );
}

var STORIES = [
  { title: "Appeals Court Backs Trump in Major Fight Over Detaining Long-Term Residents", cat: "POLITICS", color: "#C42D3A", articles: 14, days: [3,4,5,9,10,11,12,13], label: "less", group: "Politics & Law", sources: "NYT, Fox News, AP, Reuters, WSJ, CNN", lede: "A federal appeals court ruled in favor of the administration's expanded detention authority, deepening a constitutional clash over immigration enforcement powers." },
  { title: "Epstein Files Released Political Fallout Continues Across Washington", cat: "POLITICS", color: "#C42D3A", articles: 18, days: [1,2,3,4,5,6,7,8,9,10,11,12,13], label: null, group: "Politics & Law", sources: "CNN, MSNBC, Fox, Daily Mail, NYT", lede: "Newly unsealed court documents have reignited political tensions as officials from both parties face scrutiny." },
  { title: "Pakistan Mosque Bombing Four Arrests Made in Connection", cat: "SECURITY", color: "#1D5AD8", articles: 6, days: [11,12,13], label: "less", group: "World & Security", sources: "Al Jazeera, Reuters, BBC", lede: "Security forces detained four suspects linked to the deadly blast that killed 32 worshippers in Peshawar." },
  { title: "Starlink Cuts Service to Russian Forces in Eastern Ukraine", cat: "MILITARY", color: "#1D5AD8", articles: 3, days: [12,13], label: "less", group: "World & Security", sources: "AP, Reuters, Kyiv Independent", lede: "SpaceX confirmed it disabled terminals identified as operating in Russian-controlled territory." },
  { title: "US Iran Nuclear Talks Resume in Oman With Economic Stakes Rising", cat: "DIPLOMACY", color: "#8B7520", articles: 38, days: [5,6,7,8,9,10,11,12,13], label: "more", group: "Economy & Business", sources: "NYT, WSJ, Reuters, AP, Al Jazeera, CNN, Fox", lede: "Negotiations have entered a critical phase with both sides signaling willingness to discuss sanctions relief." },
  { title: "Job Market Decline Mirrors 2009 Recession Warning Signs", cat: "ECONOMY", color: "#8B7520", articles: 10, days: [3,4,5,8,9,12,13], label: "less", group: "Economy & Business", sources: "WSJ, Bloomberg, CNBC, Reuters", lede: "January payroll figures fell short of expectations for the third consecutive month." },
  { title: "Houston Doctor Indicted for Falsifying Transplant Records", cat: "HEALTHCARE", color: "#046B48", articles: 6, days: [8,9,10], label: "less", group: "Science & Health", sources: "AP, Houston Chronicle, CNN", lede: "Federal prosecutors allege the surgeon manipulated patient data to move favored recipients up the waitlist." },
];

var ALL_GROUPS = ["Politics & Law", "World & Security", "Economy & Business", "Science & Health"];
var GC = { "Politics & Law": "#C42D3A", "World & Security": "#1D5AD8", "Economy & Business": "#8B7520", "Science & Health": "#046B48" };

// ============ SECTION HEADER ============
function SectionHeader({ name, count, animSet, index }) {
  var _vis = useState(false), vis = _vis[0], setVis = _vis[1];
  useEffect(function() {
    var t = setTimeout(function() { setVis(true); }, 50 + index * 200);
    return function() { clearTimeout(t); };
  }, [index]);

  var wipeStyle = animSet === "inkSpread" ? {
    opacity: vis ? 1 : 0,
    transform: vis ? "translateX(0)" : "translateX(-20px)",
    transition: "all 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
  } : {};

  return (
    <div style={Object.assign({}, wipeStyle, { borderLeft: "3px solid " + GC[name], paddingLeft: 14, marginBottom: 14 })}>
      <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color: "#111827", letterSpacing: "0.05em" }}>{name.toUpperCase()}</span>
      <span style={{ fontFamily: "monospace", fontSize: 11, color: "#9CA3AF", marginLeft: 10 }}>{count} stories</span>
    </div>
  );
}

// ============ MAIN PAGE ============
function Page({ animSet }) {
  var _mounted = useState(false), mounted = _mounted[0], setMounted = _mounted[1];
  useEffect(function() { setMounted(true); }, []);

  var grouped = [];
  ALL_GROUPS.forEach(function(gn) {
    var st = [];
    STORIES.forEach(function(s) { if (s.group === gn) st.push(s); });
    if (st.length > 0) grouped.push({ name: gn, stories: st });
  });

  var useTypewriter = animSet === "typewriter" && mounted;
  var useCounter = animSet === "typewriter" || animSet === "ambient";

  var sections = [];
  var cardIdx = 0;
  grouped.forEach(function(g, gi) {
    var cards = [];
    g.stories.forEach(function(s, i) {
      cards.push(<HCard key={i} s={s} animSet={animSet} index={cardIdx} />);
      cardIdx++;
    });
    sections.push(
      <div key={g.name} style={{ marginBottom: 44 }}>
        <SectionHeader name={g.name} count={g.stories.length} animSet={animSet} index={gi} />
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{cards}</div>
      </div>
    );
  });

  return (
    <div style={{ background: "#F0ECE2", minHeight: "100vh" }}>
      {/* Global keyframes */}
      <style>{"\n        @keyframes radial-breathe { 0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.6; } 50% { transform: translate(-50%, -50%) scale(1.15); opacity: 1; } }\n        @keyframes blink-cursor { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }\n        @keyframes ink-fill { 0% { opacity: 0; transform: scale(0.3); } 100% { opacity: 1; transform: scale(1); } }\n        @keyframes float-particle { 0%, 100% { transform: translate(0, 0); opacity: 0.3; } 25% { transform: translate(10px, -15px); opacity: 0.6; } 50% { transform: translate(-5px, -25px); opacity: 0.4; } 75% { transform: translate(15px, -10px); opacity: 0.7; } }\n        @keyframes tl-shimmer { 0%, 100% { opacity: 0.85; } 50% { opacity: 1; } }\n        @keyframes ripple-expand { 0% { transform: translate(-50%, -50%) scale(0); opacity: 1; } 100% { transform: translate(-50%, -50%) scale(1); opacity: 0; } }\n        @keyframes hero-fade-up { 0% { opacity: 0; transform: translateY(16px); } 100% { opacity: 1; transform: translateY(0); } }\n        @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }\n      "}</style>

      {/* Header */}
      <div style={{ background: "#FFFFFF", padding: "12px 44px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #E5E5E5" }}>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 20, fontWeight: 700 }}>
          <span style={{ color: "#111827" }}>Clear</span><span style={{ color: "#4A6FA5" }}>Signal</span>
        </div>
        <div style={{ fontFamily: "monospace", fontSize: 10, color: "#9CA3AF", letterSpacing: "0.05em", textTransform: "uppercase" }}>TRACKING 203 STORIES · 100+ SOURCES</div>
      </div>

      {/* Hero */}
      <div style={{
        position: "relative", overflow: "hidden",
        background: "linear-gradient(170deg, #FFFFFF 0%, #FAFBFD 20%, #F2F4F8 40%, #E8ECF2 60%, #DEE3EC 80%, #D4DAE5 100%)",
        padding: "56px 44px", borderBottom: "2px solid #3D5F8F",
      }}>
        {animSet === "ambient" && <Particles />}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", maxWidth: 1200, margin: "0 auto", gap: 48, position: "relative", zIndex: 1 }}>
          <div style={{ flex: "1 1 50%", maxWidth: "50%" }}>
            {/* Tagline */}
            <div style={{
              animation: animSet !== "typewriter" ? "hero-fade-up 0.8s ease-out both" : "none",
            }}>
              {useTypewriter ? (
                <div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 48, fontWeight: 800, color: "#111827", lineHeight: 1.05, letterSpacing: "-0.02em", minHeight: 52 }}>
                    <Typewriter text="Same event." speed={50} delay={200} color="#111827" />
                  </div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 48, fontWeight: 800, color: "#4A6FA5", lineHeight: 1.05, letterSpacing: "-0.02em", marginBottom: 20, minHeight: 52 }}>
                    <Typewriter text="Different realities." speed={50} delay={900} color="#4A6FA5" />
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 48, fontWeight: 800, color: "#111827", lineHeight: 1.05, letterSpacing: "-0.02em" }}>Same event.</div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 48, fontWeight: 800, color: "#4A6FA5", lineHeight: 1.05, letterSpacing: "-0.02em", marginBottom: 20 }}>Different realities.</div>
                </div>
              )}
            </div>

            <div style={{
              fontFamily: "Georgia, serif", fontSize: 15, color: "#6B7280", lineHeight: 1.75, marginBottom: 36, maxWidth: 460,
              animation: "hero-fade-up 0.8s ease-out 0.3s both",
            }}>
              The same story can look completely different depending on who tells it. We track how outlets across the political spectrum cover the same events, score what matters, and surface what's being overlooked.
            </div>

            <div style={{
              display: "flex", gap: 0, borderTop: "1px solid rgba(0,0,0,0.06)", paddingTop: 18,
              animation: "hero-fade-up 0.8s ease-out 0.5s both",
            }}>
              {(function() {
                var st = [[33, "stories analyzed"], [303, "articles collected"], [100, "sources monitored"]];
                var els = [];
                st.forEach(function(p, i) {
                  els.push(
                    <div key={p[1]} style={{ paddingRight: i < 2 ? 32 : 0, marginRight: i < 2 ? 32 : 0, borderRight: i < 2 ? "1px solid rgba(0,0,0,0.06)" : "none" }}>
                      <div style={{ fontFamily: "monospace", fontSize: 24, fontWeight: 700, color: "#111827" }}>
                        {useCounter ? <Counter target={p[0]} duration={1800} active={mounted} /> : p[0]}
                        {i === 2 ? "+" : ""}
                      </div>
                      <div style={{ fontFamily: "monospace", fontSize: 9, color: "#9CA3AF", letterSpacing: "0.03em", marginTop: 3 }}>{p[1]}</div>
                    </div>
                  );
                });
                return els;
              })()}
            </div>
          </div>

          <div style={{
            flex: "1 1 50%", maxWidth: "50%", display: "flex", flexDirection: "column", alignItems: "center",
            animation: "hero-fade-up 0.8s ease-out 0.4s both",
          }}>
            <RadialChart size={300} animSet={animSet} />
            <div style={{ fontFamily: "monospace", fontSize: 9, color: "#9CA3AF", marginTop: 10 }}>◉ lighter = impact &nbsp;&nbsp; ◉ solid = coverage</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ background: "#FFFFFF", borderBottom: "1px solid #E5E5E5" }}>
        <div style={{ maxWidth: 1288, margin: "0 auto", padding: "0 44px", display: "flex" }}>
          {(function() {
            var tabs = ["ALL"].concat(ALL_GROUPS);
            var els = [];
            tabs.forEach(function(t) {
              var isA = t === "ALL";
              var color = t === "ALL" ? "#4A6FA5" : GC[t];
              els.push(
                <div key={t} style={{
                  padding: "16px 20px 14px", textAlign: "center", flex: 1,
                  background: isA ? color : "transparent",
                  borderBottom: "3px solid " + (isA ? color : "transparent"),
                  cursor: "pointer",
                }}>
                  <div style={{ fontFamily: "monospace", fontSize: 11, fontWeight: isA ? 700 : 600, color: isA ? "#FFFFFF" : "#111827", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                    {t === "ALL" ? "ALL" : t.toUpperCase()}
                  </div>
                </div>
              );
            });
            return els;
          })()}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "24px 44px 60px", maxWidth: 1288, margin: "0 auto" }}>{sections}</div>

      <div style={{ borderTop: "1px solid #DED8CA", padding: "20px 44px", display: "flex", justifyContent: "space-between" }}>
        <div style={{ fontFamily: "monospace", fontSize: 10, color: "#9CA3AF" }}>© 2026 ClearSignal</div>
        <div style={{ fontFamily: "monospace", fontSize: 9, color: "#C0C0C0" }}>◉ lighter = impact &nbsp;&nbsp; ◉ solid = coverage</div>
      </div>
    </div>
  );
}

export default function AnimVariations() {
  var _a = useState("breathe"), active = _a[0], setActive = _a[1];
  var _key = useState(0), key = _key[0], setKey = _key[1];
  var keys = ["breathe", "typewriter", "inkSpread", "ambient"];

  function pick(k) {
    setActive(k);
    setKey(key + 1);
  }

  var btns = [];
  keys.forEach(function(k) {
    var v = ANIM_SETS[k], isA = active === k;
    btns.push(
      <button key={k} onClick={function() { pick(k); }} style={{
        background: isA ? "#4A6FA5" : "transparent", border: "1px solid " + (isA ? "#4A6FA5" : "#E5E5E5"),
        color: isA ? "#FFFFFF" : "#6B7280", fontFamily: "monospace", fontSize: 10, padding: "8px 14px",
        cursor: "pointer", transition: "all 0.2s",
        display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2,
      }}>
        <span style={{ fontWeight: 600 }}>{v.name}</span>
        <span style={{ fontSize: 8, opacity: isA ? 0.8 : 0.6, maxWidth: 260, textAlign: "left", lineHeight: 1.3 }}>{v.desc}</span>
      </button>
    );
  });

  return (
    <div>
      <div style={{ position: "sticky", top: 0, zIndex: 100, background: "rgba(255,255,255,0.97)", backdropFilter: "blur(8px)", borderBottom: "1px solid #E5E5E5", padding: "10px 44px", display: "flex", gap: 8, alignItems: "stretch" }}>
        <span style={{ fontFamily: "monospace", fontSize: 10, color: "#9CA3AF", marginRight: 12, display: "flex", alignItems: "center" }}>ANIMATIONS:</span>
        {btns}
        <span style={{ fontFamily: "monospace", fontSize: 9, color: "#C0C0C0", display: "flex", alignItems: "center", marginLeft: 12 }}>Click same button to replay</span>
      </div>
      <Page key={key} animSet={active} />
    </div>
  );
}
