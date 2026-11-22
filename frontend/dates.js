/* Locale dates. Article dates must not use the week-of label. */
const DATE_LOCALE = {
  en: "en-GB",
  fi: "fi-FI",
  et: "et-EE",
  lv: "lv-LV",
  lt: "lt-LT",
  pl: "pl-PL",
};

function formatDate(iso, lang) {
  if (!iso || !/^\d{4}-\d{2}-\d{2}/.test(iso)) return iso || "";
  const parts = iso.slice(0, 10).split("-");
  const date = new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
  const locale = DATE_LOCALE[lang] || "en-GB";
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatDate: formatDate, DATE_LOCALE: DATE_LOCALE };
}
