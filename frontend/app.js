const START = "2021-01-04";
const COUNTRIES = ["FI", "EE", "LV", "LT", "PL"];

const state = {
  text: {},
  rows: [],
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
    reason.textContent = sign.reason + " " + state.text.same_reading;
    button.append(name, word, reason);
    button.addEventListener("click", () => openWhy(code));
    strip.appendChild(button);
  });
}

function renderMap() {
  const title = document.getElementById("map-title");
  if (title) title.textContent = state.text.map_title;
}

function renderNews() {
  const title = document.getElementById("news-title");
  if (title) title.textContent = state.text.news_title;
  document.getElementById("filter-all").textContent = state.text.filter_all;
  document.getElementById("filter-hostile").textContent = state.text.filter_hostile;
  document.getElementById("news-note").textContent = state.text.hostile_note;
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
  const [text, csv] = await Promise.all([
    fetch("i18n/en.json").then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
  ]);
  state.text = text;
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
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
}

main();
