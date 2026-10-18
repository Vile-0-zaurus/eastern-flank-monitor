const START = "2021-01-04";
const COUNTRIES = ["FI", "EE", "LV", "LT", "PL"];

const state = {
  text: {},
  rows: [],
  events: [],
  map: null,
  news: [],
  official: {},
  countryHeadlines: {},
  why: null,
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
  if (shown === 0 || shown === 1) return { word: state.text.sign_normal, kind: "normal", reason: state.text.reason_normal };
  if (shown === 2) return { word: state.text.sign_tense, kind: "tense", reason: state.text.reason_tense };
  if (shown >= 3) return { word: state.text.sign_danger, kind: "danger", reason: state.text.reason_danger };
  return { word: state.text.level_none, kind: "nodata", reason: state.text.reason_none };
}

function weekNews() {
  return state.news.filter((story) => story.week === current().week && visibleStory(story));
}

function isCyrillic(text) {
  return /[А-Яа-яЁё]/.test(text || "");
}

function isEnglishTitle(text) {
  if (isCyrillic(text)) return false;
  if (/[ąęćłńśźżĀāĒēĪīŪūĢģĶķĻļŅņČčĖėĮįŠšŲųŽž]/.test(text || "")) return false;
  const words = (text || "").toLowerCase().match(/[a-z']+/g) || [];
  const common = new Set(["the", "a", "of", "and", "to", "in", "for", "on", "with", "from", "by", "is", "are", "was", "were", "that", "this", "as", "at", "an", "after", "over", "into", "about", "its"]);
  const hits = words.filter((word) => common.has(word)).length;
  return hits >= 2 || (words.length >= 5 && hits >= 1);
}

function visibleStory(story) {
  const title = story.title || "";
  if (isCyrillic(title)) return Boolean(story.english);
  return isEnglishTitle(title);
}

const SHORT = {
  event_zapad: "Zapad-2021",
  event_hospitals: "Field hospital",
  event_buildup_apr: "Troop buildup",
  event_vehicles_dec: "Armoured vehicles",
  event_arriving: "Forces arriving",
  event_logistics: "Medical supplies",
  event_allied: "Allied Resolve",
  event_warning: "Border massing",
  event_mozyr: "Near Mozyr",
  event_belgorod: "Field hospital",
};

function shortLabel(event) {
  return SHORT[event.textKey] || "Stored report";
}

function placeText(event) {
  return (event.places || []).map((place) => place.name.toLowerCase()).join(" ");
}

function ukraineFacing(event) {
  const names = placeText(event);
  return /mozyr|gomel|zyabrovka|ukrainian border|border with ukraine/.test(names)
    || event.textKey === "event_allied"
    || event.textKey === "event_mozyr"
    || event.textKey === "event_hospitals";
}

function concerns(event, code) {
  if (!COUNTRIES.includes(code) || ukraineFacing(event)) return false;
  if (event.textKey === "event_zapad" || event.tag === "western_md") return true;
  if (event.tag === "belarus") return code === "LV" || code === "LT" || code === "PL";
  return false;
}

function panelHeadlines(code) {
  return ((state.countryHeadlines[current().week] || {})[code] || []).slice(0, 3);
}

function dotOpacity(week, date) {
  const age = (Date.parse(week) - Date.parse(date)) / 86400000 / 7;
  if (age < 0 || age > 4) return 0;
  if (age < 1) return 0.4 + 0.6 * age;
  if (age > 3) return Math.max(0.35, 0.4 + 0.6 * (4 - age));
  return 1;
}

function regionLine() {
  const sign = signFor(current());
  const week = current().week;
  const concerned = [];
  let label = "";
  activeEvents(week).forEach((event) => {
    const names = COUNTRIES.filter((code) => concerns(event, code)).map((code) => state.text["country_" + code]);
    if (!names.length) return;
    if (!label) label = shortLabel(event);
    names.forEach((name) => {
      if (!concerned.includes(name)) concerned.push(name);
    });
  });
  if (label && concerned.length) {
    return "Region: " + sign.word + " — " + label + " (" + concerned.join(", ") + ")";
  }
  const named = COUNTRIES.filter((code) => panelHeadlines(code).length).map((code) => state.text["country_" + code]);
  if (sign.kind !== "normal" && named.length) {
    return "Region: " + sign.word + " — headlines name " + named.join(", ");
  }
  return "Region: " + sign.word;
}

function renderStrip() {
  const strip = document.getElementById("country-strip");
  strip.innerHTML = "";
  const region = document.getElementById("region-state");
  if (region) region.textContent = regionLine();
  COUNTRIES.forEach((code) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "country-card";
    button.id = "country-" + code;
    button.dataset.country = code;
    const name = document.createElement("span");
    name.className = "country-name";
    name.textContent = state.text["country_" + code];
    const reason = document.createElement("span");
    reason.className = "reason";
    const facts = [];
    const events = activeEvents(current().week).filter((event) => concerns(event, code));
    if (events.length) facts.push(shortLabel(events[0]));
    const headlines = panelHeadlines(code);
    if (headlines.length) {
      facts.push(headlines.length + " stored headline" + (headlines.length === 1 ? "" : "s") + " name " + state.text["country_" + code]);
    }
    reason.textContent = facts.join(". ");
    button.append(name, reason);
    button.addEventListener("click", () => {
      stop();
      openWhy(code);
    });
    strip.appendChild(button);
  });
  const shared = document.getElementById("shared-reading");
  if (shared) shared.textContent = "Cards list only facts about that country.";
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
  note.textContent = plainNote(event.note);
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
    path.setAttribute("class", "land land-" + country.id + (COUNTRIES.includes(country.id) ? " state-" + signFor(current()).kind : ""));
    const label = state.text["country_" + country.id] || country.name;
    path.setAttribute("aria-label", label);
    if (["FI", "EE", "LV", "LT", "PL", "UA"].includes(country.id)) {
      path.addEventListener("click", () => {
        stop();
        openWhy(country.id);
      });
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
      dot.setAttribute("r", "9");
      dot.setAttribute("class", "event-dot");
      dot.setAttribute("data-place", place.name);
      dot.setAttribute("data-date", event.date);
      dot.setAttribute("fill", "#1d4ed8");
      dot.setAttribute("stroke", "#ffffff");
      dot.setAttribute("stroke-width", "2");
      dot.setAttribute("opacity", dotOpacity(week, event.date).toFixed(2));
      const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tip.textContent = shortLabel(event) + ". " + (state.text[event.textKey] || place.name);
      dot.appendChild(tip);
      dot.addEventListener("click", (click) => {
        click.stopPropagation();
        stop();
        showEvent(event, place);
        const code = COUNTRIES.find((item) => concerns(event, item)) || null;
        openWhy(code, event);
      });
      svg.appendChild(dot);
      if (place === event.places[0]) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", (x + 12).toFixed(1));
        label.setAttribute("y", (y - 8).toFixed(1));
        label.setAttribute("class", "map-event-label");
        label.setAttribute("opacity", dotOpacity(week, event.date).toFixed(2));
        label.textContent = shortLabel(event);
        svg.appendChild(label);
      }
    });
  });
  host.innerHTML = "";
  host.appendChild(svg);
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
    heading.textContent = code === "other" ? "Not tied to one country" : state.text["country_" + code];
    section.appendChild(heading);
    const list = document.createElement("ul");
    groups[code].forEach((story) => {
      const item = document.createElement("li");
      item.className = "story";
      const original = document.createElement("p");
      original.textContent = state.text.original_label + ": " + story.title;
      const english = document.createElement("p");
      const englishText = englishLine(story);
      english.textContent = englishText;
      const meta = document.createElement("p");
      meta.className = "note";
      meta.textContent = story.outlet + ", " + weekWords(story.date).replace("Week of ", "");
      const link = document.createElement("a");
      link.href = story.url;
      link.textContent = state.text.source;
      item.append(original, meta, link);
      if (englishText) item.insertBefore(english, meta);
      list.appendChild(item);
    });
    section.appendChild(list);
    host.appendChild(section);
  });
}

function englishLine(story) {
  if (!story.english) return "";
  return state.text.machine_translation + ": " + story.english;
}

function plainNote(note) {
  if (!note) return "";
  return note
    .split(/(?<=\.)\s+/)
    .filter((sentence) => !/^(Stays \d|Changed from \d)/.test(sentence))
    .join(" ");
}

function dateWords(iso) {
  return weekWords(iso).replace("Week of ", "");
}

function rowForCode(code) {
  const region = code === "UA" ? "ukraine_test" : "eastern_flank";
  return state.rows.find((row) => row.region === region && row.week === current().week) || current();
}

function appendStory(list, story) {
  const item = document.createElement("li");
  item.className = "story";
  const same = story.english && story.english === story.title;
  if (!same) {
    const original = document.createElement("p");
    original.textContent = state.text.original_label + ": " + story.title;
    item.append(original);
  }
  const englishText = englishLine(story);
  if (englishText && !same) {
    const english = document.createElement("p");
    english.textContent = englishText;
    item.append(english);
  }
  if (same) {
    const line = document.createElement("p");
    line.textContent = story.english;
    item.append(line);
  }
  const meta = document.createElement("p");
  meta.className = "note";
  meta.textContent = story.outlet + ", " + dateWords(story.date);
  const link = document.createElement("a");
  link.href = story.url;
  link.textContent = state.text.source;
  item.append(meta, link);
  list.appendChild(item);
}

function appendEventLine(list, event) {
  const item = document.createElement("li");
  const title = document.createElement("p");
  const place = (event.places || []).map((item) => item.name).join(", ");
  title.textContent = (place ? place + ". " : "") + (state.text[event.textKey] || "");
  const when = document.createElement("p");
  when.className = "note";
  when.textContent = dateWords(event.date);
  const note = document.createElement("p");
  note.textContent = plainNote(event.note);
  const link = document.createElement("a");
  link.href = event.source;
  link.textContent = state.text.source;
  item.append(title, when, note, link);
  list.appendChild(item);
}

function openWhy(code, focus) {
  state.why = { code: code || null, focusDate: focus ? focus.date : "", focusTag: focus ? focus.tag : "" };
  const panel = document.getElementById("why");
  const row = rowForCode(code);
  const sign = signFor(row);
  panel.hidden = false;
  document.getElementById("why-close").textContent = state.text.close;
  const name = code ? state.text["country_" + code] : (focus && focus.places ? focus.places[0].name : "this report");
  document.getElementById("why-title").textContent = "This week in " + name;
  document.getElementById("why-subject").textContent = name + " — " + sign.word + " — " + weekWords(current().week);
  const eventsHost = document.getElementById("why-events");
  const officialHost = document.getElementById("why-official");
  const mediaHost = document.getElementById("why-media");
  eventsHost.innerHTML = "";
  officialHost.innerHTML = "";
  mediaHost.innerHTML = "";
  const region = code === "UA" ? "ukraine_test" : "eastern_flank";
  let events = code
    ? activeEvents(current().week).filter((event) => concerns(event, code))
    : [];
  if (focus && !events.some((event) => event.date === focus.date && event.tag === focus.tag)) {
    events = [focus].concat(events);
  }
  const official = (state.official[current().week] || []).filter((item) => {
    if (!code || !item.countries || !item.countries.length) return true;
    return item.countries.includes(code);
  });
  let media = code ? panelHeadlines(code) : [];
  const quiet = !events.length && !official.length && !media.length;
  document.getElementById("why-quiet").hidden = !quiet;
  document.getElementById("why-body").hidden = quiet;
  if (quiet) return;
  if (!events.length) {
    eventsHost.textContent = "No events reported in our sources.";
  } else {
    const list = document.createElement("ul");
    events.forEach((event) => appendEventLine(list, event));
    eventsHost.appendChild(list);
  }
  if (!official.length) {
    officialHost.textContent = state.text.no_source_found;
  } else {
    const list = document.createElement("ul");
    official.forEach((item) => {
      const line = document.createElement("li");
      const summary = document.createElement("p");
      summary.textContent = item.summary;
      const meta = document.createElement("p");
      meta.className = "note";
      meta.textContent = item.who + ", " + dateWords(item.date) + ". " + item.label;
      const link = document.createElement("a");
      link.href = item.url;
      link.textContent = state.text.source;
      line.append(summary, meta, link);
      list.appendChild(line);
    });
    officialHost.appendChild(list);
  }
  if (!media.length) {
    mediaHost.textContent = code
      ? "No headline in the stored sample names " + state.text["country_" + code] + " this week."
      : state.text.news_empty;
  } else {
    const list = document.createElement("ul");
    media.slice(0, 6).forEach((story) => appendStory(list, story));
    mediaHost.appendChild(list);
  }
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
  if (!document.getElementById("why").hidden && state.why) {
    const focus = state.events.find((event) => event.date === state.why.focusDate && event.tag === state.why.focusTag);
    openWhy(state.why.code, focus);
  }
}

function setToggle() {
  const button = document.getElementById("play");
  if (!button) return;
  const playing = Boolean(state.timer);
  button.textContent = playing ? "Pause" : "Play";
  button.setAttribute("aria-pressed", playing ? "true" : "false");
}

function stop() {
  state.playToken = (state.playToken || 0) + 1;
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  setToggle();
}

function play() {
  stop();
  const token = state.playToken;
  state.timer = setInterval(() => {
    if (token !== state.playToken || !state.timer) return;
    if (state.index >= flankWeeks().length - 1) {
      stop();
      return;
    }
    state.index += 1;
    renderWeek();
  }, 900);
  setToggle();
}

function togglePlayback() {
  if (state.timer) stop();
  else play();
}

async function main() {
  const [text, csv, events, map, news, official, countryHeadlines] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch("events.json").then((response) => response.json()),
    fetch("vendor/flank-map.json").then((response) => response.json()),
    fetch("news.json").then((response) => response.json()),
    fetch("official.json").then((response) => response.json()),
    fetch("country-headlines.json").then((response) => response.json()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
  state.events = events;
  state.map = map;
  state.news = news;
  state.official = official;
  state.countryHeadlines = countryHeadlines;
  document.title = text.title;
  document.getElementById("title").textContent = text.title;
  document.getElementById("banner").textContent = "Prototype — replaying 2021–22. Not live.";
  document.getElementById("how-link").textContent = text.how_link;
  document.getElementById("play").textContent = text.play;
  document.getElementById("disclaimer-short").textContent = text.disclaimer_short;
  document.getElementById("disclaimer-more").textContent = text.more;
  document.getElementById("disclaimer-full").textContent = text.disclaimer_full;
  const params = new URLSearchParams(location.search);
  if (params.get("week")) {
    const found = flankWeeks().findIndex((row) => row.week === params.get("week"));
    if (found >= 0) state.index = found;
  }
  renderWeek();
  document.getElementById("play").addEventListener("click", togglePlayback);
  document.getElementById("slider").addEventListener("input", (event) => {
    stop();
    state.index = Number(event.target.value);
    renderWeek();
  });
  document.getElementById("slider").addEventListener("change", stop);
  document.getElementById("why-close").addEventListener("click", () => {
    document.getElementById("why").hidden = true;
    state.why = null;
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
