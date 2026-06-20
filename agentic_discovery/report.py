"""Graph -> a self-contained, mobile-friendly HTML deliverable.

The synthesizers in each module produce text artifacts (Mermaid, Markdown).
This turns those plus the raw graph into one rich HTML page you can open on a
phone: a rendered process diagram, an interactive knowledge graph, the written
documentation and AI ideas, plus coverage/provenance/contradiction panels.

It is deliberately *generic* — it renders whatever artifacts a module emits and
whatever node/edge types are in the graph, so every discovery module gets a
graphical report for free. Rendering libraries load from CDNs (Mermaid, marked,
vis-network); the page itself is a single file with all data embedded.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field

from .graph import KnowledgeGraph

# Stable colour per node type — keeps the legend and graph consistent.
_PALETTE = [
    "#4c6ef5", "#12b886", "#f59f00", "#e8590c", "#ae3ec9",
    "#1098ad", "#e64980", "#7048e8", "#74b816", "#fa5252",
]


@dataclass
class ReportMeta:
    module_title: str = "Discovery"
    goal: str = ""
    interviewee: str = ""
    coverage_trace: list[float] = field(default_factory=list)
    stop_reason: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)


def _type_colors(graph: KnowledgeGraph) -> dict[str, str]:
    types = sorted({n.type for n in graph.nodes.values()})
    return {t: _PALETTE[i % len(_PALETTE)] for i, t in enumerate(types)}


def _vis_data(graph: KnowledgeGraph, colors: dict[str, str]) -> dict:
    nodes = []
    for n in graph.nodes.values():
        srcs = ", ".join(sorted(n.sources)) or "—"
        title = f"{n.type} · confidence {n.confidence:.0%} · source: {srcs}"
        nodes.append({
            "id": n.id, "label": n.label, "group": n.type,
            "title": title, "color": colors.get(n.type, "#868e96"),
            "value": 1 + len(graph.edges_from(n.id)) + len(graph.edges_to(n.id)),
        })
    edges = [{"from": e.source, "to": e.target, "label": e.type}
             for e in graph.edges.values()]
    return {"nodes": nodes, "edges": edges}


def _provenance_rows(graph: KnowledgeGraph) -> list[dict]:
    rows = []
    for n in graph.nodes.values():
        for c in n.claims:
            if c.value != "exists":
                continue
            rows.append({
                "entity": f"{n.type}: {n.label}",
                "source": c.source,
                "confidence": f"{c.confidence:.0%}",
                "quote": c.quote or "",
            })
    return rows


def _contradiction_rows(graph: KnowledgeGraph) -> list[dict]:
    return [{"entity": f"{node.type}: {node.label}", "attribute": attr,
             "values": values}
            for node, attr, values in graph.contradictions()]


def _mermaid_artifact(artifacts: dict[str, str]) -> str | None:
    for name, content in artifacts.items():
        if name.endswith(".mmd"):
            return content
    return None


def _markdown_artifacts(artifacts: dict[str, str]) -> dict[str, str]:
    return {name: content for name, content in artifacts.items()
            if not name.endswith(".mmd")}


def _nice(name: str) -> str:
    base = re.sub(r"\.(md|mmd|txt)$", "", name)
    return base.replace("-", " ").replace("_", " ").title()


def build_html_report(graph: KnowledgeGraph, artifacts: dict[str, str],
                      meta: ReportMeta) -> str:
    colors = _type_colors(graph)
    payload = {
        "vis": _vis_data(graph, colors),
        "mermaid": _mermaid_artifact(artifacts),
        "markdown": _markdown_artifacts(artifacts),
        "provenance": _provenance_rows(graph),
        "contradictions": _contradiction_rows(graph),
        "history": [{"q": q, "a": a} for q, a in meta.history],
        "meta": {
            "title": meta.module_title,
            "goal": meta.goal,
            "interviewee": meta.interviewee,
            "coverage": meta.coverage_trace,
            "coverage_pct": (round(meta.coverage_trace[-1] * 100)
                             if meta.coverage_trace else 0),
            "stop_reason": meta.stop_reason,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        },
        "legend": [{"type": t, "color": c} for t, c in colors.items()],
    }
    data_json = json.dumps(payload).replace("</", "<\\/")
    title = html.escape(meta.module_title)
    return _TEMPLATE.replace("__TITLE__", title).replace("__DATA__", data_json)


# --------------------------------------------------------------------------- #
# Single-file template. Data is injected as JSON; rendering is client-side.    #
# --------------------------------------------------------------------------- #
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<title>__TITLE__ · Discovery report</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vis-network@9/standalone/umd/vis-network.min.js"></script>
<style>
  :root { --bg:#0f1115; --card:#181b22; --line:#272b35; --ink:#e8eaed;
          --muted:#9aa3b2; --accent:#4c6ef5; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header { padding:18px 16px 12px; border-bottom:1px solid var(--line);
           position:sticky; top:0; background:var(--bg); z-index:5; }
  h1 { margin:0 0 4px; font-size:18px; }
  .goal { color:var(--muted); font-size:13px; }
  .stats { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
  .pill { background:var(--card); border:1px solid var(--line); border-radius:999px;
          padding:5px 11px; font-size:12px; color:var(--muted); }
  .pill b { color:var(--ink); }
  .cov { display:inline-block; min-width:42px; }
  .bar { height:6px; border-radius:6px; background:var(--line); overflow:hidden;
         margin-top:10px; }
  .bar > i { display:block; height:100%; background:linear-gradient(90deg,#4c6ef5,#12b886); }
  nav { display:flex; gap:4px; padding:8px 12px; overflow-x:auto;
        border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); }
  nav button { background:none; border:none; color:var(--muted); padding:8px 12px;
               font-size:13px; border-radius:8px; white-space:nowrap; cursor:pointer; }
  nav button.on { color:var(--ink); background:var(--card); }
  main { padding:14px 16px 60px; max-width:920px; margin:0 auto; }
  section { display:none; }
  section.on { display:block; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:14px 16px; margin-bottom:14px; }
  .card h2 { margin:0 0 10px; font-size:15px; }
  #graph { height:62vh; min-height:340px; border-radius:12px; background:#fff; }
  .mermaid { background:#fff; border-radius:12px; padding:12px; overflow:auto; }
  .legend { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
  .legend span { font-size:12px; color:var(--muted); display:flex; align-items:center; gap:6px; }
  .dot { width:11px; height:11px; border-radius:3px; display:inline-block; }
  .md :first-child { margin-top:0; }
  .md h1 { font-size:18px; } .md h2 { font-size:15px; margin-top:18px; }
  .md code { background:#0c0e12; padding:1px 5px; border-radius:5px; font-size:13px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { text-align:left; padding:7px 8px; border-bottom:1px solid var(--line);
           vertical-align:top; }
  th { color:var(--muted); font-weight:600; }
  .warn { border-color:#5c2b2b; }
  .warn h2 { color:#ffa8a8; }
  .empty { color:var(--muted); font-style:italic; }
  .qa { margin-bottom:12px; }
  .qa .q { color:var(--accent); } .qa .a { color:var(--ink); }
  footer { color:var(--muted); font-size:11px; text-align:center; padding:18px; }
</style>
</head>
<body>
<header>
  <h1 id="rtitle"></h1>
  <div class="goal" id="rgoal"></div>
  <div class="stats" id="rstats"></div>
  <div class="bar"><i id="rbar"></i></div>
</header>
<nav id="tabs"></nav>
<main>
  <section id="t-overview" class="on"></section>
  <section id="t-diagram"><div class="card"><h2>Process map</h2>
    <div id="mermaidHost"></div></div></section>
  <section id="t-graph"><div class="card"><h2>Knowledge graph</h2>
    <div id="graph"></div><div class="legend" id="glegend"></div></div></section>
  <section id="t-details"></section>
  <section id="t-evidence"></section>
</main>
<footer>Generated by Agentic Discovery — every fact traces to who said it.</footer>
<script>
const D = __DATA__;
const $ = (id) => document.getElementById(id);
const esc = (s) => (s==null?"":String(s).replace(/[&<>]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])));

// header
$("rtitle").textContent = D.meta.title;
$("rgoal").textContent = D.meta.goal || "";
$("rbar").style.width = D.meta.coverage_pct + "%";
$("rstats").innerHTML = [
  `<span class="pill">coverage <b class="cov">${D.meta.coverage_pct}%</b></span>`,
  `<span class="pill"><b>${D.meta.nodes}</b> entities</span>`,
  `<span class="pill"><b>${D.meta.edges}</b> relationships</span>`,
  D.contradictions.length ? `<span class="pill">⚠ <b>${D.contradictions.length}</b> contradiction(s)</span>` : "",
  D.meta.interviewee ? `<span class="pill">${esc(D.meta.interviewee)}</span>` : "",
].join("");

// tabs (only show those with content)
const tabs = [
  ["overview","Overview", true],
  ["diagram","Diagram", !!D.mermaid],
  ["graph","Graph", D.vis.nodes.length>0],
  ["details","Findings", Object.keys(D.markdown).length>0],
  ["evidence","Evidence", true],
];
const nav = $("tabs");
tabs.filter(t=>t[2]).forEach(([id,label],i)=>{
  const b=document.createElement("button");
  b.textContent=label; b.dataset.t=id; if(i===0)b.className="on";
  b.onclick=()=>{ document.querySelectorAll("nav button").forEach(x=>x.classList.remove("on"));
    document.querySelectorAll("section").forEach(x=>x.classList.remove("on"));
    b.classList.add("on"); $("t-"+id).classList.add("on");
    if(id==="graph") drawGraph(); if(id==="diagram") drawMermaid(); };
  nav.appendChild(b);
});

// overview
(function(){
  const cov = D.meta.coverage.map(c=>Math.round(c*100)+"%").join(" → ") || "—";
  let h = `<div class="card"><h2>Summary</h2>
    <table>
      <tr><th>Coverage progression</th><td>${cov}</td></tr>
      <tr><th>Stopped because</th><td>${esc(D.meta.stop_reason)}</td></tr>
      <tr><th>Entities captured</th><td>${D.meta.nodes}</td></tr>
      <tr><th>Relationships</th><td>${D.meta.edges}</td></tr>
    </table></div>`;
  if(D.legend.length){
    h += `<div class="card"><h2>What was discovered</h2><div class="legend">` +
      D.legend.map(l=>`<span><i class="dot" style="background:${l.color}"></i>${esc(l.type)}</span>`).join("") +
      `</div></div>`;
  }
  $("t-overview").innerHTML = h;
})();

// details (markdown artifacts)
(function(){
  const host=$("t-details"); let h="";
  for(const [name,content] of Object.entries(D.markdown)){
    h += `<div class="card md"><h2>${esc(niceName(name))}</h2>` +
         marked.parse(content) + `</div>`;
  }
  host.innerHTML = h || `<div class="card empty">No written findings yet.</div>`;
})();
function niceName(n){ return n.replace(/\.(md|mmd|txt)$/,"").replace(/[-_]/g," ")
  .replace(/\b\w/g, c=>c.toUpperCase()); }

// evidence: provenance + contradictions + transcript
(function(){
  let h="";
  if(D.contradictions.length){
    h += `<div class="card warn"><h2>⚠ Contradictions</h2>
      <table><tr><th>Entity</th><th>Attribute</th><th>Conflicting values</th></tr>` +
      D.contradictions.map(c=>`<tr><td>${esc(c.entity)}</td><td>${esc(c.attribute)}</td>
        <td>${c.values.map(esc).join(" vs ")}</td></tr>`).join("") + `</table></div>`;
  }
  h += `<div class="card"><h2>Provenance</h2>` +
    (D.provenance.length ? `<table><tr><th>Entity</th><th>Source</th><th>Conf.</th></tr>` +
      D.provenance.map(r=>`<tr><td>${esc(r.entity)}</td><td>${esc(r.source)}</td>
        <td>${esc(r.confidence)}</td></tr>`).join("") + `</table>`
      : `<span class="empty">No claims recorded.</span>`) + `</div>`;
  if(D.history.length){
    h += `<div class="card"><h2>Interview transcript</h2>` +
      D.history.map(x=>`<div class="qa"><div class="q">🧭 ${esc(x.q)}</div>
        <div class="a">${esc(x.a)}</div></div>`).join("") + `</div>`;
  }
  $("t-evidence").innerHTML = h;
})();

// diagram (lazy)
let mermaidDone=false;
function drawMermaid(){
  if(mermaidDone || !D.mermaid) return; mermaidDone=true;
  mermaid.initialize({startOnLoad:false, theme:"default", securityLevel:"loose"});
  const host=$("mermaidHost");
  const div=document.createElement("div"); div.className="mermaid";
  div.textContent=D.mermaid; host.appendChild(div);
  mermaid.run({nodes:[div]}).catch(e=>{host.innerHTML=
    `<pre class="empty">Diagram failed to render: ${esc(e.message)}</pre>`;});
}

// interactive knowledge graph (lazy)
let graphDone=false;
function drawGraph(){
  if(graphDone || !D.vis.nodes.length) return; graphDone=true;
  const data={nodes:new vis.DataSet(D.vis.nodes), edges:new vis.DataSet(
    D.vis.edges.map(e=>({...e, arrows:"to", font:{size:10,color:"#666"}})))};
  new vis.Network($("graph"), data, {
    nodes:{shape:"dot", scaling:{min:8,max:26}, font:{size:13}},
    edges:{color:{color:"#adb5bd"}, smooth:{type:"dynamic"}},
    physics:{stabilization:true, barnesHut:{springLength:130}},
    interaction:{hover:true, tooltipDelay:120},
  });
  $("glegend").innerHTML = D.legend.map(l=>
    `<span><i class="dot" style="background:${l.color}"></i>${esc(l.type)}</span>`).join("");
}
</script>
</body>
</html>
"""
