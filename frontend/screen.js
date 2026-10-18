const START = "2021-01-04";
const COUNTRIES = ["FI", "EE", "LV", "LT", "PL"];
const NATO = {
  role: "NATO",
  label: "NATO page on the eastern flank",
  url: "https://www.nato.int/en/what-we-do/deterrence-and-defence/strengthening-natos-eastern-flank",
};
const CHECK = {
  FI: [
    { role: "Preparedness", label: "72 hours, Finnish preparedness", url: "https://72tuntia.fi/en/" },
    NATO,
  ],
  EE: [NATO],
  LV: [
    { role: "Preparedness", label: "Latvian Fire and Rescue Service", url: "https://www.vugd.gov.lv/en" },
    { role: "Defence ministry", label: "Latvian Ministry of Defence", url: "https://www.mod.gov.lv/en" },
    { role: "Border guard", label: "Latvian State Border Guard", url: "https://www.rs.gov.lv/en" },
    NATO,
  ],
  LT: [
    { role: "Border guard", label: "Lithuanian State Border Guard", url: "https://vsat.lrv.lt/en/" },
    NATO,
  ],
  PL: [
    { role: "Interior", label: "Polish Ministry of the Interior", url: "https://www.gov.pl/web/mswia" },
    { role: "Defence ministry", label: "Polish Ministry of National Defence", url: "https://www.gov.pl/web/national-defence" },
    { role: "Border guard", label: "Polish Border Guard", url: "https://www.strazgraniczna.pl/" },
    NATO,
  ],
};

const state = {
  text: {},
  rows: [],
  events: [],
  map: null,
  news: [],
  official: {},
  counts: {},
  usual: {},
  country: "FI",
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
    if (char === '"') quoted = true;
    else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") cell += char;
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

function countryName(code) {
  return state.text["country_" + code] || code;
}

function weekWords(iso) {
  const [year, month, day] = iso.split("-");
  return fill(state.text.week_of, {
    day: String(Number(day)),
    month: state.text["month_" + Number(month)],
    year,
  });
}

function dateWords(iso) {
  return weekWords(iso).replace("Week of ", "");
}

function weekAge(week, iso) {
  return (Date.parse(week) - Date.parse(iso)) / 86400000 / 7;
}

function eventCountries(event) {
  const names = (event.places || []).map((place) => place.name.toLowerCase()).join(" ");
  const codes = new Set();
  if (names.includes("kaliningrad")) {
    codes.add("LT");
    codes.add("PL");
  }
  if (event.tag === "belarus" || /belarus|gomel|zyabrovka|mozyr/.test(names)) {
    codes.add("LT");
    codes.add("LV");
    codes.add("PL");
  }
  if (/northwest russia|karelia|pskov|leningrad oblast/.test(names)) {
    codes.add("FI");
    codes.add("EE");
  }
  return [...codes];
}

function forCountry(events, code) {
  return events.filter((event) => eventCountries(event).includes(code));
}

function activeEvents(week) {
  return state.events.filter((event) => {
    if (!event.places || !event.places.length) return false;
    if (event.date > week) return false;
    return weekAge(week, event.date) <= 4;
  });
}

function buildCounts() {
  COUNTRIES.forEach((code) => {
    state.counts[code] = {};
  });
  state.news.forEach((story) => {
    (story.countries || []).forEach((code) => {
      if (!state.counts[code]) return;
      state.counts[code][story.week] = (state.counts[code][story.week] || 0) + 1;
    });
  });
  COUNTRIES.forEach((code) => {
    const values = Object.values(state.counts[code]).filter((count) => count > 0).sort((a, b) => a - b);
    state.usual[code] = values.length ? values[Math.floor(values.length / 2)] : 0;
  });
}

function countFor(code, week) {
  return state.counts[code][week] || 0;
}

function readingFor(code, week) {
  const count = countFor(code, week);
  const usual = state.usual[code];
  const name = countryName(code);
  if (count < 20) {
    const usualLine = usual
      ? " A usual week in this stored sample that names " + name + " has about " + usual + " headline" + (usual === 1 ? "" : "s") + "."
      : "";
    return {
      uncertain: true,
      zone: "",
      text: count + " headline" + (count === 1 ? "" : "s") + " in this stored sample name " + name + " this week. Too few for a firm reading — uncertain." + usualLine,
    };
  }
  const ratio = usual ? count / usual : 1;
  let zone = "usual";
  let text = "Russian media wrote about " + name + " about as often as usual (" + count + " headlines this week; a usual week in this sample has about " + usual + ").";
  if (usual && ratio >= 1.5) {
    zone = "busier";
    text = "Russian media wrote " + Math.round(ratio) + "× more about " + name + " than usual (" + count + " headlines this week; a usual week in this sample has about " + usual + ").";
  } else if (usual && ratio <= 0.8) {
    zone = "quiet";
    text = "Russian media wrote less about " + name + " than usual (" + count + " headlines this week; a usual week in this sample has about " + usual + ").";
  }
  return { uncertain: false, zone, text };
}

function trendFor(code, week) {
  const weeks = flankWeeks();
  const index = weeks.findIndex((row) => row.week === week);
  if (index <= 0) return "No earlier week to compare.";
  const now = countFor(code, week);
  const before = countFor(code, weeks[index - 1].week);
  if (now < 20 || before < 20) return "→ Not enough headlines to compare with last week.";
  if (now > before) return "↑ More headlines than last week.";
  if (now < before) return "↓ Fewer headlines than last week.";
  return "→ About the same number of headlines as last week.";
}

function causesFor(code, week) {
  const fresh = forCountry(state.events, code).filter((event) => {
    return event.date <= week && weekAge(week, event.date) < 1;
  });
  const lines = fresh
    .map((event) => state.text[event.textKey] || "")
    .filter((line) => line && !/attack|invasion|war|crisis|danger|blood/i.test(line))
    .slice(0, 2);
  if (!lines.length) return "No new events this week.";
  return "Why: " + lines.join(" ");
}

function clear(node) {
  if (node) node.innerHTML = "";
}

function addLink(parent, href, label) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = label;
  parent.appendChild(link);
  return link;
}

function renderSelect() {
  const host = document.getElementById("country-select");
  clear(host);
  COUNTRIES.forEach((code) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = "country-" + code;
    button.className = "country-pick";
    button.dataset.country = code;
    button.textContent = countryName(code);
    button.setAttribute("aria-pressed", code === state.country ? "true" : "false");
    button.addEventListener("click", () => {
      state.country = code;
      renderWeek();
    });
    host.appendChild(button);
  });
}

function renderReading() {
  const code = state.country;
  const week = current().week;
  const reading = readingFor(code, week);
  document.getElementById("country-heading").textContent = countryName(code);
  document.getElementById("reading-line").textContent = reading.text;
  document.querySelectorAll("#meter [data-zone]").forEach((zone) => {
    zone.classList.toggle("on", zone.dataset.zone === reading.zone);
  });
  document.getElementById("trend").textContent = trendFor(code, week);
  document.getElementById("why-line").textContent = causesFor(code, week);
  const means = document.getElementById("means");
  clear(means);
  means.append("What it means for you: No action needed — follow official guidance ");
  const guide = (CHECK[code] || [])[0];
  if (guide) addLink(means, guide.url, guide.label);
}

function renderThisWeek() {
  const code = state.country;
  const week = current().week;
  const name = countryName(code);
  document.getElementById("neutral").textContent = "Official pages and Russian state media are shown as two separate sides. A short note is not a substitute for the linked page.";
  const officialHost = document.getElementById("official-side");
  clear(officialHost);
  const official = (state.official[week] || []).filter((item) => (item.countries || []).includes(code)).slice(0, 3);
  if (!official.length) {
    officialHost.textContent = "No official page was collected for " + name + " this week.";
  } else {
    const list = document.createElement("ul");
    official.forEach((item) => {
      const line = document.createElement("li");
      const who = document.createElement("p");
      who.textContent = item.who + ", " + dateWords(item.date) + ".";
      const mark = document.createElement("p");
      mark.textContent = "AI summary — check the original.";
      line.append(who, mark);
      addLink(line, item.url, "Official page");
      list.appendChild(line);
    });
    officialHost.appendChild(list);
  }
  const mediaHost = document.getElementById("media-side");
  clear(mediaHost);
  const named = state.news.filter((story) => story.week === week && (story.countries || []).includes(code));
  mediaHost.textContent = named.length + " headline" + (named.length === 1 ? "" : "s") + " in the stored sample name " + name + " this week. The titles are under More.";
  const events = forCountry(activeEvents(week), code).slice(0, 3);
  const list = document.getElementById("week-events");
  clear(list);
  events.forEach((event) => {
    const item = document.createElement("li");
    const line = document.createElement("p");
    line.textContent = (state.text[event.textKey] || "A stored report.") + " " + dateWords(event.date) + ".";
    item.appendChild(line);
    addLink(item, event.source, "Source");
    list.appendChild(item);
  });
  const note = document.getElementById("not-happening");
  const negated = forCountry(activeEvents(week), code).some((event) => /not that|not field|not a report/i.test(event.note || ""));
  note.hidden = !negated;
  note.textContent = negated ? "Not happening: a stored source does not describe this as fighting that has already started." : "";
}

function renderRecent() {
  const code = state.country;
  const week = current().week;
  const host = document.getElementById("recent-events");
  clear(host);
  const rows = forCountry(state.events, code).filter((event) => event.date <= week && weekAge(week, event.date) <= 8);
  if (!rows.length) {
    host.textContent = "No mapped events in the last 8 weeks.";
    return;
  }
  rows.forEach((event) => {
    const item = document.createElement("li");
    item.textContent = dateWords(event.date) + " — " + (state.text[event.textKey] || "Stored report") + " ";
    addLink(item, event.source, "Source");
    host.appendChild(item);
  });
}

function renderCheck() {
  const code = state.country;
  const host = document.getElementById("check-links");
  clear(host);
  document.getElementById("check-note").textContent = "Only pages that loaded from this computer are listed. Missing roles were left out.";
  (CHECK[code] || []).forEach((item) => {
    const line = document.createElement("li");
    line.append(item.role + ": ");
    addLink(line, item.url, item.label);
    host.appendChild(line);
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

function renderMap() {
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
  const labels = {
    FI: [64.8, 26.2], EE: [58.7, 25.8], LV: [56.9, 24.8], LT: [55.35, 24.2],
    PL: [52.0, 19.3], BY: [53.7, 27.9], UA: [49.2, 31.4], RU: [58.2, 35.5], KG: [54.55, 20.7],
  };
  state.map.countries.forEach((country) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", country.d);
    path.setAttribute("data-country", country.id);
    path.setAttribute("class", "land land-" + country.id);
    path.setAttribute("aria-label", state.text["country_" + country.id] || country.name);
    if (COUNTRIES.includes(country.id)) {
      path.addEventListener("click", () => {
        state.country = country.id;
        renderWeek();
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
    text.textContent = state.text["country_" + country.id] || country.name;
    svg.appendChild(text);
  });
  forCountry(activeEvents(week), state.country).forEach((event) => {
    event.places.forEach((place) => {
      const [x, y] = project(place.lon, place.lat);
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", x.toFixed(1));
      dot.setAttribute("cy", y.toFixed(1));
      dot.setAttribute("r", "7");
      dot.setAttribute("class", "event-dot");
      dot.setAttribute("data-place", place.name);
      dot.setAttribute("data-date", event.date);
      dot.setAttribute("fill", "#5c7a99");
      dot.setAttribute("stroke", "#fff");
      dot.setAttribute("stroke-width", "1.5");
      dot.addEventListener("click", (click) => {
        click.stopPropagation();
        const box = document.getElementById("map-detail");
        box.hidden = false;
        clear(box);
        const title = document.createElement("p");
        title.textContent = place.name + " — " + (state.text[event.textKey] || "Stored report");
        box.append(title, document.createTextNode(" " + dateWords(event.date) + " "));
        addLink(box, event.source, "Source");
      });
      svg.appendChild(dot);
    });
  });
  host.innerHTML = "";
  host.appendChild(svg);
}

function renderNews() {
  const host = document.getElementById("news");
  clear(host);
  document.getElementById("news-title").textContent = "News";
  document.getElementById("news-note").textContent = "Titles are the stored sample, not our words.";
  let items = state.news.filter((story) => story.week === current().week && (story.countries || []).includes(state.country));
  if (state.filter === "hostile") items = items.filter((story) => story.hostile);
  if (!items.length) {
    host.textContent = "No headlines in the stored sample for this country this week.";
    return;
  }
  const list = document.createElement("ul");
  items.forEach((story) => {
    const item = document.createElement("li");
    item.dataset.source = "headline";
    const title = document.createElement("p");
    title.dataset.source = "headline";
    title.textContent = story.title;
    item.appendChild(title);
    if (story.english) {
      const english = document.createElement("p");
      english.dataset.source = "headline";
      english.textContent = story.english;
      item.appendChild(english);
    }
    const meta = document.createElement("p");
    meta.className = "note";
    meta.textContent = story.outlet + ", " + dateWords(story.date);
    item.appendChild(meta);
    addLink(item, story.url, "Source");
    list.appendChild(item);
  });
  host.appendChild(list);
}

function renderWeek() {
  const row = current();
  document.getElementById("week-label").textContent = weekWords(row.week);
  const how = document.getElementById("how-link");
  how.href = "how-it-works.html?week=" + encodeURIComponent(row.week);
  document.getElementById("charts-link").href = how.href;
  const slider = document.getElementById("slider");
  slider.max = String(flankWeeks().length - 1);
  slider.value = String(state.index);
  renderSelect();
  renderReading();
  renderThisWeek();
  renderMap();
  renderRecent();
  renderCheck();
  renderNews();
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
  const [text, csv, events, map, news, official] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch("events.json").then((response) => response.json()),
    fetch("vendor/flank-map.json").then((response) => response.json()),
    fetch("news.json").then((response) => response.json()),
    fetch("official.json").then((response) => response.json()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
  state.events = events;
  state.map = map;
  state.news = news;
  state.official = official;
  buildCounts();
  document.title = text.title;
  document.getElementById("title").textContent = text.title;
  document.getElementById("banner").textContent = text.banner;
  document.getElementById("how-link").textContent = text.how_link;
  document.getElementById("play").textContent = text.play;
  document.getElementById("pause").textContent = text.pause;
  const params = new URLSearchParams(location.search);
  if (COUNTRIES.includes(params.get("country"))) state.country = params.get("country");
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
