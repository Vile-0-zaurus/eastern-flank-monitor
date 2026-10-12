"""Full backtest scoring. Rules are SPEC §8.1, tag backtest-run-prereg. No model calls."""
from __future__ import annotations

from datetime import date

from pipeline.score.engine import layer_level, overall_level, week_end

# SPEC §8.1. near_ukraine is ukraine only. kaliningrad is the flank only.
C2_MAP = {
    "near_ukraine": frozenset({"ukraine_test"}),
    "kaliningrad": frozenset({"eastern_flank"}),
    "belarus": frozenset({"ukraine_test", "eastern_flank"}),
    "western_md": frozenset({"ukraine_test", "eastern_flank"}),
}
HOLD_WEEKS_AFTER = 4
RANKED_START = date(2021, 1, 4)
RANKED_END = date(2022, 2, 14)
CAL_END = date(2021, 6, 21)


def _chosen_c2(events, scoring_region: str, week: date) -> dict:
    end = week_end(week)
    chosen = {}
    for event in events:
        mapped = C2_MAP.get(event["region"])
        if not mapped or scoring_region not in mapped:
            continue
        if event["date"] > week or event["source_date"] > end:
            continue
        age = (week - event["date"]).days // 7
        if age > HOLD_WEEKS_AFTER:
            continue
        current = chosen.get(event["region"])
        if current is None or event["date"] >= current["date"]:
            chosen[event["region"]] = event
    return chosen


def c2_level(events, scoring_region: str, week: date) -> int | None:
    """Max active event that maps to this region. A later same-tag event supersedes."""
    chosen = _chosen_c2(events, scoring_region, week)
    if not chosen:
        return None
    return max(event["level"] for event in chosen.values())


def c2_note(events, scoring_region: str, week: date) -> str:
    chosen = _chosen_c2(events, scoring_region, week)
    return ";".join(f"{tag}={chosen[tag]['level']}" for tag in sorted(chosen))


def o1_level(points, week: date) -> int | None:
    """Latest change-point on or before this week. Earlier weeks are no data."""
    end = week_end(week)
    chosen = None
    for point in points:
        if point["level"] is None or point["date"] > week:
            continue
        source = point.get("source_date")
        if source is None or source > end:
            continue
        if chosen is None or point["date"] >= chosen["date"]:
            chosen = point
    if chosen is None:
        return None
    return chosen["level"]


def o2_level(months, week: date) -> int | None:
    """The month that contains Monday. An empty month does not borrow the last one."""
    month = date(week.year, week.month, 1)
    chosen = None
    for row in months:
        if row["date"] != month:
            continue
        chosen = row
    if chosen is None or chosen["level"] is None:
        return None
    source = chosen.get("source_date")
    if source is None or source > week_end(week):
        return None
    return chosen["level"]


def score_layers(intent, capability, o1, o2, weights, elevated_level=2, strong_level=3) -> dict:
    """One week. Hybrid is no data. Serious and Critical are not confirmed."""
    opportunity = layer_level({"O1": o1, "O2": o2}, weights["opportunity"])
    if capability is None:
        capability_level = None
    else:
        capability_level = layer_level({"C2": capability}, weights["capability"])
    layers = {
        "intent": intent,
        "capability": capability_level,
        "opportunity": opportunity,
        "hybrid": None,
    }
    overall = overall_level(
        layers,
        confirmed=False,
        elevated_level=elevated_level,
        strong_level=strong_level,
    )
    return {
        "intent": intent,
        "capability": capability_level,
        "opportunity": opportunity,
        "hybrid": None,
        "o1": o1,
        "o2": o2,
        "c2": capability,
        "proposed": overall.proposed,
        "shown": overall.shown,
        "shown_label": overall.shown_label,
    }


def is_ranked(row) -> bool:
    if row["partial"]:
        return False
    return RANKED_START <= row["week"] <= RANKED_END


def test_a_passes(rows) -> bool:
    """Ukraine shown level at least Elevated on one ranked week."""
    return any(
        row["region"] == "ukraine_test"
        and is_ranked(row)
        and row["shown"] is not None
        and row["shown"] >= 2
        for row in rows
    )


def test_b_passes(rows) -> bool:
    """No Serious or Critical proposal on a ranked eastern-flank week."""
    ranked = [row for row in rows if row["region"] == "eastern_flank" and is_ranked(row)]
    return all(row["proposed"] is None or row["proposed"] < 3 for row in ranked)


def _reached(row, kind: str) -> bool:
    if kind == "watchful":
        return row["shown"] is not None and row["shown"] >= 1
    if kind == "elevated":
        return row["shown"] is not None and row["shown"] >= 2
    if kind == "serious":
        return row["proposed"] is not None and row["proposed"] >= 3
    raise ValueError(kind)


def first_reach(rows, region: str, kind: str) -> date | None:
    ranked = sorted(
        (row for row in rows if row["region"] == region and is_ranked(row)),
        key=lambda row: row["week"],
    )
    for row in ranked:
        if _reached(row, kind):
            return row["week"]
    return None


def first_reach_after(rows, region: str, kind: str) -> date | None:
    ranked = sorted(
        (
            row
            for row in rows
            if row["region"] == region and is_ranked(row) and row["week"] > CAL_END
        ),
        key=lambda row: row["week"],
    )
    for row in ranked:
        if _reached(row, kind):
            return row["week"]
    return None


def _parse_day(value) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text)


def series_from_decisions(decisions) -> dict:
    from pipeline.score.manual_decisions import applied_level

    series = {"c2": [], "o1": [], "o2": []}
    for row in decisions:
        day = _parse_day(row.get("date"))
        if day is None:
            continue
        item = {
            "date": day,
            "source_date": _parse_day(row.get("source_date")),
            "level": applied_level(row),
            "region": (row.get("region") or "").strip(),
        }
        name = row.get("input")
        if name == "c2":
            if item["level"] is None or item["source_date"] is None:
                continue
            series["c2"].append(item)
        elif name == "o1":
            if item["level"] is None or item["source_date"] is None:
                continue
            series["o1"].append(item)
        elif name == "o2":
            series["o2"].append(item)
    return series


def build_rows(intent_rows, decisions, weights) -> list[dict]:
    series = series_from_decisions(decisions)
    rows = []
    for source in intent_rows:
        week = source["week"]
        region = source["region"]
        capability = c2_level(series["c2"], region, week)
        scored = score_layers(
            source["intent"],
            capability,
            o1_level(series["o1"], week),
            o2_level(series["o2"], week),
            weights,
        )
        rows.append(
            {
                "region": region,
                "week": week,
                "partial": source["partial"],
                "ranked": is_ranked({"week": week, "partial": source["partial"]}),
                "c2_note": c2_note(series["c2"], region, week),
                **scored,
            }
        )
    return rows


FIELDS = [
    "region",
    "week",
    "partial",
    "ranked",
    "intent",
    "capability",
    "opportunity",
    "hybrid",
    "o1",
    "o2",
    "c2",
    "proposed",
    "shown",
    "shown_label",
    "c2_note",
]


def _csv(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def load_intent(path) -> list[dict]:
    import csv

    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            text = (row.get("intent") or "").strip()
            rows.append(
                {
                    "region": row["region"],
                    "week": date.fromisoformat(row["week"]),
                    "partial": row["partial"] == "True",
                    "intent": None if text == "" else int(text),
                }
            )
    return rows


def write_table(path, rows) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv(row.get(key)) for key in FIELDS})


def check_rows(rows) -> None:
    if len(rows) != 122:
        raise RuntimeError(f"expected 122 weeks, got {len(rows)}")
    for region in ("ukraine_test", "eastern_flank"):
        ranked = [row for row in rows if row["region"] == region and row["ranked"]]
        if len(ranked) != 59:
            raise RuntimeError(f"{region} ranked weeks: {len(ranked)}")
    if any(row["hybrid"] is not None for row in rows):
        raise RuntimeError("hybrid was scored")
    april = [row for row in rows if row["week"] == date(2021, 4, 19)]
    earlier = [row for row in rows if row["week"] == date(2021, 4, 12)]
    if len(april) != 2 or any(row["o1"] != 3 for row in april):
        raise RuntimeError("O1 correction was not applied")
    if len(earlier) != 2 or any(row["o1"] is not None for row in earlier):
        raise RuntimeError("O1 was applied before its change-point")


def run(root) -> str:
    from pathlib import Path

    from pipeline.score.engine import load_model
    from pipeline.score.manual_decisions import load_decisions

    root = Path(root)
    intent_path = root / "docs/reports/2026-10-11-i2-weeks.csv"
    before = intent_path.read_bytes()
    config = load_model(root / "config/model.yaml")
    if config["elevated_level"] != 2 or config["strong_level"] != 3:
        raise RuntimeError("convergence levels do not match the tagged run")
    approved = [
        root / "manual/o1-ukraine-war-approved.csv",
        root / "manual/o2-us-commitment-approved.csv",
        root / "manual/c2-force-posture-approved.csv",
    ]
    raw = {path: path.read_bytes() for path in approved}
    decisions = load_decisions(approved)
    if {path: path.read_bytes() for path in approved} != raw:
        raise RuntimeError("approved files were rewritten")
    rows = build_rows(load_intent(intent_path), decisions, config["weights"])
    if intent_path.read_bytes() != before:
        raise RuntimeError("intent table was rewritten")
    check_rows(rows)
    out = root / "docs/reports/2026-10-12-backtest-weeks.csv"
    write_table(out, rows)
    return str(out)
