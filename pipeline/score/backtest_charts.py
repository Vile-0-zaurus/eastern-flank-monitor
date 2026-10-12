"""Charts for the tagged backtest table. Does not rescore."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from pipeline.score.backtest_run import C2_MAP
from pipeline.score.manual_decisions import applied_level, load_decisions

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "docs" / "reports" / "2026-10-12-backtest-weeks.csv"
CHARTS = ROOT / "docs" / "charts"
INVASION = date(2022, 2, 24)
APPROVED = [
    ROOT / "manual" / "o1-ukraine-war-approved.csv",
    ROOT / "manual" / "o2-us-commitment-approved.csv",
    ROOT / "manual" / "c2-force-posture-approved.csv",
]


def load_table(path=TABLE) -> dict[str, list[dict]]:
    import csv

    by_region: dict[str, list[dict]] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed = {
                "week": date.fromisoformat(row["week"]),
                "partial": row["partial"] == "True",
                "shown_label": row["shown_label"],
            }
            for key in ("intent", "capability", "opportunity", "hybrid", "shown"):
                parsed[key] = None if row[key] == "" else int(row[key])
            by_region.setdefault(row["region"], []).append(parsed)
    return by_region


def event_labels(region: str, decisions=None) -> dict[date, str]:
    if decisions is None:
        decisions = load_decisions(APPROVED)
    grouped: dict[date, list[str]] = {}
    for row in decisions:
        if row.get("input") != "c2":
            continue
        tag = (row.get("region") or "").strip()
        mapped = C2_MAP.get(tag)
        if not mapped or region not in mapped:
            continue
        level = applied_level(row)
        text = (row.get("date") or "").strip()
        if level is None or not text:
            continue
        grouped.setdefault(date.fromisoformat(text), []).append(f"{tag} {level}")
    return {day: ", ".join(parts) for day, parts in grouped.items()}


def _plot_tail(axis, weeks, values, partial, **style) -> None:
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


def _wrap_caption(caption: str, width: int = 118) -> str:
    parts = caption.split("; ")
    lines = []
    current = ""
    for part in parts:
        piece = part if not current else "; " + part
        if current and len(current) + len(piece) > width:
            lines.append(current)
            current = part
        else:
            current = (current + piece) if current else part
    if current:
        lines.append(current)
    return "\n".join(lines)


def chart(region: str, rows: list[dict], labels: dict[date, str], path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    weeks = [row["week"] for row in rows]
    partial = bool(rows[-1]["partial"]) if rows else False
    fig, axes = plt.subplots(5, 1, figsize=(11, 13), sharex=True)
    panels = [
        ("Intent", "intent", "#14532d"),
        ("Capability", "capability", "#1f4e79"),
        ("Opportunity", "opportunity", "#9a3412"),
        ("Hybrid", "hybrid", "#6b7280"),
        ("Overall shown", "shown", "#111827"),
    ]
    for axis, (name, key, color) in zip(axes, panels):
        _plot_tail(
            axis,
            weeks,
            [row[key] for row in rows],
            partial,
            color=color,
            linewidth=1.4,
            marker="o",
            markersize=2.4,
        )
        axis.set_ylabel(name)
        axis.set_ylim(-0.25, 4.35)
        axis.set_yticks([0, 1, 2, 3, 4])
        axis.axvspan(date(2021, 1, 1), date(2021, 6, 30), color="#d6d3d1", alpha=0.35, zorder=0)
        axis.axvline(INVASION, color="#111827", linewidth=1.0)
        axis.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    axes[0].annotate(
        "Invasion",
        xy=(INVASION, 1.08),
        xycoords=("data", "axes fraction"),
        ha="right",
        va="bottom",
        fontsize=6.5,
        color="#111827",
        annotation_clip=False,
    )
    for day in sorted(labels):
        axes[1].axvline(day, color="#1f4e79", linewidth=0.5, alpha=0.45)
    caption = "C2 events: " + "; ".join(
        f"{day.isoformat()} {text}" for day, text in sorted(labels.items())
    )
    if not labels:
        caption = "C2 events: none"
    axes[3].text(0.01, 0.62, "no data", transform=axes[3].transAxes, fontsize=8, color="#6b7280")
    proposed = [
        row["week"]
        for row in rows
        if "proposed" in row["shown_label"]
    ]
    if proposed:
        axes[4].scatter(proposed, [2] * len(proposed), s=18, facecolors="none", edgecolors="#9a3412", zorder=3)
        axes[4].text(0.01, 0.78, "open marker: Serious or Critical proposed", transform=axes[4].transAxes, fontsize=7, color="#9a3412")
    if partial:
        axes[0].annotate(
            "partial week",
            xy=(weeks[-1], 0.02),
            xycoords=("data", "axes fraction"),
            ha="right",
            va="bottom",
            fontsize=6.5,
        )
    axes[4].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    title = "Eastern flank" if region == "eastern_flank" else "Ukraine test"
    fig.suptitle(f"{title}: weekly layers and overall  |  backtest-run-prereg")
    fig.tight_layout()
    fig.subplots_adjust(top=0.94, bottom=0.11)
    fig.text(0.01, 0.01, _wrap_caption(caption), fontsize=6.5, color="#1f4e79", ha="left", va="bottom")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def draw_charts() -> list[str]:
    table = load_table()
    paths = []
    for region, rows in table.items():
        path = CHARTS / f"{region}-backtest.png"
        chart(region, rows, event_labels(region), path)
        paths.append(str(path))
    return paths
