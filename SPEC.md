# SPEC.md — Eastern Flank Monitor (working title)

> This file is the single source of truth for the project.
> Every coding session starts by reading it. If a decision changes, update this file first, then the code.

---

## 1. Purpose

An independent early-warning app that tracks Russian military, political and grey-zone activity directed toward **Finland, Estonia, Latvia, Lithuania and Poland**, and turns it into a calm, honest, easy-to-understand risk picture.

**The goal:** a person with no military or technical background can stay informed in **2–5 minutes a day**.

### Non-goals
- Not an official warning or alert service.
- Not a news aggregator with a risk color on top.
- Not a real-time military tracker.
- Does not give crisis advice of its own.
- No push alerts in Stage 1.

---

## 2. Users and UX principles

**Primary user:** an ordinary resident of the region. No military or technical knowledge assumed.

**Principles:**
1. **The user chooses the depth.** Three reading depths:
   - **Depth 1 — Summary (≈30 sec):** overall level in plain words + 2–3 sentences on what changed.
   - **Depth 2 — Layers (≈2 min):** four layer cards. Each shows its level, a short trend and one sentence of explanation. Switching layers takes one click.
   - **Depth 3 — Details (optional):** charts, indicator values, baselines, sources, methodology.
2. **Plain language on Depths 1–2.** No jargon. ("Russia closed sea areas for live-fire exercises", not "NAVAREA warnings".) Technical terms are allowed on Depth 3, with short explanations.
3. **"No significant change" is a valid answer** and is shown in one line. Calm is the default tone.
4. **Every level change is explained:** which layer moved, which indicators moved, and why.
5. **Levels are named, not only colored.** Each level has a one-line definition the user can open.
6. **Each level links to official preparedness guidance** for each covered country (e.g. Finland's 72-hour home preparedness guidance). The app never writes its own crisis instructions.
7. **Language:** English only in Stage 1, but all UI text lives in translation files from day one (see §9) so other languages can be added later.
8. **Platform:** desktop browser first. Layout should not break on a narrow screen, but mobile design is not a Stage 1 goal.

---

## 3. Scope

**Actor tracked:** Russia, including Kaliningrad, and Belarus where it acts as a staging area.
**Region of concern:** Finland, Estonia, Latvia, Lithuania, Poland (including the Suwałki corridor).

### Stages
| Stage | What | Gate to next stage |
|---|---|---|
| 1 | Working version that runs locally, used by the admin + 1–3 test users (see §15) | Backtest done, results look meaningful, test users find it useful |
| 2 | Public website (e.g. GitHub Pages + scheduled updates) | Real users and stable data pipeline |
| 3 | Mobile app | Only if the project takes off |

---

## 4. Boundaries, ethics and legal

These rules are not optional and override any feature request.

1. **Track the Russian side and aggregated incidents only.** Never collect, display or publish locations or movements of Finnish, Baltic, Polish, or other NATO/allied forces or infrastructure.
2. **No crisis advice.** Link to official authorities only.
3. **No personal data.** Do not collect or show information about private individuals.
4. **Respect source terms and licenses.** Check each data source's terms of use before using it (some conflict datasets restrict redistribution). Record license notes in `docs/sources.md`.
5. **No secrets in the repo.** API keys live in a local `.env` file that is listed in `.gitignore`.
6. **Never bypass access blocks** (no user-agent spoofing, no VPN workarounds).
7. **Never circumvent legal or sanctions-based blocks (DNS, VPN, proxies).**
8. **Disclaimer** — shown on every page (short version in the footer, full version on an "About" page):

> **Short:** Independent analysis project. Not an official warning service. In a crisis, follow your national authorities.
>
> **Full:** This app is an independent, non-commercial analysis project based on publicly available information. It is not affiliated with any government, military or official agency, and it is not an official warning or alert service. Its assessments may be incomplete or wrong. Do not base safety decisions on this app alone. In any emergency or crisis, follow the instructions of your national authorities and official emergency services.

*(Have the disclaimer reviewed by a legal professional before Stage 2 public launch.)*

---

## 5. The model

### 5.1 Four layers

| Layer | Question it answers | Plain-language name |
|---|---|---|
| **Capability** | Can Russia do it? | "Military readiness" |
| **Intent** | Are they preparing the story? | "Signals of intent" |
| **Opportunity** | Is the window open? | "Window of opportunity" |
| **Hybrid** | How hot is the grey zone? | "Grey-zone activity" |

### 5.2 Indicators

Status: **MVP** = Stage 1 build. **Later** = after MVP works. Every MVP source must pass the data reality check (Milestone M0) before it is built on.

**Intent**
| ID | Indicator | Status |
|---|---|---|
| I1 | Volume of Russian state-media coverage about FI/EE/LV/LT/PL, normalized to total coverage | MVP |
| I2 | Share of that coverage using pretext frames: "protecting compatriots", "Nazism/fascism", "illegitimate borders", "NATO preparing aggression", "historical Russian lands" (AI-classified) | MVP |
| I3 | Official acts: Duma bills, foreign ministry statements, decrees about the region (semi-manual log) | MVP (manual) |

**Capability**
| ID | Indicator | Status |
|---|---|---|
| C1 | Russian navigation warnings / live-fire sea-area closures in the Baltic and Gulf of Finland (count and frequency) | MVP if source verified |
| C2 | Force posture notes near the border, from official intelligence reports and established think tanks (manual, time-stamped) | MVP (manual) |
| C3 | Satellite imagery checks (e.g. Sentinel-1 radar) of selected known garrisons | Later |
| C4 | Recruitment/mobilization signals in northwest Russian regions (bonuses, job ads, decrees) | Later |
| C5 | Procurement signals: medical, field hospitals, fuel (public procurement portal) | Later |
| C6 | Exercise anomalies: units not returning to base after exercises | Later |

**Opportunity**
| ID | Indicator | Status |
|---|---|---|
| O1 | Ukraine war status (active / frozen / ceasefire freeing forces), scored 0–4 weekly | MVP (manual) |
| O2 | US commitment to European defense, scored 0–4 weekly | MVP (manual) |

**Hybrid**
| ID | Indicator | Status |
|---|---|---|
| H1 | GPS interference over the Baltic region | MVP if source verified |
| H2 | Incident log: cable/pipeline damage, sabotage, airspace and drone violations, border provocations, instrumentalized migration (from official reports, manual) | MVP (manual) |
| H3 | Shadow fleet / suspicious vessel activity from AIS data | Later |

Manual indicators are honest by design: they are clearly labeled "analyst input" in the app, with the date and source.

### 5.3 Scoring

1. **Baseline:** each automated indicator has a rolling baseline (default: trailing 180 days). The score reflects how far today's value is from normal (e.g. a z-score or percentile).
2. **Indicator → layer:** each layer gets a level 0–4 from its indicators (weighted average, weights in a config file, not in code).
3. **Cost-to-fake weighting:** signals that are expensive to fake (logistics, mobilization, procurement) weigh more than cheap ones (rhetoric volume, flyovers).
4. **Convergence rule — the main protection against false alarms:**
   - The overall level can only rise above **Watchful** when **two or more layers** are at Elevated or higher.
   - **Hybrid alone** and **Opportunity alone** can never raise the overall level above Watchful.
   - **Serious** and **Critical** require manual analyst confirmation before being shown. Unconfirmed, they are shown as "Elevated (Serious proposed, awaiting confirmation)" or "Elevated (Critical proposed, awaiting confirmation)", not as plain Elevated.
5. **Cadence:** data updates daily (short "what changed" note). The overall level is reassessed **weekly**, unless a layer jumps two or more levels at once.
6. **No hindsight:** a row counts for week W only if source_date ≤ last day of W. A later source_date is ignored for that week. Week W is Monday through Sunday. A missing source_date does not count. Ignored is no data, not zero.

### 5.4 Levels (draft — thresholds to be tuned by the backtest)

| Level | Name | Draft definition |
|---|---|---|
| 0 | **Calm** | All layers at or near normal. |
| 1 | **Watchful** | One layer elevated, or several slightly above normal. Typical for the current period. |
| 2 | **Elevated** | Two layers elevated at the same time. |
| 3 | **Serious** | Three layers elevated, or Capability and Intent both strongly elevated. Analyst-confirmed. |
| 4 | **Critical** | Capability and Intent both at high levels plus at least one other layer elevated. Analyst-confirmed. |

Tuning is not silent. Cutoffs and weights are pre-registered in §5.6, before any real-data run. A later change must be reported separately in the backtest report.

### 5.5 Headline rules

These rules apply to Intent classification (I1, I2) and to human labeling.

1. "About the region" means about Finland, Estonia, Latvia, Lithuania, or Poland, on any topic.
2. Kaliningrad local or domestic news is not about the region. It is Russia, unless it involves those five countries, NATO, borders, or the military.
3. Ukraine-only or Russia-only news is not about the region, even if NATO is mentioned.
4. Judge the wording, not the topic. A neutral report on a sensitive topic is ordinary news unless the wording itself is loaded.
5. Scare quotes around the target country's own terms, such as «советская оккупация», are mild hostile framing.
6. A quote from the target country's officials is not Russian framing. A quote from Russian officials is.

### 5.6 Pre-registration

Written before any real-data scoring run. Tag: `scoring-prereg`.

Threshold method: z-score levels computed from a calm calibration period (2021-01-01..2021-06-30). Draft cutoffs, registered here and not yet computed from that period: level 1 ≥ 1.0, level 2 ≥ 1.5, level 3 ≥ 2.0, level 4 ≥ 3.0 SD. Below level 1 is level 0.

Registered draft weights at this tag, not findings: Intent I1 1, I2 2, I3 3. Capability C1 2, C2 3. Opportunity O1 1, O2 1. Hybrid H1 2, H2 3.

Any later change to cutoffs or weights must be reported separately in the backtest report. A change that appears only in code or config, and not in that report, does not count.

---

## 6. Data sources (to verify in M0)

M0 was run on 2026-10-04 from a host in FI. Verdicts below. Details in `docs/sources.md`.

| Source | Feeds | Notes / risks |
|---|---|---|
| GDELT (news database, Russian-language media included) | I1, I2, backtest | **PARTLY.** Raw GKG files work and cover 2015 onward, including 2021-01-01 to 2022-02-24 (198.47 GiB of GKG). DOC 2.0 API returned HTTP 429 for this host and is not used. No BigQuery CLI, so no dry-run. One day (2021-06-15) stream-filtered to state outlets plus a location mention of FI/EE/LV/LT/PL kept 13 rows; 100% had a page title. That hit rate is too thin, and several headlines do not name those countries, so the location tag is noisy. Do not treat one day as proof that I1 will be dense. |
| Russian state media feeds (TASS, RIA, MFA) | I1, I2 live | **PARTLY.** TASS English and RIA RSS work with a normal research user-agent. Current day only, no full text, no archive. TASS Russian returned 403 to that user-agent and is skipped (no spoofing). MFA RSS URLs were rejected. |
| Russian navigation warnings / live-fire closures | C1 | **PARTLY.** `mil.ru` times out from this host. Current Russian Petersburg and Kaliningrad warnings are on the Swedish Baltic NAVTEX page as HTML and are parseable. In-force list only. No 2021 archive found. Allied notices on that page are not stored. |
| GPS interference data (e.g. gpsjam.org) | H1 | **PARTLY.** Daily CSV is a plain GET from 2022-02-14. No data before that, so it cannot cover the backtest start. No license stated on the about page. Not used until the owner allows public use (§12). |
| Official intelligence reports (Supo, Estonian Foreign Intelligence Service, Lithuanian VSD, Danish DDIS, etc.) | C2, context | Manual reading, annual/periodic. Not tested in M0. |
| Think-tank reporting (e.g. ISW) | C2, H2 | Manual, cite source and date. Not tested in M0. |
| Official incident reports from regional governments | H2 | Manual. Not tested in M0. |

---

## 7. Rules for AI-generated text

Plain-language summaries are written by an AI model from the scored data. They must:

1. Only state what the data shows. No speculation about future events.
2. No dramatic words ("imminent", "war is coming", "alarming", "shocking").
3. Always name which layer moved and why.
4. Never claim more certainty than the data supports.
5. Say "No significant change" when nothing meaningful changed.
6. Stay under 80 words for the Depth 1 summary.
7. Never mention locations or movements of Finnish, Baltic, Polish or NATO forces.

Headline classification uses these rules:

1. "About the region" means about Finland, Estonia, Latvia, Lithuania, or Poland, on any topic.
2. Kaliningrad local or domestic news is not about the region. It is Russia, unless it involves those five countries, NATO, borders, or the military.
3. Ukraine-only or Russia-only news is not about the region, even if NATO is mentioned.
4. Judge the wording, not the topic. A neutral report on a sensitive topic is ordinary news unless the wording itself is loaded.
5. Scare quotes around the target country's own terms, such as «советская оккупация», are mild hostile framing.
6. A quote from the target country's officials is not Russian framing. A quote from Russian officials is.

A provider error is "AI unavailable", never a default label (§14.4).

The prompt for summaries lives in `prompts/summary.md` and is version-controlled. The classifier prompt is `prompts/classify_frames.md`.

---

## 8. Backtest

**Purpose:** prove the model is useful before anyone relies on it.

- **Period:** January 2021 – 24 February 2022 (the buildup before Russia's full-scale invasion of Ukraine). The region differs from ours, but the method is the same.
- **No hindsight:** for each simulated date, only use information that was published **before** that date. Manual inputs are reconstructed from dated sources only.
- **Data method:** stream-filtered raw GDELT GKG (download a file, keep matching rows, delete the zip). DOC API, RSS, and gpsjam are **not** used for the backtest. RSS has no 2021 archive. gpsjam starts 2022-02-14. DOC did not return data from this host.
- **Mostly Intent layer:** historical data for other layers is sparse. The backtest is honest about this.
- **Report:** when would the model have reached Elevated / Serious, how many weeks before 24 Feb 2022, and how many false alarms along the way.
- **Results are published in the app** (Depth 3 / About page), including weaknesses.

---

## 9. Technical architecture (Stage 1)

**Principle:** keep it simple, explainable and easy to move to a public website in Stage 2.

- **Intent source:** GKG is the primary Intent source for both the backtest and live running. RSS (TASS English, RIA) is a supplement for the current day only, not a backtest source.
- **Language:** Python 3.11+
- **Storage:** SQLite (one local file)
- **Pipeline:** Python scripts that fetch → store → score → write JSON output
- **AI:** provider set in config, chosen by validation results. Key in `.env`.
- **Frontend:** a static site (HTML + JavaScript + a chart library such as Chart.js) that reads the JSON output. Runs locally with a simple local web server. In Stage 2 the same site can be published as-is.
- **Translations:** all UI text in `frontend/i18n/en.json`. No hard-coded UI strings.
- **Config:** indicator weights, baselines and thresholds in `config/model.yaml`.

### Repo structure (proposed)
```
/
├── SPEC.md
├── README.md
├── .env.example          # template, no real keys
├── config/
│   └── model.yaml        # weights, baselines, thresholds
├── data/                 # local SQLite + raw downloads (gitignored)
├── pipeline/
│   ├── fetch/            # one module per source
│   ├── score/            # baselines, layer scores, convergence rule
│   ├── summarize/        # AI summaries
│   └── run_daily.py
├── manual/               # analyst inputs (CSV/YAML, dated, with sources)
├── backtest/
├── prompts/
│   └── summary.md
├── frontend/
│   ├── index.html
│   ├── i18n/en.json
│   └── ...
├── docs/
│   ├── sources.md        # sources, licenses, notes
│   └── methodology.md
└── tests/
```

---

## 10. Milestones

| ID | Milestone | Done when |
|---|---|---|
| **M0** | Data reality check | A short script per MVP source proves we can fetch real data. Results written to `docs/sources.md`. Failed sources get alternatives or are dropped. |
| **M1** | Narrative pipeline (Intent) | Done. See `docs/validation-report.md`. The GKG backfill finished on 2026-10-09. The service is disabled. Do not restart it. |
| **M2** | Scoring | Baselines, layer levels and convergence rule work on stored data; config-driven. |
| **M3** | Backtest | 2021–22 backtest report produced. Level thresholds tuned. |
| **M4** | Dashboard | Three depths working locally in the browser, with disclaimer, level definitions, and demo mode (§16). |
| **M5** | More sources + admin page | Remaining MVP indicators added (C1, H1). Local admin page (§13) replaces hand-edited files in `manual/`. |
| **M6** | Stage 2 prep | Scheduled updates, public hosting, legal review of disclaimer. |

---

## 11. Rules for coding sessions

1. Read this file first. Work on **one milestone at a time**.
2. Do not add features outside the current milestone. Put new ideas in §12.
3. Small commits with clear messages.
4. Never commit secrets or raw scraped data.
5. Any change to the model, scope or boundaries: update this file in the same commit.

---

## 12. Open questions / parking lot

- M5 — X as a source = a fixed WHITELIST of official accounts only, no open scanning.
  (a) Hybrid layer: defense ministries, armed forces, border guards, police, crisis channels of FI/EE/LV/LT/PL — keep ONLY incident reports involving Russia/Belarus; never store posts about own/NATO force exercises or movements.
  (b) Intent layer: Russian MFA and Russian embassies in FI/EE/LV/LT/PL.
  Each account verified via a link from the institution's official website.
  Prefer the institution's website/RSS where available; X via xAI API only, as a supplement. Check xAI API pricing and X terms first. Store post text + link only.
- Ask the gpsjam owner for permission before any public use of its data.
- Outlet-type weighting: state outlets vs state-aligned media. Not applied yet.
- Check rubaltic.ru coverage before adding it to the daily collector. It did not appear in the 2021-06-15 GKG sample.
- Re-test MFA feed occasionally; never bypass.
- Collector source availability depends on the admin's location; GDELT is the location-independent primary source.
- Final project name.
- Exact source for Russian navigation warnings (C1).
- Whether automated GPS interference data is available (H1).
- Which official preparedness pages to link per country.
- Whether Belarus gets its own indicators later.
- Additional languages (Finnish, Estonian, Latvian, Lithuanian, Polish) if the project takes off.
- How test users access the local app in Stage 1 (same machine vs. local network).
- Scaling budget for Stage 2 (decide after the test phase).
- M2: consider weekly aggregation for I2 — daily regional headline volume is low (~100/day).
- Cascade: the classifier scores every headline; the judge re-checks only headlines the classifier flagged as hostile.
- Next backfill progress log: rows kept, failures, and ETA. Not built yet. The running backfill is not to be restarted for this.

---

## 13. Admin workflow

**Principle:** the admin reviews and approves; the app does the legwork. Target: **15–20 minutes per week**, plus about 5 minutes per month for the health panel.

Until M5, manual inputs are edited by hand in `manual/` (CSV/YAML). From M5, a local admin page replaces this.

### 13.1 Weekly session
The admin page shows a short to-do list in priority order. When the list is empty, the session is done.

| Item | What the app prepares | What the admin does |
|---|---|---|
| Incident log (H2) | Candidate incidents collected from official sources of FI/EE/LV/LT/PL (border guards, defense ministries, government feeds), with an AI-drafted one-line entry | Approve ✓ / reject ✗ / edit |
| Opportunity scores (O1, O2) | 0–4 slider pre-set to last week's value + short AI note on whether a change is suggested | Confirm or move slider |
| Force posture notes (C2) | AI-drafted summary of relevant points when a new official intelligence report or major think-tank analysis appears | Approve / edit / reject |
| Level confirmation | Shown only when the model proposes Serious or Critical | Confirm or hold at lower level, with a one-line reason |
| Intent layer change | Shown only when the Intent layer rises a level: the top 5 headlines driving it, with AI frame scores | Agree / disagree |
| Escalated headlines | At most 5 per week. Judge-unsure first, then judge/classifier disagreements, newest first. Headlines that already have a human gold label are skipped | Agree / disagree, or label |

### 13.2 Monthly health panel
- Status per data source: working / degraded / broken.
- API spend this month vs. the limit.
- Classifier spot-check: 10 random classified headlines; admin clicks agree / disagree. Disagreement rate is logged over time.

### 13.3 Rules
1. **Every AI suggestion shows its source link.** No source → no suggestion. (Protects against rubber-stamping.)
2. Candidate incidents come from **official feeds**, not general web search.
3. All admin decisions are logged with date and reason (audit trail).
4. **The admin page is local only — also in Stage 2.** The public site shows published results only. Publishing happens from the admin's machine. No admin functions are ever exposed on the public site.
5. **The gold set (`validation/gold.csv`) is reused automatically** whenever the model, provider, or prompt changes. The admin does not relabel it.
6. **All admin judging happens in the one local admin page.** The M1 labeling page becomes part of that page at M5.

---

## 14. Costs and maintenance

### 14.1 Costs
| Item | Cost |
|---|---|
| GDELT, GitHub, Python libraries, local VM | Free |
| Claude API — backtest (one full run, batched) | Rough estimate: ~$5–10 per run |
| Claude API — live operation (classification + summaries) | Rough estimate: ~$1–3 per month |
| Development reruns / prompt testing | Expect 3–5× the above while building |
| Domain name | ~€10–15/year, **Stage 2 only** |
| Legal review of disclaimer | One-time, **before Stage 2 public launch** |

Estimates depend on real headline volumes (to be confirmed in M0/M1).

### 14.2 Cost rules
1. **Spend limit set in the Anthropic console before M1.** Stage 1 default: low monthly limit (e.g. $20). Raise only on purpose.
2. Use the **cheapest model that passes the classifier test** (M1 validation).
3. Use **batch processing** for non-urgent work (backtest, bulk classification).
4. Send headlines in groups per request, not one by one.
5. **Cache every classification** in the database; never classify the same headline twice.
6. Before any large run, the pipeline prints an **estimated cost** and waits for confirmation.
7. Scaling (more users, hosting, more sources) is decided only after Stage 1 shows the app is used and useful.

### 14.3 Maintenance
| When | Task | Time |
|---|---|---|
| Daily | Nothing — fetching, scoring and summaries run automatically | 0 |
| Weekly | Admin session (§13.1) | 15–20 min |
| Monthly | Health panel (§13.2) | ~5 min |
| A few times a year | Read new official intelligence reports; review model weights/thresholds | 1–2 h |

### 14.4 Honesty rules for missing or stale data
1. If a source fails, the indicator shows **"No data"** — never a zero, which would look like "calm".
2. Every manual input shows **"Last analyst update: N days ago"**.
3. If a manual layer has not been updated for **more than 14 days**, it is marked **out of date** on the public view.
4. If the overall assessment rests mostly on stale or missing data, the summary says so.
5. If an AI provider errors, the app shows **"AI unavailable"**. It never stores a default or zero classification.

---

## 15. Stage 1 test phase

**Users:** the admin + 1–3 test users (friends or colleagues, no military background preferred).

**Access:** the app runs on the admin's machine. Test users use it either on that machine or over the local network. *(Exact method to be decided at M4 — see §12.)*

**Duration:** at least 4 weeks of daily use.

**What we observe:**
- Do test users actually open it, and how often?
- Can they explain the current level and why, in their own words, after 2–5 minutes?
- Which depth do they use (summary / layers / details)?
- Does anything confuse or alarm them unnecessarily?
- Is the admin's weekly session really ≤ 20 minutes?

**Feedback:** a short check-in with each test user after week 1 and week 4 (3–5 questions). Findings go into `docs/test-phase.md` and decide whether to go to Stage 2.

---

## 16. Portfolio and low-maintenance mode

**Demo mode** replays the 2021–22 backtest from saved data. It is the default showcase. It makes no API calls.

`config/app.yaml` has `live_monitoring: off`. Off means no API calls. The app shows "paused since <date> — showing demo".

**Auto-pause** if there has been no admin session for 30 days, or if key sources have failed for 7 or more days. Free collectors may keep running. Paid calls stop.

**Money:** prepaid credits only. No paid infrastructure before Stage 2.

**Restart:** `README.md` has "Restart in 10 minutes". Dependencies are pinned in `requirements.txt`.

---

## 17. AI judge and call-human

The judge labels validation sets. The human audits about 20 headlines. The judge may stand in for gold on hostile-versus-ordinary **only if** agreement with the human is at least 85%. Until that test passes, the judge is not a gold proxy.

**Escalation.** A headline goes to the admin queue only if the judge says unsure, or the judge and the classifier disagree on hostile versus ordinary. Headlines that already have a human gold label are skipped. The weekly cap is 5, judge-unsure first, then disagreements, newest first. Overflow is stored with `decided_by = judge_no_human` and is visible on Depth 3. Every decision stores `decided_by`: `judge`, `human`, or `judge_no_human`.

**Monthly spot-check.** The judge re-checks 10 headlines. The human sees only the disagreements.

**Model change.** When the judge model changes, re-audit with about 10 human labels before trusting it again.

**Cascade.** The classifier scores every headline. The judge re-checks only headlines flagged hostile (§12).

**Judge.** The pipeline judge is Claude Sonnet 5.5 (`claude-sonnet-5-5`). Opus 5.5 (`claude-opus-5-5`) is an optional reference and is not called by the pipeline. The classifier is grok-build-0.1. See `docs/validation-report.md`. The judge may stand in for gold on hostile-versus-ordinary only if agreement with the human is at least 85%.

Non-urgent judge runs (validation, backtest) use the Batch API. The fixed rules block of the prompt is sent with prompt caching.
