"""Scoring skeleton. No live data and no model calls."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


def _parse_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def week_end(week_monday: date) -> date:
    """Last day of a Monday-start week."""
    return week_monday + timedelta(days=6)


def counts_for_week(row: dict, week_monday: date) -> bool:
    """A row counts for week W only if source_date is on or before Sunday."""
    source = _parse_date(row.get("source_date"))
    if source is None:
        return False
    return source <= week_end(week_monday)


def rows_for_week(rows: list[dict], week_monday: date) -> list[dict]:
    return [row for row in rows if counts_for_week(row, week_monday)]


def manual_level_for_week(rows: list[dict], week_monday: date) -> int | None:
    """Numeric manual level for one week. A late source is ignored, not zeroed."""
    levels = []
    for row in rows:
        if not counts_for_week(row, week_monday) or not _date_in_week(row, week_monday):
            continue
        level = _level(row.get("value"))
        if level is not None:
            levels.append(level)
    if not levels:
        return None
    return levels[-1]


def layer_level(levels: dict, weights: dict) -> int | None:
    """Weighted level. A missing indicator is left out, not scored as zero."""
    total = 0.0
    weight = 0.0
    for name, raw_weight in weights.items():
        level = levels.get(name)
        if level is None:
            continue
        total += level * raw_weight
        weight += raw_weight
    if weight <= 0:
        return None
    return _clamp_level(round(total / weight))


def live_layer_level(levels: dict, weights: dict, round_average: bool):
    """Live rule. round_average false keeps 1.5. It does not change the stored backtest."""
    total = 0.0
    weight = 0.0
    for name, raw_weight in weights.items():
        level = levels.get(name)
        if level is None:
            continue
        total += level * raw_weight
        weight += raw_weight
    if weight <= 0:
        return None
    value = total / weight
    if round_average:
        return _clamp_level(round(value))
    return value


def rolling_baseline(points, as_of: date, window_days: int, min_points: int):
    """Mean and sample std of the trailing window. Too few points is no data, not zero."""
    values = _trailing_values(points, as_of, window_days)
    if len(values) < max(min_points, 2):
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return (mean, math.sqrt(variance))


def rolling_baseline_mad(points, as_of: date, window_days: int, min_points: int, mad_scale: float):
    """Median and MAD scaled to an SD-equivalent. Too few points is no data, not zero."""
    values = _trailing_values(points, as_of, window_days)
    if len(values) < max(min_points, 2):
        return None
    center = _median(values)
    mad = _median([abs(value - center) for value in values])
    return (center, mad * float(mad_scale))


def _median(values) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _trailing_values(points, as_of: date, window_days: int) -> list[float]:
    start = as_of - timedelta(days=window_days)
    values = []
    for day, value in points:
        parsed = _parse_date(day)
        if parsed is None or parsed < start or parsed >= as_of:
            continue
        values.append(float(value))
    return values


def _clamp_level(level: int) -> int:
    return max(0, min(4, level))


@dataclass(frozen=True)
class Overall:
    proposed: int | None
    shown: int | None
    shown_label: str


LEVEL_NAMES = {0: "Calm", 1: "Watchful", 2: "Elevated", 3: "Serious", 4: "Critical"}


def _shown_label(proposed: int | None, shown: int | None, confirmed: bool) -> str:
    if proposed is None or shown is None:
        return "No data"
    if not confirmed and proposed >= 3:
        name = "Serious" if proposed == 3 else "Critical"
        return f"Elevated ({name} proposed, awaiting confirmation)"
    return LEVEL_NAMES[shown]


def overall_level(layers, confirmed, elevated_level, strong_level) -> Overall:
    """Convergence rule. One layer, Hybrid alone, or Opportunity alone stays at Watchful."""
    if all(level is None for level in layers.values()):
        return Overall(None, None, "No data")
    present = [level for level in layers.values() if level is not None]
    elevated = [level for level in present if level >= elevated_level]
    intent = layers.get("intent")
    capability = layers.get("capability")
    intent_strong = intent is not None and intent >= strong_level
    capability_strong = capability is not None and capability >= strong_level
    other_elevated = any(
        layers.get(name) is not None and layers[name] >= elevated_level
        for name in ("opportunity", "hybrid")
    )
    if intent_strong and capability_strong and other_elevated:
        proposed = 4
    elif len(elevated) >= 3 or (intent_strong and capability_strong):
        proposed = 3
    elif len(elevated) >= 2:
        proposed = 2
    elif any(level >= 1 for level in present):
        proposed = 1
    else:
        proposed = 0
    shown = proposed
    if proposed >= 3 and not confirmed:
        shown = 2
    return Overall(proposed, shown, _shown_label(proposed, shown, confirmed))


def level_from_z(z, thresholds) -> int | None:
    """Map a z-score to 0–4 using config thresholds. Missing z is no data."""
    if z is None:
        return None
    level = 0
    for raw_level, min_z in thresholds.items():
        if z >= float(min_z):
            level = max(level, int(raw_level))
    return _clamp_level(level)


def _level(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        number = value
    else:
        text = str(value).strip()
        if not text.lstrip("-").isdigit():
            return None
        number = int(text)
    if 0 <= number <= 4:
        return number
    return None


def indicator_level(
    value,
    points,
    as_of,
    window_days,
    min_points,
    thresholds,
    method="median_mad",
    mad_scale=1.4826,
):
    """Indicator level from the registered baseline. No baseline is no data, not zero."""
    if value is None:
        return None
    if method == "median_mad":
        base = rolling_baseline_mad(points, as_of, window_days, min_points, mad_scale)
    elif method == "mean_sd":
        base = rolling_baseline(points, as_of, window_days, min_points)
    else:
        raise ValueError(method)
    if base is None:
        return None
    center, scale = base
    if scale == 0:
        return 0 if float(value) == center else None
    return level_from_z((float(value) - center) / scale, thresholds)


def visible_incidents(rows, week_monday: date) -> list[dict]:
    """H2 rows whose own date is in the week and whose source was already public."""
    end = week_end(week_monday)
    kept = []
    for row in rows:
        day = _parse_date(row.get("date"))
        if day is None or day < week_monday or day > end:
            continue
        if counts_for_week(row, week_monday):
            kept.append(row)
    return kept


def load_model(path) -> dict:
    """Read config/model.yaml. Weights and thresholds stay in that file, not in code."""
    text = Path(path).read_text(encoding="utf-8")
    return _parse_model(text)


def _date_in_week(row: dict, week_monday: date) -> bool:
    day = _parse_date(row.get("date"))
    if day is None:
        return False
    return week_monday <= day <= week_end(week_monday)


def _parse_model(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.split("#", 1)[0].rstrip()
        if ":" not in line:
            raise ValueError(f"bad model line: {raw}")
        key, _, value = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not value.strip():
            child: dict = {}
            parent[_model_key(key)] = child
            stack.append((indent, child))
        else:
            parent[_model_key(key)] = _scalar(value)
    return root


def _model_key(key: str):
    key = key.strip()
    if key.isdigit():
        return int(key)
    return key


def _scalar(value: str):
    text = value.strip()
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text.strip("\"'")
