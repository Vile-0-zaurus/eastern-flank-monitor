"""Rules for the human gold set. No model is called from here."""
from __future__ import annotations


def counts_toward_agreement(row: dict) -> bool:
    """Unsure rows are reviewed separately and are not part of the agreement score."""
    return (row.get("unsure") or "").strip().lower() != "yes"
