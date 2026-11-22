/* Countdown visibility. Shown only when live monitoring is on. */
function countdownState(config, now) {
  const on = String((config && config.live_monitoring) || "").trim() === "on";
  const end = String((config && config.live_end_date) || "").trim();
  const current = now instanceof Date ? now : new Date();
  const today = current.toISOString().slice(0, 10);
  if (end && today >= end) {
    return { visible: false, ended: true, text: "Live monitoring ended " + end };
  }
  const stamp = config && config.next_update_time;
  if (!on || !stamp) return { visible: false, ended: false, text: "" };
  const match = String(stamp).match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return { visible: false, ended: false, text: "" };
  const next = new Date(current.getTime());
  next.setHours(Number(match[1]), Number(match[2]), 0, 0);
  if (next <= current) next.setDate(next.getDate() + 1);
  const minutes = Math.max(0, Math.round((next - current) / 60000));
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return { visible: true, ended: false, text: "Next update in " + hh + ":" + mm };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { countdownState: countdownState };
}
