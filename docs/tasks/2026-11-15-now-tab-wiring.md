# Now tab wiring

Saved 2026-11-15 before any other work on this assignment.

No API calls. Never bypass blocks: no VPN, no DNS changes, no user-agent spoofing. Do not rescore the stored week table. Do not restart the 2021-22 backfill. Commit and push after each section. If low on steps, stop at a committed point and say what is left.

## Section 1 — diagnose, report first

1. Why does the Poland chip show 134 stories while the dossier says "No news about Poland"? Check: does the Now dossier read data/now/gkg-now.sqlite? Are Now headlines hidden for lack of an English line? Report counts per country per week: stored / relevant / with English / shown.

## Section 2 — fill the Now tab

2. Translate yourself (no API) the Russian Now headlines that will be shown: per country per week, the top 5 relevant (hostile-flagged first if available, else most region-specific). Store the English lines.
3. New dossier section "Regional media" (Yle, BBC — already English): per country per week, up to 3 relevant stories, source link. Label "Regional media (Yle, BBC)".
4. Incidents: all 11 on the map as dots with type icons, active from their date; dossier section "Incidents this week" (and "Recent incidents" for the last 8 weeks), each with its "Officially confirmed" / "Reported" label + source link. Region overview lists incidents first.
5. Now mode never reads replay data: remove "Last notable: 241 weeks ago…"; quiet week → last notable item WITHIN the Now window, or "Quiet week."
6. Remove placeholder sentences ("not in a separate file", "listed under the map…"). Officials section in Now: Russian officials from Now headlines naming Putin/Kremlin/Peskov/Lavrov/Zakharova/Shoigu/MoD/Duma (English first); regional officials from the incident sources. Empty → hide the section.
7. Banner: "Snapshot: 3 Aug – 25 Oct 2026 · attention and incidents only."

## Section 3 — replay fix

8. Relevance leak: "CDU leader… Afghanistan… NATO's biggest fiasco" must not appear (off-topic; German speaker isn't regional/Western-officials scope unless about the region). Tighten the rule: Western officials only from FI/EE/LV/LT/PL, NATO, EU, US, and only on region-relevant topics. Add a self-test case.
9. Self-test: in Now mode, every country with stories > 0 shows at least one item; every incident appears on the map and in the dossier; no replay data in Now mode. Video ~/Desktop/efm-now2.mp4 (30 s). Commit, push, STOP.
