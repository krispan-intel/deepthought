# DeepThought Agent Workflow & Collaboration

## Agent Team Structure

### Development Agents (Code & Infrastructure)
- **Architect** — System design, technical decisions, architecture planning
- **PM** — Project management, task allocation, progress tracking
- **Writer** — Implementation of production code
- **Tester** — Test suite development and validation
- **Reviewer** — Code review and quality assurance

### Analysis Agents (Data & Quality)
- **Corpus Analyst** — Vector DB health, coverage gap analysis, data source recommendations
- **Metrics Analyst** — Pipeline performance metrics, bottleneck identification, trend analysis

### Pipeline Agents (Runtime Execution)
- **Forager** — Topological void detection
- **Maverick** — Technical invention draft generation
- **Professor** — Pre-flight technical review
- **Patent Shield** — Prior-art conflict screening
- **Reality Checker** — Physical feasibility analysis
- **Debate Panel** — Committee consensus decision

---

## Workflow Patterns

### Pattern 1: Feature Development (Normal Sprint Work)

```
1. User Request → Architect
   └─ Architect designs solution, creates task list

2. Architect → PM
   └─ PM receives task list, assigns work

3. PM → Writer
   └─ "Please implement Task #1-3 (professor.py, pipeline integration)"

4. Writer → Code
   └─ Implements features, commits to branch

5. PM → Tester (in parallel or after Writer)
   └─ "Please write test suite for Professor agent"

6. Tester → Tests
   └─ Writes tests, reports results to PM

7. PM → Reviewer (optional)
   └─ "Please review PR #123"

8. Reviewer → Feedback
   └─ Reviews code, suggests improvements

9. PM → User
   └─ "Feature complete, 5 tests passing ✅"
```

**Example:** Adding Professor pre-flight reviewer (completed 2026-04-09)

---

### Pattern 2: System Health Check (Weekly Scheduled)

```
EVERY MONDAY 09:00:

1. Metrics Analyst (Auto-triggered)
   └─ Generates daily report from last 100 runs
   └─ Identifies bottlenecks, calculates success rates
   └─ Output: docs/metrics_reports/2026-04-09.md

2. PM reads Metrics Analyst report
   └─ If critical issues detected → triggers action

3. If "No voids rate > 30%" → Corpus Analyst
   └─ PM: "Corpus Analyst, please analyze gaps causing No voids failures"
   
4. Corpus Analyst
   └─ Analyzes ChromaDB coverage, identifies TDX/CXL gaps
   └─ Recommends specific data sources (Intel TDX spec, LKML patches)
   └─ Output: docs/corpus_analysis/2026-04-09.md

5. PM creates action items from reports
   └─ PM → Writer: "Please implement TDX crawler (ROI: 16.0)"
   └─ PM → Architect: "Review corpus recommendations, approve P0 tasks"

6. PM reports to User
   └─ "Weekly health: 42% No voids (critical), TDX ingestion planned"
```

**Trigger Conditions:**
- ✅ Scheduled: Every Monday morning
- ✅ Threshold: APPROVED rate < 1% for 50 runs
- ✅ Threshold: No voids rate > 30%

---

### Pattern 3: Incident Response (Performance Degradation)

```
TRIGGER: APPROVED rate drops from 3% to 0% over 50 runs

1. Auto-trigger → Metrics Analyst
   └─ Generate incident report comparing current vs baseline
   └─ Identify which stage degraded (Forager? RC? Debate?)

2. Metrics Analyst → PM
   └─ "🔴 Incident: APPROVED rate dropped -3pp, RC rejection up 20pp"

3. PM evaluates severity
   └─ If critical: escalate to Architect immediately
   └─ If minor: add to weekly review

4. PM → Architect
   └─ "Architect, analyze RC rejection increase — prompt regression?"

5. Architect investigates
   └─ Reviews recent changes (git log), compares configs
   └─ Hypothesis: "Recent Maverick prompt change caused regression"

6. Architect → PM
   └─ "Task: Revert Maverick prompt to v1, run A/B test"

7. PM → Writer
   └─ "Please revert agents/maverick.py to commit abc123"

8. PM → Metrics Analyst (after 50 runs)
   └─ "Compare performance: old prompt vs new prompt"

9. Metrics Analyst → PM
   └─ A/B test report: old prompt has 15% better RC pass rate

10. PM → User
    └─ "Incident resolved, reverted prompt, APPROVED rate back to 3%"
```

**Trigger Conditions:**
- 🔴 APPROVED rate drops > 2pp
- 🔴 Any stage failure rate increases > 20pp
- 🔴 Pipeline throughput < 50% of baseline

---

### Pattern 4: Optimization Campaign (Continuous Improvement)

```
QUARTERLY: Systematic prompt/config optimization

1. PM → Metrics Analyst
   └─ "Generate 90-day trend report, identify stable low performers"

2. Metrics Analyst
   └─ "RC rejection stable at 35% for 3 months — optimization opportunity"
   └─ Analyzes failure patterns: 40% are "evidence grounding" issues

3. PM → Architect
   └─ "Can we improve Maverick evidence grounding? Worth the effort?"

4. Architect evaluates
   └─ Reviews Maverick prompt, proposes 3 variants
   └─ Designs A/B test plan (baseline vs variant A vs variant B)

5. Architect → PM
   └─ "Task list: Implement 3 prompt variants, run 50 trials each"

6. PM → Writer
   └─ "Create feature flag for prompt variants in configs/settings.py"

7. Writer implements, Tester validates

8. PM runs A/B test (150 runs over 2 days)

9. PM → Metrics Analyst
   └─ "Analyze A/B test results for 3 prompt variants"

10. Metrics Analyst → PM
    └─ "Variant B wins: RC rejection 35% → 22%, p-value 0.015"

11. PM → Writer
    └─ "Deploy variant B as default, remove feature flag"

12. PM → User
    └─ "Optimization complete: RC rejection ↓ 13pp, APPROVED rate ↑ 2pp"
```

---

## Agent Collaboration Matrix

### Who Talks to Whom

| Agent           | Talks To                           | About                                    |
|-----------------|-------------------------------------|------------------------------------------|
| **User**        | PM, Architect                       | Requirements, status updates             |
| **PM**          | All agents                          | Task assignment, progress tracking       |
| **Architect**   | PM, Writer, Tester                  | Design specs, technical guidance         |
| **Writer**      | PM, Tester, Reviewer                | Code completion, issues found            |
| **Tester**      | PM, Writer                          | Test results, bugs discovered            |
| **Reviewer**    | PM, Writer                          | Code feedback, approval                  |
| **Metrics Analyst** | PM, Architect, Corpus Analyst   | Performance reports, bottlenecks         |
| **Corpus Analyst** | PM, Writer, Architect            | Coverage gaps, ingestion recommendations |

### Information Flow

```
User Requirements
    ↓
Architect (design) → PM (plan) → Writer (code) → Tester (validate)
                                      ↓
                                 Reviewer (approve)
                                      ↓
                                    Commit

Pipeline Logs
    ↓
Metrics Analyst → PM
    ↓
If bottleneck detected → Corpus Analyst → PM → Writer (fix)
```

---

## Trigger Conditions Reference

### Scheduled Triggers
| Frequency | Agent           | Action                        |
|-----------|-----------------|-------------------------------|
| Daily     | Metrics Analyst | Generate daily quality report |
| Weekly    | Corpus Analyst  | Coverage health check         |
| Weekly    | PM              | Sprint planning review        |

### Threshold Triggers
| Condition                     | Agent           | Action                          |
|-------------------------------|------------------|---------------------------------|
| No voids rate > 30%           | Corpus Analyst   | Gap analysis + recommendations  |
| APPROVED rate < 1% (50 runs)  | Metrics Analyst  | Incident report                 |
| RC rejection > 40%            | Metrics Analyst  | Failure pattern analysis        |
| Any stage degradation > 20pp  | Metrics Analyst  | Performance regression report   |

### Event Triggers
| Event                         | Agent           | Action                          |
|-------------------------------|------------------|---------------------------------|
| New Cartesian keyword added   | Corpus Analyst   | Coverage check for new keyword  |
| Config change deployed        | Metrics Analyst  | Before/after comparison         |
| A/B test requested            | Metrics Analyst  | Statistical analysis            |

---

## Best Practices

### For PM
1. ✅ Always assign tasks with clear scope and deadline
2. ✅ Trigger Metrics Analyst after every 50 runs
3. ✅ Read both Metrics + Corpus reports before sprint planning
4. ✅ Escalate critical bottlenecks to Architect immediately
5. ❌ Don't write code yourself (assign to Writer)

### For Architect
1. ✅ Provide complete task lists with priorities
2. ✅ Review Corpus Analyst recommendations before approving ingestion
3. ✅ Design A/B tests when optimizing prompts/configs
4. ❌ Don't implement code (provide specs to Writer)

### For Metrics Analyst
1. ✅ Focus on top 3 bottlenecks, not all issues
2. ✅ Always link bottlenecks to actionable next steps
3. ✅ Compare trends, not just current snapshot
4. ❌ Don't report metrics without interpretation

### For Corpus Analyst
1. ✅ Quantify gaps (doc counts, success rates, ROI)
2. ✅ Recommend specific sources, not generic "add more data"
3. ✅ Prioritize by ROI, not by effort
4. ❌ Don't propose unfeasible crawlers (10-day projects)

---

## Communication Protocols

### Report Formats
- **Metrics Analyst:** Markdown reports to `docs/metrics_reports/YYYY-MM-DD.md`
- **Corpus Analyst:** Markdown reports to `docs/corpus_analysis/YYYY-MM-DD.md`
- **PM:** Status updates as conversation messages
- **Writer/Tester:** Commit messages + PR descriptions

### Notification Channels
- **Critical Issues:** PM notified immediately via conversation
- **Daily Reports:** Saved to docs, PM reviews next morning
- **A/B Test Results:** Metrics Analyst → PM → decision

### Decision Authority
- **Architecture decisions:** Architect (final authority)
- **Priority/scheduling:** PM (final authority)
- **Technical implementation:** Writer (with Architect guidance)
- **Test coverage:** Tester (with PM approval)
- **Ingestion priorities:** Corpus Analyst recommendations → PM approval → Writer execution

---

## Example: Complete Feature Development Flow

**Scenario:** System has 42% "No voids found" failures

```
Day 1 Monday:
09:00 — Metrics Analyst: Daily report shows 42% No voids (critical)
09:15 — PM reads report, triggers Corpus Analyst
10:00 — Corpus Analyst: TDX (5 docs), CXL (12 docs) are gaps
10:30 — Corpus Analyst: Recommends Intel TDX spec ingestion (ROI: 16.0)
11:00 — PM → Architect: "Review corpus recommendations, approve?"
11:30 — Architect: "Approved, P0 task: TDX crawler"
12:00 — PM → Writer: "Please implement crawlers/intel_tdx_crawler.py"

Day 2 Tuesday:
10:00 — Writer: "TDX crawler complete, ingested 8 PDFs"
11:00 — PM → Tester: "Please test TDX crawler"
14:00 — Tester: "3/3 tests passing ✅"
15:00 — PM: Commit + restart pipeline service

Day 3-4 Wednesday-Thursday:
(Pipeline runs 50 iterations with new TDX corpus)

Day 5 Friday:
09:00 — Metrics Analyst: "No voids rate 42% → 28% (↓ 14pp)"
09:30 — PM → User: "TDX ingestion successful, No voids reduced 33%"
10:00 — PM: Close task, update TODO.md
```

**Result:** 2 days development, 2 days validation, 14pp improvement ✅
