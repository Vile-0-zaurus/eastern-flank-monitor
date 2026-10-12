const LAYERS = ["intent", "capability", "opportunity", "hybrid"];
const START = "2021-01-04";
const INVASION_WEEK = "2022-02-21";

const state = {
  text: {},
  rows: [],
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

function levelName(value) {
  if (value === null || value === "") return state.text.level_none;
  return state.text["level_" + value] || state.text.level_none;
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

function weeksForRegion() {
  return state.rows.filter((row) => row.region === state.region);
}

function current() {
  return weeksForRegion()[state.index];
}

function previous() {
  const rows = weeksForRegion();
  return state.index > 0 ? rows[state.index - 1] : null;
}

function numberOrNull(value) {
  return value === "" || value === undefined ? null : Number(value);
}

function changedSentence(before, after, layer) {
  const name = state.text["layer_" + layer];
  if (before === null && after === null) return "";
  if (before === null) return fill(state.text.moved, { layer: name, before: state.text.level_none, after: levelName(after) });
  if (after === null) return fill(state.text.nodata_layer, { layer: name });
  if (before === after) return "";
  return fill(state.text.moved, { layer: name, before: levelName(before), after: levelName(after) });
}

function summary(row, prior) {
  const sentences = [fill(state.text.shown_is, { label: row.shown_label || levelName(numberOrNull(row.shown)) })];
  if (!prior) {
    sentences.push(state.text.no_change);
  } else {
    const changes = LAYERS.map((layer) => changedSentence(
      numberOrNull(prior[layer]),
      numberOrNull(row[layer]),
      layer,
    )).filter(Boolean);
    sentences.push(changes.length ? changes.join("; ") + "." : state.text.no_change);
  }
  const empty = LAYERS.filter((layer) => numberOrNull(row[layer]) === null).map((layer) => state.text["layer_" + layer]);
  if (empty.length) {
    sentences.push(empty.map((layer) => fill(state.text.nodata_layer, { layer })).join(" "));
  }
  return sentences.slice(0, 3).join(" ");
}

function trend(layer) {
  const now = numberOrNull(current()[layer]);
  const prior = previous();
  const before = prior ? numberOrNull(prior[layer]) : null;
  if (now === null) return state.text.trend_none;
  if (before === null) return state.text.trend_new;
  if (now > before) return state.text.trend_up;
  if (now < before) return state.text.trend_down;
  return state.text.trend_same;
}

function explanation(layer, row) {
  if (layer === "intent") return state.text.explain_intent;
  if (layer === "hybrid") return state.text.explain_hybrid;
  if (layer === "capability") {
    return row.c2_note
      ? fill(state.text.explain_capability, { note: row.c2_note })
      : state.text.explain_capability_empty;
  }
  const o1 = numberOrNull(row.o1);
  const o2 = numberOrNull(row.o2);
  if (o1 === null && o2 === null) return state.text.explain_opportunity_empty;
  if (o1 !== null && o2 !== null) {
    return fill(state.text.explain_opportunity, { o1: levelName(o1), o2: levelName(o2) });
  }
  const name = o1 === null ? state.text.name_o2 : state.text.name_o1;
  const value = levelName(o1 === null ? o2 : o1);
  return fill(state.text.explain_opportunity_one, { name, value });
}

function visibleEvents() {
  const week = current().week;
  return state.events.filter((event) => event.date <= week && event.regions.includes(state.region));
}

function renderStatic() {
  document.title = state.text.title;
  document.getElementById("title").textContent = state.text.title;
  document.getElementById("banner").textContent = state.text.banner;
  document.getElementById("paused").textContent = state.text.paused;
  document.getElementById("play").textContent = state.text.play;
  document.getElementById("pause").textContent = state.text.pause;
  document.getElementById("week-name").textContent = state.text.week;
  document.getElementById("region-name").textContent = state.text.region;
  document.getElementById("disclaimer-short").textContent = state.text.disclaimer_short;
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
  document.getElementById("week-label").textContent = row.week;
  const arrived = state.events.filter((event) => event.date === row.week && event.regions.includes(state.region));
  document.getElementById("arrived").textContent = arrived.map((event) => event.date + ": " + event.label).join("; ");
  const label = row.shown_label || levelName(numberOrNull(row.shown));
  document.getElementById("level-words").textContent = label;
  document.getElementById("summary").textContent = summary(row, previous());
  const partial = document.getElementById("partial-note");
  partial.hidden = row.partial !== "True" && row.week !== INVASION_WEEK;
  const notes = [];
  if (row.partial === "True") notes.push(state.text.partial);
  if (row.week === INVASION_WEEK) notes.push(state.text.invasion);
  partial.textContent = notes.join(" ");
  renderCards(row);
  renderEvents();
  renderIndicators(row);
  renderChart(rows);
  document.querySelectorAll("[data-depth]").forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.depth === String(state.depth) ? "true" : "false");
  });
  document.getElementById("depth-1").hidden = state.depth !== 1;
  document.getElementById("depth-2").hidden = state.depth !== 2;
  document.getElementById("depth-3").hidden = state.depth !== 3;
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
    level.textContent = levelName(numberOrNull(row[layer]));
    const trendText = document.createElement("p");
    trendText.textContent = trend(layer);
    const line = document.createElement("p");
    line.textContent = explanation(layer, row);
    button.append(title, level, trendText, line);
    button.addEventListener("click", () => {
      state.selected = layer;
      renderWeek();
    });
    cards.appendChild(button);
  });
}

function renderEvents() {
  const list = document.getElementById("events");
  list.innerHTML = "";
  const events = visibleEvents();
  if (!events.length) {
    const item = document.createElement("li");
    item.textContent = state.text.events_none;
    list.appendChild(item);
    return;
  }
  events.forEach((event) => {
    const item = document.createElement("li");
    item.textContent = event.date + ": " + event.label + ", " + levelName(event.level);
    list.appendChild(item);
  });
}

function renderIndicators(row) {
  const table = document.getElementById("indicators");
  table.innerHTML = "";
  const fields = [
    ["layer_intent", levelName(numberOrNull(row.intent))],
    ["layer_capability", levelName(numberOrNull(row.capability))],
    ["layer_opportunity", levelName(numberOrNull(row.opportunity))],
    ["layer_hybrid", levelName(numberOrNull(row.hybrid))],
    ["name_o1", levelName(numberOrNull(row.o1))],
    ["name_o2", levelName(numberOrNull(row.o2))],
  ];
  fields.forEach(([key, value]) => {
    const tr = document.createElement("tr");
    const name = document.createElement("th");
    name.textContent = state.text[key];
    const cell = document.createElement("td");
    cell.textContent = value;
    tr.append(name, cell);
    table.appendChild(tr);
  });
}

function series(rows, key) {
  return rows.slice(0, state.index + 1).map((row) => {
    const value = numberOrNull(row[key]);
    return value === null ? null : value;
  });
}

function renderChart(rows) {
  const labels = rows.slice(0, state.index + 1).map((row) => row.week);
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
    pointRadius: 2,
    tension: 0,
  }));
  if (state.chart) {
    state.chart.data.labels = labels;
    state.chart.data.datasets = datasets;
    state.chart.update();
    return;
  }
  state.chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: { y: { min: 0, max: 4, ticks: { stepSize: 1 } } },
    },
  });
}

function setDepth(depth) {
  state.depth = depth;
  renderWeek();
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
    const last = weeksForRegion().length - 1;
    if (state.index >= last) {
      stop();
      return;
    }
    state.index += 1;
    renderWeek();
  }, 1200);
}

async function main() {
  const [text, csv, events] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch("data/events.json").then((response) => response.json()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
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
    const rows = weeksForRegion();
    const found = rows.findIndex((row) => row.week === week);
    state.index = found >= 0 ? found : 0;
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
    renderWeek();
  });
  document.querySelectorAll("[data-depth]").forEach((button) => {
    button.addEventListener("click", () => setDepth(Number(button.dataset.depth)));
  });
}

main();
