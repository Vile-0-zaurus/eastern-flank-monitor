# SPEC — Eastern Flank: Lessons & Practices

> Retrospective of the Eastern Flank Monitor project (4 Oct – 22 Nov 2026).
> Purpose: carry what worked into future projects, and avoid repeating what failed.
> Use it together with `docs/protocols.md` in the project repo.

---

## 1. The project in one paragraph

A portfolio prototype that watches Russia's side for signs of military tension toward Finland, Estonia, Latvia, Lithuania and Poland. It replays 2021–22 week by week and shows a "Now" snapshot of 2026: country briefings, an incident map (confirmed vs. reported), a Russia tab, six interface languages. Under the hood: 79,291 GDELT files filtered to ~4 GB, an AI headline classifier validated against human labels, a pre-registered backtest with an honest pass and an honest fail. Built by one non-coder ("boss"), one planner/reviewer AI, and one executor agent. Total recorded AI spend: about $4.69.

**Status:** finished, public on GitHub, tagged `v1.0-prototype`, live pipeline built but switched off until deployment.

---

## 2. What worked

| Practice | Why it worked |
|---|---|
| **A written SPEC from day one** | Every agent session started from the same source of truth. Scope drift was caught early. |
| **Milestones with "done when" conditions** | One finished piece before the next; no half-built pile. |
| **Data reality check before design (M0)** | Found blocked sources, missing history and the real download size before anything was built on them. |
| **Gates and stop rules in every assignment** | The agent stopped instead of guessing: missing SPEC, leaky filter, approval timeouts, unclear data. |
| **Pre-registration (locking rules before testing)** | The backtest result is believable. A fail stayed a fail; fixes were reported separately as post-hoc. |
| **Human-validated AI** | A 20-headline human audit + adjudication turned "the AI says so" into "93.3% agreement with a human, kappa 0.86". |
| **Real-charge caps + calibration runs** | After the early surprises, every paid run matched or beat its estimate. |
| **Honesty rules** | "No data ≠ zero", "Confirmed vs. Reported", "a missing fact beats a guessed one". These made the project credible. |
| **Separate agent identity** | Commits under a project email; the secret and personal-info scans came back clean. |
| **Agent self-testing** | Once the agent ran its own browser click-tests, the "send me screenshots of bugs" loop ended. |
| **Everything in the repo** | Crashes, freezes, reboots and context compression never lost real work. |

---

## 3. What failed (and what it taught)

| What happened | Root cause | Lesson |
|---|---|---|
| **Real AI cost was ~3.2× the tracker** | Reasoning models bill hidden "thinking" tokens the tracker didn't count | Calibrate with a tiny run; trust the console, not estimates |
| **A $10 auto-recharge hit the card** | Auto-reload was on in one provider's console | Turn auto-reload off everywhere on day one |
| **~20,000 rows saved as "AI unavailable"** | Balance ran out; failures were stored as final answers | Failures must be retryable; stop the whole run on balance/auth errors |
| **Downloads that never finished** | "Last 12 weeks before today" kept moving | Fixed date windows, never rolling ones, for one-off jobs |
| **Machine froze twice** | Suspend/resume in the VM | Sleep off during long jobs; resumable services |
| **Download 2× slower** | VPN on | Check the network path before blaming the source |
| **Collector missed days** | Ran at boot before DNS worked | Wait for real connectivity; second safety run |
| **The "old page" problem** | Browser cached old JavaScript | Cache-busting (`?v=<commit>`) on every asset |
| **Agent stalled for hours** | Approval prompt timed out while nobody watched | Skip-and-list rule: skip, continue, list "Needs your approval" |
| **Agent stopped mid-task** | 90-step limit per turn | Split big assignments into parts; commit at each step |
| **Agent got sloppy** | Context compressed repeatedly | Fresh session + handoff prompt from repo files |
| **Assignments got cut off** | Input size limit | Short assignments; save every task to `docs/tasks/` first |
| **Frontend took ~15 rounds** | Built screens before knowing what users need; showed the model, not the answer | **Mockup first.** Validate the user value before building UI |
| **Per-country weekly view felt empty** | Data too thin at country/week level | Check data density per screen before designing it |
| **Inverted scale, wrong mapping** | Planner errors (scale middle rungs; Belarus mapped by border, not direction) | Human checks the data; check against source text, not notes |
| **"Averaging hid the extreme"** | Weighted average flattened a huge Ukraine attention spike | Warning systems need max-signal rules, not only averages |

---

## 4. Lessons by area

### 4.1 Working with AI agents
- **Roles:** human = boss (decides, approves, judges); planner AI = plans and reviews; executor agent = builds. The second pair of eyes caught many errors.
- **The agent reads files, not chats.** SPEC, protocols, task files and STATE.md are the agent's memory.
- **Every assignment:** goal, numbered steps, gates, stop rules, "save task first", "commit after each step", report format.
- **Fresh session** when the agent warns about compressed context; handoff prompt = read these files, state, rules, next task.
- **Approvals:** safe commands (git, tests, local server) always-allowed; deletes, installs, system changes, paid APIs always confirmed.
- **Reports are reviewed, not trusted blindly.** Numbers that don't add up get questioned (e.g. 16,207 of 16,128 files).
- **Voice doesn't reach the reviewer.** Use dictation (text) or typed notes; screen videos show *where*, text says *what*.

### 4.2 Budget
1. Free first; pay only for what's missing.
2. Prepaid credits only; **auto-reload off everywhere**.
3. One API key per project; ledger in `docs/budget.md`.
4. **Calibration run (1–5% of the job) before any big run.** Price = calibrated cost × 1.2.
5. Hard cap on the **real** charge, enforced after every batch.
6. Measure one unit (e.g. one language) before scaling to all.
7. **Sampling beats brute force** (100–200 items/week gave the trend at a fraction of the cost).
8. Compare console balance before/after every paid run.
9. Upfront price + explicit OK for every paid step.

### 4.3 Data
- Test reachability, legality and history **before** building on a source.
- **Never bypass blocks** (no VPN, DNS tricks, user-agent spoofing). Sanctions-based blocks are a legal line.
- Dated sources only; **no hindsight** in backtests (source date ≤ end of week).
- Discovery sources (trackers) ≠ citations; confirm with primary/official sources.
- Store small: stream-filter raw files in memory, keep only needed columns (490 GB raw → 4 GB kept).
- Keep wide filters at download time; filter precisely later in the database (re-runnable, no re-download).

### 4.4 Honesty and validation
- Lock rules and prompts (git tags) **before** testing; report post-hoc changes separately.
- Never tune on the test set; freeze gold labels before the AI runs.
- Human labels first, AI second; adjudicate disagreements openly; report raw and adjudicated numbers.
- "No data" is never shown as zero or calm.
- Label certainty: Confirmed vs. Reported.
- Never claim more than the facts ("collected politely without bypassing", not "no scraping"; not "we broke no law").
- A clear failure, explained, is worth more in a portfolio than a fake success.

### 4.5 Product and UX
- **Mockup first.** Judge a picture in one minute before building a screen for a week.
- Show **the answer, not the engine**: "How is my country? What happened? What's not happening?"
- **Stories, not counts.** "Zakharova said…" beats "17 headlines (usual 20)".
- One fixed reading order; one hover card; no hidden drawers and mystery buttons ("Dossier", "Show all").
- Plain words; fixed everyday comparisons (weather station, smoke detector, two witnesses).
- Calm design: numbers + context, no alarm words, muted colors.
- **The 5-second test:** glance, look away, can you say what's going on?
- The builder is the first test user. If the builder doesn't understand it, nobody will.
- Watch the opponent's side first (the user's own insight: "you watch what happens in your opponent's yard").

### 4.6 Operations
- Long jobs as resumable background services; skip finished work; never pay twice.
- Fixed windows for one-off jobs; rolling windows only for live mode.
- Memory limits (stream/chunk; stop under 1.5 GB free); disk guard.
- Commit and push after every step; VM snapshot before big changes.
- Cache-busting for local web apps.
- Status command in plain English (`efm-status`) with "ACTION NEEDED" only for real problems.
- End dates in config for anything that runs or spends; nothing runs forever by accident.

---

## 5. Reusable checklists

### 5.1 Project start
- [ ] One-paragraph purpose + target user + non-goals
- [ ] SPEC.md with milestones and "done when"
- [ ] Boundaries (legal, ethical, privacy) written down
- [ ] Separate agent identity/email for commits; private repo
- [ ] API keys per project, prepaid, auto-reload OFF, spend limits set
- [ ] **Mockup of the main screen, judged by the human, before any build**
- [ ] Data reality check (M0) before design

### 5.2 Every agent assignment
- [ ] Save task to `docs/tasks/` first
- [ ] Numbered steps, gates, stop rules
- [ ] "No API calls" unless a run id + cap is approved
- [ ] Commit + push after each step/section
- [ ] "If low on steps, stop at a committed point"
- [ ] Approvals: skip-and-list
- [ ] Report in plain words + "Needs your approval"

### 5.3 Every paid run
- [ ] Calibration run → measured price
- [ ] Upfront price × 1.2 + hard real-charge cap
- [ ] Console balance noted before and after
- [ ] Ledger entry

### 5.4 Before going public
- [ ] Secret scan of full history
- [ ] Personal-info scan (emails, paths, screenshots, browser tabs)
- [ ] LICENSE + data/licenses section
- [ ] README: pitch → demo GIF → highlights → tech stack → honest results
- [ ] Disclaimer reviewed (legal review before a public *website*)

### 5.5 Before deploying live
- [ ] End date + monthly cap in config
- [ ] Week-one calibration of real costs
- [ ] Weekly admin routine defined (≤ 20 min)
- [ ] Phone layout tested

---

## 6. Templates

### 6.1 Assignment skeleton
```
AGENT — <TASK NAME>. NO API calls. Save to docs/tasks/ first. Commit + push after each section.
APPROVALS: if a command times out, skip it, continue, list it under "Needs your approval".
If low on steps: stop at a committed point, say what's left.
| # | Task |
|---|------|
| 1 | ... |
Report in plain words, STOP.
```

### 6.2 New-session handoff
```
AGENT — NEW SESSION HANDOFF. Project: <path>.
Read first: README.md, SPEC.md, STATE.md, docs/protocols.md, the 3 newest files in docs/reports/ and docs/tasks/.
Run the status script and git status.
STATE: <3–5 lines>. STANDING RULES: <budget, data, honesty, approvals>.
TASK: <next task>. Report, STOP.
```

---

## 7. What we take out of this project

**Assets**
- A finished, public, honest portfolio project with a demo video and GIF
- A reusable rulebook (`docs/protocols.md`) and this lessons file
- A working agent workflow: SPEC → milestones → gated assignments → reports → review

**Skills**
- Running AI agents as a team lead, not a typist
- Budgeting AI work (calibration, caps, hidden-token awareness)
- Designing honest evaluations (pre-registration, human validation, adjudication)
- Judging UX as a user, and explaining why a screen fails

**Numbers worth quoting**
- 79,291 files processed → ~4 GB kept
- Classifier vs. human: 93.3% agreement, kappa 0.86
- Backtest: Test A pass (lenient), Test B fail (explained)
- 89 unit tests + browser self-tests; 6 interface languages
- Total recorded AI spend ≈ $4.69

**The three biggest takeaways**
1. **Measure before you trust** — costs, data, agent reports, your own assumptions.
2. **Mockup before you build** — the frontend cost more rounds than everything else combined.
3. **Honest beats impressive** — a documented failure is a stronger portfolio story than a hidden one.
