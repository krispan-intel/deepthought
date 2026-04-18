#!/usr/bin/env python3
"""
Generate TID HTML from completed_reviews + completed_maverick data.
Used both for batch generation and auto-integration in Auto Worker.
"""
import json, glob, os
from html import escape
from datetime import datetime
from pathlib import Path


def generate_tid_html(run_id: str, review_data: dict, mav_data: dict) -> str:
    reviews = review_data.get("reviews", {})
    chairman = review_data.get("chairman_result", {})
    revision_trace = review_data.get("revision_trace", [])
    final_drafts = review_data.get("final_drafts", [])
    target = mav_data.get("target", "")
    void_context = mav_data.get("void_context", "")[:500]

    draft = final_drafts[0] if final_drafts else (mav_data.get("drafts") or [{}])[0]
    td = draft.get("tid_detail", {})
    scores = draft.get("scores", {})

    verdict = chairman.get("final_verdict", "REVISE")
    rule = chairman.get("rule_trigger", "")
    rounds = review_data.get("debate_rounds", 1)
    approves = sum(1 for r in reviews.values() if r.get("status") == "APPROVE")
    all_scores = [float(r.get("score", 0)) for r in reviews.values()]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0
    verdict_color = {"APPROVE": "#22c55e", "REVISE": "#f59e0b", "REJECT": "#ef4444"}.get(verdict, "#64748b")

    def stars(n):
        n = min(5, max(1, int(n or 1)))
        return "★" * n + "☆" * (5 - n)

    def p(text):
        return f"<div style='white-space:pre-wrap;line-height:1.7;'>{escape(str(text or 'N/A')).replace(chr(92)+'n', chr(10))}</div>"

    def code_block(text):
        return f"<pre class='arch-pre'>{escape(str(text or 'N/A')).replace(chr(92)+'n', chr(10))}</pre>"

    claims = td.get("draft_claims", [])
    claims_html = "".join(f"<li style='margin-bottom:8px;'>{escape(str(c))}</li>" for c in claims)
    risks_html = "".join(f"<li style='margin-bottom:6px;'>{escape(str(r))}</li>" for r in td.get("risks_and_mitigations", []))
    refs_html = "".join(f"<li>{escape(str(r))}</li>" for r in td.get("references", []))
    conf_html = "".join(f"<li style='margin-bottom:6px;'>{escape(str(c))}</li>" for c in td.get("claim_confidence", []))

    review_cards = ""
    for name, r in reviews.items():
        status = r.get("status", "?")
        score = r.get("score", 0)
        flaw = r.get("fatal_flaw", "").strip()
        yc = r.get("yellow_cards", 0)
        issues = r.get("issues", [])
        sc = {"APPROVE": "#22c55e", "REVISE": "#f59e0b", "REJECT": "#ef4444"}.get(status, "#64748b")
        issues_html = "".join(f"<li style='font-size:13px;margin-bottom:4px;'>{escape(str(i))}</li>" for i in issues[:5])
        flaw_html = f'<p style="color:#ef4444;font-weight:600;font-size:13px;">⚠ Fatal Flaw: {escape(flaw)}</p>' if flaw else ""
        review_cards += f"""
<div style="border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:10px;border-left:4px solid {sc};">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
    <strong>{escape(name.replace('_',' ').title())}</strong>
    <span style="display:flex;gap:10px;align-items:center;">
      <span style="background:{sc};color:#fff;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:700;">{status}</span>
      <span style="color:#d99a00;">{stars(score)}</span>
      <span style="color:#64748b;font-size:12px;">YC:{yc}</span>
    </span>
  </div>
  {flaw_html}<ul style="margin-top:8px;">{issues_html}</ul>
</div>"""

    trace_html = ""
    for t in revision_trace:
        rnd = t.get("round", "?")
        v = t.get("verdict", "?")
        vc = {"APPROVE": "#22c55e", "REVISE": "#f59e0b", "REJECT": "#ef4444"}.get(v, "#64748b")
        fb = t.get("specialist_feedback", [])[:5]
        fb_html = "".join(f"<li style='font-size:12px;margin-bottom:3px;'>{escape(str(fi)[:200])}</li>" for fi in fb)
        trace_html += f"""
<div style="border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:8px;background:#f8f9fa;">
  <div style="display:flex;gap:10px;align-items:center;">
    <strong>Round {rnd}</strong>
    <span style="background:{vc};color:#fff;border-radius:4px;padding:2px 8px;font-size:12px;">{v}</span>
    <span style="color:#64748b;font-size:12px;">{escape(t.get('rule_trigger',''))}</span>
  </div>
  <details style="margin-top:8px;"><summary style="cursor:pointer;color:#64748b;font-size:13px;">Feedback ({len(fb)} items)</summary>
    <ul style="margin-top:4px;">{fb_html}</ul></details>
</div>"""

    orig_titles = [d.get("title","") for d in mav_data.get("drafts", [])]
    orig_html = "".join(f"<li style='font-size:13px;'>{escape(t)}</li>" for t in orig_titles)

    void_lines = [l for l in void_context.split('\n') if l.strip() and ('Void' in l or 'Sparse anchors' in l or 'MMR Score' in l)][:6]
    void_brief = '\n'.join(void_lines)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>[{approves}/4 ★ {avg:.1f}] {escape(draft.get('title','')[:60])}</title>
  <style>
    :root{{--bg:#f7f7f4;--card:#fff;--ink:#1f2328;--muted:#59636e;--line:#dde2e7;--star:#d99a00;}}
    body{{margin:0;background:radial-gradient(circle at 20% 0%,#eef3ff,var(--bg) 42%);color:var(--ink);font:15px/1.6 "Segoe UI",sans-serif;}}
    .wrap{{max-width:1080px;margin:0 auto;padding:28px 16px 72px;}}
    .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:14px;}}
    h1{{font-size:20px;margin:0 0 10px;}} h2{{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:6px;margin:0 0 10px;}}
    h3{{font-size:14px;color:var(--muted);margin:14px 0 6px;}}
    .pill{{background:#f2f5f8;border:1px solid var(--line);border-radius:999px;padding:3px 9px;display:inline-block;margin:2px 4px 0 0;font-size:12px;}}
    .muted{{color:var(--muted);}} .stars{{color:var(--star);}}
    ul,ol{{margin:6px 0 0 18px;}} li{{margin-bottom:3px;}}
    .arch-pre{{background:#f0f2f5;border:1px solid var(--line);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;white-space:pre-wrap;line-height:1.5;overflow-x:auto;}}
    table{{width:100%;border-collapse:collapse;}} th,td{{border-bottom:1px solid var(--line);text-align:left;padding:7px 5px;font-size:13px;}}
  </style>
</head>
<body><div class="wrap">

<div style="background:{verdict_color};color:#fff;border-radius:14px;padding:16px;margin-bottom:14px;text-align:center;">
  <div style="font-size:12px;opacity:.85;">{escape(run_id)} &nbsp;|&nbsp; {rounds} DP rounds &nbsp;|&nbsp; {approves}/4 APPROVE &nbsp;|&nbsp; Avg {avg:.1f}/5</div>
  <div style="font-size:18px;font-weight:700;margin-top:4px;">{verdict} — {escape(rule)}</div>
</div>

<section class="card">
  <h1>{escape(draft.get('title',''))}</h1>
  <div class="muted" style="font-size:12px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:4px;margin-top:6px;">
    <div><strong>Target:</strong> {escape(target)}</div>
    <div><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d')}</div>
    <div><strong>System:</strong> DeepThought TVA</div>
  </div>
  <h3>Original Maverick Drafts</h3><ul>{orig_html}</ul>
  {'<h3>Void Signal</h3><pre style="font-size:11px;background:#f8f9fa;padding:8px;border-radius:6px;white-space:pre-wrap;">' + escape(void_brief) + '</pre>' if void_brief else ''}
</section>

<section class="card">
  <h2>1. Executive Summary</h2>
  <h3>One-Liner</h3>{p(draft.get('one_liner',''))}
  <div style="margin-top:8px;">
    <div class="pill"><strong>Novelty:</strong> {escape(str(draft.get('novelty_thesis',''))[:220])}</div>
    <div class="pill"><strong>Feasibility:</strong> {escape(str(draft.get('feasibility_thesis',''))[:180])}</div>
  </div>
</section>

<section class="card">
  <h2>2. Technical Invention Disclosure</h2>
  <h3>2.1 Problem Statement</h3>{p(td.get('problem_statement',''))}
  <h3>2.2 Prior-Art Gap</h3>{p(td.get('prior_art_gap',''))}
  <h3>2.3 Proposed Invention</h3>{p(td.get('proposed_invention',''))}
  <h3>2.4 Architecture</h3>{code_block(td.get('architecture_overview',''))}
  <h3>2.5 Implementation Plan</h3>{p(td.get('implementation_plan',''))}
  <h3>2.6 Validation Plan</h3>{p(td.get('validation_plan',''))}
</section>

<section class="card">
  <h2>3. Patent Claims</h2>
  <ol>{claims_html}</ol>
  {'<h3>Claim Confidence</h3><ul>' + conf_html + '</ul>' if conf_html else ''}
</section>

{'<section class="card"><h2>4. Risks &amp; Mitigations</h2><ul>' + risks_html + '</ul></section>' if risks_html else ''}
{'<section class="card"><h2>5. References</h2><ul>' + refs_html + '</ul></section>' if refs_html else ''}

<section class="card">
  <h2>6. Debate Panel Review</h2>
  <p class="muted" style="font-size:12px;">{approves}/4 APPROVE · Avg {avg:.1f}/5 · {rounds} rounds · Verdict: <strong style="color:{verdict_color};">{verdict}</strong></p>
  {review_cards}
</section>

{'<section class="card"><h2>7. Revision Trace</h2>' + trace_html + '</section>' if trace_html else ''}

<footer class="card muted" style="text-align:center;font-size:11px;">
  DeepThought TVA · Human Review Queue · {escape(target)}
</footer>
</div></body></html>"""


def generate_all_human_review(output_dir: str = "output/generated/human_review"):
    """Batch generate HTML for all new-format REVISE TIDs."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build run_id → maverick data map (new format only)
    mav_map = {}
    for f in glob.glob('data/completed_maverick/*.json'):
        data = json.load(open(f))
        if data.get('void_context'):
            mav_map[data.get('run_id', '')] = data

    count = 0
    for f in glob.glob('data/completed_reviews/*.json'):
        data = json.load(open(f))
        rid = data.get('run_id', '')
        if rid not in mav_map:
            continue
        cr = data.get('chairman_result', {})
        if cr.get('final_verdict') != 'REVISE':
            continue

        reviews = data.get('reviews', {})
        all_scores = [float(r.get('score', 0)) for r in reviews.values()]
        avg = sum(all_scores) / len(all_scores) if all_scores else 0
        approves = sum(1 for r in reviews.values() if r.get('status') == 'APPROVE')

        fname = f"tid_{avg:.1f}avg_{approves}approve_{rid[:12]}.html"
        out_path = out_dir / fname

        if out_path.exists():
            continue  # skip already generated

        try:
            html = generate_tid_html(rid, data, mav_map[rid])
            out_path.write_text(html)
            count += 1
            print(f"  [{approves}/4 avg={avg:.1f}] {fname}")
        except Exception as e:
            print(f"  ERROR {rid}: {e}")

    print(f"\nGenerated {count} HTML files → {output_dir}/")
    return count


if __name__ == "__main__":
    import sys
    os.chdir(Path(__file__).parent.parent)
    generate_all_human_review()
