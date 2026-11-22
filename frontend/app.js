const START = "2021-01-04";
const ASSET_V = "4206358";

function t(key) {
  const pack = state.text || {};
  const value = pack[key];
  return value == null || value === "" ? key : value;
}

function asset(path) {
  return path + (path.includes("?") ? "&" : "?") + "v=" + ASSET_V;
}

const COUNTRIES = ["FI", "EE", "LV", "LT", "PL"];

const state = {
  text: {},
  rows: [],
  events: [],
  map: null,
  news: [],
  official: {},
  officials: {},
  inside: { weeks: {} },
  focus: "LT",
  countryHeadlines: {},
  why: null,
  index: 0,
  timer: null,
  filter: "all",
  russiaOpen: false,
  moreFeed: {},
  mode: "replay",
  nowPack: null,
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

function inNow() {
  return state.mode === "now" && state.nowPack;
}

function flankWeeks() {
  if (inNow()) {
    return state.nowPack.weeks.map((week) => ({
      week,
      region: "eastern_flank",
      shown: "",
      shown_label: "",
    }));
  }
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

function isRussianOriginal(text) {
  if (!isCyrillic(text)) return false;
  return !/[іїєґІЇЄҐјљњћђџЈЉЊЋЂЏ]/.test(text || "");
}

function isForeignService(story) {
  const blob = ((story.title || "") + " " + (story.url || "") + " " + (story.outlet || "")).toLowerCase();
  return /sputnik türkiye|sputnik turkiye|sputnik brasil|sputnik mundo|br\.sputnik|tr\.sputnik|mundo\.sputnik|pl\.sputnik|rs\.sputnik|arabic\.sputnik/.test(blob)
    || /[ãõçñ¿¡ğşıİı]/.test(story.title || "");
}

function mentionsRegion(text) {
  const value = text || "";
  if (/\bnato\b/i.test(value)) return true;
  if (/(?<![а-яё])нато(?![а-яё])/i.test(value)) return true;
  return /finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|poland|polish|baltic|belarus|kaliningrad|ukraine|ukrainian|border|military|troop|army|exercise|drill|sanction|deploy|финлянд|финск|эстон|латви|литв|польш|прибалт|балтий|беларус|белорус|калининград|украин|границ|погранич|военн|войск|арми|учен|санкц|разв[её]ртыван/i.test(value);
}

function foreignSenator(text) {
  return /\b(us|u\.s\.|american|french|dutch|german|british|italian|european)\s+senators?\b/i.test(text || "");
}

function allowedOriginal(story) {
  if (isForeignService(story)) return false;
  const title = story.title || "";
  if (isRussianOriginal(title)) return true;
  if (isEnglishTitle(title)) return true;
  return story.kind === "official" && isEnglishTitle(story.english || story.summary || "");
}

function historyCulture(text) {
  const value = text || "";
  if (/jaruzelski|ярузельск/i.test(value)) return true;
  if (/how poland rebelled|как бунтовала польша/i.test(value)) return true;
  return false;
}

function showNews(story) {
  if (historyCulture((story.title || "") + " " + (story.english || ""))) return false;
  if (!allowedOriginal(story)) return false;
  const title = story.title || "";
  if (isCyrillic(title) && !story.english) return false;
  return mentionsRegion((story.title || "") + " " + (story.english || "") + " " + (story.summary || ""));
}

function russianSpeaker(text) {
  const value = text || "";
  if (/миноборон\w* украин/i.test(value) && !/путин|кремл|песков|лавров|захаров|шоигу|госдум|совфед|совет федерации|сенатор|federation council|russian senator/i.test(value)) return false;
  if (/путин|кремл|песков|лавров|захаров|шоигу|миноборон|госдум|совфед|совет федерации|сенатор|putin|kremlin|peskov|lavrov|zakharova|shoigu|state duma|federation council|russian senator|russian diplomat/i.test(value)) return true;
  if (/\bsenator\b/i.test(value) && !foreignSenator(value) && /russian politics|says senator|senator says|senator insists|— senator|– senator|- senator/i.test(value)) return true;
  return false;
}

function flankTopic(text) {
  return /finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|poland|polish|baltic|belarus|kaliningrad|финлянд|эстон|латви|литв|польш|прибалт|беларус|белорус|калининград/i.test(text || "");
}

function disallowedWesternSpeaker(text) {
  return /\b(cdu|csu)\b/i.test(text || "") || /german (leader|chancellor)|former italian prime minister/i.test(text || "");
}

function westernSpeaker(text) {
  const value = text || "";
  if (disallowedWesternSpeaker(value)) return false;
  if (/столтенберг|stoltenberg|north atlantic council|nato secretary/i.test(value)) return true;
  if (/\b(us|u\.s\.|american)\s+senators?\b/i.test(value)) return true;
  if (/biden|байден|blinken|блинкен|psaki|псаки|white house|белый дом|state department|department of state|pentagon|госдеп/i.test(value)) return true;
  if (/european commission|еврокомисс|евросоюз|european council|borrell|боррел/i.test(value)) return true;
  if (/президент\w* (финлянд|эстон|латви|литв|польш)|премьер\w*.{0,40}(финлянд|эстон|латви|литв|польш)|мид (литв|польш|латви|эстон|финлянд)/i.test(value)) return true;
  if (/(president|prime minister|foreign minister|defence minister|defense minister|government|ministry) of (finland|estonia|latvia|lithuania|poland)/i.test(value)) return true;
  if (/(finnish|estonian|latvian|lithuanian|polish) (president|prime minister|minister|government)/i.test(value)) return true;
  if (/niinist|kallas|karis|nauseda|duda|morawiecki/i.test(value)) return true;
  return false;
}

function speakerSide(story) {
  const blob = (story.title || "") + " " + (story.english || "") + " " + (story.summary || "") + " " + (story.who || "") + " " + (story.outlet || "");
  if (russianSpeaker(blob)) return "russian";
  if (westernSpeaker(blob)) return "western";
  return "";
}

function visibleStory(story) {
  return showNews(story);
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

function trendArrow() {
  const rows = flankWeeks();
  const now = Number(rows[state.index] && rows[state.index].shown);
  const prev = state.index > 0 ? Number(rows[state.index - 1].shown) : now;
  if (Number.isNaN(now) || Number.isNaN(prev) || now === prev) return "→";
  return now > prev ? "↑" : "↓";
}

function storyKey(story) {
  return (story.title || story.english || "").toLowerCase().replace(/[^a-zа-яё0-9]+/gi, " ").replace(/\s+/g, " ").trim();
}

function dedupeStories(items) {
  const kept = [];
  items.forEach((story) => {
    const key = storyKey(story);
    if (!key) return;
    const dup = kept.some((prior) => {
      const other = storyKey(prior);
      return other === key || (key.length > 28 && other.length > 28 && (other.includes(key) || key.includes(other)));
    });
    if (!dup) kept.push(story);
  });
  return kept;
}

function countryMedia(code) {
  if (inNow() && state.nowHeadlines) {
    const week = ((state.nowHeadlines.weeks || {})[current().week] || {})[code] || [];
    return dedupeStories(week.filter(showNews));
  }
  return dedupeStories(((state.countryHeadlines[current().week] || {})[code] || []).filter(showNews));
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
    const names = COUNTRIES.filter((code) => concerns(event, code)).map((code) => englishCountry(code));
    if (!names.length) return;
    if (!label) label = shortLabel(event);
    names.forEach((name) => {
      if (!concerned.includes(name)) concerned.push(name);
    });
  });
  if (label && concerned.length) {
    return "Region: " + sign.word + " — " + label + " (" + concerned.join(", ") + ")";
  }
  const named = COUNTRIES.filter((code) => countryMedia(code).length).map((code) => englishCountry(code));
  if (sign.kind !== "normal" && named.length) {
    return "Region: " + sign.word + " — headlines name " + named.join(", ");
  }
  return "Region: " + sign.word;
}

function weekEnd(week) {
  const start = new Date(week + "T00:00:00Z");
  start.setUTCDate(start.getUTCDate() + 6);
  return start.toISOString().slice(0, 10);
}

function nowAttention(code) {
  const pack = state.nowPack;
  const week = current().week;
  const count = ((pack.attention || {})[week] || {})[code] || 0;
  const usual = (pack.usual || {})[code];
  return { count, usual };
}

function nowIncidents(code, week) {
  const start = week || current().week;
  const end = weekEnd(start);
  return (state.nowPack.incidents || []).filter((item) => {
    if (item.date < start || item.date > end) return false;
    return !code || item.country === code;
  });
}

function activeIncidents(code) {
  const end = weekEnd(current().week);
  const floor = state.nowPack.window_start || "2026-08-03";
  return (state.nowPack.incidents || []).filter((item) => {
    if (item.date > end || item.date < floor) return false;
    return !code || item.country === code;
  });
}

function recentIncidents(code) {
  const start = new Date(current().week + "T00:00:00Z");
  start.setUTCDate(start.getUTCDate() - 56);
  const floor = start.toISOString().slice(0, 10);
  return activeIncidents(code).filter((item) => item.date < current().week && item.date >= floor);
}

function incidentLabel(item) {
  if (item.status) return item.status;
  if (/^Officially confirmed/i.test(item.summary || "")) return "Officially confirmed";
  if (/^Reported/i.test(item.summary || "")) return "Reported";
  return "Reported";
}

function appendIncidentLine(list, incident) {
  const item = document.createElement("li");
  item.className = "incident-line";
  item.dataset.date = incident.date;
  item.dataset.country = incident.country;
  const title = document.createElement("button");
  title.type = "button";
  title.className = "incident-jump";
  title.textContent = incidentLabel(incident) + ". " + incident.place + ". " + incident.summary;
  title.addEventListener("click", () => focusIncident(incident));
  const link = document.createElement("a");
  link.href = incident.source;
  link.textContent = t("source");
  item.append(title, link);
  list.appendChild(item);
}

function appendIncidentBlock(host, title, items) {
  if (!items.length) return;
  const heading = document.createElement("h3");
  heading.className = "section-label";
  heading.textContent = title;
  const list = document.createElement("ul");
  items.forEach((incident) => appendIncidentLine(list, incident));
  host.append(heading, list);
}

function attentionWords(code) {
  const reading = nowAttention(code);
  const incidents = nowIncidents(code).length;
  const usual = reading.usual == null ? "no usual" : "usual " + reading.usual;
  const arrow = reading.usual == null ? "" : reading.count > reading.usual ? " ↑" : reading.count < reading.usual ? " ↓" : " →";
  return reading.count + " stories, " + usual + arrow + " · " + incidents + (incidents === 1 ? " incident" : " incidents");
}

function renderNowStrip() {
  const strip = document.getElementById("country-strip");
  strip.innerHTML = "";
  const region = document.getElementById("region-state");
  if (region) {
    region.replaceChildren();
    const label = document.createElement("span");
    label.className = "region-label";
    label.textContent = t("mode_now");
    region.append(label);
  }
  const note = document.getElementById("now-label");
  if (note) {
    note.hidden = false;
    note.textContent = t("now_scope");
  }
  COUNTRIES.forEach((code) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "country-card" + (state.focus === code ? " picked" : state.focus ? " dimmed" : "");
    button.setAttribute("aria-pressed", state.focus === code ? "true" : "false");
    button.id = "country-" + code;
    button.dataset.country = code;
    const name = document.createElement("span");
    name.className = "country-name";
    name.textContent = state.text["country_" + code];
    const word = document.createElement("span");
    word.className = "sign";
    word.textContent = attentionWords(code);
    button.append(name, word);
    button.addEventListener("click", () => {
      stop();
      pickCountry(code);
    });
    strip.appendChild(button);
  });
  const russia = document.createElement("button");
  russia.type = "button";
  russia.id = "russia-square";
  russia.className = "russia-square" + (state.russiaOpen ? " picked" : "");
  russia.setAttribute("aria-pressed", state.russiaOpen ? "true" : "false");
  const russiaName = document.createElement("span");
  russiaName.className = "country-name";
  russiaName.textContent = t("tab_russia");
  russia.append(russiaName);
  russia.addEventListener("click", () => {
    stop();
    toggleRussia();
  });
  strip.appendChild(russia);
}

function selectTab(code) {
  state.focus = code;
  state.russiaOpen = code === "RU";
  state.why = null;
  renderStrip();
  renderMap();
  renderCountryNews();
  renderOfficials();
  renderBriefing();
  syncDrawer();
}

function storedStoryCount(code) {
  const weeks = (state.replayCounts && state.replayCounts.weeks) || {};
  const row = weeks[current().week];
  if (row && Object.prototype.hasOwnProperty.call(row, code)) return row[code];
  if (row) return 0;
  return countryMedia(code).length;
}

function tabLabel(code) {
  const name = code === "RU" ? t("tab_russia") : state.text["country_" + code];
  if (code === "RU") return t("tab_russia");
  const stories = inNow() ? nowAttention(code).count : storedStoryCount(code);
  const usual = inNow() ? nowAttention(code).usual : null;
  const incidents = inNow()
    ? nowIncidents(code).length
    : activeEvents(current().week).filter((event) => concerns(event, code)).length;
  const usualText = usual == null ? "" : " (" + fill(t("tab_usual"), { count: usual }) + ")";
  const incidentText = incidents === 1 ? fill(t("tab_incident"), { count: incidents }) : fill(t("tab_incidents"), { count: incidents });
  return name + " · " + fill(t("tab_stories"), { count: stories }) + usualText + " · " + incidentText;
}

function renderStrip() {
  const strip = document.getElementById("country-strip");
  if (!strip) return;
  strip.innerHTML = "";
  const region = document.getElementById("region-state");
  if (region) region.replaceChildren();
  const note = document.getElementById("now-label");
  if (note) {
    note.hidden = !inNow();
    if (inNow()) note.textContent = t("now_scope");
  }
  COUNTRIES.concat(["RU"]).forEach((code) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "country-card" + (state.focus === code ? " picked" : "");
    button.setAttribute("aria-pressed", state.focus === code ? "true" : "false");
    button.id = code === "RU" ? "russia-square" : "country-" + code;
    button.dataset.country = code;
    const label = document.createElement("span");
    label.className = "tab-label";
    label.textContent = tabLabel(code);
    button.append(label);
    button.addEventListener("click", () => {
      stop();
      selectTab(code);
    });
    strip.appendChild(button);
  });
}

function syncDrawer() {
  document.body.classList.add("dossier-open");
  const brief = document.getElementById("country-brief");
  const inside = document.getElementById("inside-main");
  const russia = state.focus === "RU";
  if (brief) brief.hidden = russia;
  if (inside) inside.hidden = !russia;
}

function renderRegionOverview() {
  const section = document.getElementById("region-overview");
  if (!section) return;
  const open = !state.focus && !state.russiaOpen;
  section.hidden = !open;
  const close = document.getElementById("drawer-close");
  if (close) close.hidden = open;
  if (!open) return;
  if (inNow()) {
    const line = document.getElementById("region-overview-line");
    if (line) line.textContent = t("incidents_first");
    const eventsHost = document.getElementById("region-events");
    eventsHost.innerHTML = "";
    appendIncidentBlock(eventsHost, "Incidents this week", nowIncidents());
    appendIncidentBlock(eventsHost, "Recent incidents", recentIncidents());
    if (!eventsHost.childElementCount) {
      eventsHost.textContent = t("quiet_week");
    }
    const newsHost = document.getElementById("region-news");
    if (newsHost) {
      newsHost.innerHTML = "";
      const regional = (state.nowPack.news || []).filter((story) => story.week === current().week).slice(0, 3);
      if (regional.length) {
        const heading = document.createElement("h3");
        heading.className = "section-label";
        heading.textContent = t("regional_yle");
        const list = document.createElement("ul");
        regional.forEach((story) => appendStory(list, story));
        newsHost.append(heading, list);
      }
    }
    return;
  }
  const line = document.getElementById("region-overview-line");
  if (line) line.textContent = regionLine();
  const eventsHost = document.getElementById("region-events");
  eventsHost.innerHTML = "";
  const events = activeEvents(current().week);
  if (!events.length) {
    eventsHost.textContent = t("no_events");
  } else {
    const list = document.createElement("ul");
    events.forEach((event) => appendEventLine(list, event));
    eventsHost.appendChild(list);
  }
  const newsHost = document.getElementById("region-news");
  newsHost.innerHTML = "";
  const items = dedupeStories(weekNews());
  if (!items.length) {
    const empty = document.createElement("p");
    empty.textContent = t("no_news_week");
    newsHost.appendChild(empty);
    return;
  }
  const shown = state.moreRegion ? items : items.slice(0, 3);
  const list = document.createElement("ul");
  shown.forEach((story) => appendStory(list, story));
  newsHost.appendChild(list);
  if (items.length > 3) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "show-more";
    more.textContent = state.moreRegion ? "Show less" : "Show more";
    more.addEventListener("click", () => {
      state.moreRegion = !state.moreRegion;
      renderRegionOverview();
    });
    newsHost.appendChild(more);
  }
}

function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function setupDoors() {
  const doors = document.getElementById("doors");
  if (!doors) return;
  if (reducedMotion() || sessionStorage.getItem("efm-doors") || new URLSearchParams(location.search).get("mode") === "now") {
    doors.remove();
    return;
  }
  doors.hidden = false;
  const finish = () => {
    if (!doors.isConnected || doors.dataset.done) return;
    doors.dataset.done = "1";
    sessionStorage.setItem("efm-doors", "1");
    doors.classList.add("open");
    window.setTimeout(() => doors.remove(), 1100);
  };
  const skip = document.getElementById("skip-doors");
  if (skip) skip.addEventListener("click", finish);
  window.setTimeout(finish, 80);
}

function toggleRussia() {
  state.russiaOpen = !state.russiaOpen;
  if (state.russiaOpen) {
    state.focus = null;
    state.why = null;
    const panel = document.getElementById("why");
    if (panel) panel.hidden = true;
  }
  renderStrip();
  renderMap();
  renderCountryNews();
  renderOfficials();
  syncDrawer();
}

function pickCountry(code) {
  selectTab(code);
}

function clearFocus() {
  selectTab("LT");
}

function renderCountryNews() {
  const section = document.getElementById("country-news");
  if (!section) return;
  const code = state.focus;
  if (!code || code === "RU") {
    section.hidden = true;
    return;
  }
  const name = state.text["country_" + code];
  section.hidden = false;
  section.classList.add("picked");
  document.getElementById("country-news-title").textContent = fill(t("russian_media_about"), { name: name });
  const host = document.getElementById("country-news-list");
  host.innerHTML = "";
  let items = countryMedia(code);
  if (state.filter === "hostile") items = items.filter((story) => story.hostile);
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-line";
    empty.textContent = t("nothing_week");
    host.append(empty);
    if (!inNow()) return;
  } else {
    const shown = state.moreNews ? items : items.slice(0, 3);
    const list = document.createElement("ul");
    shown.forEach((story) => {
      if (!story.countries || !story.countries.length) story.countries = [code];
      appendStory(list, story);
    });
    host.append(list);
    if (items.length > 3) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "show-more";
      more.textContent = state.moreNews ? "Show less" : "Show more";
      more.addEventListener("click", () => {
        state.moreNews = !state.moreNews;
        renderCountryNews();
      });
      host.append(more);
    }
  }
  if (!inNow()) return;
}

function emptyLine(host) {
  if (!host) return;
  host.innerHTML = "";
  const line = document.createElement("p");
  line.className = "empty-line";
  line.textContent = t("nothing_week");
  host.append(line);
}

function regionalStories(code) {
  if (inNow()) {
    return (state.nowPack.news || []).filter((story) => story.week === current().week && (story.countries || []).includes(code)).slice(0, 3);
  }
  return weekNews().filter((story) => /yle\.fi|bbc\./i.test((story.outlet || "") + (story.url || "")) && (story.countries || []).includes(code)).slice(0, 3);
}

function bottomSentence(code) {
  if (code === "RU") {
    const source = inNow() ? state.nowPack.inside : state.insideMain;
    const cards = (((source || {}).weeks || {})[current().week] || {}).cards || [];
    const card = cards.find((item) => item.line);
    return card && card.line ? card.line : "Inside Russia is context only. It does not change the reading.";
  }
  const name = englishCountry(code);
  let attention = "There are stored Russian stories about " + name + " this week";
  if (inNow()) {
    const reading = nowAttention(code);
    if (reading.usual == null) attention = "Russian coverage of " + name + " has no usual for comparison";
    else if (reading.count > reading.usual) attention = "Russian coverage of " + name + " is above the usual";
    else if (reading.count < reading.usual) attention = "Russian coverage of " + name + " is below the usual";
    else attention = "Russian coverage of " + name + " matches the usual";
  }
  const incident = inNow() ? nowIncidents(code)[0] : null;
  if (incident) return attention + ". " + incidentLabel(incident) + ": " + incident.place + ".";
  const story = countryMedia(code)[0];
  if (story && englishText(story)) return attention + ". " + englishText(story) + ".";
  return attention + ".";
}

function bestHeadline(code) {
  const russian = countryMedia(code).filter((story) => englishText(story));
  const hostile = russian.find((story) => story.hostile);
  if (hostile) return hostile;
  if (russian.length) return russian[0];
  const regional = regionalStories(code).filter((story) => englishText(story));
  return regional[0] || null;
}

function appendInTheNews(host, story) {
  const list = document.createElement("ul");
  appendStory(list, story);
  if (!list.childElementCount) return false;
  const label = document.createElement("h3");
  label.className = "section-label";
  label.textContent = t("in_the_news");
  host.append(label, list);
  return true;
}

function snapshotIncidents(code) {
  return (state.nowPack && state.nowPack.incidents || [])
    .filter((item) => item.country === code)
    .slice()
    .sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : 0);
}

function addFact(list, label, value, source) {
  const item = document.createElement("li");
  const text = document.createElement("p");
  text.textContent = label + ": " + value;
  item.append(text);
  if (source) {
    const link = document.createElement("a");
    link.href = source;
    link.textContent = t("source");
    item.append(link);
  }
  list.append(item);
}

function renderFactCard(code) {
  const card = document.getElementById("country-facts");
  const body = document.getElementById("country-facts-body");
  if (!card || !body) return;
  const facts = state.facts && state.facts[code];
  if (!facts || code === "RU") {
    card.hidden = true;
    body.replaceChildren();
    return;
  }
  card.hidden = false;
  body.replaceChildren();
  const list = document.createElement("ul");
  list.className = "fact-list";
  if (facts.nato && facts.nato.date && facts.nato.source) {
    addFact(list, t("fact_nato"), dateWords(facts.nato.date), facts.nato.source);
  }
  (facts.borders || []).forEach((border) => {
    if (!border.text || !border.source) return;
    const label = border.with === "belarus" ? t("fact_border_belarus") : t("fact_border_russia");
    addFact(list, label, border.text, border.source);
  });
  const rows = snapshotIncidents(code);
  const latest = rows[rows.length - 1];
  if (latest && latest.source) {
    const value = rows.length + ". " + t("fact_latest") + ": " + dateWords(latest.date) + ", " + latest.place;
    addFact(list, t("fact_incidents"), value, latest.source);
  } else {
    addFact(list, t("fact_incidents"), "0. " + t("fact_latest") + ": " + t("fact_none"), "");
  }
  body.append(list);
}

function renderBriefing() {
  const code = state.focus || "LT";
  const title = document.getElementById("briefing-title");
  if (title) title.textContent = code === "RU" ? t("tab_russia") : (state.text["country_" + code] || code);
  const bottom = document.getElementById("bottom-line-text");
  if (bottom) bottom.textContent = bottomSentence(code);
  renderFactCard(code);
  if (code === "RU") return;
  ["brief-happened", "officials", "country-news"].forEach((id) => {
    const node = document.getElementById(id);
    if (node) node.hidden = false;
  });
  const happened = document.getElementById("region-events");
  if (happened) {
    happened.innerHTML = "";
    let hadItem = false;
    if (inNow()) {
      const items = nowIncidents(code);
      if (items.length) {
        hadItem = true;
        const list = document.createElement("ul");
        items.forEach((incident) => appendIncidentLine(list, incident));
        happened.append(list);
      }
    } else {
      const items = activeEvents(current().week).filter((event) => concerns(event, code));
      if (items.length) {
        hadItem = true;
        const list = document.createElement("ul");
        items.forEach((event) => appendEventLine(list, event));
        happened.append(list);
      }
    }
    if (!hadItem) {
      const story = bestHeadline(code);
      if (story) appendInTheNews(happened, story);
    }
    const stories = regionalStories(code);
    if (hadItem && stories.length) {
      const label = document.createElement("h3");
      label.className = "section-label";
      label.textContent = t("regional_media");
      const list = document.createElement("ul");
      stories.forEach((story) => appendStory(list, story));
      happened.append(label, list);
    }
    if (!happened.childElementCount) emptyLine(happened);
  }
  const regionalSection = document.getElementById("brief-regional");
  const regionalHost = document.getElementById("brief-regional-body");
  const stories = regionalStories(code);
  if (regionalSection) regionalSection.hidden = !stories.length;
  if (regionalHost) {
    regionalHost.innerHTML = "";
    if (stories.length) {
      const list = document.createElement("ul");
      stories.forEach((story) => appendStory(list, story));
      regionalHost.append(list);
    }
  }
  const ru = document.getElementById("officials-ru");
  const west = document.getElementById("officials-west");
  if (ru && west && !ru.childElementCount && !west.childElementCount) emptyLine(ru);
  collapseEmptyBriefing();
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
  when.textContent = dateWords(event.date);
  const note = document.createElement("p");
  note.textContent = plainNote(event.note);
  if (place.area) {
    const area = document.createElement("p");
    area.className = "note";
    area.textContent = t("area_note");
    box.append(title, when, note, area);
  } else {
    box.append(title, when, note);
  }
  const link = document.createElement("a");
  link.href = event.source;
  link.textContent = state.text.source;
  box.append(link);
}

function collapseEmptyBriefing() {
  const brief = document.getElementById("country-brief");
  if (!brief || brief.hidden) return;
  const lines = [...brief.querySelectorAll(".empty-line")].filter((node) => !node.closest("[hidden]"));
  lines.slice(1).forEach((node) => {
    const section = node.closest("section");
    node.remove();
    if (section && !section.querySelector("li, a, .empty-line")) section.hidden = true;
  });
}

function incidentIcons() {
  return {
    drone: "M0,-7 L6,5 L0,2 L-6,5 Z",
    aircraft: "M0,-6 L2,-1 L7,-1 L7,1 L2,1 L0,6 L-2,1 L-7,1 L-7,-1 L-2,-1 Z",
    border: "M-5,-5 H5 V5 H-5 Z",
    sabotage: "M0,-7 L1.5,-1.5 L7,-2 L2.5,1.5 L4,7 L0,3.5 L-4,7 L-2.5,1.5 L-7,-2 L-1.5,-1.5 Z",
  };
}

function renderLegend() {
  const host = document.getElementById("map-legend");
  if (!host) return;
  host.innerHTML = "";
  const icons = incidentIcons();
  ["drone", "aircraft", "border", "sabotage"].forEach((type) => {
    const item = document.createElement("span");
    item.className = "legend-item";
    item.dataset.type = type;
    item.append(iconSvg(icons[type]), document.createTextNode(t("legend_" + type)));
    host.append(item);
  });
  ["confirmed", "reported"].forEach((label) => {
    const item = document.createElement("span");
    item.className = "legend-item legend-" + label;
    item.textContent = t("legend_" + label);
    host.append(item);
  });
}

function iconSvg(path) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "-8 -8 16 16");
  svg.setAttribute("class", "legend-icon");
  svg.setAttribute("aria-hidden", "true");
  const shape = document.createElementNS("http://www.w3.org/2000/svg", "path");
  shape.setAttribute("d", path);
  shape.setAttribute("fill", "none");
  shape.setAttribute("stroke", "currentColor");
  shape.setAttribute("stroke-width", "1.4");
  svg.append(shape);
  return svg;
}

const MAP_HOME = { x: -40, y: -36, w: 860, h: 1060 };

function mapView() {
  if (!state.mapView) state.mapView = { x: MAP_HOME.x, y: MAP_HOME.y, w: MAP_HOME.w, h: MAP_HOME.h };
  return state.mapView;
}

function applyMapView(svg) {
  const view = mapView();
  svg.setAttribute("viewBox", view.x + " " + view.y + " " + view.w + " " + view.h);
  svg.setAttribute("data-zoom", String(Math.round(view.w)));
  if (state.mapFocusPlace) svg.setAttribute("data-focus-place", state.mapFocusPlace);
  if (svg.isConnected) layoutIncidents(svg);
}

const ICON_SCREEN_R = 18;

function pixelsPerUser(svg) {
  if (!svg || !svg.isConnected) return 0;
  const ctm = svg.getScreenCTM();
  if (ctm && ctm.a) return Math.abs(ctm.a);
  const rect = svg.getBoundingClientRect();
  const view = mapView();
  if (!rect.width || !view.w) return 0;
  return rect.width / view.w;
}

function fitIncidentIcons(svg) {
  const px = pixelsPerUser(svg);
  if (!px) return;
  const r = ICON_SCREEN_R / px;
  svg.querySelectorAll(".incident-dot circle").forEach((circle) => {
    circle.setAttribute("r", r.toFixed(3));
    circle.setAttribute("stroke-width", (1.5 / px).toFixed(3));
  });
  svg.querySelectorAll(".incident-dot path").forEach((icon) => {
    const s = r / 9;
    icon.setAttribute("transform", "scale(" + s.toFixed(4) + ")");
    icon.setAttribute("stroke-width", (1.2 / s).toFixed(3));
  });
  svg.querySelectorAll(".incident-count").forEach((text) => {
    text.setAttribute("font-size", (14 / px).toFixed(2));
  });
}

function clampMapView(minW) {
  const view = mapView();
  const floor = minW || MAP_HOME.w / 8;
  const maxW = MAP_HOME.w;
  view.w = Math.min(maxW, Math.max(floor, view.w));
  view.h = view.w * (MAP_HOME.h / MAP_HOME.w);
  const pad = 80;
  view.x = Math.min(MAP_HOME.x + MAP_HOME.w - view.w + pad, Math.max(MAP_HOME.x - pad, view.x));
  view.y = Math.min(MAP_HOME.y + MAP_HOME.h - view.h + pad, Math.max(MAP_HOME.y - pad, view.y));
}

function zoomMap(factor, anchor) {
  const view = mapView();
  const cx = anchor ? anchor.x : view.x + view.w / 2;
  const cy = anchor ? anchor.y : view.y + view.h / 2;
  const rx = (cx - view.x) / view.w;
  const ry = (cy - view.y) / view.h;
  view.w = view.w * factor;
  view.h = view.w * (MAP_HOME.h / MAP_HOME.w);
  clampMapView();
  view.x = cx - rx * view.w;
  view.y = cy - ry * view.h;
  clampMapView();
  const svg = document.getElementById("flank-map");
  if (svg) applyMapView(svg);
}

function resetMap() {
  state.mapView = { x: MAP_HOME.x, y: MAP_HOME.y, w: MAP_HOME.w, h: MAP_HOME.h };
  state.mapFocusPlace = "";
  const svg = document.getElementById("flank-map");
  if (svg) {
    svg.removeAttribute("data-focus-place");
    applyMapView(svg);
  }
}

function focusMap(lon, lat, place) {
  const point = project(Number(lon), Number(lat));
  const view = mapView();
  view.w = MAP_HOME.w / 5;
  view.h = view.w * (MAP_HOME.h / MAP_HOME.w);
  view.x = point[0] - view.w / 2;
  view.y = point[1] - view.h / 2;
  clampMapView();
  state.mapFocusPlace = place || "";
  const svg = document.getElementById("flank-map");
  if (svg) applyMapView(svg);
}

function focusIncident(incident) {
  if (!incident || incident.lon == null || incident.lat == null) return;
  focusMap(incident.lon, incident.lat, incident.place || "");
  if (incident.country && state.focus !== incident.country) selectTab(incident.country);
  else {
    const svg = document.getElementById("flank-map");
    if (svg) applyMapView(svg);
  }
}

function svgPoint(svg, event) {
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  return point.matrixTransform(ctm.inverse());
}

function mapScale(svg) {
  const ctm = svg.getScreenCTM();
  if (ctm && ctm.a) return { x: ctm.a, y: ctm.d };
  const rect = svg.getBoundingClientRect();
  const view = mapView();
  return {
    x: rect.width ? rect.width / view.w : 1,
    y: rect.height ? rect.height / view.h : 1,
  };
}

function onMapWheel(event) {
  const svg = document.getElementById("flank-map");
  if (!svg) return;
  event.preventDefault();
  const at = svgPoint(svg, event);
  zoomMap(event.deltaY > 0 ? 1.15 : 1 / 1.15, at);
}

function onMapPointerDown(event) {
  if (event.button !== 0) return;
  if (event.target.closest && event.target.closest("a, button")) return;
  const svg = document.getElementById("flank-map");
  if (!svg || !svg.contains(event.target)) return;
  const scale = mapScale(svg);
  state.mapDrag = {
    x: event.clientX,
    y: event.clientY,
    vx: mapView().x,
    vy: mapView().y,
    sx: scale.x || 1,
    sy: scale.y || 1,
    moved: false,
  };
  try { svg.setPointerCapture(event.pointerId); } catch (err) { /* capture can fail on a replaced node */ }
}

function onMapPointerMove(event) {
  const drag = state.mapDrag;
  if (!drag) return;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  if (Math.hypot(dx, dy) > 4) drag.moved = true;
  if (!drag.moved) return;
  const view = mapView();
  view.x = drag.vx - dx / drag.sx;
  view.y = drag.vy - dy / drag.sy;
  clampMapView();
  const svg = document.getElementById("flank-map");
  if (svg) applyMapView(svg);
  event.preventDefault();
}

function onMapPointerUp() {
  const drag = state.mapDrag;
  state.mapDrag = null;
  if (drag && drag.moved) state.mapSuppressClick = true;
}

function onMapClickCapture(event) {
  if (!state.mapSuppressClick) return;
  state.mapSuppressClick = false;
  event.stopPropagation();
  event.preventDefault();
}

function wireMapControls() {
  const host = document.getElementById("map");
  if (!host || host.dataset.wired) return;
  host.dataset.wired = "1";
  host.addEventListener("wheel", onMapWheel, { passive: false });
  host.addEventListener("pointerdown", onMapPointerDown);
  host.addEventListener("pointermove", onMapPointerMove);
  host.addEventListener("pointerup", onMapPointerUp);
  host.addEventListener("pointercancel", onMapPointerUp);
  host.addEventListener("click", onMapClickCapture, true);
  const zoomIn = document.getElementById("zoom-in");
  const zoomOut = document.getElementById("zoom-out");
  const zoomReset = document.getElementById("zoom-reset");
  if (zoomIn) zoomIn.addEventListener("click", () => zoomMap(1 / 1.25));
  if (zoomOut) zoomOut.addEventListener("click", () => zoomMap(1.25));
  if (zoomReset) zoomReset.addEventListener("click", resetMap);
  window.addEventListener("resize", () => {
    const svg = document.getElementById("flank-map");
    if (svg) layoutIncidents(svg);
  });
}

function renderMap() {
  const title = document.getElementById("map-title");
  if (title) title.textContent = state.text.map_title;
  const host = document.getElementById("map");
  renderLegend();
  const detail = document.getElementById("map-detail");
  if (detail) detail.hidden = true;
  if (!state.map) {
    host.textContent = "";
    return;
  }
  const week = current().week;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.id = "flank-map";
  applyMapView(svg);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Map of the eastern flank and nearby countries");
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
    const picked = state.focus === country.id || (state.russiaOpen && country.id === "RU");
    const dimmed = (state.focus && state.focus !== country.id) || (state.russiaOpen && country.id !== "RU");
    const kind = inNow() ? "now" : signFor(current()).kind;
    path.setAttribute("class", "land land-" + country.id + (COUNTRIES.includes(country.id) ? " state-" + kind : "") + (picked ? " picked" : "") + (dimmed ? " dimmed" : ""));
    const label = state.text["country_" + country.id] || country.name;
    path.setAttribute("aria-label", label);
    if (COUNTRIES.includes(country.id)) {
      path.addEventListener("click", () => {
        stop();
        pickCountry(country.id);
      });
    } else if (country.id === "UA") {
      path.addEventListener("click", () => {
        stop();
        openWhy(country.id);
      });
    } else if (country.id === "RU") {
      path.addEventListener("click", () => {
        stop();
        selectTab("RU");
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
  crimeaLabel.textContent = t("crimea");
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
  if (inNow()) drawIncidents(svg, week);
  host.innerHTML = "";
  host.appendChild(svg);
  layoutIncidents(svg);
  requestAnimationFrame(() => layoutIncidents(svg));
}

function drawIncidents(svg) {
  state.incidentMarks = activeIncidents();
  const layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  layer.id = "incident-layer";
  svg.appendChild(layer);
}

function clusterLimitPx() {
  return ICON_SCREEN_R * 4;
}

function clusterIncidents(svg, items) {
  const ctm = svg.getScreenCTM();
  const points = items.map((item, index) => {
    const at = project(Number(item.lon), Number(item.lat));
    const point = svg.createSVGPoint();
    point.x = at[0];
    point.y = at[1];
    const screen = ctm ? point.matrixTransform(ctm) : { x: 0, y: 0 };
    return { item, index, x: at[0], y: at[1], sx: screen.x, sy: screen.y };
  });
  const parent = points.map((point) => point.index);
  const find = (index) => {
    let at = index;
    while (parent[at] !== at) {
      parent[at] = parent[parent[at]];
      at = parent[at];
    }
    return at;
  };
  const limit = clusterLimitPx();
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      const apart = Math.hypot(points[i].sx - points[j].sx, points[i].sy - points[j].sy);
      if (apart < limit) parent[find(points[i].index)] = find(points[j].index);
    }
  }
  const groups = new Map();
  points.forEach((point) => {
    const key = find(point.index);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(point);
  });
  return [...groups.values()];
}

function labelBoxes(svg) {
  return [...svg.querySelectorAll(".map-label")].map((node) => node.getBBox());
}

function hitsLabel(x, y, r, boxes) {
  return boxes.some((box) => {
    const nearX = Math.max(box.x, Math.min(x, box.x + box.width));
    const nearY = Math.max(box.y, Math.min(y, box.y + box.height));
    return Math.hypot(x - nearX, y - nearY) < r + 4;
  });
}

function clearOfLabels(x, y, r, boxes) {
  if (!hitsLabel(x, y, r, boxes)) return [x, y];
  const step = r * 2.4;
  const shifts = [[step, 0], [-step, 0], [0, step], [0, -step], [step, step], [-step, step], [step, -step], [-step, -step]];
  for (let n = 1; n <= 3; n++) {
    for (const [dx, dy] of shifts) {
      const next = [x + dx * n, y + dy * n];
      if (!hitsLabel(next[0], next[1], r, boxes)) return next;
    }
  }
  return [x, y + step * 3];
}

function raiseCountryLabels(svg) {
  svg.querySelectorAll(".map-label").forEach((node) => svg.appendChild(node));
}

function zoomUntilSeparate(items) {
  const svg = document.getElementById("flank-map");
  if (!svg || items.length < 2) return;
  const projected = items.map((item) => project(Number(item.lon), Number(item.lat)));
  let minUser = Infinity;
  let cx = 0;
  let cy = 0;
  projected.forEach((point) => {
    cx += point[0];
    cy += point[1];
  });
  cx /= projected.length;
  cy /= projected.length;
  for (let i = 0; i < projected.length; i++) {
    for (let j = i + 1; j < projected.length; j++) {
      minUser = Math.min(minUser, Math.hypot(projected[i][0] - projected[j][0], projected[i][1] - projected[j][1]));
    }
  }
  const px = pixelsPerUser(svg);
  if (!px) return;
  const view = mapView();
  const needed = minUser > 0 ? minUser * px * view.w / clusterLimitPx() * 0.7 : view.w / 4;
  view.w = Math.min(view.w, needed);
  view.h = view.w * (MAP_HOME.h / MAP_HOME.w);
  view.x = cx - view.w / 2;
  view.y = cy - view.h / 2;
  clampMapView(Math.min(MAP_HOME.w / 8, needed));
  applyMapView(svg);
}

function layoutIncidents(svg) {
  const layer = svg.querySelector("#incident-layer");
  if (!layer) return;
  layer.replaceChildren();
  const items = state.incidentMarks || [];
  if (!items.length || !svg.getScreenCTM()) return;
  const px = pixelsPerUser(svg) || 1;
  const r = ICON_SCREEN_R / px;
  const boxes = labelBoxes(svg);
  const icons = incidentIcons();
  clusterIncidents(svg, items).forEach((group) => {
    if (group.length > 1) drawIncidentBadge(layer, group, r, boxes);
    else drawIncidentIcon(layer, group[0], r, boxes, icons);
  });
  fitIncidentIcons(svg);
  raiseCountryLabels(svg);
}

function drawIncidentIcon(layer, point, r, boxes, icons) {
  const incident = point.item;
  const [x, y] = clearOfLabels(point.x, point.y, r, boxes);
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const confirmed = /confirmed/i.test(incident.status || "");
  const reported = /reported/i.test(incident.status || incident.summary || "");
  dot.setAttribute("class", "incident-dot" + (confirmed ? " status-confirmed" : reported ? " status-reported" : ""));
  dot.setAttribute("data-type", incident.type || "unspecified");
  dot.setAttribute("data-date", incident.date);
  dot.setAttribute("data-country", incident.country);
  dot.setAttribute("data-place", incident.place || "");
  dot.setAttribute("transform", "translate(" + x.toFixed(1) + " " + y.toFixed(1) + ")");
  const shape = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  shape.setAttribute("r", r.toFixed(2));
  shape.setAttribute("fill", "#0f766e");
  shape.setAttribute("stroke", "#ffffff");
  shape.setAttribute("stroke-width", "2");
  dot.append(shape);
  if (icons[incident.type]) {
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "path");
    icon.setAttribute("d", icons[incident.type]);
    icon.setAttribute("fill", "none");
    icon.setAttribute("stroke", "#ffffff");
    icon.setAttribute("stroke-width", "1.4");
    dot.append(icon);
  }
  const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
  tip.textContent = incidentLabel(incident) + ". " + (incident.type || "unspecified") + ". " + incident.summary;
  dot.append(tip);
  dot.addEventListener("click", (click) => {
    click.stopPropagation();
    stop();
    openIncident(incident);
  });
  layer.appendChild(dot);
}

function drawIncidentBadge(layer, group, r, boxes) {
  const x0 = group.reduce((sum, point) => sum + point.x, 0) / group.length;
  const y0 = group.reduce((sum, point) => sum + point.y, 0) / group.length;
  const [x, y] = clearOfLabels(x0, y0, r, boxes);
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "g");
  dot.setAttribute("class", "incident-dot incident-badge");
  dot.setAttribute("data-count", String(group.length));
  dot.setAttribute("transform", "translate(" + x.toFixed(1) + " " + y.toFixed(1) + ")");
  const shape = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  shape.setAttribute("r", r.toFixed(2));
  shape.setAttribute("fill", "#0f766e");
  shape.setAttribute("stroke", "#ffffff");
  shape.setAttribute("stroke-width", "2");
  const count = document.createElementNS("http://www.w3.org/2000/svg", "text");
  count.setAttribute("class", "incident-count");
  count.setAttribute("text-anchor", "middle");
  count.setAttribute("dominant-baseline", "central");
  count.textContent = String(group.length);
  dot.append(shape, count);
  dot.addEventListener("click", (click) => {
    click.stopPropagation();
    stop();
    zoomUntilSeparate(group.map((point) => point.item));
  });
  layer.appendChild(dot);
}

function openIncident(incident) {
  if (incident && incident.country) selectTab(incident.country);
}

function renderNews() {
  if (inNow()) {
    renderNowNews();
    return;
  }
  const title = document.getElementById("news-title");
  if (title) title.textContent = state.text.news_title;
  document.getElementById("filter-all").textContent = state.text.filter_all;
  document.getElementById("filter-hostile").textContent = state.text.filter_hostile;
  document.getElementById("filter-all").setAttribute("aria-pressed", state.filter === "all" ? "true" : "false");
  document.getElementById("filter-hostile").setAttribute("aria-pressed", state.filter === "hostile" ? "true" : "false");
  document.getElementById("news-note").textContent = state.text.hostile_note;
  const host = document.getElementById("news");
  host.innerHTML = "";
  let items = dedupeStories(weekNews());
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
    heading.textContent = code === "other" ? t("not_one_country") : state.text["country_" + code];
    section.appendChild(heading);
    const list = document.createElement("ul");
    const expanded = Boolean(state.moreFeed[code]);
    const shown = expanded ? groups[code] : groups[code].slice(0, 3);
    shown.forEach((story) => appendStory(list, story));
    section.appendChild(list);
    if (groups[code].length > 3) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "show-more";
      more.textContent = expanded ? "Show less" : "Show more";
      more.addEventListener("click", () => {
        state.moreFeed[code] = !state.moreFeed[code];
        renderNews();
      });
      section.appendChild(more);
    }
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

function englishCountry(code) {
  return {
    FI: "Finland",
    EE: "Estonia",
    LV: "Latvia",
    LT: "Lithuania",
    PL: "Poland",
    UA: "Ukraine",
    BY: "Belarus",
    RU: "Russia",
    KG: "Kaliningrad",
  }[code] || code;
}

function dateWords(iso) {
  return formatDate(iso, state.lang || "en");
}

function rowForCode(code) {
  const region = code === "UA" ? "ukraine_test" : "eastern_flank";
  return state.rows.find((row) => row.region === region && row.week === current().week) || current();
}

function englishText(story) {
  if (story.english) return story.english;
  if (isEnglishTitle(story.title)) return story.title;
  return "";
}

function appendStory(list, story) {
  const english = englishText(story);
  if (!english) return;
  const item = document.createElement("li");
  item.className = "story";
  item.dataset.countries = (story.countries || []).join(",");
  const line = document.createElement("p");
  line.className = "headline-en";
  line.textContent = english;
  item.append(line);
  if (isCyrillic(story.title) && story.title !== english) {
    const original = document.createElement("p");
    original.className = "headline-ru";
    original.textContent = story.title;
    item.append(original);
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
  if (inNow() || !document.getElementById("why")) return;
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
  eventsHost.innerHTML = "";
  officialHost.innerHTML = "";
  const region = code === "UA" ? "ukraine_test" : "eastern_flank";
  let events = code
    ? activeEvents(current().week).filter((event) => concerns(event, code))
    : [];
  if (focus && !events.some((event) => event.date === focus.date && event.tag === focus.tag)) {
    events = [focus].concat(events);
  }
  const official = (state.official[current().week] || []).filter((item) => {
    if (code && item.countries && item.countries.length && !item.countries.includes(code)) return false;
    const story = { title: item.who || "", english: item.summary || "", summary: item.summary || "", who: item.who || "", kind: "official", url: item.url || "" };
    return showNews(story) && speakerSide(story) === "western" && flankTopic(story.title + " " + (story.english || "") + " " + (story.summary || "")) && !disallowedWesternSpeaker(story.title + " " + (story.english || ""));
  });
  let media = code ? countryMedia(code) : [];
  const quiet = !events.length && !official.length && !media.length;
  document.getElementById("why-quiet").hidden = !quiet;
  document.getElementById("why-body").hidden = quiet;
  if (quiet) return;
  if (!events.length) {
    eventsHost.textContent = media.length
      ? (englishText(media[0]).english || ("Headlines name " + name + " this week."))
      : "No events reported in our sources.";
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
  renderOfficials();
}

function renderMoodCard(article, item) {
  const sentence = document.createElement("p");
  sentence.className = "russia-line";
  sentence.textContent = item.line;
  const axis = document.createElement("p");
  axis.className = "note";
  axis.textContent = item.axis || "% of Russians naming this country unfriendly";
  const chart = document.createElement("div");
  chart.className = "mood-chart";
  const max = Math.max(...item.bars.map((bar) => Number(bar.pct) || 0), 1);
  item.bars.forEach((bar) => {
    const row = document.createElement("div");
    row.className = "mood-row" + (bar.reference ? " reference" : "");
    const name = document.createElement("span");
    name.className = "mood-name";
    name.textContent = bar.name;
    const track = document.createElement("span");
    track.className = "mood-track";
    const fill = document.createElement("span");
    fill.className = "mood-fill";
    fill.style.width = bar.pct == null ? "0" : Math.round((Number(bar.pct) / max) * 100) + "%";
    track.append(fill);
    const value = document.createElement("span");
    value.className = "mood-value";
    value.textContent = bar.pct == null ? "not listed" : bar.pct + "%";
    row.append(name, track, value);
    chart.append(row);
  });
  const meta = document.createElement("p");
  meta.className = "note mood-meta";
  meta.textContent = "Poll date: " + item.poll_date + ", published " + dateWords(item.published) + ". " + item.pollster + ". " + item.caution;
  const link = document.createElement("a");
  link.href = item.url;
  link.textContent = t("source");
  const details = document.createElement("details");
  details.className = "full-poll";
  const summary = document.createElement("summary");
  summary.textContent = "Full poll";
  const full = document.createElement("p");
  full.textContent = item.full || "";
  details.append(summary, full);
  article.append(sentence, axis, chart, meta, link, details);
}

function cardTitle(title) {
  const map = {
    "Defence Ministry": "card_mod",
    "Defence contractors": "card_plant",
    "Conscription": "card_conscription",
    "Ruble": "card_ruble",
    "Key rate": "card_key",
  };
  return map[title] ? t(map[title]) : title;
}

function cardStory(item) {
  return (item.english || "").trim();
}

function isEmptyCard(item) {
  const line = (item.line || "").trim();
  return !cardStory(item) && (!line || line === "No new data this week");
}

function isCountLine(line) {
  return /\d/.test(line || "") && /headline|post|event/i.test(line || "");
}

function inCallUp(week) {
  const start = new Date(week + "T00:00:00Z");
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + 6);
  const year = start.getUTCFullYear();
  const seasons = [
    [new Date(Date.UTC(year, 3, 1)), new Date(Date.UTC(year, 6, 15))],
    [new Date(Date.UTC(year, 9, 1)), new Date(Date.UTC(year, 11, 31))],
  ];
  return seasons.some(([open, close]) => start <= close && end >= open);
}

function conscriptionNews(item) {
  return Boolean(cardStory(item) || /\d+\s+conscription/i.test(item.line || ""));
}

function weekHasEvent(week) {
  return (state.events || []).some((event) => {
    const age = (Date.parse(week) - Date.parse(event.date)) / 86400000;
    return age >= 0 && age < 7;
  });
}

function weekNotable(week) {
  if (inNow()) return nowIncidents(null, week).length > 0;
  return weekHasEvent(week);
}

function eventLine(event) {
  return state.text[event.textKey] || (event.note || "").split(". ")[0];
}

function lastNotable(week) {
  const prior = (state.events || []).filter((event) => event.date <= week && event.source);
  if (!prior.length) return null;
  prior.sort((a, b) => (a.date < b.date ? 1 : -1));
  const event = prior[0];
  const weeks = Math.max(0, Math.round((Date.parse(week) - Date.parse(event.date)) / 86400000 / 7));
  return { weeks, line: eventLine(event), url: event.source };
}

function renderQuiet(week) {
  const quiet = document.getElementById("inside-quiet");
  if (!quiet) return;
  quiet.innerHTML = "";
  if (inNow()) {
    renderNowQuiet(quiet, week);
    return;
  }
  if (weekNotable(week)) {
    quiet.hidden = true;
    return;
  }
  const last = lastNotable(week);
  if (!last) {
    quiet.hidden = true;
    return;
  }
  quiet.hidden = false;
  const text = document.createElement("span");
  text.textContent = "Last notable: " + last.weeks + " weeks ago — " + last.line + " ";
  const link = document.createElement("a");
  link.href = last.url;
  link.textContent = t("source");
  quiet.append(text, link);
}

function renderNowQuiet(quiet, week) {
  if (nowIncidents(null, week).length) {
    quiet.hidden = true;
    return;
  }
  const prior = (state.nowPack.incidents || []).filter((item) => item.date < week && item.date >= state.nowPack.window_start);
  prior.sort((a, b) => (a.date < b.date ? 1 : -1));
  quiet.hidden = false;
  if (!prior.length) {
    quiet.textContent = "Quiet week.";
    return;
  }
  const last = prior[0];
  const weeks = Math.max(1, Math.round((Date.parse(week) - Date.parse(last.date)) / 86400000 / 7));
  const text = document.createElement("span");
  text.textContent = "Last notable: " + weeks + (weeks === 1 ? " week ago — " : " weeks ago — ") + last.place + ". " + last.summary + " ";
  const link = document.createElement("a");
  link.href = last.source;
  link.textContent = t("source");
  quiet.append(text, link);
}

function latestMood(week) {
  const weeks = Object.keys((state.insideMain && state.insideMain.weeks) || {}).filter((key) => key <= week).sort();
  let found = null;
  weeks.forEach((key) => {
    const mood = ((state.insideMain.weeks[key] || {}).cards || []).find((item) => item.title === "Public mood" && item.bars && item.bars.length);
    if (mood) found = mood;
  });
  return found;
}

function renderBackground(week) {
  const box = document.getElementById("inside-background");
  if (!box) return;
  box.innerHTML = "";
  const mood = latestMood(week);
  if (!mood) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  const label = document.createElement("h3");
  label.textContent = "Background";
  const line = document.createElement("p");
  line.textContent = mood.line;
  const when = document.createElement("p");
  when.className = "note";
  when.textContent = "Poll date: " + (mood.poll_date || "") + ", published " + dateWords(mood.published) + ".";
  const details = document.createElement("details");
  details.className = "full-poll";
  const summary = document.createElement("summary");
  summary.textContent = "Full poll";
  const chartHost = document.createElement("div");
  details.append(summary, chartHost);
  box.append(label, line, when, details);
  renderMoodCard(chartHost, mood);
}

function renderTicks() {
  const host = document.getElementById("week-ticks");
  if (!host) return;
  const rows = flankWeeks();
  if (host.childElementCount !== rows.length) {
    host.innerHTML = "";
    rows.forEach(() => {
      const tick = document.createElement("span");
      tick.className = "tick";
      host.append(tick);
    });
  }
  [...host.children].forEach((tick, index) => {
    tick.classList.toggle("notable", weekNotable(rows[index].week));
  });
}

function renderNowNews() {
  const host = document.getElementById("news");
  host.innerHTML = "";
  const week = current().week;
  const items = (state.nowPack.news || []).filter((story) => story.week === week);
  if (!items.length) {
    const empty = document.createElement("p");
    empty.textContent = t("no_yle");
    host.appendChild(empty);
    return;
  }
  const list = document.createElement("ul");
  items.slice(0, 8).forEach((story) => appendStory(list, story));
  host.appendChild(list);
}

function renderInsideMain() {
  const source = inNow() ? state.nowPack.inside : state.insideMain;
  const host = document.getElementById("inside-cards");
  if (!host || !source) return;
  const note = document.getElementById("inside-main-note");
  const coverage = document.getElementById("inside-coverage");
  const volume = document.getElementById("inside-volume");
  if (note) note.textContent = source.note || "";
  if (coverage) coverage.textContent = source.coverage || "";
  if (volume) volume.textContent = source.volume_note || "";
  host.innerHTML = "";
  const week = current().week;
  const block = (source.weeks || {})[week];
  const cards = block ? block.cards : [];
  renderQuiet(week);
  cards.forEach((item) => {
    if (item.title === "Public mood" || (item.bars && item.bars.length)) return;
    if (item.title === "Conscription" && !(inCallUp(week) || conscriptionNews(item))) return;
    if (isEmptyCard(item)) return;
    const article = document.createElement("article");
    article.className = "russia-card";
    const title = document.createElement("h3");
    title.textContent = cardTitle(item.title);
    const story = cardStory(item);
    const line = document.createElement("p");
    line.className = "russia-line";
    if (item.count) {
      line.textContent = item.line || item.english || "";
      const count = document.createElement("p");
      count.className = "card-count";
      count.textContent = item.count + (item.arrow ? " " + item.arrow : "");
      article.append(title, line, count);
    } else if (story) {
      line.textContent = story;
      article.append(title, line);
    } else if (isCountLine(item.line)) {
      article.classList.add("compact");
      line.className = "card-count";
      line.textContent = item.line + (item.arrow ? " " + item.arrow : "");
      article.append(title, line);
    } else {
      line.textContent = item.line + (item.arrow ? " " + item.arrow : "");
      article.append(title, line);
    }
    if (!item.count && story && isCountLine(item.line)) {
      const count = document.createElement("p");
      count.className = "card-count";
      count.textContent = item.line + (item.arrow ? " " + item.arrow : "");
      article.append(count);
    }
    if (item.russian) {
      const russian = document.createElement("p");
      russian.className = "headline-ru";
      russian.textContent = item.russian;
      article.append(russian);
    }
    if (item.url) {
      const link = document.createElement("a");
      link.href = item.url;
      link.textContent = t("source");
      article.append(link);
    }
    host.append(article);
  });
  if (!inNow()) renderBackground(week);
  renderTicks();
}

function renderWeek() {
  const rows = flankWeeks();
  const row = rows[state.index];
  const slider = document.getElementById("slider");
  slider.max = String(rows.length - 1);
  slider.value = String(state.index);
  document.getElementById("week-label").textContent = weekWords(row.week);
  renderStrip();
  renderMap();
  renderNews();
  const whyPanel = document.getElementById("why");
  if (whyPanel && !whyPanel.hidden && state.why && !inNow()) {
    const focus = state.events.find((event) => event.date === state.why.focusDate && event.tag === state.why.focusTag);
    openWhy(state.why.code, focus);
  }
  renderOfficials();
  renderBriefing();
  renderInside();
  renderInsideMain();
  renderCountryNews();
  syncDrawer();
}

function officialCode() {
  if (state.why && COUNTRIES.includes(state.why.code)) return state.why.code;
  return "REGION";
}

function renderInside() {
  const host = document.getElementById("inside-lines");
  if (!host) return;
  if (inNow()) {
    host.innerHTML = "";
    return;
  }
  if (!state.inside) return;
  const block = (state.inside.weeks || {})[current().week] || {};
  host.innerHTML = "";
  (block.lines || []).forEach((line) => {
    const item = document.createElement("li");
    item.className = "inside-line";
    const text = document.createElement("p");
    text.className = "headline-en";
    text.textContent = line.text.replaceAll("stored headlines", "headlines");
    if (!reducedMotion() && /\d/.test(line.text)) {
      const token = (state.countToken = (state.countToken || 0) + 1);
      const target = Number((line.text.match(/\d+/) || ["0"])[0]);
      let step = 0;
      const tick = () => {
        if (token !== state.countToken || !text.isConnected) return;
        step += 1;
        if (step >= 5) {
          text.textContent = line.text;
          return;
        }
        text.textContent = line.text.replace(String(target), String(Math.round(target * step / 5)));
        window.requestAnimationFrame(tick);
      };
      window.requestAnimationFrame(tick);
    }
    item.append(text);
    if (line.title && line.english && isCyrillic(line.title) && line.title !== line.english) {
      const original = document.createElement("p");
      original.className = "headline-ru";
      original.textContent = line.title;
      item.append(original);
    }
    if (line.url && line.english) {
      const link = document.createElement("a");
      link.href = line.url;
      link.textContent = line.outlet ? line.outlet : state.text.source;
      item.append(link);
    }
    host.append(item);
  });
  const background = document.getElementById("inside-background");
  if (background) background.textContent = block.background || "";
  const sources = document.getElementById("inside-sources");
  if (sources) sources.textContent = state.inside.sources || "";
}

function officialRows(side) {
  const week = state.officials[current().week] || {};
  const code = officialCode();
  const own = ((week[side] || {})[code] || []);
  const other = side === "russian" ? "western" : "russian";
  const moved = ((week[other] || {})[code] || []).filter((item) => speakerSide(item) === side);
  return dedupeStories(own.concat(moved)).filter((item) => {
    if (!showNews(item) || speakerSide(item) !== side) return false;
    if (side !== "western") return true;
    const blob = (item.title || "") + " " + (item.english || "") + " " + (item.summary || "");
    return flankTopic(blob) && !disallowedWesternSpeaker(blob);
  }).slice(0, 3);
}

function renderOfficials() {
  const section = document.getElementById("officials");
  const note = document.getElementById("officials-note");
  if (inNow()) {
    const code = state.focus;
    const week = current().week;
    const pool = (((state.nowHeadlines || {}).officials || {})[week] || {});
    const rows = code ? (pool[code] || []) : Object.values(pool).flat();
    const russian = dedupeStories(rows.filter((item) => russianSpeaker((item.title || "") + " " + (item.english || "")) && item.english)).slice(0, 3);
    const western = dedupeStories(rows.filter((item) => {
      const blob = (item.title || "") + " " + (item.english || "");
      return item.english && !russianSpeaker(blob) && westernSpeaker(blob) && flankTopic(blob);
    })).slice(0, 3);
    [["russian", russian], ["western", western]].forEach(([side, items]) => {
      const host = document.getElementById(side === "russian" ? "officials-ru" : "officials-west");
      if (!host) return;
      host.innerHTML = "";
      if (!items.length) return;
      const list = document.createElement("ul");
      items.forEach((story) => appendStory(list, story));
      host.append(list);
    });
    if (section) section.hidden = false;
    if (note) note.hidden = true;
    return;
  }
  if (section) section.hidden = false;
  if (note) note.hidden = false;
  ["russian", "western"].forEach((side) => {
    const host = document.getElementById(side === "russian" ? "officials-ru" : "officials-west");
    if (!host) return;
    host.innerHTML = "";
    const rows = officialRows(side);
    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "empty-line";
      empty.textContent = t("nothing_week");
      host.append(empty);
      return;
    }
    const list = document.createElement("ul");
    rows.forEach((story) => appendStory(list, story));
    host.append(list);
  });
}

function setToggle() {
  const button = document.getElementById("play");
  if (!button) return;
  const playing = Boolean(state.timer);
  button.textContent = playing ? t("pause") : t("play");
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

function nextIndex(from) {
  const rows = flankWeeks();
  const skip = document.getElementById("skip-quiet") && document.getElementById("skip-quiet").checked;
  let index = from + 1;
  if (!skip) return index;
  while (index < rows.length && !weekNotable(rows[index].week)) index += 1;
  return index;
}

function play() {
  stop();
  const token = state.playToken;
  state.timer = setInterval(() => {
    if (token !== state.playToken || !state.timer) return;
    const next = nextIndex(state.index);
    if (next >= flankWeeks().length) {
      stop();
      return;
    }
    state.index = next;
    renderWeek();
  }, 900);
  setToggle();
}

function togglePlayback() {
  if (state.timer) stop();
  else play();
}

async function main() {
  setupDoors();
  const [text, csv, events, map, news, official, countryHeadlines, officials, inside, insideMain, nowPack, nowHeadlines, replayCounts, appYaml, facts, fi, et, lv, lt, pl] = await Promise.all([
    fetch(asset("i18n/en.json")).then((response) => response.json()),
    fetch("../docs/reports/2026-10-12-backtest-weeks.csv").then((response) => response.text()),
    fetch(asset("events.json")).then((response) => response.json()),
    fetch(asset("vendor/flank-map.json")).then((response) => response.json()),
    fetch(asset("news.json")).then((response) => response.json()),
    fetch(asset("official.json")).then((response) => response.json()),
    fetch(asset("country-headlines.json")).then((response) => response.json()),
    fetch(asset("officials.json")).then((response) => response.json()),
    fetch(asset("inside-russia.json")).then((response) => response.json()),
    fetch(asset("inside-main.json")).then((response) => response.json()),
    fetch(asset("now-view.json")).then((response) => response.json()),
    fetch(asset("now-headlines.json")).then((response) => response.json()),
    fetch(asset("replay-counts.json")).then((response) => response.ok ? response.json() : { weeks: {} }),
    fetch("../config/app.yaml").then((response) => response.ok ? response.text() : ""),
    fetch(asset("country-facts.json")).then((response) => response.json()),
    fetch(asset("i18n/fi.json")).then((response) => response.json()),
    fetch(asset("i18n/et.json")).then((response) => response.json()),
    fetch(asset("i18n/lv.json")).then((response) => response.json()),
    fetch(asset("i18n/lt.json")).then((response) => response.json()),
    fetch(asset("i18n/pl.json")).then((response) => response.json()),
  ]);
  state.text = text;
  state.locales = { en: text, fi: fi, et: et, lv: lv, lt: lt, pl: pl };
  let saved = "en";
  try {
    saved = localStorage.getItem("efm-lang") || "en";
  } catch (err) {
    saved = "en";
  }
  state.lang = state.locales[saved] ? saved : "en";
  state.text = state.locales[state.lang];
  state.rows = parseCsv(csv).filter((row) => row.week >= START);
  state.events = events;
  state.map = map;
  state.news = news;
  state.official = official;
  state.officials = officials;
  state.inside = inside;
  state.insideMain = insideMain;
  state.nowPack = nowPack;
  state.facts = facts;
  state.nowHeadlines = nowHeadlines;
  state.replayCounts = replayCounts || { weeks: {} };
  state.appConfig = parseAppYaml(appYaml);
  state.countryHeadlines = countryHeadlines;
  document.title = text.title;
  document.getElementById("title").textContent = text.title;
  document.getElementById("banner").textContent = t("banner_replay");
  document.getElementById("play").textContent = t("play");
  document.getElementById("disclaimer-short").textContent = t("footer_warning");
  const aboutOpen = document.getElementById("about-open");
  const aboutClose = document.getElementById("about-close");
  const aboutPanel = document.getElementById("about-panel");
  if (aboutOpen && aboutPanel) {
    aboutOpen.addEventListener("click", () => { aboutPanel.hidden = false; });
  }
  if (aboutClose && aboutPanel) {
    aboutClose.addEventListener("click", () => { aboutPanel.hidden = true; });
  }
  applyCountdown();
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
  const whyClose = document.getElementById("why-close");
  if (whyClose) whyClose.addEventListener("click", () => { clearFocus(); });
  const drawerClose = document.getElementById("drawer-close");
  if (drawerClose) drawerClose.addEventListener("click", () => { stop(); clearFocus(); });
  document.getElementById("filter-all").addEventListener("click", () => {
    state.filter = "all";
    renderNews();
    renderCountryNews();
  });
  document.getElementById("filter-hostile").addEventListener("click", () => {
    state.filter = "hostile";
    renderNews();
    renderCountryNews();
  });
  const showAll = document.getElementById("show-all");
  if (showAll) showAll.addEventListener("click", () => { stop(); selectTab("LT"); });
  document.getElementById("mode-replay").addEventListener("click", () => setMode("replay"));
  document.getElementById("mode-now").addEventListener("click", () => setMode("now"));
  document.querySelectorAll("#lang-switch [data-lang]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  wireMapControls();
  applyChrome();
  if (params.get("mode") === "now") setMode("now");
  else renderWeek();
}

function setMode(mode) {
  stop();
  state.mode = mode;
  state.index = 0;
  state.focus = "LT";
  state.why = null;
  state.russiaOpen = false;
  document.getElementById("mode-replay").setAttribute("aria-pressed", mode === "replay" ? "true" : "false");
  document.getElementById("mode-now").setAttribute("aria-pressed", mode === "now" ? "true" : "false");
  const note = document.getElementById("now-label");
  if (note) note.hidden = mode !== "now";
  document.getElementById("banner").textContent = mode === "now"
    ? t("banner_now")
    : t("banner_replay");
  renderWeek();
}

function applyChrome() {
  document.documentElement.lang = state.lang || "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.getAttribute("data-i18n");
    if (key) node.textContent = t(key);
  });
  const note = document.getElementById("lang-note");
  if (note) {
    const foreign = state.lang && state.lang !== "en";
    note.hidden = !foreign;
    note.textContent = foreign ? t("translation_note") : "";
  }
  document.querySelectorAll("#lang-switch [data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.lang === (state.lang || "en") ? "true" : "false");
  });
  document.title = t("title");
  ["zoom-in", "zoom-out"].forEach((id) => {
    const button = document.getElementById(id);
    if (button) button.setAttribute("aria-label", t(id === "zoom-in" ? "zoom_in" : "zoom_out"));
  });
  const heading = document.getElementById("title");
  if (heading) heading.textContent = t("title");
}

function setLanguage(code) {
  const next = state.locales && state.locales[code] ? code : "en";
  state.lang = next;
  state.text = state.locales[next];
  try {
    localStorage.setItem("efm-lang", next);
  } catch (err) {
    /* storage can be blocked; the choice still applies to this view */
  }
  applyChrome();
  if (state.rows) renderWeek();
}

function parseAppYaml(text) {
  const config = {};
  String(text || "").split("\n").forEach((line) => {
    const match = line.match(/^([A-Za-z0-9_]+):\s*"?([^"#]*)"?\s*$/);
    if (match) config[match[1]] = match[2].trim();
  });
  return config;
}

function applyCountdown() {
  const node = document.getElementById("next-update");
  if (!node || typeof countdownState !== "function") return;
  const result = countdownState(state.appConfig || {}, new Date());
  node.hidden = !result.visible;
  node.textContent = result.visible ? result.text : "";
}

main();
