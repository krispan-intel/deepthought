"""
scripts/generate_run_report.py

Generate a self-contained HTML dashboard summarising every pipeline run.

Usage:
    python scripts/generate_run_report.py
    python scripts/generate_run_report.py --output output/generated/run_report.html
    python scripts/generate_run_report.py --limit 200   # last N runs only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUNS_FILE  = PROJECT_ROOT / "data/processed/pipeline_runs.jsonl"
AUDIT_FILE = PROJECT_ROOT / "logs/audit/pipeline_audit.jsonl"
DEFAULT_OUT = PROJECT_ROOT / "output/generated/run_report.html"


# ── Data Loading ──────────────────────────────────────────────────

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_data(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Merge pipeline_runs with audit log, newest-first."""
    runs   = _load_jsonl(RUNS_FILE)
    audits = {r["run_id"]: r for r in _load_jsonl(AUDIT_FILE) if "run_id" in r}

    # Newest-first
    runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    if limit:
        runs = runs[:limit]

    merged = []
    for run in runs:
        audit = audits.get(run["run_id"], {})
        meta  = audit.get("metadata", {})
        merged.append({
            "run_id":        run.get("run_id", ""),
            "timestamp":     run.get("timestamp", ""),
            "run_status":    run.get("run_status", "UNKNOWN"),
            "failed_stages": run.get("failed_stages", []),
            "last_error":    run.get("last_error", ""),
            "target":        run.get("input", {}).get("target", ""),
            "domain":        run.get("input", {}).get("domain", ""),
            "n_drafts":      run.get("input", {}).get("n_drafts", 0),
            "void_count":    len(run.get("void_statuses", [])),
            "tid_statuses":  run.get("tid_statuses", []),
            "debate_result": run.get("debate_result") or audit.get("debate_result"),
            "output_paths":  run.get("output_paths", {}),
            # From audit log
            "stage_status":           meta.get("stage_status", {}),
            "rc_reports":             meta.get("reality_checker_reports", []),
            "conference_trace":       meta.get("conference_review_trace", []),
            "committee_reports":      meta.get("committee_reports", {}),
            "committee_review_log":   meta.get("committee_review_log", []),
            "judge_trace":            meta.get("judge_trace", {}),
            "forager_obs":            meta.get("forager_observations", {}),
            "rejected_reason":        meta.get("rejected_reason", ""),
            "maverick_gen":           meta.get("maverick_generation", {}),
        })
    return merged


# ── Summary Stats ─────────────────────────────────────────────────

def compute_stats(runs: List[Dict]) -> Dict[str, Any]:
    total = len(runs)
    by_status: Dict[str, int] = {}
    for r in runs:
        s = r["run_status"]
        by_status[s] = by_status.get(s, 0) + 1

    stage_fails: Dict[str, int] = {}
    for r in runs:
        for s in r["failed_stages"]:
            stage_fails[s] = stage_fails.get(s, 0) + 1

    # Rejection reasons bucketed
    error_buckets: Dict[str, int] = {}
    for r in runs:
        if r["run_status"] in ("REJECTED", "RETRY_PENDING"):
            err = r["last_error"] or r["rejected_reason"] or "unknown"
            if "no topological voids" in err.lower():
                key = "No voids found"
            elif "maverick" in " ".join(r["failed_stages"]).lower() or "json" in err.lower():
                key = "Maverick parse error"
            elif "three-strikes" in err.lower() or "maximum revision" in err.lower():
                key = "Exceeded max revisions"
            elif "committee" in err.lower() or "debate" in err.lower() or "fatal" in err.lower():
                key = "Committee rejection"
            elif "patent shield" in err.lower():
                key = "Patent Shield blocked"
            elif r["failed_stages"]:
                key = f"Stage failure: {r['failed_stages'][0]}"
            else:
                key = "Debate panel REJECT"
            error_buckets[key] = error_buckets.get(key, 0) + 1

    return {
        "total": total,
        "by_status": by_status,
        "stage_fails": stage_fails,
        "error_buckets": error_buckets,
    }


# ── Stats HTML (Python-rendered, small & static) ─────────────────

def _esc(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _short(s: str, n: int = 120) -> str:
    s = str(s).strip()
    return s if len(s) <= n else s[:n] + "…"


# ── Stats Bar ─────────────────────────────────────────────────────

def render_stats(stats: Dict, runs: List[Dict]) -> str:
    total   = stats["total"]
    by_st   = stats["by_status"]
    buckets = stats["error_buckets"]

    approved  = by_st.get("APPROVED", 0)
    rejected  = by_st.get("REJECTED", 0)
    retry     = by_st.get("RETRY_PENDING", 0)
    rate      = f"{approved/total*100:.1f}%" if total else "0%"

    bucket_rows = "".join(
        f'<tr><td>{_esc(k)}</td><td>{v}</td><td>{v/total*100:.1f}%</td></tr>'
        for k, v in sorted(buckets.items(), key=lambda x: -x[1])
    )

    return f"""
<div class="stats-bar">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Total Runs</div></div>
  <div class="stat" style="--c:#22c55e"><div class="stat-num" style="color:#22c55e">{approved}</div><div class="stat-label">Approved</div></div>
  <div class="stat" style="--c:#ef4444"><div class="stat-num" style="color:#ef4444">{rejected}</div><div class="stat-label">Rejected</div></div>
  <div class="stat" style="--c:#f59e0b"><div class="stat-num" style="color:#f59e0b">{retry}</div><div class="stat-label">Retry Pending</div></div>
  <div class="stat"><div class="stat-num">{rate}</div><div class="stat-label">Approval Rate</div></div>
</div>
<details class="bucket-details">
  <summary>Rejection breakdown</summary>
  <table><thead><tr><th>Reason</th><th>Count</th><th>%</th></tr></thead>
  <tbody>{bucket_rows}</tbody></table>
</details>"""


# ── Full HTML (data embedded as JSON; cards rendered by JS) ──────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0f172a; color: #e2e8f0; font-size: 14px; }
a { color: #7dd3fc; }
h1 { font-size: 1.5rem; font-weight: 700; }

.top-bar { background: #1e293b; padding: 1rem 1.5rem;
           border-bottom: 1px solid #334155; display: flex;
           align-items: center; gap: 1rem; }
.gen-ts { font-size: 0.8rem; color: #64748b; margin-left: auto; }

.stats-bar { display: flex; gap: 1.5rem; padding: 1rem 1.5rem;
             background: #1e293b; border-bottom: 1px solid #334155; flex-wrap: wrap; }
.stat { text-align: center; min-width: 80px; }
.stat-num   { font-size: 1.6rem; font-weight: 700; }
.stat-label { font-size: 0.75rem; color: #94a3b8; }

.bucket-details { padding: 0.5rem 1.5rem 1rem; background: #1e293b;
                  border-bottom: 1px solid #334155; }
.bucket-details summary { cursor: pointer; color: #94a3b8; font-size: 0.85rem; padding: 0.25rem 0; }
table { border-collapse: collapse; width: 100%; max-width: 640px; margin-top: 0.5rem; }
th, td { text-align: left; padding: 0.3rem 0.75rem; font-size: 0.82rem; }
th { color: #94a3b8; border-bottom: 1px solid #334155; }
td { border-bottom: 1px solid #1e293b; }

.controls { display: flex; gap: 0.75rem; padding: 0.75rem 1.5rem;
            background: #0f172a; border-bottom: 1px solid #1e293b;
            flex-wrap: wrap; align-items: center; }
.controls input  { background: #1e293b; border: 1px solid #334155; border-radius: 6px;
                   color: #e2e8f0; padding: 0.4rem 0.75rem; width: 300px; }
.controls select { background: #1e293b; border: 1px solid #334155; border-radius: 6px;
                   color: #e2e8f0; padding: 0.4rem 0.5rem; }
.controls button { background: #334155; border: none; border-radius: 6px; color: #e2e8f0;
                   padding: 0.4rem 0.9rem; cursor: pointer; }
.controls button:hover { background: #475569; }
.count-label { color: #64748b; font-size: 0.82rem; }

.pagination { display: flex; align-items: center; gap: 0.4rem; margin-left: auto; flex-wrap: wrap; }
.pagination button { background: #1e293b; border: 1px solid #334155; border-radius: 5px;
                     color: #e2e8f0; padding: 0.3rem 0.65rem; cursor: pointer; font-size: 0.82rem; }
.pagination button:hover { background: #334155; }
.pagination button.active { background: #3b82f6; border-color: #3b82f6; font-weight: 700; }
.pagination button:disabled { opacity: 0.35; cursor: default; }
.pagination .pg-info { color: #64748b; font-size: 0.8rem; padding: 0 0.25rem; }

.runs { padding: 0.75rem 1.5rem; display: flex; flex-direction: column; gap: 0.5rem;
        min-height: 120px; }

.run-card { border-radius: 8px; border: 1px solid #334155;
            background: #1e293b; overflow: hidden; }
.card-approved { border-left: 3px solid #22c55e; }
.card-rejected { border-left: 3px solid #ef4444; }
.card-other    { border-left: 3px solid #f59e0b; }

.card-header { padding: 0.65rem 1rem; cursor: pointer; user-select: none; }
.card-header:hover { background: #263347; }
.card-title  { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.target-text { font-weight: 500; font-size: 0.88rem; }
.card-meta   { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.3rem; flex-wrap: wrap; }
.stage-pills { margin-top: 0.25rem; display: flex; gap: 0.25rem; flex-wrap: wrap; }
.run-id      { font-size: 0.72rem; margin-top: 0.2rem; }
.expand-icon { margin-left: auto; color: #64748b; font-size: 0.75rem; }

.card-body { padding: 0.75rem 1rem; border-top: 1px solid #334155;
             display: flex; flex-direction: column; gap: 0.75rem; }

.badge { border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.78rem;
         font-weight: 600; color: #fff; display: inline-block; }
.tag   { background: #1e293b; border: 1px solid #334155; border-radius: 4px;
         padding: 0.1rem 0.4rem; font-size: 0.75rem; }
.dim   { color: #64748b; }
.small { font-size: 0.8rem; }

.section-label { font-size: 0.75rem; font-weight: 700; color: #7dd3fc;
                 text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
.draft-card { background: #0f172a; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.3rem; }
.critique   { font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem; }
.error-box  { background: #1a0a0a; border: 1px solid #7f1d1d; border-radius: 6px;
              padding: 0.5rem 0.75rem; font-size: 0.8rem; color: #fca5a5;
              white-space: pre-wrap; word-break: break-word; }
.round-header { font-size: 0.8rem; font-weight: 600; color: #cbd5e1;
                padding: 0.25rem 0; border-bottom: 1px solid #1e293b; margin-top: 0.3rem; }
.round-item   { font-size: 0.8rem; padding: 0.2rem 0 0.2rem 0.5rem;
                border-bottom: 1px dashed #1e293b; color: #94a3b8; }
.round-item strong { color: #cbd5e1; }
.judge-result { border: 1px solid; border-radius: 6px; padding: 0.5rem 0.75rem;
                margin-top: 0.5rem; font-size: 0.85rem; }
.empty-msg { color: #475569; text-align: center; padding: 2rem; }
"""

# JavaScript: all card rendering + pagination lives here.
# ALL_RUNS is injected as a JSON literal by render_html().
JS = r"""
const PAGE_SIZE = 50;
let filtered = ALL_RUNS;
let currentPage = 0;

// ── Utilities ───────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function short(s, n) {
  s = String(s ?? '').trim();
  return s.length <= n ? s : s.slice(0, n) + '…';
}
function fmtTs(ts) {
  try { return new Date(ts).toISOString().slice(0,16).replace('T',' '); }
  catch { return String(ts).slice(0,16); }
}
const STATUS_COLOR = {
  APPROVED:'#22c55e', APPROVED_AND_EXPORTED:'#22c55e',
  REJECTED:'#ef4444', RETRY_PENDING:'#f59e0b',
  RUNNING:'#3b82f6'
};
function statusColor(s){ return STATUS_COLOR[s] || '#6b7280'; }
function badge(s, small) {
  const sz = small ? 'font-size:0.7rem;' : '';
  return `<span class="badge" style="background:${statusColor(s)};${sz}">${esc(s)}</span>`;
}

// ── Card section renderers ───────────────────────────────────────
function renderVoidSection(run) {
  const obs = run.forager_obs || {};
  const cnt = obs.void_count ?? run.void_count ?? 0;
  if (!cnt) return '<p class="dim">No voids retrieved.</p>';
  const mode = esc(obs.search_mode || '');
  const top  = (obs.top_voids || []).slice(0,3);
  const rows = top.map(v => `<tr>
    <td>${esc(short(v.label||'',50))}</td>
    <td>${esc(short(v.anchor_a||v.anchor_c||'',40))}</td>
    <td>${esc(short(v.anchor_b||'',40))}</td>
    <td>${(v.mmr_score||0).toFixed(4)}</td></tr>`).join('');
  return `<div class="section-label">Forager (${mode}, ${cnt} voids)</div>
<table><thead><tr><th>Label</th><th>Anchor A</th><th>Anchor B</th><th>MMR</th></tr></thead>
<tbody>${rows}</tbody></table>`;
}

function renderDraftSection(run) {
  const tids = run.tid_statuses || [];
  const rcMap = {};
  (run.rc_reports || []).forEach(r => { rcMap[r.title] = r; });
  if (!tids.length) {
    const mg = run.maverick_gen || {};
    return `<p class="dim">No drafts. ${esc(mg.reason || mg.status || '')}</p>`;
  }
  let html = '<div class="section-label">Drafts</div>';
  tids.forEach(t => {
    const st  = t.status || '';
    const col = st.includes('APPROVED') ? '#22c55e' : st === 'REJECTED' ? '#ef4444' : '#6b7280';
    const err = esc(short(t.last_error||'', 120));
    let links = '';
    if (t.output_html)     links += ` <a href="../${esc(t.output_html)}" target="_blank">HTML</a>`;
    if (t.output_markdown) links += ` <a href="../${esc(t.output_markdown)}" target="_blank">MD</a>`;
    const rc = rcMap[t.title] || {};
    const critique = rc.verdict
      ? `<div class="critique"><b>RC:</b> ${esc(rc.verdict)} — ${esc(short(rc.reason||'',200))}</div>`
      : '';
    html += `<div class="draft-card" style="border-left:3px solid ${col}">
  <div>${badge(st,true)} <strong>${esc(short(t.title||'Untitled',80))}</strong>${links}</div>
  ${err ? `<div class="dim small">${err}</div>` : ''}
  ${critique}
</div>`;
  });
  return html;
}

function renderRevisionSection(run) {
  const trace = run.conference_trace || [];
  const reviews = trace.filter(e => e.event === 'review_round');
  const revises = trace.filter(e => e.event === 'maverick_revision');
  if (!reviews.length && !revises.length) return '';
  const ICON = {APPROVE:'✅', REVISE:'🔄', REJECT:'❌'};
  let html = `<div class="section-label">Conference Review (${reviews.length} rounds)</div>`;
  reviews.forEach(rr => {
    const items = rr.items || [];
    const ap = items.filter(i=>i.verdict==='APPROVE').length;
    const rv = items.filter(i=>i.verdict==='REVISE').length;
    const rj = items.filter(i=>i.verdict==='REJECT').length;
    html += `<div class="round-header">Round ${rr.round||'?'} — ✅${ap} 🔄${rv} ❌${rj}</div>`;
    items.forEach(item => {
      const icon = ICON[item.verdict] || '?';
      const ff = item.fatal_flaw ? ` <span style="color:#ef4444">⛔ ${esc(short(item.fatal_flaw,100))}</span>` : '';
      html += `<div class="round-item">${icon} <em>${esc(short(item.title||'',60))}</em> — ${esc(short(item.reason||'',180))}${ff}</div>`;
    });
  });
  revises.forEach(rv => {
    const items = rv.items || [];
    html += `<div class="round-header">Revision ${rv.round||'?'}</div>`;
    items.forEach(item => {
      const icon = item.status==='REVISED' ? '✏️' : item.status?.includes('FALLBACK') ? '⚠️' : '⏭️';
      html += `<div class="round-item">${icon} ${esc(short(item.before_title||'',50))} → ${esc(short(item.after_title||'',50))} <span class="dim">[${esc(item.status||'')}]</span></div>`;
    });
  });
  return html;
}

function renderCommitteeSection(run) {
  const log   = run.committee_review_log || [];
  const debate = run.debate_result;
  if (!log.length && !debate) return '';
  let html = '<div class="section-label">Debate Panel</div>';
  log.forEach(rev => {
    const st  = rev.status || '';
    const col = st==='APPROVE' ? '#22c55e' : st==='REJECT' ? '#ef4444' : '#f59e0b';
    const ff  = rev.fatal_flaw ? ` <span style="color:#ef4444">⛔ ${esc(short(rev.fatal_flaw,100))}</span>` : '';
    html += `<div class="round-item">
  <span class="badge" style="background:${col};font-size:0.7rem">${esc(st)}</span>
  <strong>${esc(rev.reviewer||'')}</strong> score=${rev.score??'?'} — ${esc(short(rev.top_issue||'',160))}${ff}
</div>`;
  });
  if (debate) {
    const v   = debate.final_verdict || '';
    const col = v==='APPROVE' ? '#22c55e' : '#ef4444';
    html += `<div class="judge-result" style="border-color:${col}">
  <b>Chairman:</b> ${badge(v)} ${debate.winning_title ? `<em>${esc(short(debate.winning_title,60))}</em>` : ''}
  confidence=${(debate.confidence||0).toFixed(2)}<br>
  <span class="dim">${esc(short(debate.synthesis||'',300))}</span>
</div>`;
  }
  return html;
}

function renderErrorSection(run) {
  const err    = run.last_error || run.rejected_reason || '';
  const stages = run.failed_stages || [];
  if (!err && !stages.length) return '';
  let html = '<div class="section-label">Rejection reason</div>';
  if (stages.length) html += `<div class="dim small">Failed stages: ${stages.map(esc).join(', ')}</div>`;
  if (err) html += `<div class="error-box">${esc(err.slice(0,600))}</div>`;
  return html;
}

function renderCard(run) {
  const st  = run.run_status || 'UNKNOWN';
  const cls = st==='APPROVED' ? 'card-approved' : st==='REJECTED' ? 'card-rejected' : 'card-other';
  const pills = Object.entries(run.stage_status||{}).map(([s,v]) =>
    `<span class="badge" style="background:${v==='OK'?'#22c55e':'#ef4444'};font-size:0.72rem">${esc(s)}</span>`
  ).join(' ');
  const body = [
    renderVoidSection(run), renderDraftSection(run),
    renderRevisionSection(run), renderCommitteeSection(run), renderErrorSection(run)
  ].join('');
  return `<div class="run-card ${cls}">
  <div class="card-header" onclick="toggleCard(this)">
    <div class="card-title">${badge(st)} <span class="target-text">${esc(short(run.target||'',140))}</span></div>
    <div class="card-meta">
      <span class="dim">${esc(fmtTs(run.timestamp))}</span>
      <span class="dim tag">${esc(run.domain||'')}</span>
      <span class="dim tag">voids:${run.void_count||0}</span>
      <span class="dim tag">drafts:${run.n_drafts||0}</span>
      <span class="expand-icon">▼</span>
    </div>
    <div class="stage-pills">${pills}</div>
    <div class="run-id dim">${esc(run.run_id||'')}</div>
  </div>
  <div class="card-body" style="display:none">${body}</div>
</div>`;
}

// ── Pagination ──────────────────────────────────────────────────
function totalPages() { return Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)); }

function renderPage(page) {
  currentPage = Math.max(0, Math.min(page, totalPages()-1));
  const start = currentPage * PAGE_SIZE;
  const slice = filtered.slice(start, start + PAGE_SIZE);
  const container = document.getElementById('runs-container');
  container.innerHTML = slice.length
    ? slice.map(renderCard).join('')
    : '<div class="empty-msg">No runs match the current filter.</div>';
  renderPagination();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

function renderPagination() {
  const total = totalPages();
  const pg    = currentPage;
  let btns = '';

  // Always show first, last, and a window around current
  const show = new Set([0, total-1]);
  for (let i = Math.max(0,pg-2); i <= Math.min(total-1,pg+2); i++) show.add(i);
  let prev = -1;
  [...show].sort((a,b)=>a-b).forEach(i => {
    if (prev !== -1 && i - prev > 1) btns += '<span class="pg-info">…</span>';
    btns += `<button onclick="renderPage(${i})" ${i===pg?'class="active"':''}>${i+1}</button>`;
    prev = i;
  });

  const info = `${filtered.length} runs · page ${pg+1}/${total}`;
  document.getElementById('pg-top').innerHTML =
  document.getElementById('pg-bottom').innerHTML =
    `<button onclick="renderPage(currentPage-1)" ${pg===0?'disabled':''}>‹</button>
     ${btns}
     <button onclick="renderPage(currentPage+1)" ${pg===total-1?'disabled':''}>›</button>
     <span class="pg-info">${info}</span>`;
  document.getElementById('countLabel').textContent = info;
}

// ── Filters ─────────────────────────────────────────────────────
let searchTimer = null;
function applyFilters() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    const q  = document.getElementById('search').value.toLowerCase();
    const st = document.getElementById('statusFilter').value;
    filtered = ALL_RUNS.filter(r => {
      const matchQ  = !q || (r.target||'').toLowerCase().includes(q) || (r.run_id||'').includes(q);
      const matchSt = !st || r.run_status === st;
      return matchQ && matchSt;
    });
    renderPage(0);
  }, 200);
}

function toggleCard(header) {
  const body = header.nextElementSibling;
  const icon = header.querySelector('.expand-icon');
  const open = body.style.display === 'none';
  body.style.display = open ? 'flex' : 'none';
  icon.textContent   = open ? '▲' : '▼';
}
function expandAll()  { document.querySelectorAll('.card-body').forEach(b => { b.style.display='flex'; b.previousElementSibling.querySelector('.expand-icon').textContent='▲'; }); }
function collapseAll(){ document.querySelectorAll('.card-body').forEach(b => { b.style.display='none'; b.previousElementSibling.querySelector('.expand-icon').textContent='▼'; }); }

// ── Boot ────────────────────────────────────────────────────────
renderPage(0);
"""


def render_html(stats: Dict, runs: List[Dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stats_html = render_stats(stats, runs)

    statuses = sorted({r["run_status"] for r in runs})
    status_options = '<option value="">All statuses</option>' + "".join(
        f'<option value="{s}">{s}</option>' for s in statuses
    )

    # Serialize only the fields the JS renderer needs (keeps JSON compact)
    def _slim(r: Dict) -> Dict:
        return {
            "run_id":               r["run_id"],
            "timestamp":            r["timestamp"],
            "run_status":           r["run_status"],
            "failed_stages":        r["failed_stages"],
            "last_error":           r["last_error"][:600] if r["last_error"] else "",
            "target":               r["target"],
            "domain":               r["domain"],
            "n_drafts":             r["n_drafts"],
            "void_count":           r["void_count"],
            "tid_statuses":         r["tid_statuses"],
            "debate_result":        r["debate_result"],
            "stage_status":         r["stage_status"],
            "rc_reports":           r["rc_reports"],
            "conference_trace":     r["conference_trace"],
            "committee_review_log": r["committee_review_log"],
            "judge_trace":          r["judge_trace"],
            "forager_obs":          r["forager_obs"],
            "rejected_reason":      r["rejected_reason"][:400] if r["rejected_reason"] else "",
            "maverick_gen":         r["maverick_gen"],
        }

    runs_json = json.dumps([_slim(r) for r in runs], ensure_ascii=False, separators=(",", ":"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DeepThought Run Report</title>
<style>{CSS}</style>
</head>
<body>

<div class="top-bar">
  <h1>🧠 DeepThought Run Report</h1>
  <span class="gen-ts">Generated {now}</span>
</div>

{stats_html}

<div class="controls">
  <input id="search" type="text" placeholder="Search target / run-id…" oninput="applyFilters()">
  <select id="statusFilter" onchange="applyFilters()">{status_options}</select>
  <button onclick="expandAll()">Expand all</button>
  <button onclick="collapseAll()">Collapse all</button>
  <span id="countLabel" class="count-label"></span>
  <div id="pg-top" class="pagination"></div>
</div>

<div id="runs-container" class="runs"></div>

<div class="controls" style="border-top:1px solid #1e293b; border-bottom:none; justify-content:flex-end;">
  <div id="pg-bottom" class="pagination"></div>
</div>

<script>
const ALL_RUNS = {runs_json};
{JS}
</script>
</body>
</html>"""


# ── Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate DeepThought run report HTML")
    parser.add_argument("--output", default=str(DEFAULT_OUT),
                        help="Output HTML path (default: output/generated/run_report.html)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only include the last N runs (default: all)")
    args = parser.parse_args()

    print(f"Loading runs from {RUNS_FILE} …")
    runs = load_data(limit=args.limit)
    print(f"  {len(runs)} runs loaded")

    stats = compute_stats(runs)
    print(f"  APPROVED={stats['by_status'].get('APPROVED', 0)} "
          f"REJECTED={stats['by_status'].get('REJECTED', 0)} "
          f"RETRY={stats['by_status'].get('RETRY_PENDING', 0)}")

    html = render_html(stats, runs)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Report written → {out}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
