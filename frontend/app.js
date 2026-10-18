const START = "2021-01-04";
const COUNTRIES = ["FI", "EE", "LV", "LT", "PL"];

const state = {
  text: {},
  rows: [],
  events: [],
  map: null,
  news: [],
  index: 0,
  timer: null,
  filter: "all",
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

function flankWeeks() {
  return state.rows.filter((row) => row.region === "eastern_flank");
}

function current() {
  return flankWeeks()[state.index];
}

function weekWords(iso) {
  const [year, month, day] = iso.split("-");
  return fill(state.text.week_of, {
    day: String(Number(day)),
    month: state.text["month_" + Number(month)],
    year,
  });
}

function signFor(row) {
  if (!row || row.shown === "") {
    return { word: state.text.sign_none || state.text.level_none, kind: "nodata", reason: state.text.reason_none };
  }
  if ((row.shown_label || "").toLowerCase().includes("proposed")) {
    return { word: state.text.sign_danger, kind: "danger", reason: state.text.reason_danger };
  }
  const shown = Number(row.shown);
  if (shown === 0) return { word: state.text.sign_normal, kind: "normal", reason: state.text.reason_normal };
  if (shown === 1 || shown === 2) return { word: state.text.sign_tense, kind: "tense", reason: state.text.reason_tense };
  if (shown >= 3) return { word: state.text.sign_danger, kind: "danger", reason: state.text.reason_danger };
  return { word: state.text.level_none, kind: "nodata", reason: state.text.reason_none };
}

function weekNews() {
  return state.news.filter((story) => story.week === current().week);
}

function countryMentioned(code) {
  return weekNews().some((story) => (story.countries || []).includes(code));
}

function renderStrip() {
  const row = current();
  const sign = signFor(row);
  const strip = document.getElementById("country-strip");
  strip.innerHTML = "";
  COUNTRIES.forEach((code) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "country-card " + sign.kind;
    button.id = "country-" + code;
    button.dataset.country = code;
    const name = document.createElement("span");
    name.className = "country-name";
    name.textContent = state.text["country_" + code];
    const word = document.createElement("span");
    word.className = "sign";
    word.textContent = sign.word;
    const reason = document.createElement("span");
    reason.className = "reason";
    const extra = countryMentioned(code)
      ? " A headline this week names " + state.text["country_" + code] + "."
      : " " + state.text.same_reading;
    reason.textContent = sign.reason + extra;
    button.append(name, word, reason);
    button.addEventListener("click", () => openWhy(code));
    strip.appendChild(button);
  });
}

function project(lon, lat) {
  const box = state.map.bounds;
  const width = state.map.width;
  const height = state.map.height;
  const x = (lon - box.minLon) / (box.maxLon - box.minLon) * width;
  const merc = (value) => Math.log(Math.tan(Math.PI / 4 + value * Math.PI / 360));
  const y = (merc(box.maxLat) - merc(lat)) / (merc(box.maxLat) - merc(box.minLat)) * height;
  return [x, y];
}

function activeEvents(week) {
  return state.events.filter((event) => {
    if (!event.places || !event.places.length) return false;
    if (event.date > week) return false;
    const age = (Date.parse(week) - Date.parse(event.date)) / 86400000 / 7;
    return age <= 4;
  });
}

function dotColor(level) {
  return ["#6b7280", "#b0893e", "#c46b2c", "#7b5ea7", "#8c4a4a"][level] || "#6b7280";
}

function showEvent(event, place) {
  const box = document.getElementById("map-detail");
  box.hidden = false;
  box.innerHTML = "";
  const title = document.createElement("p");
  title.textContent = place.name + " — " + (state.text[event.textKey] || "");
  const when = document.createElement("p");
  when.textContent = weekWords(event.date);
  const note = document.createElement("p");
  note.textContent = event.note || "";
  if (place.area) {
    const area = document.createElement("p");
    area.className = "note";
    area.textContent = "The report does not name a town. The dot marks that area.";
    box.append(title, when, note, area);
  } else {
    box.append(title, when, note);
  }
  const link = document.createElement("a");
  link.href = event.source;
  link.textContent = state.text.source;
  box.append(link);
}

function renderMap() {
  const title = document.getElementById("map-title");
  if (title) title.textContent = state.text.map_title;
  const host = document.getElementById("map");
  const detail = document.getElementById("map-detail");
  if (detail) detail.hidden = true;
  if (!state.map) {
    host.textContent = "";
    return;
  }
  const week = current().week;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 " + state.map.width + " " + state.map.height);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Map of the eastern flank and nearby countries");
  svg.id = "flank-map";
  const labels = {
    FI: [64.8, 26.2],
    EE: [58.7, 25.8],
    LV: [56.9, 24.8],
    LT: [55.35, 24.2],
    PL: [52.0, 19.3],
    BY: [53.7, 27.9],
    UA: [49.2, 31.4],
    RU: [58.2, 35.5],
    KG: [54.55, 20.7],
  };
  state.map.countries.forEach((country) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", country.d);
    path.setAttribute("data-country", country.id);
    path.setAttribute("class", "land land-" + country.id);
    const label = state.text["country_" + country.id] || country.name;
    path.setAttribute("aria-label", label);
    if (["FI", "EE", "LV", "LT", "PL", "UA"].includes(country.id)) {
      path.addEventListener("click", () => openWhy(country.id));
    }
    svg.appendChild(path);
    const at = labels[country.id];
    if (!at) return;
    const [x, y] = project(at[1], at[0]);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x.toFixed(1));
    text.setAttribute("y", y.toFixed(1));
    text.setAttribute("class", "map-label");
    text.textContent = label;
    svg.appendChild(text);
  });
  const crimea = project(34.4, 45.15);
  const crimeaLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
  crimeaLabel.setAttribute("x", crimea[0].toFixed(1));
  crimeaLabel.setAttribute("y", crimea[1].toFixed(1));
  crimeaLabel.setAttribute("class", "map-label");
  crimeaLabel.textContent = "Crimea";
  svg.appendChild(crimeaLabel);
  activeEvents(week).forEach((event) => {
    event.places.forEach((place) => {
      const [x, y] = project(place.lon, place.lat);
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", x.toFixed(1));
      dot.setAttribute("cy", y.toFixed(1));
      dot.setAttribute("r", "7");
      dot.setAttribute("class", "event-dot");
      dot.setAttribute("data-place", place.name);
      dot.setAttribute("data-date", event.date);
      dot.setAttribute("fill", dotColor(event.level));
      dot.setAttribute("stroke", "#fff");
      dot.setAttribute("stroke-width", "1.5");
      const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tip.textContent = place.name;
      dot.appendChild(tip);
      dot.addEventListener("click", (click) => {
        click.stopPropagation();
        showEvent(event, place);
      });
      svg.appendChild(dot);
    });
  });
  host.innerHTML = "";
  host.appendChild(svg);
  const credit = document.createElement("p");
  credit.className = "note";
  credit.id = "map-credit";
  credit.textContent = "Country outlines are public-domain Natural Earth data, kept on this computer. No live map tiles. A dot stays for four weeks.";
  host.appendChild(credit);
}

function renderNews() {
  const title = document.getElementById("news-title");
  if (title) title.textContent = state.text.news_title;
  document.getElementById("filter-all").textContent = state.text.filter_all;
  document.getElementById("filter-hostile").textContent = state.text.filter_hostile;
  document.getElementById("filter-all").setAttribute("aria-pressed", state.filter === "all" ? "true" : "false");
  document.getElementById("filter-hostile").setAttribute("aria-pressed", state.filter === "hostile" ? "true" : "false");
  document.getElementById("news-note").textContent = state.text.hostile_note;
  const host = document.getElementById("news");
  host.innerHTML = "";
  let items = weekNews();
  if (state.filter === "hostile") items = items.filter((story) => story.hostile);
  if (!items.length) {
    const empty = document.createElement("p");
    empty.textContent = state.text.news_empty;
    host.appendChild(empty);
    return;
  }
  const order = ["FI", "EE", "LV", "LT", "PL", "UA", "BY", "other"];
  const groups = {};
  items.forEach((story) => {
    const codes = story.countries && story.countries.length ? story.countries : ["other"];
    codes.forEach((code) => {
      if (!groups[code]) groups[code] = [];
      groups[code].push(story);
    });
  });
  order.filter((code) => groups[code]).forEach((code) => {
    const section = document.createElement("section");
    section.className = "news-group";
    const heading = document.createElement("h3");
    heading.textContent = code === "other" ? "No single country" : state.text["country_" + code];
    section.appendChild(heading);
    const list = document.createElement("ul");
    groups[code].forEach((story) => {
      const item = document.createElement("li");
      item.className = "story";
      const original = document.createElement("p");
      original.textContent = state.text.original_label + ": " + story.title;
      const english = document.createElement("p");
      english.textContent = state.text.machine_translation + ": " + (story.english || "not stored.");
      const meta = document.createElement("p");
      meta.className = "note";
      meta.textContent = story.outlet + ", " + weekWords(story.date).replace("Week of ", "");
      const link = document.createElement("a");
      link.href = story.url;
      link.textContent = state.text.source;
      item.append(original, english, meta, link);
      list.appendChild(item);
    });
    section.appendChild(list);
    host.appendChild(section);
  });
}

function openWhy(code) {
  const panel = document.getElementById("why");
  const sign = signFor(current());
  panel.hidden = false;
  document.getElementById("why-title").textContent = state.text.why_panel;
  document.getElementById("why-close").textContent = state.text.close;
  document.getElementById("why-subject").textContent = state.text["country_" + code] + " — " + weekWords(current().week);
  document.getElementById("why-events").textContent = sign.reason;
  document.getElementById("why-official").textContent = state.text.no_source_found;
  document.getElementById("why-media").textContent = "";
}

function renderWeek() {
  const rows = flankWeeks();
  const row = rows[state.index];
  const slider = document.getElementById("slider");
  slider.max = String(rows.length - 1);
  slider.value = String(state.index);
  document.getElementById("week-label").textContent = weekWords(row.week);
  const how = document.getElementById("how-link");
  how.href = "how-it-works.html?week=" + encodeURIComponent(row.week);
  renderStrip();
  renderMap();
  renderNews();
  if (!document.getElementById("why").hidden) {
    const open = document.querySelector(".country-card[aria-pressed='true']");
    if (open) openWhy(open.dataset.country);
  }
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
    if (state.index >= flankWeeks().length - 1) {
      stop();
      return;
    }
    state.index += 1;
    renderWeek();
  }, 900);
}

async function main() {
  const [text, csv, events, map, news] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch("events.json").then((response) => response.json()),
    fetch("vendor/flank-map.json").then((response) => response.json()),
    fetch("news.json").then((response) => response.json()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
  state.events = events;
  state.map = map;
  state.news = news;
  document.title = text.title;
  document.getElementById("title").textContent = text.title;
  document.getElementById("banner").textContent = text.banner;
  document.getElementById("how-link").textContent = text.how_link;
  document.getElementById("play").textContent = text.play;
  document.getElementById("pause").textContent = text.pause;
  document.getElementById("disclaimer-short").textContent = text.disclaimer_short;
  document.getElementById("disclaimer-more").textContent = text.more;
  document.getElementById("disclaimer-full").textContent = text.disclaimer_full;
  const params = new URLSearchParams(location.search);
  if (params.get("week")) {
    const found = flankWeeks().findIndex((row) => row.week === params.get("week"));
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
  document.getElementById("why-close").addEventListener("click", () => {
    document.getElementById("why").hidden = true;
  });
  document.getElementById("filter-all").addEventListener("click", () => {
    state.filter = "all";
    renderNews();
  });
  document.getElementById("filter-hostile").addEventListener("click", () => {
    state.filter = "hostile";
    renderNews();
  });
}

main();
