#!/usr/bin/env node
const assert = require("assert");
const { formatDate } = require("../frontend/dates.js");

const iso = "2026-10-12";
assert.strictEqual(formatDate(iso, "en"), "12 October 2026");
assert.strictEqual(formatDate(iso, "fi"), "12. lokakuuta 2026");
assert.strictEqual(formatDate(iso, "lt"), "2026 m. spalio 12 d.");
assert.strictEqual(formatDate(iso, "pl"), "12 października 2026");
assert.ok(!formatDate(iso, "lv").toLowerCase().includes("week"));
assert.ok(!formatDate(iso, "et").toLowerCase().includes("nädal"));
console.log("PASS date formats", formatDate(iso, "et"), formatDate(iso, "lv"));
