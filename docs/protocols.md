# Protocols

Standing rules for every task and every session on this project. SPEC.md is the source of truth. If this file and SPEC.md disagree, SPEC.md wins, then fix this file.

## Approvals

APPROVALS: If a command waits for approval and times out, do not stop the task and do not retry in a loop. Skip that step, continue with everything that doesn't depend on it, and end the report with a 'Needs your approval' list: exact command + one-line plain-language explanation of what it does + why it's needed.

A timed-out approval is not a no. It is a skipped step. Do not rephrase the same command and run it again. Do not wait in a loop. Work that does not need that command still gets done. The report ends with the list, even if the rest of the task succeeded.
