#!/usr/bin/env python3
"""
Claude Agent Auto Worker V2

Batch processes pending tasks using real LLMClient (gh copilot CLI backend).
This replaces the template-based approach with genuine LLM-powered generation.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.llm_client import LLMClient
from agents.json_parser import robust_json_parse
from scripts.generate_tid_html import generate_tid_html

logger.add("logs/claude_agent_auto_worker.log", rotation="100 MB", retention="7 days")


class ClaudeAgentAutoWorkerV2:
    def __init__(self, worker_id: str = None, backend: str = None):
        self.worker_id = worker_id or f"w{os.getpid()}"
        self.llm = LLMClient(backend_override=backend)

        self.pending_maverick = Path("data/pending_maverick")
        self.pending_professor = Path("data/pending_professor")
        self.pending_reality_checker = Path("data/pending_reality_checker")
        self.pending_reviews = Path("data/pending_reviews")

        self.completed_maverick = Path("data/completed_maverick")
        self.completed_professor = Path("data/completed_professor")
        self.completed_reality_checker = Path("data/completed_reality_checker")
        self.completed_reviews = Path("data/completed_reviews")

        # Ensure directories exist
        for d in [self.pending_maverick, self.pending_professor, self.pending_reality_checker, self.pending_reviews,
                  self.completed_maverick, self.completed_professor, self.completed_reality_checker, self.completed_reviews]:
            d.mkdir(parents=True, exist_ok=True)

    def process_maverick_task(self, pending_file: Path):
        """Generate 3 patent drafts using real LLM (gh copilot CLI)"""
        logger.info(f"Processing Maverick task: {pending_file.name}")

        request = json.loads(pending_file.read_text())
        run_id = request["run_id"]
        system_prompt = request["system_prompt"]
        user_prompt = request["user_prompt"]
        model = request["model"]

        try:
            # Call real LLM
            response_text = self.llm.chat(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.85
            )

            # Parse JSON response
            result = self._parse_json_response(response_text, "Maverick")

            if "drafts" not in result or len(result["drafts"]) == 0:
                raise ValueError("No drafts generated")

            # Save to completed (preserve request metadata for downstream chaining)
            result["run_id"] = run_id
            result["timestamp"] = datetime.now().isoformat()
            result["domain"] = request.get("domain", "")
            result["target"] = request.get("target", "")
            result["void_context"] = request.get("void_context", "")
            completed_file = self.completed_maverick / f"{run_id}.json"
            completed_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

            # Clean up pending
            pending_file.unlink()

            logger.info(f"Maverick task completed: {run_id} | drafts={len(result['drafts'])}")

            # Chain: auto-create Professor pending task
            self._chain_to_professor(run_id, request, result)
            return True

        except Exception as exc:
            logger.error(f"Maverick task failed: {run_id} | error={exc}")
            return False

    def process_professor_task(self, pending_file: Path):
        """Review drafts using real LLM"""
        logger.info(f"Processing Professor task: {pending_file.name}")

        request = json.loads(pending_file.read_text())
        run_id = request["run_id"]
        system_prompt = request["system_prompt"]
        user_prompt = request["user_prompt"]
        model = request.get("model", "claude-sonnet-4-5")

        try:
            response_text = self.llm.chat(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )

            result = self._parse_json_response(response_text, "Professor")
            result["run_id"] = run_id
            result["timestamp"] = datetime.now().isoformat()

            completed_file = self.completed_professor / f"{run_id}.json"
            completed_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            pending_file.unlink()

            passed = sum(1 for v in result.get("verdicts", []) if v.get("verdict") == "PASS")
            total = len(result.get("verdicts", []))
            logger.info(f"Professor task completed: {run_id} | passed={passed}/{total}")

            # Chain: auto-create Reality Checker pending task (if any drafts passed)
            if passed > 0:
                self._chain_to_reality_checker(run_id, request, result)
            else:
                logger.info(f"Professor rejected all drafts: {run_id} | skipping RC")
            return True

        except Exception as exc:
            logger.error(f"Professor task failed: {run_id} | error={exc}")
            return False

    def process_reality_checker_task(self, pending_file: Path):
        """
        Reality check with revision loop.

        Flow: critique → if REVISE → revise drafts → re-critique → up to max_revisions
              if APPROVE → chain to Debate Panel
              if REJECT  → stop
        """
        logger.info(f"Processing Reality Checker task: {pending_file.name}")

        request = json.loads(pending_file.read_text())
        run_id = request["run_id"]
        drafts = request.get("drafts", [])
        model = request.get("model", "claude-sonnet-4-5")
        max_revisions = 3

        # Load Maverick originals as ultimate fallback for safety net
        mav_drafts = {}
        try:
            mav_file = self.completed_maverick / f"{run_id}.json"
            if mav_file.exists():
                mav_data = json.loads(mav_file.read_text())
                for i, d in enumerate(mav_data.get("drafts", [])):
                    mav_drafts[i] = d
        except Exception:
            pass

        try:
            current_drafts = drafts
            all_critiques = []
            revision_trace = []

            for revision_round in range(max_revisions + 1):
                # Step 1: Critique current drafts
                result_critiques = []
                for draft in current_drafts:
                    system_prompt, user_prompt = self._build_critique_prompts(draft)
                    response_text = self.llm.chat_reality_checker(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.2
                    )
                    critique = self._parse_json_response(response_text, "RealityChecker")
                    result_critiques.append(critique)

                all_critiques = result_critiques

                # Determine overall status
                statuses = [c.get("status", c.get("verdict", "REVISE")).upper() for c in result_critiques]
                has_approve = any(s in ("APPROVE", "APPROVED") for s in statuses)
                has_reject = all(s == "REJECT" for s in statuses)
                has_revise = any(s == "REVISE" for s in statuses)

                logger.info(
                    f"RC round {revision_round + 1}/{max_revisions + 1}: {run_id} | "
                    f"statuses={statuses} | approve={has_approve} reject={has_reject} revise={has_revise}"
                )

                # If all REJECT → stop
                if has_reject:
                    rc_status = "REJECT"
                    break

                # If no REVISE (all APPROVE) → pass to Debate Panel
                if not has_revise:
                    rc_status = "APPROVE"
                    break

                # REVISE: if we have rounds left, revise and re-critique
                if revision_round >= max_revisions:
                    rc_status = "REVISE"
                    logger.info(f"RC max revisions reached: {run_id} | passing to Debate Panel as REVISE")
                    break

                # Step 2: Revise drafts based on critiques
                revised_drafts = []
                for i, draft in enumerate(current_drafts):
                    critique = result_critiques[i] if i < len(result_critiques) else {}
                    system_prompt, user_prompt = self._build_revise_prompts(draft, critique)
                    response_text = self.llm.chat(
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.5
                    )
                    revised = self._parse_json_response(response_text, "RealityChecker")
                    # Safety net: fill missing tid_detail fields
                    # Priority: revised → current draft → Maverick original
                    orig_td = draft.get("tid_detail", {})
                    mav_td = mav_drafts.get(i, {}).get("tid_detail", {})
                    rev_td = revised.get("tid_detail", {})
                    for field in ("problem_statement", "prior_art_gap", "proposed_invention",
                                  "architecture_overview", "implementation_plan", "validation_plan",
                                  "draft_claims", "risks_and_mitigations", "references"):
                        if not rev_td.get(field):
                            rev_td[field] = orig_td.get(field) or mav_td.get(field) or ""
                    if rev_td:
                        revised["tid_detail"] = rev_td
                    revised_drafts.append(revised)

                # Record revision trace
                critique_feedback = []
                for i, c in enumerate(result_critiques):
                    issues = c.get("critical_issues", c.get("issues", c.get("hallucinations_found", [])))
                    feedback = c.get("actionable_feedback", "")
                    critique_feedback.append({
                        "draft_index": i,
                        "verdict": c.get("status", c.get("verdict", "?")),
                        "issues": issues[:5] if isinstance(issues, list) else [],
                        "feedback": str(feedback)[:300],
                    })
                revision_trace.append({
                    "round": revision_round + 1,
                    "statuses": statuses,
                    "critique_feedback": critique_feedback,
                    "drafts_before": [d.get("title", "") for d in current_drafts],
                    "drafts_after": [d.get("title", "") for d in revised_drafts],
                })

                current_drafts = revised_drafts
                logger.info(f"RC revised {len(revised_drafts)} drafts: {run_id} | round {revision_round + 1}")

            # Save result
            result = {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "status": rc_status,
                "critiques": all_critiques,
                "final_drafts": current_drafts,
                "revision_rounds": revision_round + 1,
                "revision_trace": revision_trace,
            }

            completed_file = self.completed_reality_checker / f"{run_id}.json"
            completed_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            pending_file.unlink()

            logger.info(f"Reality Checker completed: {run_id} | status={rc_status} | rounds={revision_round + 1}")

            # Chain based on final status
            if rc_status == "APPROVE":
                # Use the final (possibly revised) drafts for Debate Panel
                request["drafts"] = current_drafts
                self._chain_to_debate_panel(run_id, request, result)
            elif rc_status == "REVISE":
                # Exhausted revisions but not rejected — still send to Debate Panel
                request["drafts"] = current_drafts
                self._chain_to_debate_panel(run_id, request, result)
            else:
                logger.info(f"Reality Checker rejected: {run_id} | skipping Debate Panel")

            return True

        except Exception as exc:
            logger.error(f"Reality Checker task failed: {run_id} | error={exc}")
            return False

    def process_debate_panel_task(self, pending_file: Path):
        """
        Debate panel review using 4 specialists + chairman synthesis.

        This is a full implementation that replicates the logic from agents/debate_panel.py:
        - 4 parallel specialist reviews (kernel_hardliner, prior_art_shark, intel_strategist, security_guardian)
        - Chairman synthesis based on specialist reports
        - Deterministic verdict rules
        - Skip fact-checking (requires vector store integration)
        """
        logger.info(f"Processing Debate Panel task: {pending_file.name}")

        request = json.loads(pending_file.read_text())
        run_id = request["run_id"]
        drafts = request.get("drafts", [])

        if not drafts:
            logger.error(f"Debate Panel task failed: {run_id} | error=No drafts provided")
            return False

        try:
            specialists = [
                {
                    "name": "kernel_hardliner",
                    "role": "Kernel Hardliner",
                    "system_prompt": (
                        "You are The Kernel Hardliner. Focus on Linux kernel implementation correctness, "
                        "locking and concurrency validity. Reject unsafe ideas."
                    ),
                },
                {
                    "name": "prior_art_shark",
                    "role": "Prior-Art Shark",
                    "system_prompt": "You are The Prior-Art Shark. Focus on novelty, non-obviousness, and overlap risk with known work.",
                },
                {
                    "name": "intel_strategist",
                    "role": "Intel Strategist",
                    "system_prompt": "You are The Intel Strategist. Focus on x86 strategic value, Xeon competitiveness, and HW/SW co-design leverage.",
                },
                {
                    "name": "security_guardian",
                    "role": "Security Guardian",
                    "system_prompt": "You are The Security and Stability Guardian. Focus on TAA/side-channel risk, crash risk, and compatibility guarantees.",
                },
            ]

            current_drafts = drafts
            max_debate_revisions = 2
            final_reports = {}
            final_verdict_result = {}
            # Start trace from previous history if this is a retry
            prev_trace = request.get("previous_revision_trace", [])
            round_offset = request.get("previous_debate_rounds", 0)
            revision_trace = list(prev_trace)  # copy previous rounds
            # Retry protection: TIDs that already survived N rounds with ≥2 APPROVE
            # cannot be killed by a fresh REJECT — only REVISE allowed
            is_retry = bool(request.get("original_run_id"))
            previous_approves = request.get("previous_approves", 0)
            retry_protect = is_retry and previous_approves >= 2

            for debate_round in range(max_debate_revisions + 1):
                # Step 1: 4-specialist review
                draft_blob = self._format_draft_blob(current_drafts)
                reports = {}
                for spec in specialists:
                    try:
                        review = self._specialist_review(
                            role=spec["role"],
                            system_prompt=spec["system_prompt"],
                            draft_blob=draft_blob,
                        )
                        reports[spec["name"]] = review
                    except Exception as exc:
                        logger.warning(f"Specialist {spec['name']} failed for {run_id}: {exc}")
                        reports[spec["name"]] = {
                            "preferred_title": "",
                            "status": "REVISE",
                            "fatal_flaw": "",
                            "score": 2,
                            "issues": ["Specialist review failed - automated fallback"],
                            "yellow_cards": 0,
                            "fact_check_queries": [],
                        }

                # Step 2: Deterministic verdict
                chairman_result = self._deterministic_verdict(reports)
                verdict = chairman_result.get("final_verdict", "UNKNOWN")

                # Retry protection: TIDs with ≥2 previous APPROVE cannot be REJECT
                # They already proved their value — retry is for refinement only
                if retry_protect and verdict == "REJECT":
                    verdict = "REVISE"
                    chairman_result = {
                        **chairman_result,
                        "final_verdict": "REVISE",
                        "synthesis": f"[Retry protection: downgraded from REJECT] {chairman_result.get('synthesis', '')}",
                        "rule_trigger": f"retry_protect_{chairman_result.get('rule_trigger', '')}",
                    }
                    logger.info(f"Retry protection applied: REJECT → REVISE for {run_id} (had {previous_approves} previous APPROVE)")

                logger.info(
                    f"Debate round {debate_round + 1}/{max_debate_revisions + 1}: {run_id} | "
                    f"verdict={verdict} | rule={chairman_result.get('rule_trigger','')}"
                )

                final_reports = reports
                final_verdict_result = chairman_result

                # APPROVE or REJECT → done
                if verdict != "REVISE":
                    break

                # REVISE: if rounds left, revise drafts using specialist feedback
                if debate_round >= max_debate_revisions:
                    logger.info(f"Debate max revisions reached: {run_id}")
                    break

                # Split feedback into two tracks for focused revision:
                # Track 1: Technical correctness (kernel_hardliner + security_guardian)
                # Track 2: Strategic/novelty (prior_art_shark + intel_strategist)
                correctness_specialists = {"kernel_hardliner", "security_guardian"}
                strategy_specialists = {"prior_art_shark", "intel_strategist"}

                correctness_issues = []
                strategy_issues = []
                for name, r in reports.items():
                    issues = [f"[{name}] {iss}" for iss in r.get("issues", [])[:4]]
                    if r.get("fatal_flaw", "").strip():
                        issues.insert(0, f"[{name}] FATAL: {r['fatal_flaw'].strip()}")
                    if name in correctness_specialists:
                        correctness_issues.extend(issues)
                    else:
                        strategy_issues.extend(issues)

                void_context = request.get("void_context", "")[:2000]
                target = request.get("target", "")

                PRESERVE_INSTRUCTION = (
                    "You MUST preserve ALL tid_detail sub-fields: "
                    "problem_statement, prior_art_gap, proposed_invention, architecture_overview, "
                    "implementation_plan, validation_plan, draft_claims (≥2 items), "
                    "risks_and_mitigations, references. Never empty these fields."
                )

                def _do_revision(draft_in: dict, feedback: list, focus: str) -> dict:
                    system_prompt = (
                        f"You are an Elite Kernel Architect revising a TID. "
                        f"Focus exclusively on {focus}. Address every issue below precisely. "
                        f"Return the COMPLETE revised draft as JSON.\n\n{PRESERVE_INSTRUCTION}"
                    )
                    user_prompt = (
                        f"Target: {target}\n\n"
                        f"Void context:\n{void_context}\n\n"
                        f"Current draft:\n{json.dumps(draft_in, indent=2, ensure_ascii=False)}\n\n"
                        f"Feedback to address ({focus}):\n" + "\n".join(feedback) + "\n\n"
                        "Return strict JSON matching the original structure exactly."
                    )
                    resp = self.llm.chat(model="gpt-5.4", system_prompt=system_prompt,
                                         user_prompt=user_prompt, temperature=0.5)
                    result = self._parse_json_response(resp, "DebateRevision")
                    # Safety net: restore any dropped fields
                    orig_td = draft_in.get("tid_detail", {})
                    rev_td = result.get("tid_detail", {})
                    for field in ("problem_statement", "prior_art_gap", "proposed_invention",
                                  "architecture_overview", "implementation_plan", "validation_plan",
                                  "draft_claims", "risks_and_mitigations", "references"):
                        if not rev_td.get(field) and orig_td.get(field):
                            rev_td[field] = orig_td[field]
                    if rev_td:
                        result["tid_detail"] = rev_td
                    for field in ("scores", "why_now", "novelty_thesis", "feasibility_thesis", "market_thesis"):
                        if not result.get(field) and draft_in.get(field):
                            result[field] = draft_in[field]
                    return result

                all_issues = correctness_issues + strategy_issues
                revised_drafts = []
                for draft in current_drafts:
                    # Pass 1: fix technical correctness (kernel + security)
                    if correctness_issues:
                        draft = _do_revision(draft, correctness_issues,
                                             "kernel correctness, locking, concurrency, and security")
                    # Pass 2: strengthen novelty and strategic positioning
                    if strategy_issues:
                        draft = _do_revision(draft, strategy_issues,
                                             "novelty, prior-art distinction, and Intel strategic value")
                    revised_drafts.append(draft)

                # Record revision trace (offset round number if retry)
                revision_trace.append({
                    "round": round_offset + debate_round + 1,
                    "verdict": verdict,
                    "rule_trigger": chairman_result.get("rule_trigger", ""),
                    "specialist_feedback": all_issues,
                    "drafts_before": [d.get("title", "") for d in current_drafts],
                    "drafts_after": [d.get("title", "") for d in revised_drafts],
                })

                current_drafts = revised_drafts
                logger.info(f"Debate revised {len(revised_drafts)} drafts: {run_id} | round {debate_round + 1}")

            # Save result
            result = {
                "run_id": run_id,
                "original_run_id": request.get("original_run_id", run_id),
                "timestamp": datetime.now().isoformat(),
                "reviews": final_reports,
                "chairman_result": final_verdict_result,
                "debate_rounds": round_offset + debate_round + 1,  # total rounds including previous
                "revision_trace": revision_trace,
                "final_drafts": current_drafts,
            }

            completed_file = self.completed_reviews / f"{run_id}.json"
            completed_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            pending_file.unlink()

            verdict = final_verdict_result.get("final_verdict", "UNKNOWN")
            rounds_done = debate_round + 1

            # Ideas that survive all debate rounds as REVISE are too complex for LLM alone.
            # Mark for human review — these are the most promising candidates.
            if verdict == "REVISE" and rounds_done >= max_debate_revisions + 1:
                human_review_dir = Path("data/pending_human_review")
                human_review_dir.mkdir(parents=True, exist_ok=True)
                human_file = human_review_dir / f"{run_id}.json"
                human_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
                logger.info(
                    f"Debate Panel → PENDING_HUMAN_REVIEW: {run_id} | "
                    f"survived {rounds_done} rounds — human architect needed"
                )
                # Auto-generate HTML for human review (only if ≥1 APPROVE)
                try:
                    # For retry runs, find the original run_id (strip -retryN suffix)
                    original_run_id = request.get("original_run_id", run_id)
                    mav_run_id = original_run_id if original_run_id != run_id else run_id
                    mav_file = Path("data/completed_maverick") / f"{mav_run_id}.json"
                    if not mav_file.exists():
                        mav_file = Path("data/completed_maverick") / f"{run_id}.json"

                    if mav_file.exists():
                        mav_data = json.loads(mav_file.read_text())
                        reviews = result.get("reviews", {})
                        all_scores = [float(r.get("score", 0)) for r in reviews.values()]
                        avg = sum(all_scores) / len(all_scores) if all_scores else 0
                        approves = sum(1 for r in reviews.values() if r.get("status") == "APPROVE")

                        if approves == 0:
                            logger.info(f"Skip HTML (0/4 APPROVE): {run_id}")
                        else:
                            html_dir = Path("output/generated/human_review")
                            html_dir.mkdir(parents=True, exist_ok=True)

                            # New HTML with new run_id
                            new_fname = f"tid_{avg:.1f}avg_{approves}approve_{run_id[:12]}.html"
                            html = generate_tid_html(run_id, result, mav_data)
                            (html_dir / new_fname).write_text(html)
                            logger.info(f"Generated HTML: {new_fname}")

                            # Also overwrite the original HTML if this is a retry
                            if original_run_id != run_id:
                                orig_pattern = f"tid_*_{original_run_id[:12]}.html"
                                orig_files = list(html_dir.glob(orig_pattern))
                                if orig_files:
                                    orig_file = orig_files[0]
                                    orig_file.write_text(html)
                                    logger.info(f"Updated original HTML: {orig_file.name} → new result from {run_id}")
                                else:
                                    orig_fname = f"tid_{avg:.1f}avg_{approves}approve_{original_run_id[:12]}.html"
                                    (html_dir / orig_fname).write_text(html)
                                    logger.info(f"Created replacement HTML: {orig_fname}")
                except Exception as exc:
                    logger.warning(f"HTML generation failed for {run_id}: {exc}")
            else:
                logger.info(f"Debate Panel completed: {run_id} | verdict={verdict} | rounds={rounds_done}")
            return True

        except Exception as exc:
            logger.error(f"Debate Panel task failed: {run_id} | error={exc}")
            return False

    def _build_critique_prompts(self, draft: dict) -> tuple[str, str]:
        """Build system and user prompts for reality checker critique mode"""
        system_prompt = (
            "You are a senior Intel patent reviewer and Linux kernel architect. "
            "Your goal is to identify technically sound ideas worth patenting and help them improve. "
            "Be rigorous but constructive: prefer REVISE over REJECT whenever the core idea is salvageable. "
            "Reserve REJECT strictly for ideas that are physically impossible, rely on fictional kernel APIs, "
            "or have an unfixable ABI breakage. "
            "\n\nCRITICAL: Historical regression anti-patterns that MUST be rejected:\n"
            "- Lazy FPU/SIMD state switching using exceptions (CVE-2018-3665)\n"
            "- Hardware exceptions as routine control flow in hot paths\n"
            "- Deferred state saving for security-critical CPU architectural state\n"
            "\nOutput valid JSON only."
        )

        tid_json = json.dumps(draft.get("tid_detail", {}), indent=2)
        user_prompt = f"""
OUTPUT FORMAT (respond with ONLY this JSON, no prose before or after):
{{
    "status": "APPROVED|REVISE|REJECT",
    "fatal_flaw": "string or empty",
    "scorecard": {{
        "innovation": 1-5,
        "feasibility": 1-5,
        "prior_art_risk": 1-5
    }},
    "hallucinations_found": ["string"],
    "actionable_feedback": "string or empty",
    "approved": boolean
}}

Draft to review:
Title: {draft.get("title", "")}
One-liner: {draft.get("one_liner", "")}

TID Detail:
{tid_json}

Verdict rules:
- APPROVED: technically feasible, no showstoppers
- REVISE: promising idea with fixable issues
- REJECT: only for physically impossible designs or pure fiction
""".strip()

        return system_prompt, user_prompt

    def _build_revise_prompts(self, draft: dict, critique: dict) -> tuple[str, str]:
        """Build prompts for reality checker revise mode"""
        system_prompt = (
            "You are a senior kernel architect revising a patent draft based on critique. "
            "Drop any components flagged as impossible. Focus on the salvageable core idea. "
            "Output valid JSON only."
        )

        feedback = critique.get("actionable_feedback", "")
        tid_json = json.dumps(draft.get("tid_detail", {}), indent=2)

        user_prompt = f"""
OUTPUT FORMAT (respond with ONLY this JSON):
{{
  "title": "string",
  "one_liner": "string",
  "novelty_thesis": "string",
  "tid_detail": {{ ... }}
}}

Original draft:
{json.dumps(draft, indent=2)}

Critique feedback:
{feedback}

Revise the draft to address the feedback.
""".strip()

        return system_prompt, user_prompt

    def _parse_json_response(self, response_text: str, agent_name: str) -> dict:
        """Parse JSON response with multiple fallback strategies"""
        # Try robust parser first
        try:
            return robust_json_parse(
                response_text,
                llm_repair_callback=None,
                agent_name=agent_name
            )
        except Exception:
            pass

        # Try direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)

        raise ValueError(f"Could not parse JSON response from {agent_name}")

    # ── Stage Chaining (Async Forager) ─────────────────────────────

    def _chain_to_professor(self, run_id: str, maverick_request: dict, maverick_result: dict):
        """After Maverick completes, auto-create Professor pending task."""
        drafts = maverick_result.get("drafts", [])
        if not drafts:
            logger.warning(f"Chain skip: no drafts from Maverick | {run_id}")
            return

        # Carry metadata from request through the chain
        domain = maverick_request.get("domain", maverick_result.get("domain", ""))
        target = maverick_request.get("target", maverick_result.get("target", ""))
        void_context = maverick_request.get("void_context", maverick_result.get("void_context", ""))
        void_context_excerpt = void_context[:2000] if void_context else ""
        draft_summaries = []
        for i, d in enumerate(drafts):
            td = d.get("tid_detail", {})
            draft_summaries.append(
                f"Draft #{i}: {d.get('title', '')}\n"
                f"  One-liner: {d.get('one_liner', '')}\n"
                f"  Novelty: {d.get('novelty_thesis', '')}\n"
                f"  Problem: {td.get('problem_statement', '')}\n"
                f"  Invention: {td.get('proposed_invention', '')}\n"
                f"  Claims: {td.get('draft_claims', '')}\n"
            )

        system_prompt = (
            "You are a Senior Kernel Architect conducting pre-flight technical review.\n"
            "Check for OBVIOUS blocking errors only: architecture rule violations and malformed JSON.\n"
            "Be lenient: when in doubt, PASS. Let Reality Checker do deep analysis.\n"
            "Output strict JSON only."
        )
        user_prompt = (
            f"Void context:\n{void_context_excerpt}\n\n"
            f"Drafts to review:\n{''.join(draft_summaries)}\n\n"
            "Output format (strict JSON):\n"
            '{"verdicts": [{"draft_index": 0, "verdict": "PASS|REJECT", "quality_score": 7.5, '
            '"blocking_issues": [{"category": "string", "severity": "critical", "description": "string"}]}], '
            '"summary": "string"}\n\nOutput now:'
        )

        pending = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "target": target,
            "void_context": void_context,
            "drafts": drafts,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": "claude-haiku-4-5",
        }

        pending_file = self.pending_professor / f"{run_id}.json"
        pending_file.write_text(json.dumps(pending, indent=2, ensure_ascii=False))
        logger.info(f"Chained Maverick → Professor: {run_id} | drafts={len(drafts)} | target={target[:60]}")

    def _chain_to_reality_checker(self, run_id: str, professor_request: dict, professor_result: dict):
        """After Professor completes, auto-create Reality Checker pending task."""
        # Filter to only passed drafts
        verdicts = professor_result.get("verdicts", [])
        passed_indices = {v.get("draft_index", i) for i, v in enumerate(verdicts) if v.get("verdict") == "PASS"}
        all_drafts = professor_request.get("drafts", [])
        passed_drafts = [d for i, d in enumerate(all_drafts) if i in passed_indices]

        if not passed_drafts:
            passed_drafts = all_drafts

        domain = professor_request.get("domain", "")
        target = professor_request.get("target", "")
        void_context = professor_request.get("void_context", "")

        pending = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "target": target,
            "void_context": void_context,
            "mode": "critique",
            "drafts": passed_drafts,
            "critiques": [],
            "revisions": 0,
            "model": "claude-sonnet-4-6",
        }

        pending_file = self.pending_reality_checker / f"{run_id}.json"
        pending_file.write_text(json.dumps(pending, indent=2, ensure_ascii=False))
        logger.info(f"Chained Professor → RC: {run_id} | drafts={len(passed_drafts)} | target={target[:60]}")

    def _chain_to_debate_panel(self, run_id: str, rc_request: dict, rc_result: dict):
        """After Reality Checker completes, auto-create Debate Panel pending task."""
        drafts = rc_request.get("drafts", [])
        if not drafts:
            logger.warning(f"Chain skip: no drafts for Debate Panel | {run_id}")
            return

        domain = rc_request.get("domain", "")
        target = rc_request.get("target", "")
        void_context = rc_request.get("void_context", "")

        pending = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "target": target,
            "void_context": void_context,
            "drafts": drafts,
        }

        pending_file = self.pending_reviews / f"{run_id}.json"
        pending_file.write_text(json.dumps(pending, indent=2, ensure_ascii=False))
        logger.info(f"Chained RC → Debate Panel: {run_id} | drafts={len(drafts)} | target={target[:60]}")

    # ── Prompt Building ──────────────────────────────────────────

    def _format_draft_blob(self, drafts: list) -> str:
        """
        Format drafts into a readable string for specialist review.

        Replicates logic from agents/debate_panel.py:_format_drafts (lines 428-447)
        """
        lines = []
        for i, d in enumerate(drafts, start=1):
            lines.extend([
                f"Draft #{i}",
                f"Title: {d.get('title', '')}",
                f"One-liner: {d.get('one_liner', '')}",
                f"Novelty: {d.get('novelty_thesis', '')}",
                f"Feasibility: {d.get('feasibility_thesis', '')}",
                f"Market: {d.get('market_thesis', '')}",
                f"Problem: {d.get('problem_statement', '')}",
                f"Proposed Invention: {d.get('proposed_invention', '')}",
                f"Architecture: {d.get('architecture_overview', '')}",
                f"Implementation Plan: {d.get('implementation_plan', '')}",
                f"Claims: {d.get('draft_claims', '')}",
                "",
            ])
        return "\n".join(lines)

    def _specialist_review(self, role: str, system_prompt: str, draft_blob: str) -> dict:
        """
        Run a single specialist review.

        Replicates logic from agents/debate_panel.py:_specialist_review (lines 240-293)
        """
        user_prompt = f"""
Role: {role}

Review all candidate drafts below and pick the strongest one for your report.

Drafts:
{draft_blob}

Return strict JSON:
{{
  "preferred_title": "string",
  "status": "APPROVE|REVISE|REJECT",
  "fatal_flaw": "string or empty",
  "score": 1,
  "issues": ["string"],
  "yellow_cards": 0,
  "fact_check_queries": ["kernel symbol or file path to verify"]
}}

CRITICAL JSON SCHEMA REQUIREMENTS:
If you assign status 'REVISE' or 'REJECT', you ABSOLUTELY MUST provide at least 3 specific, actionable technical critiques in the "issues" array.
DO NOT return an empty array []. An empty issues array will cause the revision feedback loop to fail.

Example of VALID issues array:
"issues": [
  "The proposed use of RCU read lock is invalid here because function X can sleep",
  "You must define a concrete data structure for the abstraction layer between eBPF and CXL",
  "The synchronization model violates scheduler correctness under concurrent wakeups"
]

If you assign status 'APPROVE', you may provide an empty issues array or constructive suggestions for future improvement.
""".strip()

        raw = self.llm.chat(
            model="claude-sonnet-4-5",  # DP specialist: uses sonnet-4-5 to spread rate limit
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
        )

        data = self._parse_json_response(raw, "DebatePanel-Specialist")

        # Normalize status
        status = str(data.get("status", "REVISE")).upper().strip()
        if status not in {"APPROVE", "REVISE", "REJECT"}:
            status = "REVISE"

        # Clamp score to 1-5
        score = data.get("score", 2)
        try:
            score = max(1, min(5, int(score)))
        except (ValueError, TypeError):
            score = 2

        return {
            "preferred_title": str(data.get("preferred_title", "")).strip(),
            "status": status,
            "fatal_flaw": str(data.get("fatal_flaw", "")).strip(),
            "score": score,
            "issues": [str(x) for x in data.get("issues", [])][:10],
            "yellow_cards": max(0, int(data.get("yellow_cards", 0) or 0)),
            "fact_check_queries": [str(x) for x in data.get("fact_check_queries", [])][:6],
        }

    @staticmethod
    def _deterministic_verdict(reports: dict) -> dict:
        """
        Apply deterministic verdict rules based on specialist reports.

        Replicates logic from agents/debate_panel.py:_deterministic_verdict (lines 362-426)
        """
        statuses = [r.get("status", "REVISE") for r in reports.values()]
        fatal = [r.get("fatal_flaw", "").strip() for r in reports.values() if r.get("fatal_flaw", "").strip()]
        scores = [float(r.get("score", 2.0) or 2.0) for r in reports.values()]
        yellow_cards = sum(int(r.get("yellow_cards", 0) or 0) for r in reports.values())

        # Rule 1: Fatal flaw → REVISE first (give revision a chance to fix it)
        # Only hard-reject if ≥3 specialists all report fatal flaws (truly unfixable)
        if len(fatal) >= 3:
            reason = "; ".join(fatal)
            return {
                "final_verdict": "REJECT",
                "synthesis": reason,
                "confidence": 0.95,
                "rule_trigger": "fatal_flaw_reject",
                "reviewer_statuses": statuses,
            }

        if fatal:
            reason = "; ".join(fatal)
            return {
                "final_verdict": "REVISE",
                "synthesis": f"Fatal flaw(s) noted by {len(fatal)} specialist(s) — revision required: {reason}",
                "confidence": 0.7,
                "rule_trigger": "fatal_flaw_revise",
                "reviewer_statuses": statuses,
            }

        # Rule 2: Majority reject (≥2 of 4 REJECT)
        reject_count = sum(1 for s in statuses if s == "REJECT")
        if reject_count >= 2:
            return {
                "final_verdict": "REJECT",
                "synthesis": f"Majority committee rejection ({reject_count}/{len(statuses)} REJECT, no fatal flaw stated)",
                "confidence": 0.9,
                "rule_trigger": "majority_reject",
                "reviewer_statuses": statuses,
            }

        # Rule 3: Yellow card reject (≥5 yellow cards, relaxed from 3)
        if yellow_cards >= 5:
            return {
                "final_verdict": "REJECT",
                "synthesis": f"Rejected by yellow-card rule (yellow_cards={yellow_cards})",
                "confidence": 0.9,
                "rule_trigger": "yellow_card_reject",
                "reviewer_statuses": statuses,
            }

        # Rule 3b: Yellow card revise (3-4 yellow cards → give revision chance)
        if yellow_cards >= 3:
            return {
                "final_verdict": "REVISE",
                "synthesis": f"Yellow cards ({yellow_cards}) — revision required",
                "confidence": 0.7,
                "rule_trigger": "yellow_card_revise",
                "reviewer_statuses": statuses,
            }

        avg_score = sum(scores) / len(scores) if scores else 0.0
        approve_count = sum(1 for s in statuses if s == "APPROVE")

        # Rule 4: Full approval (all APPROVE + avg score >= 4)
        if approve_count == len(statuses) and avg_score >= 4.0:
            return {
                "final_verdict": "APPROVE",
                "synthesis": f"Full committee approval (avg_score={avg_score:.1f}).",
                "confidence": 0.92,
                "rule_trigger": "full_committee_approval",
                "reviewer_statuses": statuses,
            }

        # Rule 5: Majority approval (≥3 of 4 APPROVE, avg score >= 3.5, no REJECT)
        if approve_count >= 3 and avg_score >= 3.5 and reject_count == 0:
            return {
                "final_verdict": "APPROVE",
                "synthesis": f"Majority committee approval ({approve_count}/{len(statuses)} APPROVE, avg_score={avg_score:.1f}).",
                "confidence": 0.80,
                "rule_trigger": "majority_approval",
                "reviewer_statuses": statuses,
            }

        # Default: Revision required
        return {
            "final_verdict": "REVISE",
            "synthesis": "Committee requested revision due to unresolved issues.",
            "confidence": 0.7,
            "rule_trigger": "revision_required",
            "reviewer_statuses": statuses,
        }

    def run_batch(self):
        """Process all pending tasks once (batch mode)"""
        stats = {
            "maverick": {"processed": 0, "succeeded": 0, "failed": 0},
            "professor": {"processed": 0, "succeeded": 0, "failed": 0},
            "reality_checker": {"processed": 0, "succeeded": 0, "failed": 0},
            "debate_panel": {"processed": 0, "succeeded": 0, "failed": 0},
        }

        logger.info("=== Batch processing started ===")

        # Process in priority order
        for pending_file in sorted(self.pending_maverick.glob("*.json")):
            stats["maverick"]["processed"] += 1
            if self.process_maverick_task(pending_file):
                stats["maverick"]["succeeded"] += 1
            else:
                stats["maverick"]["failed"] += 1

        for pending_file in sorted(self.pending_professor.glob("*.json")):
            stats["professor"]["processed"] += 1
            if self.process_professor_task(pending_file):
                stats["professor"]["succeeded"] += 1
            else:
                stats["professor"]["failed"] += 1

        for pending_file in sorted(self.pending_reality_checker.glob("*.json")):
            stats["reality_checker"]["processed"] += 1
            if self.process_reality_checker_task(pending_file):
                stats["reality_checker"]["succeeded"] += 1
            else:
                stats["reality_checker"]["failed"] += 1

        for pending_file in sorted(self.pending_reviews.glob("*.json")):
            stats["debate_panel"]["processed"] += 1
            if self.process_debate_panel_task(pending_file):
                stats["debate_panel"]["succeeded"] += 1
            else:
                stats["debate_panel"]["failed"] += 1

        logger.info("=== Batch processing completed ===")
        logger.info(f"Stats: {json.dumps(stats, indent=2)}")

        # Print summary
        print("\n" + "="*80)
        print("BATCH PROCESSING SUMMARY")
        print("="*80)
        for agent, data in stats.items():
            if data["processed"] > 0:
                print(f"{agent.upper()}: {data['succeeded']}/{data['processed']} succeeded, {data['failed']} failed")
        print("="*80 + "\n")

        return stats

    def run_continuous(self, check_interval_seconds: int = 10):
        """
        Continuously monitor and process pending tasks (async cleanup mode).

        This mode is designed for copilot CLI which can be unstable:
        - Tolerates individual task failures
        - Continues processing even if some tasks timeout
        - Runs indefinitely in background
        """
        import time

        logger.info("=== Continuous async worker started | id={} | interval={}s ===", self.worker_id, check_interval_seconds)
        print(f"Claude Agent Auto Worker V2 started (id={self.worker_id}, interval={check_interval_seconds}s)")
        print("Monitoring pending directories for tasks...")
        print("Press Ctrl+C to stop")

        # On startup: restore any stale .lock files to .json
        # (previous session may have crashed leaving locks behind)
        stale_cleared = 0
        for pending_dir in [self.pending_maverick, self.pending_professor,
                            self.pending_reality_checker, self.pending_reviews]:
            for lock_file in pending_dir.glob("*.lock"):
                run_id = lock_file.stem.split(".")[0]
                json_file = pending_dir / f"{run_id}.json"
                try:
                    if not json_file.exists():
                        lock_file.rename(json_file)
                    else:
                        lock_file.unlink()
                    stale_cleared += 1
                except OSError:
                    pass
        if stale_cleared:
            logger.info(f"Startup: cleared {stale_cleared} stale lock files")

        total_stats = {
            "maverick": {"succeeded": 0, "failed": 0},
            "professor": {"succeeded": 0, "failed": 0},
            "reality_checker": {"succeeded": 0, "failed": 0},
            "debate_panel": {"succeeded": 0, "failed": 0},
        }

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                had_work = False

                # Process one task from each queue per cycle (fair scheduling)
                pending_files = {
                    "maverick": list(self.pending_maverick.glob("*.json")),
                    "professor": list(self.pending_professor.glob("*.json")),
                    "reality_checker": list(self.pending_reality_checker.glob("*.json")),
                    "debate_panel": list(self.pending_reviews.glob("*.json")),
                }

                total_pending = sum(len(files) for files in pending_files.values())

                if total_pending > 0 and cycle_count % 10 == 0:  # Log every 10 cycles
                    logger.info(
                        f"Cycle {cycle_count} | Pending: Maverick={len(pending_files['maverick'])} "
                        f"Professor={len(pending_files['professor'])} "
                        f"RealityChecker={len(pending_files['reality_checker'])} "
                        f"DebatePanel={len(pending_files['debate_panel'])}"
                    )

                # Strict waterfall priority: DP > RC > Professor > Maverick
                # Pick one task from the highest-priority non-empty queue.
                # This lets Forager run freely — Maverick backlog never blocks reviews.
                priority_queue = None
                for agent in ("debate_panel", "reality_checker", "professor", "maverick"):
                    if pending_files.get(agent):
                        priority_queue = agent
                        break

                active_queues = ({priority_queue: pending_files[priority_queue]}
                                 if priority_queue else {})

                # Process one task from the selected queue
                for agent, files in active_queues.items():
                    if not files:
                        continue

                    # Try to claim a task via atomic rename (supports concurrent workers)
                    pending_file = None
                    claimed_file = None
                    for candidate in sorted(files):
                        try:
                            # Use run_id to build clean lock name (prevents suffix accumulation)
                            stem = candidate.stem  # e.g. "run-abc123"
                            run_id_part = stem.split('.')[0]  # strip any prior suffixes
                            claimed = candidate.parent / f"{run_id_part}.{self.worker_id}.lock"
                            candidate.rename(claimed)
                            pending_file = claimed
                            claimed_file = claimed
                            break
                        except (FileNotFoundError, OSError):
                            # Another worker already claimed this task
                            continue

                    if pending_file is None:
                        continue

                    had_work = True

                    try:
                        if agent == "maverick":
                            success = self.process_maverick_task(pending_file)
                        elif agent == "professor":
                            success = self.process_professor_task(pending_file)
                        elif agent == "reality_checker":
                            success = self.process_reality_checker_task(pending_file)
                        elif agent == "debate_panel":
                            success = self.process_debate_panel_task(pending_file)
                        else:
                            continue

                        if success:
                            total_stats[agent]["succeeded"] += 1
                        else:
                            total_stats[agent]["failed"] += 1
                            # Restore file for retry if it still exists
                            if claimed_file and claimed_file.exists():
                                original = claimed_file.parent / (claimed_file.stem.split(".")[0] + ".json")
                                try:
                                    claimed_file.rename(original)
                                except OSError:
                                    pass

                    except Exception as exc:
                        logger.error(f"Unexpected error processing {agent} task {pending_file.name}: {exc}")
                        total_stats[agent]["failed"] += 1
                        # Restore file for retry
                        if claimed_file and claimed_file.exists():
                            original = claimed_file.parent / (claimed_file.stem.split(".")[0] + ".json")
                            try:
                                claimed_file.rename(original)
                            except OSError:
                                pass

                if not had_work:
                    # No pending tasks, sleep
                    time.sleep(check_interval_seconds)
                else:
                    # Had work, check again quickly
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("=== Continuous worker stopped by user ===")
                print("\n" + "="*80)
                print("WORKER STOPPED - LIFETIME STATISTICS")
                print("="*80)
                for agent, data in total_stats.items():
                    total = data["succeeded"] + data["failed"]
                    if total > 0:
                        success_rate = (data["succeeded"] / total * 100) if total > 0 else 0
                        print(f"{agent.upper()}: {data['succeeded']}/{total} succeeded ({success_rate:.1f}%), {data['failed']} failed")
                print("="*80 + "\n")
                break

            except Exception as exc:
                logger.error(f"Worker loop error: {exc}")
                time.sleep(check_interval_seconds)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude Agent Auto Worker V2")
    parser.add_argument("--batch", action="store_true", help="Process all pending tasks and exit")
    parser.add_argument("--worker-id", default=None, help="Worker ID for concurrent mode (default: w<PID>)")
    parser.add_argument("--backend", default=None, choices=["copilot_cli", "claude_code_cli", "openai"],
                        help="Override LLM backend for this worker")
    args = parser.parse_args()

    worker = ClaudeAgentAutoWorkerV2(worker_id=args.worker_id, backend=args.backend)

    if args.batch:
        worker.run_batch()
    else:
        worker.run_continuous(check_interval_seconds=10)
