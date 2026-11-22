# Budget

Date: 2026-10-10. No model calls in this note.

## ukraine-calib-20

The console balance moved from $15.01 to $14.29. That is $0.72. The tracker recorded $0.222026 for the same 21 calls (20 batches, one 1-headline retry).

The tracker is about 3.2 times low. It is not fixed for those 20 batches. The responses were not saved. Only three numbers were kept, in the journal line: input tokens, completion tokens, and cached input tokens.

Saved totals for the 21 calls:

1. Input tokens: 50,428.
2. Completion tokens: 85,799.
3. Cached input tokens: 18,496. These are a subset of the input tokens, not an extra charge.
4. Uncached input tokens: 31,932.

No stored field contains reasoning tokens, image tokens, or `cost_in_usd_ticks`. Those fields cannot be reconstructed.

## Prices

grok-build-0.1, below 200,000 prompt tokens, from the xAI pricing page (page date 2026-09-29) and the model page:

1. Input: $1.00 per million.
2. Cached input: $0.20 per million.
3. Output: $2.00 per million.
4. At 200,000 prompt tokens or more, those three rates double. These calls were about 2,500 prompt tokens, so the higher rate does not apply.
5. grok-build-0.1 has no Batch API discount. The model page says batch is not supported.
6. The client calls `https://api.x.ai/v1`. That is the global endpoint. The 1.1x United States regional premium does not apply to this config.

xAI bills four token types on a text call: input, cached input, reasoning, and completion. Reasoning has no separate published price. It is billed at the output rate. The usage object also carries `cost_in_usd_ticks`, which is the exact charge for that request after discounts. 1 USD = 10,000,000,000 ticks. The old tracker never read it.

## What the stored fields add up to

Old tracker, $1 input and $2 output, cache ignored: $0.222026. That matches the spend table.

Fixed formula on the same stored fields, with the cached rate applied: $0.207229. That is further from $0.72, not closer. The missing cache discount was not the undercount.

A 1.1x premium on the old tracker would be $0.244. That is not $0.72 either.

The gap from the old tracker to the console is $0.497974. If that gap is reasoning billed at $2 per million, and not already inside the saved completion count, it implies 248,987 reasoning tokens across the 21 calls, about 11,857 per call. That is an inference. It is not a stored count. Adding it by hand would make $0.72 only by assuming the cause. The fixed tracker does not do that, and it does not match $0.72 for these 20 batches.

## Tracker change

Future grok calls in the I2 runner record the exact ticks when the response includes them. If ticks are absent, the formula counts uncached input, cached input, completion, and reasoning tokens that are outside `completion_tokens`. The usage log line keeps those fields. The pre-call ceiling still uses visible input and output only. It cannot see reasoning tokens before the call, so it will not stop a run at the real console cost.

The 21 spend rows were not rewritten. Inventing the missing tokens would make the ledger look matched when it is not.

## Reasoning effort

Do not send a reasoning option on the classifier. It would change the model against the validated setup, and it was not used.

The official reasoning page lists `reasoning_effort` for grok-4.7, grok-4.6, and grok-4.5 only. The settings are low, medium, and high. High is the default. Reasoning cannot be turned off on those models. grok-4.6 and later also accept xhigh. grok-build-0.1 is not in that table. Its model page says reasoning is on. It does not publish a switch to lower it, and it does not publish how many reasoning tokens a lower setting would save. There is no expected price for a lower setting on this model without a call. No call was made.

## ukraine-100-finish

Date: 2026-10-10. No model call. The service was not started.

The approved cap is $4.70 of real ticks for run id ukraine-100-finish. It does not raise `config/llm.yaml` `hard_stop_usd`. The calibration factor in `config/budget.yaml` is 3.2. Estimates are the higher of the measured-token figure and the output-cap figure, times 3.2.

Pending rows, read only, stories unchanged:

1. Ukraine 100/week subset: 6,100. Already ok: 1,000. Pending: 5,100.
2. Eastern flank, existing 200/week sample: 11,987. Already ok: 11,700. Pending: 287.
3. To call: 5,387 headlines, 108 batches. No Sonnet.

Visible estimate from measured tokens: $1.156468. Visible output-cap estimate: $1.597880. Higher figure times 3.2: $5.113216. That is above $4.70, so the runner exits before the first call.

The measured figure times 3.2 is $3.700698. That is under the cap. It is not the gate. The gate is the higher figure.

The stated console balance before this decision is $14.29. Nothing in this step spent against it.

Started 2026-10-10 18:46 EEST as user unit efm-ukraine-100-finish. The assignment named the measured gate, $3.700698, which is under $4.70. The output-cap figure, $5.113216, is not the gate. The real stop is still recorded ticks, checked after each batch, so one in-flight batch can cross $4.70 and the next batch does not start. Balance noted before the first call: $14.29. llm.yaml hard_stop_usd was not raised.


The runner now stops a later run when the sum of recorded `cost_in_usd_ticks` for that run reaches the cap, and also when a response does not include ticks. A batch is not sent once that sum has reached the cap. Tests cover the tick sum, a missing tick field, and a batch that must not call.

## ukraine-100-finish finished

Date: 2026-10-11. No model call in this note. Unit efm-ukraine-100-finish is inactive. Result=success.

Every named sample row has one real grok-build-0.1 answer. Status is ok, and `hostile_framing` is stored. No named row is missing. No named row has both ok and AI unavailable.

1. Ukraine 100/week subset, `ukraine_calib_flag`: before, 1,000 ok and 5,100 pending, out of 6,100. After, 6,100 of 6,100 ok. Missing: 0.
2. Eastern flank 200/week, `stories.sampled=1`: before, 11,700 ok and 287 pending, out of 11,987. After, 11,987 of 11,987 ok. Missing: 0.
3. The other 6,083 Ukraine answers are still AI unavailable. They are outside the 100/week subset. They were not scored.

Console balance before the run: $14.29. Console balance after: $10.75. Real cost from those two readings: $3.54.

Recorded `cost_in_usd_ticks` for run id ukraine-100-finish: 35,448,122,000 ticks, which is $3.5448122, across 109 spend rows. Every one of those rows has ticks. Ukraine test: 103 rows, 33,753,902,000 ticks, $3.3753902. Eastern flank: 6 rows, 1,694,220,000 ticks, $0.169422.

The recorded ticks are $0.0048122 above the console difference. That gap was not closed by inventing tokens. llm.yaml hard_stop_usd was not raised.

## ui-translate-1

Date: 2026-11-22. Lithuanian only. Model claude-sonnet-5-5. No extended thinking: thinking type between_tools, effort low. thinking_tokens was 0 on every batch. Cache tokens were 0.

Hard cap: $0.15 real. The runner did not start a batch whose own token ceiling would cross that cap.

API usage fields, six batches:

1. Input tokens: 5,600.
2. Output tokens: 7,595.
3. Cache read and cache write: 0.
4. Thinking tokens: 0.

Price from config/llm.yaml: $2 per million input, $10 per million output. Real cost: $0.087150. The visible estimate for one language was about $0.05. The real cost is about 1.7 times that estimate. It does not match $0.05. It is under the $0.15 cap. The other four languages were not called.

Anthropic does not return cost ticks on this endpoint. The dollar figure is the usage tokens times the published rates, not a console reading. The console balance was not visible.

## ui-translate-2

Date: 2026-11-22. Finnish, Estonian, Latvian, and Polish. Lithuanian was not called. Model claude-sonnet-5-5. No extended thinking: thinking type between_tools, effort low. thinking_tokens was 0 on every batch. Cache tokens were 0.

Hard cap: $0.45 real. The runner did not start a batch whose own token ceiling would cross that cap. No retry was needed.

API usage fields, 24 batches:

1. Input tokens: 22,970.
2. Output tokens: 29,632.
3. Cache read and cache write: 0.
4. Thinking tokens: 0.

Price from config/llm.yaml: $2 per million input, $10 per million output. Real cost: $0.342260. The measured Lithuanian rate times four was $0.348600. This run is under that figure and under the $0.45 cap.

Per language, from the same usage fields:

1. Finnish: 5,744 in, 7,687 out, $0.088358.
2. Estonian: 5,744 in, 7,124 out, $0.082728.
3. Latvian: 5,744 in, 7,484 out, $0.086328.
4. Polish: 5,738 in, 7,337 out, $0.084846.

Anthropic does not return cost ticks on this endpoint. The dollar figure is the usage tokens times the published rates, not a console reading. The console balance was not visible. llm.yaml hard_stop_usd was not raised.
