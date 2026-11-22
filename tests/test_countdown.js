#!/usr/bin/env node
const assert = require("assert");
const { countdownState } = require("../frontend/countdown.js");

const now = new Date("2026-11-22T12:00:00");
const off = countdownState({ live_monitoring: "off", next_update_time: "06:00" }, now);
assert.strictEqual(off.visible, false);
assert.strictEqual(off.text, "");

const missing = countdownState({ live_monitoring: "on" }, now);
assert.strictEqual(missing.visible, false);

const on = countdownState({ live_monitoring: "on", next_update_time: "18:30" }, now);
assert.strictEqual(on.visible, true);
assert.strictEqual(on.text, "Next update in 06:30");

const wrapped = countdownState({ live_monitoring: "on", next_update_time: "06:00" }, now);
assert.strictEqual(wrapped.visible, true);
assert.strictEqual(wrapped.text, "Next update in 18:00");

console.log("PASS countdown both states");
