import { useState, useMemo } from "react";

const S = [
  { id:67, topic:"Trump Administration Deportation Policy Effects", cat:"POLITICS", imp:78, att:100, arts:228, srcs:71, pop:"11M+ undocumented immigrants", sl:-0.28, sc:-0.05, sr:0.18,
    a:{ hl:"Trump Administration Immigration Enforcement Actions Draw State and Local Responses", dl:"WASHINGTON", lede:"Immigration and Customs Enforcement operations under the Trump administration have prompted responses from state and local governments, civil rights organizations, and educational institutions.", ctx:"The Trump administration has expanded immigration enforcement operations, including deportation proceedings and increased ICE presence in communities. Schools, churches, and courthouses have become flashpoints as advocates push back against enforcement in sensitive locations.", con:[{th:"Economic impact of deportation policy",sA:"Washington Examiner",bA:"right",cA:"Reports rents are falling as deportations rise, suggesting immigration enforcement is changing housing markets",sB:"The Guardian",bB:"left-center",cB:"Characterizes Republican policies as separating and destroying families, focusing on social harm rather than economic effects"},{th:"ICE enforcement tactics near schools",sA:"Breitbart",bA:"right",cA:"Reports immigrant families describe sending children to school as an act of faith amid enforcement concerns",sB:"MPR News",bB:"center",cB:"Covers community impact on school attendance and parent anxiety about ICE presence near educational facilities"}], fax:[{cl:"ICE chartered flights on aircraft owned by Trump family associates",re:"The Guardian reports ICE used jets owned by a Trump family friend, though contract details require verification",v:"unverified"},{cl:"Census Bureau plans to test citizenship question for 2030 census",re:"Multiple outlets confirm the Census Bureau is including citizenship questions in test surveys",v:"confirmed"}], bl:"Families in immigrant communities face decisions about daily activities like school attendance amid expanded enforcement. Housing markets and local economies may experience changes.", cn:"228 articles from 71 sources across all political leans. Right-leaning outlets emphasize economic effects; left-leaning sources focus on family separation and civil rights." }},
  { id:26, topic:"Stellantis Takes $26.5B EV Writedown, Shares Plunge 20%", cat:"BUSINESS", imp:72, att:24, arts:3, srcs:2, pop:"Stellantis workers, EV investors", sl:null, sc:-0.35, sr:null,
    a:{ hl:"Stellantis Takes $26.5 Billion Writedown, Shares Drop Over 20 Percent", dl:"AMSTERDAM", lede:"Stellantis NV shares fell more than 20 percent after the automaker announced a $26.5 billion writedown tied to its electric vehicle operations — one of the largest financial adjustments in automotive history.", ctx:"The writedown reflects broader challenges in the EV transition as consumer adoption slows and competition from Chinese manufacturers intensifies. Stellantis, parent of Jeep, Chrysler, Ram, and Fiat, had invested heavily in electrification.", con:[{th:"EV transition framing",sA:"CNBC",bA:"center",cA:"Framed as Stellantis over-estimating the pace of the energy transition",sB:"Google News",bB:"center",cB:"Described neutrally as an EV-related writedown"}], fax:[{cl:"$26.5 billion writedown announced",re:"Multiple outlets consistently report this figure",v:"confirmed"},{cl:"Shares fell over 20%",re:"Market data confirms the decline",v:"confirmed"}], bl:"Stellantis workers may face job cuts or plant closures. Consumers may see fewer new EV models. The writedown signals the EV transition is far more expensive than projected.", cn:"Only 3 articles from 2 center-leaning sources. No left or right coverage despite massive significance for climate policy, jobs, and investors." }},
  { id:24, topic:"Sudan Humanitarian Crisis Worsens as Conflict Continues", cat:"WORLD", imp:78, att:54, arts:5, srcs:5, pop:"25M+ Sudanese civilians", sl:-0.40, sc:-0.32, sr:null,
    a:{ hl:"Sudan Crisis Deepens as Civil War Displaces Millions", dl:"KHARTOUM", lede:"The ongoing civil war in Sudan has displaced over 10 million people and created what the UN calls the world's largest humanitarian crisis, yet coverage remains sparse.", ctx:"Fighting between the Sudanese Armed Forces and the Rapid Support Forces has destroyed hospitals, blocked aid corridors, and triggered famine conditions in multiple regions.", con:[{th:"Scale of crisis",sA:"The Guardian",bA:"left-center",cA:"Describes Sudan as a forgotten catastrophe eclipsing other global conflicts",sB:"AP",bB:"center",cB:"Reports factually on displacement numbers without editorial framing"}], fax:[{cl:"Over 10 million displaced",re:"UN agencies confirm this figure",v:"confirmed"}], bl:"25 million Sudanese civilians face famine, displacement, and violence. International aid remains far below what's needed.", cn:"5 articles from 5 sources. For a crisis affecting 25 million people, remarkably little attention." }},
  { id:61, topic:"US and Iran Begin Nuclear Talks in Oman", cat:"WORLD", imp:74, att:85, arts:24, srcs:16, pop:"Global security", sl:-0.12, sc:-0.08, sr:-0.22,
    a:{ hl:"US and Iran Begin Nuclear Talks in Oman Amid Uncertain Prospects", dl:"MUSCAT", lede:"American and Iranian officials met in Oman for negotiations over Iran's nuclear program, the first direct talks as the Trump administration prepares expanded sanctions.", ctx:"The US withdrew from the JCPOA in 2018. Iran has since expanded enrichment beyond original limits, bringing it closer to weapons-grade capability.", con:[{th:"Likelihood of success",sA:"Bloomberg",bA:"left-center",cA:"Iran signals negotiations won't lead to quick resolution",sB:"National Review",bB:"right",cB:"Frames Iran as wanting to turn back to the pre-2018 agreement without concessions"}], fax:[{cl:"Officials are meeting in Oman",re:"Confirmed by multiple outlets",v:"confirmed"}], bl:"If talks fail, Americans could face higher oil prices, continued Middle East instability, and potential military escalation.", cn:"24 articles from 16 sources, heavily skewed left-center with minimal right-wing attention." }},
  { id:38, topic:"Supreme Court Upholds California Congressional Map", cat:"POLITICS", imp:68, att:50, arts:4, srcs:4, pop:"39M Californians, 52 House seats", sl:0.56, sc:null, sr:-0.36,
    a:{ hl:"Supreme Court Declines to Block California Congressional Map", dl:"WASHINGTON", lede:"The Supreme Court rejected an emergency request to block California's congressional map, allowing current boundaries for the 2026 midterms.", ctx:"Challengers alleged racial gerrymandering. The decision affects 52 congressional seats — more than any other state.", con:[{th:"Significance of ruling",sA:"Vox",bA:"left",cA:"Characterized as a victory for Democrats from a Republican-majority Court",sB:"The Federalist",bB:"right",cB:"Framed the map as racially gerrymandered"}], fax:[{cl:"The ruling is a victory for Democrats",re:"The order allows the current map to stand but is not a final ruling on the merits",v:"lacks context"}], bl:"California voters will use the current map for 2026 midterms. Could affect balance of power in the House.", cn:"Only 4 articles with a stark left-right divide. Sparse for 52 seats." }},
  { id:64, topic:"DNI Gabbard Attends FBI Raid on Georgia Election Office", cat:"POLITICS", imp:68, att:70, arts:11, srcs:5, pop:"Election integrity", sl:-0.30, sc:-0.15, sr:null,
    a:{ hl:"Director of National Intelligence Attends FBI Raid on Georgia Election Office", dl:"ATLANTA", lede:"DNI Tulsi Gabbard accompanied FBI agents during a raid on the Fulton County election office, raising questions about the intelligence community's role in domestic law enforcement.", ctx:"The DNI position typically coordinates 18 intelligence agencies focused on foreign threats. Her presence at a domestic operation is unprecedented for the role.", con:[{th:"Appropriateness of Gabbard's role",sA:"The Guardian",bA:"left-center",cA:"Characterized as a warning about intelligence overreach",sB:"PBS",bB:"center",cB:"Reported Trump's statement that Gabbard joined at AG Bondi's insistence"}], fax:[{cl:"Gabbard was physically present",re:"Video footage confirmed her presence",v:"confirmed"},{cl:"The DNI typically participates in domestic law enforcement",re:"The role focuses on foreign intelligence; this is outside standard responsibilities",v:"lacks context"}], bl:"The nation's top intelligence official attending a local election office raid blurs the line between intelligence and domestic law enforcement.", cn:"11 articles from 5 sources, all left or center. Zero right-leaning coverage." }},
  { id:84, topic:"Various Business and Lifestyle Ventures Announced", cat:"BUSINESS", imp:18, att:78, arts:7, srcs:6, pop:"Minimal", sl:null, sc:0.12, sr:0.08, a:null },
  { id:125, topic:"Black Hole Jet Destroys Surrounding Planets", cat:"SCIENCE", imp:2, att:61, arts:3, srcs:6, pop:"None", sl:null, sc:0.30, sr:null, a:null },
];

const BC={"far-left":"#1D4ED8",left:"#2563EB","left-center":"#3B82F6",center:"#6B7280","right-center":"#DC2626",right:"#B91C1C","far-right":"#991B1B"};
const VR={confirmed:{bg:"#DCFCE7",c:"#166534",b:"#BBF7D0"},misleading:{bg:"#FEE2E2",c:"#991B1B",b:"#FECACA"},"lacks context":{bg:"#FEF3C7",c:"#92400E",b:"#FDE68A"},unverified:{bg:"#F3F4F6",c:"#4B5563",b:"#E5E7EB"}};
const CATS=[{key:"POLITICS",label:"POLITICS",color:"#D93644"},{key:"WORLD",label:"WORLD",color:"#2563EB"},{key:"BUSINESS",label:"BUSINESS",color:"#B8860B"},{key:"SCIENCE",label:"SCIENCE",color:"#047857"}];
const gap=s=>Math.round(s.imp-s.att);
const cc=c=>CATS.find(x=>x.key===c)?.color||"#6B7280";

function Hero({stories,onPick}){
  const under=stories.filter(s=>gap(s)>=30&&s.a).sort((a,b)=>gap(b)-gap(a))[0];
  const over=stories.filter(s=>gap(s)<=-30).sort((a,b)=>gap(a)-gap(b))[0];
  if(!under)return null;
  return(
    <div style={{background:"white",borderBottom:"1px solid #E5E7EB"}}>
      <div style={{maxWidth:1200,margin:"0 auto",padding:"56px 40px 0"}}>
        <h2 style={{fontSize:48,fontWeight:700,fontFamily:"'Source Serif 4',Georgia,serif",color:"#111827",lineHeight:1.1,marginBottom:14,letterSpacing:"-0.02em"}}>
          The news you're<br/>not getting.
        </h2>
        <p style={{fontSize:18,color:"#4B5563",fontFamily:"'Source Serif 4',Georgia,serif",lineHeight:1.7,maxWidth:560,marginBottom:48}}>
          We track hundreds of sources across the political spectrum and compare what's covered against what actually matters.
        </p>
      </div>
      <div style={{display:"flex",maxWidth:1200,margin:"0 auto"}}>
        {/* Underreported */}
        <div onClick={()=>onPick(under.id)} style={{flex:1,background:"#FEF2F2",padding:"32px 40px",cursor:"pointer",transition:"background 0.12s",borderTop:"3px solid #DC2626"}}
          onMouseEnter={e=>e.currentTarget.style.background="#FEE2E2"} onMouseLeave={e=>e.currentTarget.style.background="#FEF2F2"}>
          <div style={{fontSize:10,fontWeight:700,color:"#DC2626",fontFamily:"'JetBrains Mono',monospace",letterSpacing:"0.12em",marginBottom:14}}>UNDERREPORTED</div>
          <h3 style={{fontSize:18,fontWeight:600,fontFamily:"'Source Serif 4',Georgia,serif",color:"#1F2937",lineHeight:1.35,marginBottom:20}}>{under.topic}</h3>
          <div style={{display:"flex",gap:28}}>
            <div>
              <div style={{fontSize:44,fontWeight:800,color:"#DC2626",fontFamily:"'JetBrains Mono',monospace",lineHeight:1}}>{under.arts}</div>
              <div style={{fontSize:10,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:4}}>articles</div>
            </div>
            <div>
              <div style={{fontSize:44,fontWeight:800,color:"#1F2937",fontFamily:"'JetBrains Mono',monospace",lineHeight:1}}>{under.imp}</div>
              <div style={{fontSize:10,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:4}}>impact score</div>
            </div>
          </div>
          <div style={{fontSize:11,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:16}}>Affects: {under.pop}</div>
        </div>
        {/* Overcovered */}
        {over&&(
          <div onClick={()=>over.a&&onPick(over.id)} style={{flex:1,background:"#FFFBEB",padding:"32px 40px",cursor:over.a?"pointer":"default",transition:"background 0.12s",borderTop:"3px solid #D97706"}}
            onMouseEnter={e=>{if(over.a)e.currentTarget.style.background="#FEF3C7"}} onMouseLeave={e=>e.currentTarget.style.background="#FFFBEB"}>
            <div style={{fontSize:10,fontWeight:700,color:"#D97706",fontFamily:"'JetBrains Mono',monospace",letterSpacing:"0.12em",marginBottom:14}}>OVERCOVERED</div>
            <h3 style={{fontSize:18,fontWeight:600,fontFamily:"'Source Serif 4',Georgia,serif",color:"#1F2937",lineHeight:1.35,marginBottom:20}}>{over.topic}</h3>
            <div style={{display:"flex",gap:28}}>
              <div>
                <div style={{fontSize:44,fontWeight:800,color:"#D97706",fontFamily:"'JetBrains Mono',monospace",lineHeight:1}}>{over.arts}</div>
                <div style={{fontSize:10,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:4}}>articles</div>
              </div>
              <div>
                <div style={{fontSize:44,fontWeight:800,color:"#1F2937",fontFamily:"'JetBrains Mono',monospace",lineHeight:1}}>{over.imp}</div>
                <div style={{fontSize:10,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:4}}>impact score</div>
              </div>
            </div>
            <div style={{fontSize:11,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginTop:16}}>Affects: {over.pop}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function CatNav({stories,sel,onSel}){
  const all=stories.filter(s=>s.a).length;
  return(
    <div style={{borderBottom:"1px solid #E5E7EB",background:"white"}}>
      <div style={{maxWidth:1200,margin:"0 auto",padding:"0 40px",display:"flex",gap:0}}>
        <button onClick={()=>onSel(null)} style={{padding:"14px 24px",background:"none",border:"none",borderBottom:!sel?"2px solid #111827":"2px solid transparent",
          color:!sel?"#111827":"#9CA3AF",fontFamily:"'JetBrains Mono',monospace",fontSize:11,fontWeight:700,letterSpacing:"0.06em"}}>
          ALL <span style={{fontWeight:400,marginLeft:4}}>{all}</span>
        </button>
        {CATS.map(cat=>{
          const n=stories.filter(s=>s.cat===cat.key&&s.a).length;
          const on=sel===cat.key;
          return(
            <button key={cat.key} onClick={()=>onSel(cat.key)} style={{padding:"14px 24px",background:"none",border:"none",
              borderBottom:on?`2px solid ${cat.color}`:"2px solid transparent",
              color:on?cat.color:"#9CA3AF",fontFamily:"'JetBrains Mono',monospace",fontSize:11,fontWeight:700,letterSpacing:"0.06em"}}>
              {cat.label} <span style={{fontWeight:400,marginLeft:4}}>{n}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Bar({s,onClick}){
  const g=gap(s),ag=Math.abs(g),isU=g>=30,isO=g<=-30,col=cc(s.cat),bc=isU?"#DC2626":isO?"#D97706":col;
  return(
    <div onClick={onClick} style={{display:"flex",alignItems:"center",padding:"14px 20px",cursor:"pointer",borderBottom:"1px solid #F3F4F6",transition:"background 0.1s"}}
      onMouseEnter={e=>e.currentTarget.style.background="#FAFAFA"} onMouseLeave={e=>e.currentTarget.style.background="white"}>
      <div style={{width:360,paddingRight:24,flexShrink:0}}>
        <div style={{fontSize:15,color:"#111827",fontFamily:"'Source Serif 4',Georgia,serif",fontWeight:500,lineHeight:1.4,marginBottom:3}}>{s.topic}</div>
        <div style={{fontSize:10,color:"#6B7280",fontFamily:"'JetBrains Mono',monospace"}}>{s.arts} articles from {s.srcs} sources</div>
      </div>
      <div style={{flex:1,display:"flex",alignItems:"center",gap:12}}>
        <div style={{flex:1,height:26,background:"#F3F4F6",overflow:"hidden",position:"relative"}}>
          <div style={{height:"100%",width:`${Math.max(ag,2)}%`,background:(isU||isO)?`linear-gradient(to right,${bc}20,${bc}55)`:`linear-gradient(to right,${col}10,${col}25)`}}/>
          {ag>=8&&<span style={{position:"absolute",left:12,top:"50%",transform:"translateY(-50%)",fontSize:11,fontWeight:700,color:(isU||isO)?bc:"#6B7280",fontFamily:"'JetBrains Mono',monospace"}}>{g>0?"+":""}{g}</span>}
        </div>
        <div style={{width:110,flexShrink:0,textAlign:"right"}}>
          {isU&&<span style={{fontSize:10,fontWeight:700,color:"#991B1B",background:"#FEE2E2",padding:"5px 12px",fontFamily:"'JetBrains Mono',monospace"}}>Underreported</span>}
          {isO&&<span style={{fontSize:10,fontWeight:700,color:"#92400E",background:"#FEF3C7",padding:"5px 12px",fontFamily:"'JetBrains Mono',monospace"}}>Overcovered</span>}
        </div>
      </div>
    </div>
  );
}

function Detail({s,onBack}){
  const a=s.a,g=gap(s),isU=g>=30,isO=g<=-30;
  return(
    <div style={{minHeight:"100vh",background:"#FAFAFA",animation:"fadeIn 0.15s ease"}}>
      {/* Sticky nav */}
      <div style={{padding:"10px 40px",borderBottom:"1px solid #E5E7EB",display:"flex",alignItems:"center",background:"white",position:"sticky",top:0,zIndex:50}}>
        <button onClick={onBack} style={{background:"none",border:"1px solid #E5E7EB",color:"#111827",fontSize:12,padding:"6px 16px",cursor:"pointer",fontFamily:"'JetBrains Mono',monospace"}}>← Back</button>
        <div style={{flex:1}}/>
        <span style={{fontSize:9,fontWeight:700,letterSpacing:"0.12em",color:"#6D28D9",fontFamily:"'JetBrains Mono',monospace"}}>CLEARSIGNAL ANALYSIS</span>
      </div>

      {a ? (<>
        {/* Hero banner — full span, colored top border like homepage cards */}
        <div style={{background:"white",borderBottom:"1px solid #E5E7EB",borderTop:isU?"3px solid #DC2626":isO?"3px solid #D97706":"3px solid #6D28D9"}}>
          <div style={{maxWidth:1200,margin:"0 auto",padding:"40px 40px 32px"}}>
            <div style={{display:"flex",gap:48,alignItems:"flex-start"}}>
              {/* Left: headline + byline */}
              <div style={{flex:1,minWidth:0}}>
                <h1 style={{fontSize:36,lineHeight:1.2,fontFamily:"'Source Serif 4',Georgia,serif",fontWeight:700,color:"#111827",marginBottom:14}}>{a.hl}</h1>
                <div style={{fontSize:13,color:"#374151",fontFamily:"'JetBrains Mono',monospace",marginBottom:16}}>
                  {a.dl} — {s.arts} articles from {s.srcs} sources{s.pop&&s.pop!=="Minimal"&&s.pop!=="None"?` — Affects: ${s.pop}`:""}
                </div>
                {/* Badges inline */}
                <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
                  {isU&&<span style={{fontSize:10,fontWeight:700,color:"#991B1B",background:"#FEE2E2",padding:"4px 10px",fontFamily:"'JetBrains Mono',monospace"}}>UNDERREPORTED</span>}
                  {isO&&<span style={{fontSize:10,fontWeight:700,color:"#92400E",background:"#FEF3C7",padding:"4px 10px",fontFamily:"'JetBrains Mono',monospace"}}>OVERCOVERED</span>}
                  <span style={{fontSize:10,fontWeight:700,color:cc(s.cat),fontFamily:"'JetBrains Mono',monospace",letterSpacing:"0.06em"}}>{s.cat}</span>
                </div>
              </div>
              {/* Right: scores block */}
              <div style={{flexShrink:0,display:"flex",gap:20}}>
                {[{l:"Impact",v:s.imp},{l:"Attention",v:s.att},{l:"Gap",v:`${g>0?"+":""}${g}`,c:isU?"#DC2626":isO?"#D97706":"#111827"}].map(x=>(
                  <div key={x.l} style={{textAlign:"center"}}>
                    <div style={{fontSize:32,fontWeight:800,color:x.c||"#111827",fontFamily:"'JetBrains Mono',monospace",lineHeight:1}}>{x.v}</div>
                    <div style={{fontSize:10,color:"#6B7280",fontFamily:"'JetBrains Mono',monospace",marginTop:4}}>{x.l}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Metadata strip — full span */}
        <div style={{background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
          <div style={{maxWidth:1200,margin:"0 auto",padding:"14px 40px",display:"flex",alignItems:"center",gap:20,flexWrap:"wrap"}}>
            <span style={{fontSize:11,fontFamily:"'JetBrains Mono',monospace",color:"#6B7280"}}>Sentiment</span>
            {[{l:"L",v:s.sl,c:"#2563EB"},{l:"C",v:s.sc,c:"#6B7280"},{l:"R",v:s.sr,c:"#DC2626"}].map(x=>(
              <span key={x.l} style={{fontSize:11,fontFamily:"'JetBrains Mono',monospace"}}><span style={{color:x.c,fontWeight:700}}>{x.l}</span> <span style={{color:x.v===null?"#D1D5DB":"#111827",fontWeight:600}}>{x.v===null?"—":`${x.v>=0?"+":""}${x.v.toFixed(2)}`}</span></span>
            ))}
            {a.cn&&(<>
              <div style={{width:1,height:14,background:"#E5E7EB"}}/>
              <span style={{fontSize:12,color:"#374151",fontFamily:"'Source Serif 4',Georgia,serif",lineHeight:1.5}}>{a.cn}</span>
            </>)}
          </div>
        </div>

        {/* Article body — max width for readability */}
        <div style={{maxWidth:1200,margin:"0 auto",padding:"0 40px"}}>
          <article style={{maxWidth:720,padding:"40px 0 80px"}}>
            <p style={{fontSize:18,lineHeight:1.85,fontFamily:"'Source Serif 4',Georgia,serif",color:"#111827",marginBottom:24}}>{a.lede}</p>
            <p style={{fontSize:16,lineHeight:1.85,fontFamily:"'Source Serif 4',Georgia,serif",color:"#1F2937",marginBottom:48}}>{a.ctx}</p>

            {a.con?.length>0&&(<>
              <div style={{height:1,background:"#E5E7EB",marginBottom:36}}/>
              <h2 style={{fontSize:13,fontWeight:700,color:"#111827",fontFamily:"'JetBrains Mono',monospace",marginBottom:8,textTransform:"uppercase",letterSpacing:"0.08em"}}>How Coverage Differs</h2>
              <p style={{fontSize:15,color:"#374151",fontFamily:"'Source Serif 4',Georgia,serif",marginBottom:28,lineHeight:1.6}}>The same story, framed differently across the political spectrum.</p>
              {a.con.map((c,i)=>(
                <div key={i} style={{marginBottom:24,border:"1px solid #E5E7EB",overflow:"hidden"}}>
                  <div style={{padding:"14px 24px",background:"#F9FAFB",borderBottom:"1px solid #E5E7EB"}}>
                    <p style={{fontSize:11,fontWeight:700,color:"#111827",fontFamily:"'JetBrains Mono',monospace",textTransform:"uppercase",letterSpacing:"0.06em"}}>{c.th}</p>
                  </div>
                  <div style={{display:"flex"}}>
                    <div style={{flex:1,padding:"20px 24px",borderRight:"1px solid #E5E7EB",borderLeft:`3px solid ${BC[c.bA]||"#6B7280"}`}}>
                      <p style={{fontSize:11,fontWeight:700,color:BC[c.bA]||"#374151",fontFamily:"'JetBrains Mono',monospace",marginBottom:10}}>{c.sA} <span style={{fontWeight:400,color:"#6B7280"}}>({c.bA})</span></p>
                      <p style={{fontSize:15,lineHeight:1.7,color:"#1F2937",fontFamily:"'Source Serif 4',Georgia,serif"}}>{c.cA}</p>
                    </div>
                    <div style={{flex:1,padding:"20px 24px",borderLeft:`3px solid ${BC[c.bB]||"#6B7280"}`}}>
                      <p style={{fontSize:11,fontWeight:700,color:BC[c.bB]||"#374151",fontFamily:"'JetBrains Mono',monospace",marginBottom:10}}>{c.sB} <span style={{fontWeight:400,color:"#6B7280"}}>({c.bB})</span></p>
                      <p style={{fontSize:15,lineHeight:1.7,color:"#1F2937",fontFamily:"'Source Serif 4',Georgia,serif"}}>{c.cB}</p>
                    </div>
                  </div>
                </div>
              ))}
            </>)}

            {a.fax?.length>0&&(<>
              <div style={{height:1,background:"#E5E7EB",marginBottom:36}}/>
              <h2 style={{fontSize:13,fontWeight:700,color:"#111827",fontFamily:"'JetBrains Mono',monospace",marginBottom:8,textTransform:"uppercase",letterSpacing:"0.08em"}}>Fact Check</h2>
              <p style={{fontSize:15,color:"#374151",fontFamily:"'Source Serif 4',Georgia,serif",marginBottom:28,lineHeight:1.6}}>Claims from coverage, checked against available evidence.</p>
              {a.fax.map((f,i)=>{const v=VR[f.v]||VR.unverified;return(
                <div key={i} style={{marginBottom:16,border:`1px solid ${v.b}`,overflow:"hidden"}}>
                  <div style={{display:"flex",alignItems:"flex-start",gap:12,padding:"18px 24px",background:v.bg+"40"}}>
                    <span style={{fontSize:10,fontWeight:700,color:v.c,background:v.bg,padding:"4px 12px",fontFamily:"'JetBrains Mono',monospace",flexShrink:0}}>{f.v.toUpperCase()}</span>
                    <p style={{fontSize:16,fontWeight:500,color:"#111827",fontFamily:"'Source Serif 4',Georgia,serif",lineHeight:1.45}}>{f.cl}</p>
                  </div>
                  <div style={{padding:"16px 24px",background:"white"}}>
                    <p style={{fontSize:15,color:"#1F2937",fontFamily:"'Source Serif 4',Georgia,serif",lineHeight:1.7}}>{f.re}</p>
                  </div>
                </div>
              );})}
            </>)}

            <div style={{height:1,background:"#E5E7EB",margin:"40px 0"}}/>
            <div style={{padding:"28px 32px",background:"#FEF2F2",border:"1px solid #FECACA",borderTop:"3px solid #DC2626"}}>
              <p style={{fontSize:10,fontWeight:700,letterSpacing:"0.1em",color:"#DC2626",fontFamily:"'JetBrains Mono',monospace",marginBottom:14}}>BOTTOM LINE — WHAT THIS MEANS FOR YOU</p>
              <p style={{fontSize:18,lineHeight:1.8,color:"#111827",fontFamily:"'Source Serif 4',Georgia,serif"}}>{a.bl}</p>
            </div>
          </article>
        </div>
      </>):(
        <div style={{maxWidth:1200,margin:"0 auto",padding:"48px 40px"}}>
          <h1 style={{fontSize:28,fontFamily:"'Source Serif 4',Georgia,serif",fontWeight:600,color:"#111827",marginBottom:20}}>{s.topic}</h1>
          <div style={{padding:32,background:"white",border:"1px solid #E5E7EB",textAlign:"center"}}>
            <p style={{fontSize:14,color:"#374151",fontFamily:"'JetBrains Mono',monospace"}}>Analysis not yet generated.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ClearSignal(){
  const [selId,setSelId]=useState(null);
  const [selCat,setSelCat]=useState(null);
  const analyzed=useMemo(()=>S.filter(s=>s.a),[]);
  const displayed=useMemo(()=>{
    let l=analyzed;
    if(selCat)l=l.filter(s=>s.cat===selCat);
    return l.sort((a,b)=>Math.abs(gap(b))-Math.abs(gap(a)));
  },[analyzed,selCat]);
  const st=useMemo(()=>({t:S.length,an:analyzed.length,arts:analyzed.reduce((s,x)=>s+x.arts,0),un:analyzed.filter(s=>gap(s)>=30).length,ov:analyzed.filter(s=>gap(s)<=-30).length}),[analyzed]);
  const sel=S.find(s=>s.id===selId);
  if(sel)return<Detail s={sel} onBack={()=>setSelId(null)}/>;
  return(
    <div style={{minHeight:"100vh",background:"#FAFAFA"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,300;8..60,400;8..60,500;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        *{box-sizing:border-box;margin:0;padding:0}
        body{background:#FAFAFA}
        button{font-family:inherit;cursor:pointer}
      `}</style>
      <header style={{background:"white",borderBottom:"1px solid #E5E7EB",padding:"14px 40px"}}>
        <div style={{maxWidth:1200,margin:"0 auto",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
          <h1 style={{fontSize:22,fontWeight:800,fontFamily:"'JetBrains Mono',monospace",color:"#111827",letterSpacing:"-0.03em"}}>Clear<span style={{color:"#6D28D9"}}>Signal</span></h1>
          <div style={{display:"flex",gap:20,fontSize:11,fontFamily:"'JetBrains Mono',monospace",color:"#6B7280",alignItems:"center"}}>
            <span>{st.an} analyzed</span><span>{st.arts.toLocaleString()} articles</span>
            <span style={{color:"#DC2626",fontWeight:600}}>{st.un} underreported</span>
            <span style={{color:"#D97706",fontWeight:600}}>{st.ov} overcovered</span>
            <span style={{color:"#D1D5DB"}}>|</span><span>Tracking {st.t}</span>
          </div>
        </div>
      </header>
      <Hero stories={S} onPick={setSelId}/>
      <CatNav stories={S} sel={selCat} onSel={setSelCat}/>
      <main style={{maxWidth:1200,margin:"0 auto",padding:"32px 40px 80px"}}>
        <div style={{marginBottom:8,display:"flex",alignItems:"baseline",gap:12}}>
          <h2 style={{fontSize:13,fontWeight:700,color:"#111827",fontFamily:"'JetBrains Mono',monospace",textTransform:"uppercase",letterSpacing:"0.08em"}}>
            {selCat||"Coverage Monitor"}
          </h2>
          <span style={{fontSize:11,color:"#6B7280",fontFamily:"'JetBrains Mono',monospace"}}>{displayed.length} stories</span>
        </div>
        {!selCat&&<p style={{fontSize:14,color:"#374151",fontFamily:"'Source Serif 4',Georgia,serif",lineHeight:1.6,marginBottom:8,maxWidth:640}}>
          Ranked by the gap between real-world significance and media coverage.
        </p>}
        {!selCat&&<div style={{display:"flex",gap:24,marginBottom:20}}>
          <div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:12,height:3,background:"#DC2626"}}/><span style={{fontSize:10,fontFamily:"'JetBrains Mono',monospace",color:"#DC2626",fontWeight:600}}>Underreported</span><span style={{fontSize:10,fontFamily:"'JetBrains Mono',monospace",color:"#6B7280"}}>— important, ignored</span></div>
          <div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:12,height:3,background:"#D97706"}}/><span style={{fontSize:10,fontFamily:"'JetBrains Mono',monospace",color:"#D97706",fontWeight:600}}>Overcovered</span><span style={{fontSize:10,fontFamily:"'JetBrains Mono',monospace",color:"#6B7280"}}>— trivial, everywhere</span></div>
        </div>}
        <div style={{background:"white",border:"1px solid #E5E7EB"}}>
          {displayed.map(s=><Bar key={s.id} s={s} onClick={()=>setSelId(s.id)}/>)}
          {displayed.length===0&&<p style={{textAlign:"center",padding:40,color:"#6B7280",fontFamily:"'JetBrains Mono',monospace",fontSize:13}}>No analyzed stories in this category yet.</p>}
        </div>
      </main>
    </div>
  );
}
