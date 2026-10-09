# Validation report

This closes the M1 narrative check. It is not a claim that the GKG backfill was finished on the day of this report. The backfill later finished on 2026-10-09. The service is disabled. Do not restart that job.

Rules 7 and 8 were written from the batch 2 adjudication items. The prompt-v3 numbers below are a no-regression check on those same items, not a fresh test.

## Pilot: gold-v1 and gold-v1.1

gold-v1 is frozen. gold-v1.1 changed relevance only, by rules 1–3, with no model output used. Eighteen rows changed. Thirty-one stayed as labeled. Id 175 stayed unlabeled.

One duplicate group had conflicting human framing labels and was excluded from the hostile metric. The pilot hostile sample was about one example, so hostile-versus-ordinary agreement from that pilot is not conclusive.

## Batch 2, prompt-v2

Twenty headlines were audited. Four were Unsure and were excluded from the percentages.

Raw hostile-versus-ordinary agreement, only where both sides called the headline relevant:

- Opus 5.5: 78.6% (11 of 14)
- Sonnet 5.5: 73.3% (11 of 15)

After adjudication, using the same rules as the scoring note: "My label stands" keeps the original label; "Judge applied the rule correctly" counts only when both judges gave the same label; a judge split and "Rule is unclear" are excluded; a label that is still Unsure is excluded.

- Opus 5.5: 93.3% (14 of 15), kappa 0.86
- Sonnet 5.5: 93.3% (14 of 15), kappa 0.86

The remaining miss for both was 554074. The human kept Ordinary news. Both judges had said Hostile framing.

## Batch 2, prompt-v3 no-regression check

prompt-v3 was tagged before this run. grok-build-0.1 and Sonnet 5.5 each returned a stored answer for all 80 headlines. Missing answers would have been marked "AI unavailable". None were missing.

Against the same adjudicated reference:

- grok-build-0.1: 100% (14 of 14), beside the prompt-v2 adjudicated 93.3%
- Sonnet 5.5: 100% (15 of 15), beside the prompt-v2 raw 73.3% and adjudicated 93.3%

This is not independent evidence. Rules 7 and 8 were taken from these headlines, including the loaded-label cases and the Belarusian-official case. A perfect score here only says the new wording did not break the adjudicated set.

On all 80, where both models called the headline relevant, grok-build-0.1 and Sonnet agreed on hostile versus ordinary for 72 of 76 (94.7%). Four headlines were not both relevant.

Spend for this close-out, under a $0.20 cap: $0.0015 to store the three previously missing grok-build answers, and $0.144 for the prompt-v3 run. Total $0.146.

## Judge choice

Sonnet 5.5 is the pipeline judge. After adjudication it cleared the 85% bar, at 93.3%, the same as Opus, and it is cheaper: $2 / $10 per million tokens, against Opus at $4 / $20. Opus 5.5 stays in config as an optional reference. It is not called by the pipeline.

## Classifier choice

grok-build-0.1 is the pipeline classifier. On the saved prompt-v2 answers it agreed with Sonnet on 65 of 74 relevant headlines (87.8%). The three answers that had been dropped are now stored. On the prompt-v3 no-regression check it matched the adjudicated reference on every scored row. grok-4.3 is not the pipeline classifier.

## Known limits

- The hostile class in the audit is 4 headlines. The 85% bar is a thin test.
- Rules 7 and 8 were derived from the same items used in the prompt-v3 check. That check cannot prove the rules on new headlines.
- Two items remain "Rule is unclear" (485234, 421591). They are excluded from the percentage and are parked for a later rule fix.
- 428813 stayed "Not about region" by the human. The new models still called it hostile. That row is outside the hostile-versus-ordinary percentage.
- 480182 was not scored. The human said the judge was correct, but Opus and Sonnet had disagreed with each other.
- The GKG backfill later finished on 2026-10-09. This report did not depend on stopping it.
