const LAYERS = ["intent", "capability", "opportunity", "hybrid"];
const START = "2021-01-04";
const MARKERS = [
  { date: "2021-05-24", key: "marker_ryanair" },
  { date: "2021-07-26", key: "marker_lithuania" },
  { date: "2021-09-20", key: "marker_zapad" },
  { date: "2021-11-08", key: "marker_poland" },
  { date: "2022-02-07", key: "marker_allied" },
  { date: "2022-02-21", key: "marker_invasion" },
];

const state = {
  text: {},
  rows: [],
  intent: {},
  events: [],
  region: "eastern_flank",
  index: 0,
  depth: 1,
  selected: "intent",
  timer: null,
  chart: null,
};

function fill(template, values) {
  return template.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? "");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const header = rows[0];
  return rows.slice(1).filter((cells) => cells[0]).map((cells) => {
    const item = {};
    header.forEach((key, index) => {
      item[key] = cells[index] ?? "";
    });
    return item;
  });
}

function numberOrNull(value) {
  return value === "" || value === undefined || value === null ? null : Number(value);
}

function weeksForRegion() {
  return state.rows.filter((row) => row.region === state.region);
}

function current() {
  return weeksForRegion()[state.index];
}

function previous() {
  return state.index > 0 ? weeksForRegion()[state.index - 1] : null;
}

function levelName(value) {
  if (value === null) return state.text.level_none;
  return state.text["level_" + value] || state.text.level_none;
}

function levelClass(value) {
  if (value === null) return "nodata";
  return ["calm", "watchful", "elevated", "serious", "critical"][value] || "nodata";
}

function weekWords(iso) {
  const [year, month, day] = iso.split("-");
  return fill(state.text.week_of, {
    day: String(Number(day)),
    month: state.text["month_" + Number(month)],
    year,
  });
}

function joinNames(names) {
  if (names.length === 1) return names[0];
  return names.slice(0, -1).join(", ") + " " + state.text.and + " " + names[names.length - 1];
}

function versusNormal(level) {
  if (level === null) return state.text.not_available;
  if (level === 0) return state.text.near_normal;
  if (level === 1) return state.text.little_above;
  if (level === 2) return state.text.above_normal;
  return state.text.well_above;
}

function intentReading(row) {
  const extra = state.intent[row.region + "|" + row.week] || {};
  return fill(state.text.attention_line, {
    attention: versusNormal(numberOrNull(extra.i1_level)),
    share: versusNormal(numberOrNull(extra.i2_level)),
  });
}

function eventText(event) {
  return state.text[event.textKey] || "";
}

function uniqueTexts(events) {
  const seen = new Set();
  const lines = [];
  events.forEach((event) => {
    const text = eventText(event);
    if (!text || seen.has(text)) return;
    seen.add(text);
    lines.push(text);
  });
  return lines;
}

function activeEvents(week) {
  const chosen = {};
  state.events.forEach((event) => {
    if (!event.regions.includes(state.region) || event.date > week) return;
    const age = (Date.parse(week) - Date.parse(event.date)) / 86400000 / 7;
    if (age > 4) return;
    const currentEvent = chosen[event.tag];
    if (!currentEvent || event.date >= currentEvent.date) chosen[event.tag] = event;
  });
  return uniqueTexts(Object.values(chosen));
}

function subWords(prefix, value) {
  const name = state.text[prefix + "_prefix"];
  const word = value === null ? state.text.sub_missing : state.text[prefix + "_" + value];
  return fill(state.text.sub_line, { name, value: word });
}

function trendText(layer) {
  const now = numberOrNull(current()[layer]);
  const prior = previous();
  const before = prior ? numberOrNull(prior[layer]) : null;
  if (now === null || before === null) return null;
  if (now > before) return { kind: "up", text: state.text.trend_up };
  if (now < before) return { kind: "down", text: state.text.trend_down };
  return { kind: "same", text: state.text.trend_same };
}

function driverLine(row) {
  const shown = numberOrNull(row.shown);
  if (shown === null) return state.text.driven_empty;
  if (shown === 0) return state.text.driven_none;
  const threshold = shown >= 2 ? 2 : 1;
  const names = LAYERS.filter((layer) => {
    const level = numberOrNull(row[layer]);
    return level !== null && level >= threshold;
  }).map((layer) => state.text["layer_" + layer]);
  if (!names.length) return state.text.driven_none;
  return fill(state.text.driven_by, { layers: joinNames(names) });
}

function badgeText(row) {
  if (row.shown_label && row.shown_label.includes("proposed")) return row.shown_label;
  return levelName(numberOrNull(row.shown));
}

function renderStatic() {
  document.title = state.text.title;
  document.getElementById("title").textContent = state.text.title;
  document.getElementById("banner").textContent = state.text.banner;
  document.getElementById("play").textContent = state.text.play;
  document.getElementById("pause").textContent = state.text.pause;
  document.getElementById("week-name").textContent = state.text.week;
  document.getElementById("region-name").textContent = state.text.region;
  document.getElementById("disclaimer-short").textContent = state.text.disclaimer_short;
  document.getElementById("disclaimer-more").textContent = state.text.more;
  document.getElementById("disclaimer-full").textContent = state.text.disclaimer_full;
  document.querySelectorAll("[data-depth]").forEach((button) => {
    button.textContent = state.text["depth_" + button.dataset.depth];
  });
  const select = document.getElementById("region");
  select.innerHTML = "";
  ["eastern_flank", "ukraine_test"].forEach((region) => {
    const option = document.createElement("option");
    option.value = region;
    option.textContent = state.text["region_" + region];
    select.appendChild(option);
  });
  select.value = state.region;
  document.getElementById("chart-title").textContent = state.text.chart_title;
  document.getElementById("indicators-title").textContent = state.text.indicators;
  document.getElementById("sources-title").textContent = state.text.sources;
  document.getElementById("intent-source").textContent = state.text.intent_source;
  document.getElementById("events-heading").textContent = state.text.events_heading;
  document.getElementById("definitions-title").textContent = state.text.definitions;
  document.getElementById("explainers-title").textContent = state.text.explainers;
  document.getElementById("preparedness-title").textContent = state.text.preparedness;
  document.getElementById("fi-link").textContent = state.text.preparedness_fi;
  document.getElementById("preparedness-other").textContent = state.text.preparedness_other;
  const definitions = document.getElementById("definitions");
  definitions.innerHTML = "";
  for (let level = 0; level <= 4; level += 1) {
    const item = document.createElement("li");
    item.textContent = state.text["level_" + level] + ": " + state.text["def_" + level];
    definitions.appendChild(item);
  }
  const explainers = document.getElementById("explainers");
  explainers.innerHTML = "";
  ["weather", "smoke", "witnesses", "temperature", "poll", "referee", "envelope", "phone"].forEach((key) => {
    const item = document.createElement("li");
    item.textContent = state.text["explainer_" + key];
    explainers.appendChild(item);
  });
}

function renderWeek() {
  const rows = weeksForRegion();
  const row = rows[state.index];
  const slider = document.getElementById("slider");
  slider.max = String(rows.length - 1);
  slider.value = String(state.index);
  document.getElementById("week-label").textContent = weekWords(row.week);
  const badge = document.getElementById("level-badge");
  badge.textContent = badgeText(row);
  badge.className = "badge " + levelClass(numberOrNull(row.shown));
  document.getElementById("drivers").textContent = driverLine(row);
  const weekEvents = document.getElementById("week-events");
  weekEvents.innerHTML = "";
  const lines = uniqueTexts(state.events.filter((event) => event.date === row.week && event.regions.includes(state.region)));
  (lines.length ? lines : [state.text.no_new_events]).forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    weekEvents.appendChild(item);
  });
  const partial = document.getElementById("partial-note");
  partial.hidden = row.partial !== "True";
  partial.textContent = state.text.partial;
  renderCards(row);
  renderEvents(row.week);
  renderIndicators(row);
  renderChart(rows);
  document.querySelectorAll("[data-depth]").forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.depth === String(state.depth) ? "true" : "false");
  });
  document.getElementById("depth-1").hidden = state.depth !== 1;
  document.getElementById("depth-2").hidden = state.depth !== 2;
  document.getElementById("depth-3").hidden = state.depth !== 3;
}

function cardLevel(layer, row) {
  if (layer === "capability" && numberOrNull(row.capability) === null) return state.text.no_events;
  return levelName(numberOrNull(row[layer]));
}

function cardLine(layer, row) {
  if (layer === "intent") return intentReading(row);
  if (layer === "hybrid") return state.text.hybrid_line;
  if (layer === "capability") {
    const lines = activeEvents(row.week);
    return lines.length ? lines.join(" ") : state.text.no_events;
  }
  return subWords("o1", numberOrNull(row.o1)) + ". " + subWords("o2", numberOrNull(row.o2)) + ".";
}

function renderCards(row) {
  const cards = document.getElementById("cards");
  cards.innerHTML = "";
  LAYERS.forEach((layer) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "card";
    button.setAttribute("aria-pressed", layer === state.selected ? "true" : "false");
    const title = document.createElement("h3");
    title.textContent = state.text["layer_" + layer];
    const level = document.createElement("p");
    level.className = "level-word " + (layer === "capability" && numberOrNull(row.capability) === null ? "nodata" : levelClass(numberOrNull(row[layer])));
    level.textContent = cardLevel(layer, row);
    const trend = document.createElement("p");
    const movement = trendText(layer);
    if (movement) {
      const arrow = document.createElement("span");
      arrow.className = "arrow " + movement.kind;
      trend.append(arrow, document.createTextNode(movement.text));
    }
    const line = document.createElement("p");
    line.textContent = cardLine(layer, row);
    button.append(title, level, trend, line);
    button.addEventListener("click", () => {
      state.selected = layer;
      renderWeek();
    });
    cards.appendChild(button);
  });
}

function renderEvents(week) {
  const list = document.getElementById("events");
  list.innerHTML = "";
  const reached = state.events.filter((event) => event.date <= week && event.regions.includes(state.region));
  const lines = [];
  const seen = new Set();
  reached.forEach((event) => {
    const text = event.date + ": " + eventText(event);
    if (seen.has(text)) return;
    seen.add(text);
    lines.push(text);
  });
  if (!lines.length) {
    const item = document.createElement("li");
    item.textContent = state.text.events_none;
    list.appendChild(item);
    return;
  }
  lines.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  });
}

function renderIndicators(row) {
  const table = document.getElementById("indicators");
  table.innerHTML = "";
  const o1 = numberOrNull(row.o1);
  const o2 = numberOrNull(row.o2);
  const fields = [
    [state.text.layer_intent, levelName(numberOrNull(row.intent))],
    [state.text.layer_capability, numberOrNull(row.capability) === null ? state.text.no_events : levelName(numberOrNull(row.capability))],
    [state.text.layer_opportunity, levelName(numberOrNull(row.opportunity))],
    [state.text.layer_hybrid, state.text.level_none],
    [state.text.o1_prefix, o1 === null ? state.text.sub_missing : state.text["o1_" + o1]],
    [state.text.o2_prefix, o2 === null ? state.text.sub_missing : state.text["o2_" + o2]],
  ];
  fields.forEach(([name, value]) => {
    const tr = document.createElement("tr");
    const head = document.createElement("th");
    head.textContent = name;
    const cell = document.createElement("td");
    cell.textContent = value;
    tr.append(head, cell);
    table.appendChild(tr);
  });
}

function series(rows, key) {
  return rows.slice(0, state.index + 1).map((row) => numberOrNull(row[key]));
}

function monthLabel(iso) {
  const [year, month] = iso.split("-");
  return state.text["month_" + Number(month)] + " " + year;
}

const markerPlugin = {
  id: "eventMarkers",
  afterDraw(chart) {
    const labels = chart.data.labels || [];
    const area = chart.chartArea;
    if (!area) return;
    const ctx = chart.ctx;
    MARKERS.forEach((marker, index) => {
      const at = labels.indexOf(marker.date);
      if (at < 0) return;
      const x = chart.scales.x.getPixelForValue(at);
      ctx.save();
      ctx.strokeStyle = "#57534e";
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, area.top);
      ctx.lineTo(x, area.bottom);
      ctx.stroke();
      ctx.fillStyle = "#44403c";
      ctx.font = "11px Georgia, serif";
      ctx.textAlign = x > area.right - 90 ? "right" : "left";
      ctx.fillText(state.text[marker.key], x > area.right - 90 ? x - 4 : x + 4, area.top + 12 + (index % 3) * 12);
      ctx.restore();
    });
  },
};

function renderChart(rows) {
  const visible = rows.slice(0, state.index + 1);
  const labels = visible.map((row) => row.week);
  const datasets = [
    ["chart_intent", "intent", "#14532d"],
    ["chart_capability", "capability", "#1f4e79"],
    ["chart_opportunity", "opportunity", "#9a3412"],
    ["chart_overall", "shown", "#111827"],
  ].map(([key, field, color]) => ({
    label: state.text[key],
    data: series(rows, field),
    borderColor: color,
    backgroundColor: color,
    spanGaps: false,
    pointRadius: 0,
    tension: 0,
  }));
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    layout: { padding: { top: 36 } },
    plugins: { legend: { position: "top" } },
    scales: {
      y: { min: 0, max: 4, ticks: { stepSize: 1 } },
      x: {
        ticks: {
          maxTicksLimit: 14,
          maxRotation: 0,
          callback(value) {
            return monthLabel(this.getLabelForValue(value));
          },
        },
      },
    },
  };
  if (state.chart) {
    state.chart.data.labels = labels;
    state.chart.data.datasets = datasets;
    state.chart.update();
    return;
  }
  state.chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: { labels, datasets },
    options,
    plugins: [markerPlugin],
  });
}

function stop() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
}

function play() {
  stop();
  state.timer = setInterval(() => {
    if (state.index >= weeksForRegion().length - 1) {
      stop();
      return;
    }
    state.index += 1;
    renderWeek();
  }, 1200);
}

async function main() {
  const [text, csv, intentCsv, events] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch("../docs/reports/2026-10-11-i2-weeks.csv").then((response) => response.text()),
    fetch("events.json").then((response) => response.json()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
  parseCsv(intentCsv).forEach((row) => {
    state.intent[row.region + "|" + row.week] = row;
  });
  state.events = events;
  const params = new URLSearchParams(location.search);
  if (params.get("region")) state.region = params.get("region");
  if (params.get("depth")) state.depth = Number(params.get("depth"));
  renderStatic();
  if (params.get("week")) {
    const found = weeksForRegion().findIndex((row) => row.week === params.get("week"));
    if (found >= 0) state.index = found;
  }
  renderWeek();
  document.getElementById("play").addEventListener("click", play);
  document.getElementById("pause").addEventListener("click", stop);
  document.getElementById("slider").addEventListener("input", (event) => {
    stop();
    state.index = Number(event.target.value);
    renderWeek();
  });
  document.getElementById("region").addEventListener("change", (event) => {
    const week = current().week;
    state.region = event.target.value;
    const found = weeksForRegion().findIndex((row) => row.week === week);
    state.index = found >= 0 ? found : 0;
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
    renderWeek();
  });
  document.querySelectorAll("[data-depth]").forEach((button) => {
    button.addEventListener("click", () => {
      state.depth = Number(button.dataset.depth);
      renderWeek();
    });
  });
}

main();
