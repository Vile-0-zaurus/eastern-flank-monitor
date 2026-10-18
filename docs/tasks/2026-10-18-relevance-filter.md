# Relevance filter round

Saved 2026-10-18 before any other work on this assignment.

No API calls. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data.

1. In news, officials, and Inside Russia, show only items whose original is Russian or English. Drop Sputnik foreign-language services, including Portuguese, Spanish, and Turkish.
2. Officials and news must mention Finland, Estonia, Latvia, Lithuania, Poland, the Baltics, Belarus, Kaliningrad, Ukraine, NATO, or a border, military, exercise, or sanctions term, in Russian or English. Otherwise do not show them. Examples to hide: Ecuador, the Taliban, China cyber, the WTO.
3. Russian officials only if the speaker is Russian: Putin, the Kremlin, Peskov, Lavrov, Zakharova, Shoigu, the Defence Ministry, the Duma, senators, or the Federation Council. Regional and Western only if the speaker is from Finland, Estonia, Latvia, Lithuania, Poland, NATO, the EU, or the United States. If the speaker is unclear, leave the item out.
4. Inside Russia examples: pick the most relevant headline, one that mentions exercises, deployments, borders, the region, Belarus, Ukraine, or NATO. Never a trivial item such as waste sorting or wildfires. If none is relevant, show the count only. Add the note: "Counts measure news volume, not military preparation."
5. Self-test: no non-Russian or non-English items, no item that fails the relevance rule, and side assignment checked against the speaker list. Commit, push, stop.
