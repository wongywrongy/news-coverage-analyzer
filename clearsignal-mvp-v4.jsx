import { useState, useMemo } from "react";

const STORIES = [
  {
    id: 67, topic: "Trump Administration Deportation Policy Effects", category: "Politics", impact_score: 78, attention_score: 100, article_count: 178, source_count: 71, status: "developing", population_affected: "11M+ immigrants",
    sentiment_left: -0.28, sentiment_center: -0.05, sentiment_right: 0.18,
    trend: [{ date: "2026-02-01", count: 12 }, { date: "2026-02-02", count: 28 }, { date: "2026-02-03", count: 45 }, { date: "2026-02-04", count: 38 }, { date: "2026-02-05", count: 32 }, { date: "2026-02-06", count: 23 }],
    analysis: {
      headline: "Trump Administration Immigration Enforcement Actions Draw State and Local Responses",
      dateline: "WASHINGTON (ClearSignal)",
      lede: "Immigration and Customs Enforcement operations under the Trump administration have prompted responses from state and local governments, civil rights organizations, and educational institutions. The actions have generated 178 articles from 67 news sources across the political spectrum.",
      context: "The Trump administration has expanded immigration enforcement operations, including deportation proceedings and increased ICE presence in communities. State and local officials have responded with varying approaches, from cooperation to resistance.",
      contrasts: [
        { theme: "Economic impact of deportation policy", sourceA: "Washington Examiner", biasA: "right", claimA: "Reports rents are falling as deportations rise, suggesting a connection between immigration enforcement and housing market changes", sourceB: "The Guardian", biasB: "left-center", claimB: "Characterizes Republican policies as separating and destroying families, focusing on social harm rather than economic effects" },
        { theme: "ICE enforcement tactics near schools", sourceA: "Breitbart", biasA: "right", claimA: "Reports immigrant families describe sending children to school as an act of faith amid enforcement concerns", sourceB: "MPR News", biasB: "center", claimB: "Covers community impact on school attendance and parent anxiety about ICE presence near educational facilities" }
      ],
      facts: [
        { claim: "ICE chartered flights on aircraft owned by Trump family associates", reality: "The Guardian reports ICE used jets owned by a Trump family friend for deportation flights, though contract details require verification", verdict: "unverified" },
        { claim: "Census Bureau plans to test citizenship question for 2030 census", reality: "Multiple outlets confirm the Census Bureau is including citizenship questions in test surveys", verdict: "confirmed" },
        { claim: "Civil rights groups issued Florida travel advisory", reality: "Civil rights organizations issued a travel advisory for FIFA World Cup attendees regarding Florida's enforcement tactics", verdict: "confirmed" }
      ],
      bottom_line: "Families in immigrant communities face decisions about daily activities like school attendance amid expanded enforcement. Housing markets and local economies may experience changes as deportation activity increases.",
      coverage_note: "178 articles from 67 sources across all political leans. Right-leaning outlets emphasize economic effects; left-leaning sources focus on family separation and civil rights."
    }
  },
  {
    id: 61, topic: "US and Iran Begin Nuclear Talks in Oman", category: "World", impact_score: 74, attention_score: 85, article_count: 16, source_count: 16, status: "fading", population_affected: "Global security",
    sentiment_left: -0.12, sentiment_center: -0.08, sentiment_right: -0.22,
    trend: [{ date: "2026-02-02", count: 3 }, { date: "2026-02-03", count: 6 }, { date: "2026-02-04", count: 4 }, { date: "2026-02-05", count: 2 }, { date: "2026-02-06", count: 1 }],
    analysis: {
      headline: "US and Iran Begin Nuclear Talks in Oman Amid Uncertain Prospects",
      dateline: "MUSCAT, Oman (ClearSignal)",
      lede: "American and Iranian officials met in Oman for negotiations over Iran's nuclear program, the first direct talks since protests shook Iran.",
      context: "The US withdrew from the JCPOA in 2018. Iran has since expanded nuclear enrichment beyond original limits.",
      contrasts: [{ theme: "Likelihood of diplomatic success", sourceA: "Bloomberg", biasA: "left-center", claimA: "Iran signals negotiations won't lead to quick resolution", sourceB: "National Review", biasB: "right", claimB: "Frames Iran as wanting to turn back time to the pre-2018 agreement" }],
      facts: [{ claim: "Officials are meeting in Oman", reality: "Multiple outlets confirm officials from both countries arrived for negotiations", verdict: "confirmed" }],
      bottom_line: "If negotiations fail, Americans could face continued Middle East instability and potential military tensions.",
      coverage_note: "16 articles from 12 sources, heavily skewed left-center with minimal right-wing attention."
    }
  },
  {
    id: 26, topic: "Stellantis Takes $26.5 Billion EV Writedown, Shares Plunge 20%", category: "Business", impact_score: 72, attention_score: 24, article_count: 3, source_count: 2, status: "stale", population_affected: "Stellantis workers, EV market",
    sentiment_left: null, sentiment_center: -0.35, sentiment_right: null,
    trend: [{ date: "2026-02-03", count: 2 }, { date: "2026-02-04", count: 1 }],
    analysis: {
      headline: "Stellantis Takes $26.5 Billion Writedown, Shares Drop Over 20 Percent",
      dateline: "AMSTERDAM (ClearSignal)",
      lede: "Stellantis NV shares fell more than 20 percent after the automaker announced a $26.5 billion writedown tied to its electric vehicle operations.",
      context: "The writedown marks one of the largest financial adjustments in automotive history and reflects broader challenges in the EV transition.",
      contrasts: [{ theme: "EV transition framing", sourceA: "CNBC", biasA: "center", claimA: "Framed as Stellantis over-estimating the pace of the energy transition", sourceB: "Google News", biasB: "center", claimB: "Described neutrally as an EV-related writedown" }],
      facts: [{ claim: "$26.5 billion writedown announced", reality: "Multiple outlets consistently report this figure", verdict: "confirmed" }, { claim: "Shares fell over 20%", reality: "Market data confirms the decline", verdict: "confirmed" }],
      bottom_line: "Stellantis workers may face job cuts. Consumers may see fewer new EV models as the company slows plans.",
      coverage_note: "Only 3 articles from 2 center-leaning sources. No left or right coverage despite significance for climate policy and jobs."
    }
  },
  {
    id: 100, topic: "ICE Deportation Operations Escalate Nationwide", category: "Politics", impact_score: 78, attention_score: 28, article_count: 4, source_count: 4, status: "developing", population_affected: "Immigrant communities",
    sentiment_left: -0.35, sentiment_center: -0.10, sentiment_right: 0.22,
    trend: [{ date: "2026-02-04", count: 1 }, { date: "2026-02-05", count: 2 }, { date: "2026-02-06", count: 1 }],
    analysis: null
  },
  {
    id: 10, topic: "EU Agrees €90 Billion Ukraine Aid Lifeline", category: "World", impact_score: 78, attention_score: 29, article_count: 4, source_count: 3, status: "stale", population_affected: "44M Ukrainians, EU taxpayers",
    sentiment_left: 0.15, sentiment_center: 0.08, sentiment_right: -0.10,
    trend: [{ date: "2026-02-01", count: 2 }, { date: "2026-02-02", count: 1 }, { date: "2026-02-03", count: 1 }],
    analysis: null
  },
  {
    id: 24, topic: "Sudan Humanitarian Crisis Worsens as Conflict Continues", category: "World", impact_score: 78, attention_score: 54, article_count: 5, source_count: 5, status: "fading", population_affected: "25M+ Sudanese civilians",
    sentiment_left: -0.40, sentiment_center: -0.32, sentiment_right: null,
    trend: [{ date: "2026-02-01", count: 1 }, { date: "2026-02-02", count: 2 }, { date: "2026-02-03", count: 1 }, { date: "2026-02-04", count: 1 }],
    analysis: null
  },
  {
    id: 106, topic: "ICE Cooperation and Enforcement Authority Debated in Congress", category: "Politics", impact_score: 68, attention_score: 27, article_count: 3, source_count: 2, status: "developing", population_affected: "Sanctuary jurisdictions",
    sentiment_left: null, sentiment_center: null, sentiment_right: -0.15,
    trend: [{ date: "2026-02-04", count: 1 }, { date: "2026-02-05", count: 2 }],
    analysis: null
  },
  {
    id: 38, topic: "Supreme Court Upholds California Congressional Map", category: "Politics", impact_score: 68, attention_score: 50, article_count: 3, source_count: 4, status: "stale", population_affected: "California voters",
    sentiment_left: 0.56, sentiment_center: null, sentiment_right: -0.36,
    trend: [{ date: "2026-02-03", count: 2 }, { date: "2026-02-04", count: 1 }],
    analysis: {
      headline: "Supreme Court Declines to Block California Congressional District Map",
      dateline: "WASHINGTON (ClearSignal)",
      lede: "The Supreme Court rejected an emergency request to block California's congressional map, allowing current boundaries to remain for 2026 elections.",
      context: "Challengers alleged racial gerrymandering in the state's redistricting process.",
      contrasts: [{ theme: "Significance of the ruling", sourceA: "Vox", biasA: "left", claimA: "Characterized as a victory for Democrats from a Republican Supreme Court", sourceB: "The Federalist", biasB: "right", claimB: "Framed the map as racially gerrymandered" }],
      facts: [{ claim: "The ruling is a victory for Democrats", reality: "The order allows the current map to stand but is not a final ruling on the merits", verdict: "lacks context" }],
      bottom_line: "California voters will use the current congressional map for the 2026 elections.",
      coverage_note: "Only 3 articles from 3 sources with a stark left-right divide. Sparse for a decision affecting 52 congressional seats."
    }
  },
  {
    id: 64, topic: "DNI Gabbard Attends FBI Raid on Georgia Election Office", category: "Politics", impact_score: 68, attention_score: 70, article_count: 10, source_count: 5, status: "developing", population_affected: "Fulton County voters",
    sentiment_left: -0.30, sentiment_center: -0.15, sentiment_right: null,
    trend: [{ date: "2026-02-03", count: 2 }, { date: "2026-02-04", count: 4 }, { date: "2026-02-05", count: 3 }, { date: "2026-02-06", count: 1 }],
    analysis: {
      headline: "Director of National Intelligence Gabbard Attends FBI Raid on Georgia Election Office",
      dateline: "ATLANTA (ClearSignal)",
      lede: "Director of National Intelligence Tulsi Gabbard accompanied FBI agents during a raid on the Fulton County election office on February 3, 2026.",
      context: "The DNI position typically focuses on coordinating intelligence agencies, making her presence at a domestic law enforcement operation unusual.",
      contrasts: [{ theme: "Framing of Gabbard's role", sourceA: "The Guardian", biasA: "left-center", claimA: "Characterized as a warning to America, questioning appropriateness", sourceB: "PBS", biasB: "center", claimB: "Reported Trump's statement that Gabbard joined at Bondi's insistence without characterization" }],
      facts: [{ claim: "Gabbard was physically present during the raid", reality: "Video footage and multiple outlets confirmed her presence", verdict: "confirmed" }, { claim: "The DNI typically participates in domestic law enforcement", reality: "The role focuses on intelligence coordination; this is outside standard responsibilities", verdict: "lacks context" }],
      bottom_line: "Raises questions about boundaries between intelligence operations and domestic law enforcement.",
      coverage_note: "10 articles from 4 sources, all left-leaning or center. No right-leaning coverage detected."
    }
  },
  {
    id: 58, topic: "Amazon Stock Falls 8% After $200B AI Spending Plan", category: "Business", impact_score: 68, attention_score: 83, article_count: 13, source_count: 11, status: "fading", population_affected: "Amazon shareholders",
    sentiment_left: 0.0, sentiment_center: -0.21, sentiment_right: -0.67,
    trend: [{ date: "2026-02-03", count: 1 }, { date: "2026-02-04", count: 8 }, { date: "2026-02-05", count: 3 }, { date: "2026-02-06", count: 1 }],
    analysis: null
  },
  {
    id: 84, topic: "Various Business and Lifestyle Ventures Announced", category: "Business", impact_score: 18, attention_score: 78, article_count: 7, source_count: 6, status: "stale", population_affected: "Minimal",
    sentiment_left: null, sentiment_center: 0.12, sentiment_right: 0.08,
    trend: [{ date: "2026-02-02", count: 3 }, { date: "2026-02-03", count: 3 }, { date: "2026-02-04", count: 1 }],
    analysis: null
  },
  {
    id: 125, topic: "Astronomers Observe Black Hole Jet Destroying Planets", category: "Science", impact_score: 2, attention_score: 61, article_count: 3, source_count: 6, status: "stale", population_affected: "None",
    sentiment_left: null, sentiment_center: 0.30, sentiment_right: null,
    trend: [{ date: "2026-02-04", count: 2 }, { date: "2026-02-05", count: 1 }],
    analysis: null
  },
];

const CAT_COLORS = {
  Politics: "#D93644", POLITICS: "#D93644",
  Health: "#1A8A7A", HEALTH: "#1A8A7A", HEALTHCARE: "#1A8A7A", "PUBLIC HEALTH": "#1A8A7A",
  Business: "#B8860B", BUSINESS: "#B8860B",
  Tech: "#6D28D9", TECHNOLOGY: "#6D28D9",
  Sports: "#1D4ED8", SPORTS: "#1D4ED8",
  Economy: "#B45309", ECONOMY: "#B45309",
  Science: "#047857", SCIENCE: "#047857",
  Entertainment: "#C2410C", ENTERTAINMENT: "#C2410C", MEDIA: "#C2410C",
  World: "#2563EB", WORLD: "#2563EB", INTERNATIONAL: "#2563EB", GEOPOLITICS: "#2563EB", "INTERNATIONAL DIPLOMACY": "#2563EB", "INTERNATIONAL RELATIONS": "#2563EB", "INTERNATIONAL AFFAIRS": "#2563EB", "FOREIGN POLICY": "#2563EB",
  Crime: "#4B5563", CRIME: "#4B5563",
  LAW: "#4B5563", LEGAL: "#4B5563",
  IMMIGRATION: "#D93644",
  EDUCATION: "#1D4ED8",
  SECURITY: "#4B5563", MILITARY: "#4B5563",
  HUMANITARIAN: "#1A8A7A", "HUMANITARIAN CRISIS": "#1A8A7A",
  CONFLICT: "#DC2626",
};
const BIAS_COLORS = { "far-left": "#1D4ED8", left: "#2563EB", "left-center": "#3B82F6", center: "#6B7280", "right-center": "#DC2626", right: "#B91C1C", "far-right": "#991B1B" };
const VERDICT_STYLES = { confirmed: { bg: "#DCFCE7", color: "#166534", border: "#BBF7D0" }, misleading: { bg: "#FEE2E2", color: "#991B1B", border: "#FECACA" }, "lacks context": { bg: "#FEF3C7", color: "#92400E", border: "#FDE68A" }, unverified: { bg: "#F3F4F6", color: "#4B5563", border: "#E5E7EB" } };
const STATUS_STYLES = { breaking: { bg: "#FEE2E2", color: "#991B1B" }, developing: { bg: "#FEF3C7", color: "#92400E" }, peak: { bg: "#FEF9C3", color: "#854D0E" }, fading: { bg: "#F3F4F6", color: "#6B7280" }, stale: { bg: "#F3F4F6", color: "#9CA3AF" } };

function getGapInfo(gap) {
  if (gap >= 30) return { label: "Underreported", barColor: "#DC2626", bgColor: "#FEE2E2", textColor: "#991B1B" };
  if (gap <= -30) return { label: "Overcovered", barColor: "#D97706", bgColor: "#FEF3C7", textColor: "#92400E" };
  return { label: null, barColor: "#D1D5DB", bgColor: null, textColor: "#9CA3AF" };
}

function Spark({ data, color, w = 64, h = 22 }) {
  if (!data || data.length < 2) return null;
  const c = data.map(d => d.count);
  const mx = Math.max(...c), mn = Math.min(...c), r = mx - mn || 1;
  const pts = c.map((v, i) => `${(i / (c.length - 1)) * w},${h - ((v - mn) / r) * (h - 6) - 3}`).join(" ");
  const ly = h - ((c[c.length - 1] - mn) / r) * (h - 6) - 3;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color + "10"} stroke="none" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
      <circle cx={w} cy={ly} r="2" fill={color} />
    </svg>
  );
}

function SentimentInline({ left, center, right }) {
  const segs = [
    { val: left, label: "L", color: "#2563EB" },
    { val: center, label: "C", color: "#6B7280" },
    { val: right, label: "R", color: "#DC2626" },
  ];
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      {segs.map(s => (
        <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
          <span style={{ fontSize: 9, color: s.color, fontFamily: "'JetBrains Mono',monospace", fontWeight: 600, opacity: 0.7 }}>{s.label}</span>
          <span style={{ fontSize: 9, color: s.val === null ? "#D1D5DB" : "#6B7280", fontFamily: "'JetBrains Mono',monospace" }}>
            {s.val === null ? "—" : `${s.val >= 0 ? "+" : ""}${s.val.toFixed(2)}`}
          </span>
        </div>
      ))}
    </div>
  );
}

function getPrimaryCategory(cat) {
  return (cat || "").split("/")[0].trim();
}

function GapChart({ stories, onSelect }) {
  const sorted = useMemo(() => {
    return [...stories]
      .filter(s => Math.abs(s.impact_score - s.attention_score) >= 10)
      .sort((a, b) => Math.abs(b.impact_score - b.attention_score) - Math.abs(a.impact_score - a.attention_score))
      .slice(0, 15);
  }, [stories]);

  return (
    <div>
      {sorted.map(s => {
        const gap = s.impact_score - s.attention_score;
        const gapInfo = getGapInfo(gap);
        const col = CAT_COLORS[s.category] || CAT_COLORS[getPrimaryCategory(s.category)] || "#888";

        return (
          <div key={s.id} onClick={() => onSelect(s.id)}
            style={{ display: "flex", alignItems: "center", padding: "5px 4px", cursor: "pointer", borderRadius: 4, transition: "background 0.12s" }}
            onMouseEnter={e => e.currentTarget.style.background = "#F9FAFB"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            {/* Story name + category */}
            <div style={{ width: 300, paddingRight: 16, flexShrink: 0 }}>
              <span style={{
                fontSize: 12, color: gapInfo.label ? "#1F2937" : "#6B7280",
                fontFamily: "'Source Serif 4',Georgia,serif",
                fontWeight: gapInfo.label ? 500 : 400,
                lineHeight: 1.3, display: "block",
              }}>{s.topic}</span>
              <span style={{ fontSize: 9, color: col, fontFamily: "'JetBrains Mono',monospace", fontWeight: 600 }}>{s.category.toUpperCase()}</span>
            </div>

            {/* Gap bar */}
            <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ flex: 1, height: 18, background: "#F9FAFB", borderRadius: 3, overflow: "hidden", position: "relative" }}>
                <div style={{
                  height: "100%", borderRadius: 3,
                  width: `${Math.max(Math.abs(gap), 2)}%`,
                  background: gapInfo.label
                    ? `linear-gradient(to right, ${gapInfo.barColor}15, ${gapInfo.barColor}50)`
                    : `linear-gradient(to right, ${col}10, ${col}35)`,
                  transition: "width 0.4s ease",
                }} />
                {Math.abs(gap) >= 10 && (
                  <span style={{
                    position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)",
                    fontSize: 9, fontWeight: 600, color: gapInfo.label ? gapInfo.textColor : "#9CA3AF",
                    fontFamily: "'JetBrains Mono',monospace",
                  }}>
                    {gap > 0 ? "+" : ""}{gap}
                  </span>
                )}
              </div>

              {/* Badge */}
              <div style={{ width: 90, flexShrink: 0, textAlign: "right" }}>
                {gapInfo.label && (
                  <span style={{
                    fontSize: 9, fontWeight: 600, color: gapInfo.textColor,
                    background: gapInfo.bgColor, padding: "3px 8px", borderRadius: 3,
                    fontFamily: "'JetBrains Mono',monospace",
                  }}>{gapInfo.label}</span>
                )}
              </div>
            </div>
          </div>
        );
      })}


    </div>
  );
}

function StoryCard({ story, onClick }) {
  const col = CAT_COLORS[story.category] || CAT_COLORS[getPrimaryCategory(story.category)] || "#888";
  const gap = story.impact_score - story.attention_score;
  const gapInfo = getGapInfo(gap);
  const statusStyle = STATUS_STYLES[story.status] || STATUS_STYLES.developing;

  return (
    <div onClick={onClick} style={{
      padding: "16px 20px", cursor: "pointer", transition: "background 0.12s",
      borderBottom: "1px solid #F3F4F6", background: "white",
    }}
      onMouseEnter={e => e.currentTarget.style.background = "#FAFAFA"}
      onMouseLeave={e => e.currentTarget.style.background = "white"}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: 15, fontWeight: 500, color: "#1F2937", fontFamily: "'Source Serif 4',Georgia,serif", lineHeight: 1.4, marginBottom: 4 }}>
            {story.topic}
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 9, color: statusStyle.color, background: statusStyle.bg, padding: "1px 6px", borderRadius: 3, fontFamily: "'JetBrains Mono',monospace" }}>{story.status}</span>
            <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>{story.article_count} articles · {story.source_count} sources</span>
            {story.analysis && <span style={{ fontSize: 8, color: "#6D28D9", fontFamily: "'JetBrains Mono',monospace", background: "#F3E8FF", padding: "1px 6px", borderRadius: 3 }}>Analysis</span>}
          </div>
        </div>
        {gapInfo.label && (
          <span style={{ fontSize: 9, fontWeight: 600, color: gapInfo.textColor, background: gapInfo.bgColor, padding: "4px 10px", borderRadius: 4, fontFamily: "'JetBrains Mono',monospace", flexShrink: 0 }}>
            {gapInfo.label}
          </span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "baseline" }}>
          <div>
            <div style={{ fontSize: 8, color: "#B0B0B0", fontFamily: "'JetBrains Mono',monospace", marginBottom: 1 }}>Impact</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "#374151", fontFamily: "'JetBrains Mono',monospace" }}>{story.impact_score}</div>
          </div>
          <span style={{ fontSize: 9, color: "#D1D5DB", fontFamily: "'JetBrains Mono',monospace" }}>{story.article_count} articles</span>
        </div>
        <div style={{ borderLeft: "1px solid #F3F4F6", paddingLeft: 14 }}>
          <SentimentInline left={story.sentiment_left} center={story.sentiment_center} right={story.sentiment_right} />
        </div>

      </div>
    </div>
  );
}

function StoryDetail({ story, onBack }) {
  const a = story.analysis;
  const col = CAT_COLORS[story.category] || CAT_COLORS[getPrimaryCategory(story.category)] || "#888";
  const gap = story.impact_score - story.attention_score;
  const gapInfo = getGapInfo(gap);
  const statusStyle = STATUS_STYLES[story.status] || STATUS_STYLES.developing;

  return (
    <div style={{ minHeight: "100vh", background: "#FAFAFA", animation: "fadeIn 0.25s ease" }}>
      <div style={{ padding: "10px 24px", borderBottom: "1px solid #E5E7EB", display: "flex", alignItems: "center", background: "white", position: "sticky", top: 0, zIndex: 50 }}>
        <button onClick={onBack} style={{ background: "none", border: "1px solid #E5E7EB", borderRadius: 6, color: "#6B7280", fontSize: 12, padding: "6px 16px", cursor: "pointer", fontFamily: "'JetBrains Mono',monospace" }}>← Back</button>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 4, height: 4, borderRadius: "50%", background: "#6D28D9" }} />
          <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: "0.12em", color: "#6D28D9", fontFamily: "'JetBrains Mono',monospace" }}>CLEARSIGNAL ANALYSIS</span>
        </div>
      </div>

      <article style={{ maxWidth: 680, margin: "0 auto", padding: "36px 24px 80px" }}>
        {/* === ARTICLE HEADER === */}
        {a ? (
          <>
            {/* Headline */}
            <h1 style={{ fontSize: 30, lineHeight: 1.28, fontFamily: "'Source Serif 4',Georgia,serif", fontWeight: 600, color: "#111827", marginBottom: 10 }}>{a.headline}</h1>

            {/* Dateline + meta inline */}
            <div style={{ marginBottom: 20 }}>
              <span style={{ fontSize: 12, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>{a.dateline}</span>
              <span style={{ fontSize: 12, color: "#D1D5DB", margin: "0 8px" }}>·</span>
              <span style={{ fontSize: 12, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>{story.article_count} articles from {story.source_count} sources</span>
              {story.population_affected && <>
                <span style={{ fontSize: 12, color: "#D1D5DB", margin: "0 8px" }}>·</span>
                <span style={{ fontSize: 12, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>Affects: {story.population_affected}</span>
              </>}
            </div>

            {/* Compact metadata bar: scores + sentiment + coverage note */}
            <div style={{ padding: "14px 18px", background: "#F9FAFB", borderRadius: 8, border: "1px solid #F3F4F6", marginBottom: 28 }}>
              {/* Metadata in one row */}
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: a.coverage_note ? 10 : 0, flexWrap: "wrap" }}>
                {/* Impact */}
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>Impact</span>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "#374151", fontFamily: "'JetBrains Mono',monospace" }}>{story.impact_score}</span>
                </div>

                <div style={{ width: 1, height: 16, background: "#E5E7EB" }} />

                {/* Badges */}
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span style={{ fontSize: 9, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono',monospace", letterSpacing: "0.05em" }}>{story.category.toUpperCase()}</span>
                  <span style={{ fontSize: 9, color: statusStyle.color, background: statusStyle.bg, padding: "1px 6px", borderRadius: 3, fontFamily: "'JetBrains Mono',monospace" }}>{story.status}</span>
                  {gapInfo.label && <span style={{ fontSize: 9, fontWeight: 600, color: gapInfo.textColor, background: gapInfo.bgColor, padding: "1px 6px", borderRadius: 3, fontFamily: "'JetBrains Mono',monospace" }}>{gapInfo.label}</span>}
                </div>

                <div style={{ width: 1, height: 16, background: "#E5E7EB" }} />

                {/* Sentiment inline */}
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>Sentiment</span>
                  {[
                    { label: "L", val: story.sentiment_left, color: "#2563EB" },
                    { label: "C", val: story.sentiment_center, color: "#6B7280" },
                    { label: "R", val: story.sentiment_right, color: "#DC2626" },
                  ].map(s => (
                    <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                      <span style={{ fontSize: 9, fontWeight: 600, color: s.color, fontFamily: "'JetBrains Mono',monospace", opacity: 0.7 }}>{s.label}</span>
                      <span style={{ fontSize: 11, fontWeight: 600, color: s.val === null ? "#D1D5DB" : "#374151", fontFamily: "'JetBrains Mono',monospace" }}>
                        {s.val === null ? "—" : `${s.val >= 0 ? "+" : ""}${s.val.toFixed(2)}`}
                      </span>
                    </div>
                  ))}
                </div>

              </div>

              {/* Coverage note as a sentence under the scores */}
              {a.coverage_note && (
                <p style={{ fontSize: 12, lineHeight: 1.6, color: "#6B7280", fontFamily: "'Source Serif 4',Georgia,serif", borderTop: "1px solid #F3F4F6", paddingTop: 10, margin: 0 }}>
                  {a.coverage_note}
                </p>
              )}
            </div>

            {/* === ARTICLE BODY === */}
            <p style={{ fontSize: 17, lineHeight: 1.85, fontFamily: "'Source Serif 4',Georgia,serif", color: "#374151", marginBottom: 24 }}>{a.lede}</p>
            <p style={{ fontSize: 16, lineHeight: 1.85, fontFamily: "'Source Serif 4',Georgia,serif", color: "#4B5563", marginBottom: 36 }}>{a.context}</p>

            {/* Divider */}
            <div style={{ height: 1, background: "#E5E7EB", marginBottom: 32 }} />

            {/* Contrasts */}
            {a.contrasts?.length > 0 && (
              <section style={{ marginBottom: 36 }}>
                <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.06em", color: "#374151", fontFamily: "'JetBrains Mono',monospace", marginBottom: 6, textTransform: "uppercase" }}>How Coverage Differs</h2>
                <p style={{ fontSize: 13, color: "#9CA3AF", fontFamily: "'Source Serif 4',Georgia,serif", marginBottom: 16 }}>
                  Different outlets frame this story in different ways. Here's how the key themes break down across the political spectrum.
                </p>
                {a.contrasts.map((c, i) => {
                  const colA = BIAS_COLORS[c.biasA] || "#6B7280";
                  const colB = BIAS_COLORS[c.biasB] || "#6B7280";
                  return (
                    <div key={i} style={{ marginBottom: 16, padding: "18px 20px", background: "white", borderRadius: 8, border: "1px solid #E5E7EB" }}>
                      <p style={{ fontSize: 11, fontWeight: 600, color: "#374151", fontFamily: "'JetBrains Mono',monospace", marginBottom: 14, textTransform: "uppercase", letterSpacing: "0.04em" }}>{c.theme}</p>
                      <div style={{ display: "flex", gap: 20 }}>
                        <div style={{ flex: 1, borderLeft: `3px solid ${colA}`, paddingLeft: 14 }}>
                          <p style={{ fontSize: 10, fontWeight: 700, color: colA, fontFamily: "'JetBrains Mono',monospace", marginBottom: 6 }}>{c.sourceA} <span style={{ fontWeight: 400, opacity: 0.6 }}>({c.biasA})</span></p>
                          <p style={{ fontSize: 14, lineHeight: 1.7, color: "#4B5563", fontFamily: "'Source Serif 4',Georgia,serif" }}>{c.claimA}</p>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0, padding: "0 4px" }}>
                          <span style={{ fontSize: 9, color: "#D1D5DB", fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>VS</span>
                        </div>
                        <div style={{ flex: 1, borderLeft: `3px solid ${colB}`, paddingLeft: 14 }}>
                          <p style={{ fontSize: 10, fontWeight: 700, color: colB, fontFamily: "'JetBrains Mono',monospace", marginBottom: 6 }}>{c.sourceB} <span style={{ fontWeight: 400, opacity: 0.6 }}>({c.biasB})</span></p>
                          <p style={{ fontSize: 14, lineHeight: 1.7, color: "#4B5563", fontFamily: "'Source Serif 4',Georgia,serif" }}>{c.claimB}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </section>
            )}

            <div style={{ height: 1, background: "#E5E7EB", marginBottom: 32 }} />

            {/* Fact Checks */}
            {a.facts?.length > 0 && (
              <section style={{ marginBottom: 36 }}>
                <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.06em", color: "#374151", fontFamily: "'JetBrains Mono',monospace", marginBottom: 6, textTransform: "uppercase" }}>Fact Check</h2>
                <p style={{ fontSize: 13, color: "#9CA3AF", fontFamily: "'Source Serif 4',Georgia,serif", marginBottom: 16 }}>
                  Claims made in coverage of this story, checked against available evidence.
                </p>
                {a.facts.map((f, i) => {
                  const vs = VERDICT_STYLES[f.verdict] || VERDICT_STYLES.unverified;
                  return (
                    <div key={i} style={{ marginBottom: 14, padding: "16px 18px", background: "white", borderRadius: 8, border: `1px solid ${vs.border}` }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 8 }}>
                        <span style={{ fontSize: 9, fontWeight: 700, color: vs.color, background: vs.bg, padding: "3px 10px", borderRadius: 4, fontFamily: "'JetBrains Mono',monospace", flexShrink: 0, marginTop: 2 }}>{f.verdict.toUpperCase()}</span>
                        <p style={{ fontSize: 15, fontWeight: 500, color: "#1F2937", fontFamily: "'Source Serif 4',Georgia,serif", lineHeight: 1.5 }}>{f.claim}</p>
                      </div>
                      <p style={{ fontSize: 14, color: "#6B7280", fontFamily: "'Source Serif 4',Georgia,serif", lineHeight: 1.7, paddingLeft: 2 }}>{f.reality}</p>
                    </div>
                  );
                })}
              </section>
            )}

            <div style={{ height: 1, background: "#E5E7EB", marginBottom: 32 }} />

            {/* Bottom Line */}
            <div style={{ padding: "20px 22px", background: "#FEF2F2", borderRadius: 8, border: "1px solid #FECACA" }}>
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "#991B1B", fontFamily: "'JetBrains Mono',monospace", marginBottom: 10 }}>BOTTOM LINE — WHAT THIS MEANS FOR YOU</p>
              <p style={{ fontSize: 16, lineHeight: 1.8, color: "#374151", fontFamily: "'Source Serif 4',Georgia,serif" }}>{a.bottom_line}</p>
            </div>
          </>
        ) : (
          <div>
            <h1 style={{ fontSize: 26, lineHeight: 1.35, fontFamily: "'Source Serif 4',Georgia,serif", fontWeight: 600, color: "#1F2937", marginBottom: 20 }}>{story.topic}</h1>

            {/* Compact metadata bar for no-analysis state */}
            <div style={{ padding: "14px 18px", background: "#F9FAFB", borderRadius: 8, border: "1px solid #F3F4F6", marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>Impact</span>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "#374151", fontFamily: "'JetBrains Mono',monospace" }}>{story.impact_score}</span>
                </div>
                <div style={{ width: 1, height: 16, background: "#E5E7EB" }} />
                <span style={{ fontSize: 9, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono',monospace" }}>{story.category.toUpperCase()}</span>
                <span style={{ fontSize: 9, color: statusStyle.color, background: statusStyle.bg, padding: "1px 6px", borderRadius: 3, fontFamily: "'JetBrains Mono',monospace" }}>{story.status}</span>
                {gapInfo.label && <span style={{ fontSize: 9, fontWeight: 600, color: gapInfo.textColor, background: gapInfo.bgColor, padding: "1px 6px", borderRadius: 3, fontFamily: "'JetBrains Mono',monospace" }}>{gapInfo.label}</span>}
              </div>
            </div>

            <div style={{ fontSize: 12, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace", marginBottom: 20 }}>{story.article_count} articles from {story.source_count} sources</div>

            <div style={{ padding: 24, background: "white", borderRadius: 8, border: "1px solid #E5E7EB", textAlign: "center" }}>
              <p style={{ fontSize: 13, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace", marginBottom: 4 }}>Neutral analysis not yet generated</p>
              <p style={{ fontSize: 12, color: "#D1D5DB", fontFamily: "'JetBrains Mono',monospace" }}>Analysis is generated for high-priority stories first.</p>
            </div>
          </div>
        )}
      </article>
    </div>
  );
}

export default function ClearSignal() {
  const [selectedId, setSelectedId] = useState(null);
  const [sortBy, setSortBy] = useState("gap");
  const [filterCat, setFilterCat] = useState("All");

  const categories = useMemo(() => {
    const pcs = [...new Set(STORIES.map(s => getPrimaryCategory(s.category)))].sort();
    return ["All", ...pcs];
  }, []);

  const filtered = useMemo(() => {
    let list = filterCat === "All" ? [...STORIES] : STORIES.filter(s => getPrimaryCategory(s.category) === filterCat);
    switch (sortBy) {
      case "gap": list.sort((a, b) => Math.abs(b.impact_score - b.attention_score) - Math.abs(a.impact_score - a.attention_score)); break;
      case "impact": list.sort((a, b) => b.impact_score - a.impact_score); break;
      case "attention": list.sort((a, b) => b.article_count - a.article_count); break;
      case "recent": list.sort((a, b) => (b.trend?.slice(-1)[0]?.date || "").localeCompare(a.trend?.slice(-1)[0]?.date || "")); break;
    }
    return list;
  }, [sortBy, filterCat]);

  const grouped = useMemo(() => {
    if (filterCat !== "All") return [[filterCat, filtered]];
    const g = {};
    filtered.forEach(s => {
      const pc = getPrimaryCategory(s.category);
      if (!g[pc]) g[pc] = [];
      g[pc].push(s);
    });
    return Object.entries(g).sort((a, b) => {
      const sA = a[1].reduce((s, x) => s + x.impact_score, 0);
      const sB = b[1].reduce((s, x) => s + x.impact_score, 0);
      return sB - sA;
    });
  }, [filtered, filterCat]);

  const buriedCount = STORIES.filter(s => s.impact_score - s.attention_score >= 30).length;
  const overCount = STORIES.filter(s => s.attention_score - s.impact_score >= 30).length;

  const selected = STORIES.find(s => s.id === selectedId);
  if (selected) return <StoryDetail story={selected} onBack={() => setSelectedId(null)} />;

  const selectStyle = { background: "white", border: "1px solid #E5E7EB", borderRadius: 6, color: "#374151", fontSize: 11, padding: "6px 12px", fontFamily: "'JetBrains Mono',monospace", cursor: "pointer", outline: "none" };

  return (
    <div style={{ minHeight: "100vh", background: "#FAFAFA", color: "#374151" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,300;8..60,400;8..60,500;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
        * { box-sizing:border-box; margin:0; padding:0; }
        body { background:#FAFAFA; }
      `}</style>

      <header style={{ background: "white", borderBottom: "1px solid #E5E7EB", padding: "20px 28px 16px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 8 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", color: "#111827", letterSpacing: "-0.03em" }}>
              Clear<span style={{ color: "#6D28D9" }}>Signal</span>
            </h1>
            <span style={{ fontSize: 11, color: "#9CA3AF", fontFamily: "'Source Serif 4',Georgia,serif", fontStyle: "italic" }}>What matters vs. what gets covered</span>
          </div>
          <div style={{ display: "flex", gap: 16, fontSize: 10, fontFamily: "'JetBrains Mono',monospace", color: "#9CA3AF" }}>
            <span>{STORIES.length} stories</span>
            <span>{STORIES.reduce((s, x) => s + x.article_count, 0).toLocaleString()} articles</span>
            <span style={{ color: "#991B1B" }}>{buriedCount} underreported</span>
            <span style={{ color: "#92400E" }}>{overCount} overcovered</span>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "24px 24px 80px" }}>
        {/* Gap chart */}
        <section style={{ background: "white", borderRadius: 10, border: "1px solid #E5E7EB", padding: "20px 24px", marginBottom: 28 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.06em", color: "#374151", fontFamily: "'JetBrains Mono',monospace", textTransform: "uppercase", marginBottom: 6 }}>Coverage Monitor</h2>
          <p style={{ fontSize: 13, color: "#6B7280", fontFamily: "'Source Serif 4',Georgia,serif", lineHeight: 1.6, marginBottom: 12 }}>
            Stories ranked by real-world significance. We compare each story's impact — who it affects, how many people, how much it matters — against the volume of media coverage it actually receives. When those two things don't match, we flag it.
          </p>
          <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: 2, background: "#DC2626", opacity: 0.7 }} />
              <span style={{ fontSize: 11, color: "#374151", fontFamily: "'JetBrains Mono',monospace", fontWeight: 500 }}>Underreported</span>
              <span style={{ fontSize: 11, color: "#9CA3AF", fontFamily: "'Source Serif 4',Georgia,serif" }}>— high significance, little coverage</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: 2, background: "#D97706", opacity: 0.7 }} />
              <span style={{ fontSize: 11, color: "#374151", fontFamily: "'JetBrains Mono',monospace", fontWeight: 500 }}>Overcovered</span>
              <span style={{ fontSize: 11, color: "#9CA3AF", fontFamily: "'Source Serif 4',Georgia,serif" }}>— low significance, heavy coverage</span>
            </div>
          </div>
          <GapChart stories={STORIES} onSelect={setSelectedId} />
        </section>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "center" }}>
          <span style={{ fontSize: 10, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace" }}>Sort by</span>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={selectStyle}>
            <option value="gap">Biggest mismatch</option>
            <option value="impact">Highest impact</option>
            <option value="recent">Most recent</option>
          </select>
          <span style={{ fontSize: 10, color: "#9CA3AF", fontFamily: "'JetBrains Mono',monospace", marginLeft: 8 }}>Category</span>
          <select value={filterCat} onChange={e => setFilterCat(e.target.value)} style={selectStyle}>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Grouped stories */}
        {grouped.map(([cat, stories]) => {
          const col = CAT_COLORS[cat] || "#888";
          return (
            <section key={cat} style={{ marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, paddingLeft: 4 }}>
                <div style={{ width: 3, height: 16, borderRadius: 2, background: col }} />
                <h3 style={{ fontSize: 12, fontWeight: 700, color: col, fontFamily: "'JetBrains Mono',monospace", letterSpacing: "0.06em" }}>{cat.toUpperCase()}</h3>
                <span style={{ fontSize: 10, color: "#D1D5DB", fontFamily: "'JetBrains Mono',monospace" }}>{stories.length}</span>
              </div>
              <div style={{ background: "white", borderRadius: 10, border: "1px solid #E5E7EB", overflow: "hidden" }}>
                {stories.map(s => <StoryCard key={s.id} story={s} onClick={() => setSelectedId(s.id)} />)}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}