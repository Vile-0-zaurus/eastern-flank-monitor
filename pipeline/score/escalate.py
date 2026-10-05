"""Call-human rule. No model is called from here."""
from __future__ import annotations

WEEKLY_CAP = 5


def _yes(value: str) -> bool:
    return str(value or "").strip().lower() == "yes"


def _unsure(row: dict) -> bool:
    rel = str(row.get("relevant") or "").strip().lower()
    hostile = str(row.get("hostile_framing") or "").strip().lower()
    return rel == "unsure" or hostile == "unsure"


def hostile_or_ordinary(row: dict) -> str:
    if str(row.get("relevant") or "").strip().lower() != "yes":
        return ""
    return "hostile" if _yes(row.get("hostile_framing")) else "ordinary"


def needs_human(judge: dict, classifier: dict) -> str:
    """Return the escalation reason, or an empty string if the judge can decide."""
    if _unsure(judge):
        return "judge_unsure"
    j = hostile_or_ordinary(judge)
    c = hostile_or_ordinary(classifier)
    if j and c and j != c:
        return "hostile_disagreement"
    return ""


def assign_decisions(items: list[dict]) -> list[dict]:
    """Judge-unsure first, then disagreements, newest first. Cap is five human reviews."""
    unsure = [r for r in items if r["reason"] == "judge_unsure"]
    other = [r for r in items if r["reason"] != "judge_unsure"]
    unsure.sort(key=lambda row: (row.get("date") or "", row.get("id") or ""), reverse=True)
    other.sort(key=lambda row: (row.get("date") or "", row.get("id") or ""), reverse=True)
    ordered = unsure + other
    out = []
    for n, row in enumerate(ordered):
        decided = "human" if n < WEEKLY_CAP else "judge_no_human"
        out.append({**row, "queue_rank": n + 1, "decided_by": decided})
    return out
