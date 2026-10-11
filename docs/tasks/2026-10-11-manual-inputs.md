# Backtest manual inputs

Saved 2026-10-11 before any work on this assignment. No API calls. Commit and push after each step. Do not commit unrelated local edits.

## 0. Save this task

Save this file and commit it first.

## 1. Lock the scales

Lock the scales in manual/README.md before any draft, then tag manual-scales.

- O2. US commitment to European security. Monthly. 0 = strong visible commitment. 4 = clear signals of withdrawal or abandonment.
- O1. Availability of Russian ground forces for a new operation. Change-points only. 0 = heavily committed elsewhere. 4 = largely free.
- C2. Force posture. Event-based. Region tag: near_ukraine, belarus, kaliningrad, or western_md. Severity 0 = normal. 1 = unusual exercise. 2 = large buildup reported. 3 = buildup plus logistics signs (field hospitals, blood, fuel). 4 = forces in attack positions or official warnings of imminent attack.

## 2. Source rules

Each entry needs a source published on or before the last day of its week or month (source_date) and a link. Archived copies are allowed if the capture date also qualifies. Prefer official statements, major news outlets, and established think tanks. Never write from model memory. No source means leave empty. Empty is no data, never calm.

## 3. Draft

Draft entries for 2021-01-01 through 2022-02-24. O2 is 14 monthly rows. O1 is change-points only. C2 is events only, about 15 to 25. Target at most 50 rows total. Each row has date, value, one-line note, source_link, and source_date. Drafts go in manual/*-draft.csv.

## 4. Approval page

One entry at a time: note, value, source link, source date. Buttons Approve, Reject, and Unsure, plus an optional note. Every click saves immediately to manual/*-approved.csv. Progress counter shows reviewed over total, for example 12 / 45. Stop any old server on its port first.

## 5. Validation report

Add to docs/validation-report.md: Capability and Opportunity reconstructed from dated public sources, approved by the admin; Hybrid layer has no data before Feb 2022 (GPS data starts 2022-02-14).

## 6. Stop

Report drafts per input, any weeks or months with no source found, and the one command to open the approval page. Then stop.
