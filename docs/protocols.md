# Protocols

Reusable rules for this project and for the next one. SPEC.md is the source of truth for Eastern Flank Monitor. If this file and SPEC.md disagree, SPEC.md wins, then fix this file.

## Tasks, gates, and stop

1. Save a non-trivial task in `docs/tasks/` before the first edit.
2. A written gate stays closed until the user opens it. Do not invent the steps that were cut off.
3. STOP means stop. Report and wait. Do not continue to save time.
4. Split a task so it fits the step limit. Finish a small working piece, commit it, and say what is left.
5. When the context is compressed, start a fresh session from `STATE.md`. Do not rebuild the lost middle from memory.
6. APPROVALS: If a command waits for approval and times out, do not stop the task and do not retry in a loop. Skip that step, continue with everything that doesn't depend on it, and end the report with a 'Needs your approval' list: exact command + one-line plain-language explanation of what it does + why it's needed.

A timed-out approval is not a no. It is a skipped step. Do not rephrase the same command and run it again.

## Budget

1. Do a small calibration run first. Measure the real charge. Assume the real charge runs higher than the estimate.
2. Nothing that costs money runs without an estimate, a hard cap on the real charge, and an explicit yes.
3. Stop before the cap is crossed. One in-flight batch can cross it. The next batch must not start.
4. Auto-reload, auto-pay, and subscriptions stay off on every provider.
5. One API key per project. The agent's own model key is not the project key.
6. Log every paid run in the project ledger: date, run id, model, estimate, real charge.
7. Reasoning models bill hidden tokens. A token tracker that ignores them will undercount. Read the provider's exact charge when it is present. Do not invent the missing tokens to make the ledger match.
8. Measure one language, or one batch, before scaling a translation or a scoring run. Use that measured cost as the next estimate.

## Honesty

1. Write the rules and the pass or fail bar before seeing the result. That is the sealed envelope.
2. Do not tune a rule on the test set. A change after the result is post-hoc. Label it. It does not rewrite the stored result.
3. No data is not zero. A failed call, an empty result, or a skipped item is missing.
4. Confirmed and reported stay separate. Confirmed means an official page confirmed it.
5. A missing fact beats a guessed one. If the dated page was not opened, leave the fact out.
6. Never claim more than the facts. A lenient pass is a lenient pass. A thin sample is a thin sample.

## Data

1. Every fact has a dated source link. A neighbor's official page can be the source for that shared border.
2. Never bypass a block. No VPN, no DNS change, no user-agent spoof. A research user-agent is the normal one.
3. Respect site terms, logins, and paywalls.
4. A discovery source is not a citation. A tracker may find an incident. The item still links to the page that states it.
5. Do not store allied force locations or movements. Watch the opponent's side.

## Ops

1. A long job is a background service. It logs status codes and errors. It can resume from the last good step. It pauses if failures pile up.
2. A finished backfill stays finished. Do not restart it. Do not rescore a frozen window.
3. A fixed window stays fixed. Now does not gain later weeks unless a new assignment says so.
4. This machine is a small VM. Stream big files. Do not load a large database all at once. Stop if memory runs low.
5. Suggest a VM snapshot before a risky change.
6. Commit a small working step. Push when the assignment says so.
7. After a page change, bump the `?v=` cache string, then refresh. An old query string shows the old page.

## Product

1. Validate user value with a mockup before building the UI. A rejected screen is cheaper as a sketch.
2. Watch the opponent's side. Do not build a tracker of our own forces.
3. Tell stories, not counts. A badge that merges icons into a number hides the event.
4. One reading order. The briefing does not repeat the same item in a later section.
5. One hover card. It does not cover the icon. The browser tooltip does not compete with it.
6. Simplicity is the safety rule. A working simple page comes before a feature. Every new dependency has to earn its place.

## Human role

The user approves, judges, and decides. The agent plans, builds, verifies, and reports. A proposal stays a proposal until the user says approve, go ahead, or the same meaning.
