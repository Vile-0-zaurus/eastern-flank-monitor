"""First Intent scoring run from stored answers. No model calls.

Uses scoring-prereg-v2 as tagged in SPEC §5.6: median and MAD times 1.4826,
cutoffs from config/model.yaml, baseline weeks fully inside 2021-01-01..2021-06-30.
A week with fewer than 7 in-window days is partial and is not ranked.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from pipeline.score.engine import layer_level, level_from_z, load_model
from pipeline.score.i1 import OUT, week_monday, weekly_summary, read_stored
from pipeline.score.i2_sample import hostile_yes, wilson_interval

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "indicators" / "i2-sample.sqlite"
ANSWERS = ROOT / "data" / "llm" / "i2-answers.sqlite"
CHARTS = ROOT / "docs" / "charts"
WEEKS_CSV = ROOT / "docs" / "reports" / "2026-10-11-i2-weeks.csv"
MODEL = ROOT / "config" / "model.yaml"

CAL_START = date(2021, 1, 1)
CAL_END = date(2021, 6, 30)
WINDOW_END = date(2022, 2, 24)
INVASION = date(2022, 2, 24)
PRECISION_YES = 123
PRECISION_NO = 71
IDS = {"eastern_flank": "I2", "ukraine_test": "I2_ukraine_test"}
I1_IDS = {"eastern_flank": "I1", "ukraine_test": "I1_ukraine_test"}
CAPS = {"eastern_flank": 200, "ukraine_test": 100}


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def fit_baseline(values: list[float], mad_scale: float) -> tuple[float, float]:
    center = _median(values)
    mad = _median([abs(value - center) for value in values])
    return center, mad * mad_scale


def score_value(value: float | None, center: float, scale: float, thresholds: dict) -> int | None:
    if value is None:
        return None
    if scale == 0:
        return 0 if float(value) == center else None
    return level_from_z((float(value) - center) / scale, thresholds)


def in_window_days(monday: date) -> int:
    start = max(monday, CAL_START)
    end = min(monday + timedelta(days=6), WINDOW_END)
    if end < start:
        return 0
    return (end - start).days + 1


def fully_inside_calibration(monday: date) -> bool:
    return monday >= CAL_START and monday + timedelta(days=6) <= CAL_END


def load_i2(region: str) -> list[dict]:
    con = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    con.execute(f"ATTACH DATABASE 'file:{ANSWERS}?mode=ro' AS ans")
    if region == "ukraine_test":
        sql = """
        SELECT s.sample_id, s.week, s.day, s.title, a.status, a.result_json
        FROM ukraine_calib_100 s
        JOIN ans.answers a
          ON a.sample_id = CAST(s.sample_id AS TEXT) AND a.model = 'grok-build-0.1'
        """
    else:
        sql = """
        SELECT s.rowid, s.week, s.day, s.title, a.status, a.result_json
        FROM stories s
        JOIN ans.answers a
          ON a.sample_id = CAST(s.rowid AS TEXT) AND a.model = 'grok-build-0.1'
        WHERE s.region = 'eastern_flank' AND s.sampled = 1
        """
    rows = []
    for sample_id, week, day, title, status, blob in con.execute(sql):
        parsed = json.loads(blob)
        parsed["sample_id"] = str(sample_id)
        parsed["region"] = region
        parsed["week"] = week
        parsed["day"] = day
        parsed["title"] = title
        parsed["status"] = status
        rows.append(parsed)
    con.close()
    return rows


def weekly_i2(rows: list[dict], region: str, precision: float | None) -> list[dict]:
    buckets: dict[str, dict] = {}
    for row in rows:
        bucket = buckets.setdefault(
            row["week"],
            {
                "region": region,
                "week": row["week"],
                "hostile": 0,
                "n": 0,
                "missing": 0,
                "frames": {name: 0 for name in ("F1", "F2", "F3", "F4", "F5", "F6", "F7_other")},
                "titles": [],
            },
        )
        flag = hostile_yes(row)
        if flag is None:
            bucket["missing"] += 1
            continue
        bucket["n"] += 1
        if flag:
            bucket["hostile"] += 1
            for name in bucket["frames"]:
                try:
                    if int(row.get(name) or 0) > 0:
                        bucket["frames"][name] += 1
                except (TypeError, ValueError):
                    continue
            if len(bucket["titles"]) < 3:
                bucket["titles"].append(row.get("title") or "")
    out = []
    for week in sorted(buckets):
        bucket = buckets[week]
        interval = wilson_interval(bucket["hostile"], bucket["n"])
        monday = date.fromisoformat(week)
        bucket["days"] = in_window_days(monday)
        bucket["partial"] = bucket["days"] != 7
        bucket["short"] = (not bucket["partial"]) and bucket["n"] < CAPS[region]
        if interval is None:
            bucket["value"] = bucket["low"] = bucket["high"] = None
            bucket["corrected"] = None
        else:
            bucket["value"], bucket["low"], bucket["high"] = interval
            bucket["corrected"] = None if precision is None else bucket["value"] * precision
        out.append(bucket)
    return out


def weekly_i1(indicator: str) -> dict[str, dict]:
    rows = weekly_summary(read_stored(OUT, indicator))
    return {row["week"]: row for row in rows}


def build(region: str, precision: float | None, config: dict) -> list[dict]:
    i2 = weekly_i2(load_i2(region), region, precision)
    i1 = weekly_i1(I1_IDS[region])
    thresholds = config["z_levels"]
    scale = float(config["mad_scale"])
    weights = config["weights"]["intent"]
    cal_i1 = []
    cal_i2 = []
    for row in i2:
        monday = date.fromisoformat(row["week"])
        i1_row = i1.get(row["week"])
        row["i1"] = None if i1_row is None else i1_row["value"]
        row["i1_days"] = None if i1_row is None else i1_row["days"]
        row["i1_numerator"] = None if i1_row is None else i1_row["numerator"]
        row["i1_denominator"] = None if i1_row is None else i1_row["denominator"]
        if i1_row and i1_row["partial"]:
            row["partial"] = True
        if fully_inside_calibration(monday) and not row["partial"]:
            if row["i1"] is not None:
                cal_i1.append(row["i1"])
            if row["value"] is not None:
                cal_i2.append(row["value"])
    i1_center, i1_scale = fit_baseline(cal_i1, scale)
    i2_center, i2_scale = fit_baseline(cal_i2, scale)
    for row in i2:
        if row["partial"]:
            row["i1_level"] = None
            row["i2_level"] = None
            row["intent"] = None
            continue
        row["i1_level"] = score_value(row["i1"], i1_center, i1_scale, thresholds)
        row["i2_level"] = score_value(row["value"], i2_center, i2_scale, thresholds)
        row["intent"] = layer_level(
            {"I1": row["i1_level"], "I2": row["i2_level"], "I3": None},
            weights,
        )
    i2[0]["baseline"] = {
        "i1_n": len(cal_i1),
        "i1_center": i1_center,
        "i1_scale": i1_scale,
        "i2_n": len(cal_i2),
        "i2_center": i2_center,
        "i2_scale": i2_scale,
        "precision": precision,
    }
    return i2


def store_i2(series: dict[str, list[dict]]) -> None:
    con = sqlite3.connect(OUT)
    cols = {row[1] for row in con.execute("PRAGMA table_info(indicators)")}
    if "ci_low" not in cols:
        con.execute("ALTER TABLE indicators ADD COLUMN ci_low REAL")
        con.execute("ALTER TABLE indicators ADD COLUMN ci_high REAL")
    before = {
        name: con.execute("SELECT COUNT(*) FROM indicators WHERE indicator=?", (name,)).fetchone()[0]
        for name in ("I1", "I1_ukraine_test")
    }
    for name in IDS.values():
        con.execute("DELETE FROM indicators WHERE indicator=?", (name,))
    for region, rows in series.items():
        for row in rows:
            con.execute(
                """
                INSERT INTO indicators
                (indicator, day, numerator, denominator, value, ci_low, ci_high)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    IDS[region],
                    row["week"],
                    None if row["value"] is None else row["hostile"],
                    None if row["value"] is None else row["n"],
                    row["value"],
                    row["low"],
                    row["high"],
                ),
            )
    con.commit()
    after = {
        name: con.execute("SELECT COUNT(*) FROM indicators WHERE indicator=?", (name,)).fetchone()[0]
        for name in ("I1", "I1_ukraine_test", "I2", "I2_ukraine_test")
    }
    con.close()
    if after["I1"] != before["I1"] or after["I1_ukraine_test"] != before["I1_ukraine_test"]:
        raise SystemExit(f"I1 rows changed: {before} -> {after}")
    print("STORED", after)


def write_csv(series: dict[str, list[dict]]) -> None:
    WEEKS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "region", "week", "partial", "short", "days",
        "i1", "i1_numerator", "i1_denominator", "i1_level",
        "hostile", "n", "missing", "value", "low", "high", "corrected", "i2_level",
        "intent",
    ]
    with WEEKS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rows in series.values():
            writer.writerows(rows)


def _num(value) -> float | None:
    if value in ("", "None", None):
        return None
    return float(value)


def _annotate(axis) -> None:
    """Event labels are notes. They do not change a score."""
    spans = [
        (date(2021, 3, 1), date(2021, 4, 30), "#b45309", "Spring buildup near Ukraine", 1.02),
        (date(2021, 7, 1), date(2021, 7, 31), "#0369a1", "Lithuania border crisis", 1.02),
        (date(2021, 11, 1), date(2021, 11, 30), "#7c3aed", "Poland border crisis", 1.02),
    ]
    for start, end, color, label, height in spans:
        axis.axvspan(start, end, color=color, alpha=0.12, zorder=0)
        axis.annotate(
            label,
            xy=(start, height),
            xycoords=("data", "axes fraction"),
            ha="left",
            va="bottom",
            fontsize=6.5,
            color=color,
            annotation_clip=False,
        )
    axis.axvline(date(2021, 5, 23), color="#b45309", linewidth=0.8, linestyle=":")
    axis.annotate(
        "Ryanair/Minsk",
        xy=(date(2021, 5, 23), 1.10),
        xycoords=("data", "axes fraction"),
        ha="center",
        va="bottom",
        fontsize=6.5,
        color="#b45309",
        annotation_clip=False,
    )


def _plot_tail(axis, weeks: list[date], values: list[float | None], partial: bool, **style) -> None:
    solid_weeks = weeks[:-1] if partial and len(weeks) > 1 else weeks
    solid_values = values[:-1] if partial and len(values) > 1 else values
    axis.plot(solid_weeks, solid_values, **style)
    if partial and len(weeks) > 1:
        axis.plot(
            weeks[-2:],
            values[-2:],
            color=style.get("color", "#111827"),
            linewidth=style.get("linewidth", 1.2),
            linestyle=":",
        )


def chart(region: str, rows: list[dict], precision: float | None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    CHARTS.mkdir(parents=True, exist_ok=True)
    weeks = [date.fromisoformat(str(row["week"])) for row in rows]
    partial = bool(rows[-1].get("partial")) if rows else False
    fig, axes = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
    _plot_tail(axes[0], weeks, [_num(row.get("i1")) for row in rows], partial, color="#1f4e79", linewidth=1.4)
    axes[0].set_ylabel("I1 share")
    _plot_tail(
        axes[1],
        weeks,
        [_num(row.get("value")) for row in rows],
        partial,
        color="#9a3412",
        linewidth=1.4,
        label="raw",
    )
    low = [_num(row.get("low")) for row in rows]
    high = [_num(row.get("high")) for row in rows]
    axes[1].fill_between(weeks, low, high, color="#9a3412", alpha=0.18, label="95% Wilson")
    if precision is not None:
        _plot_tail(
            axes[1],
            weeks,
            [_num(row.get("corrected")) for row in rows],
            partial,
            color="#9a3412",
            linewidth=1.2,
            linestyle="--",
            label="precision-corrected",
        )
        axes[1].legend(frameon=False, fontsize=8, loc="upper left")
    else:
        axes[1].text(0.01, 0.90, "precision not measured", transform=axes[1].transAxes, fontsize=8)
    axes[1].set_ylabel("I2 hostile share")
    intent = [_num(row.get("intent")) for row in rows]
    _plot_tail(axes[2], weeks, intent, False, color="#14532d", linewidth=1.4, marker="o", markersize=2.5)
    axes[2].set_ylabel("Intent level")
    axes[2].set_ylim(-0.2, 4.2)
    axes[2].set_yticks([0, 1, 2, 3, 4])
    counts = [_num(row.get("hostile")) for row in rows]
    _plot_tail(axes[3], weeks, counts, partial, color="#1f2937", linewidth=1.4)
    axes[3].set_ylabel("Hostile count")
    for axis in axes:
        axis.axvspan(CAL_START, CAL_END, color="#d6d3d1", alpha=0.35, zorder=0)
        axis.axvline(INVASION, color="#111827", linewidth=1.0)
        axis.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    _annotate(axes[0])
    axes[0].annotate(
        "Invasion",
        xy=(INVASION, 1.10),
        xycoords=("data", "axes fraction"),
        ha="right",
        va="bottom",
        fontsize=6.5,
        color="#111827",
        annotation_clip=False,
    )
    if partial:
        axes[0].annotate(
            "partial week",
            xy=(weeks[-1], 0.02),
            xycoords=("data", "axes fraction"),
            ha="right",
            va="bottom",
            fontsize=6.5,
            color="#111827",
        )
        axes[2].annotate(
            "not ranked",
            xy=(weeks[-1], 0.05),
            ha="right",
            va="bottom",
            fontsize=6.5,
            color="#111827",
        )
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    title = "Eastern flank" if region == "eastern_flank" else "Ukraine test"
    fig.suptitle(f"{title}: weekly I1, I2, Intent, hostile count  |  scoring-prereg-v2")
    fig.tight_layout()
    fig.subplots_adjust(top=0.86)
    path = CHARTS / f"{region}-intent.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def redraw_charts() -> list[str]:
    """Redraw from the checked week table. Does not open the indicator database."""
    by_region: dict[str, list[dict]] = {}
    with WEEKS_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["partial"] = row["partial"] == "True"
            by_region.setdefault(row["region"], []).append(row)
    paths = []
    for region, rows in by_region.items():
        precision = 123 / 194 if region == "eastern_flank" else None
        paths.append(str(chart(region, rows, precision)))
    return paths


def first_reach(rows: list[dict], level: int) -> str | None:
    for row in rows:
        if row["partial"] or row["intent"] is None:
            continue
        if row["intent"] >= level:
            return row["week"]
    return None


def weeks_before(week: str | None) -> str:
    if week is None:
        return "never"
    monday = date.fromisoformat(week)
    days = (INVASION - monday).days
    return f"{days} days ({days / 7:.2f} weeks) before 2022-02-24"


def main() -> None:
    config = load_model(MODEL)
    precision = PRECISION_YES / (PRECISION_YES + PRECISION_NO)
    series = {
        "eastern_flank": build("eastern_flank", precision, config),
        "ukraine_test": build("ukraine_test", None, config),
    }
    store_i2(series)
    write_csv(series)
    paths = [str(chart(region, rows, series[region][0]["baseline"]["precision"])) for region, rows in series.items()]
    summary = {"charts": paths, "precision": precision, "regions": {}}
    for region, rows in series.items():
        base = rows[0]["baseline"]
        alarms = [
            {
                "week": row["week"],
                "intent": row["intent"],
                "i1": row["i1"],
                "i1_level": row["i1_level"],
                "i2": row["value"],
                "i2_level": row["i2_level"],
                "hostile": row["hostile"],
                "n": row["n"],
                "frames": row["frames"],
                "titles": row["titles"],
            }
            for row in rows
            if not row["partial"] and row["intent"] is not None and row["intent"] >= 2
        ]
        summary["regions"][region] = {
            "weeks": len(rows),
            "partial": [row["week"] for row in rows if row["partial"]],
            "short": [row["week"] for row in rows if row["short"]],
            "missing": sum(row["missing"] for row in rows),
            "baseline": base,
            "first": {str(level): first_reach(rows, level) for level in (1, 2, 3, 4)},
            "before": {str(level): weeks_before(first_reach(rows, level)) for level in (1, 2, 3, 4)},
            "alarms": alarms,
            "max_intent": max((row["intent"] or 0) for row in rows if not row["partial"]),
        }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
