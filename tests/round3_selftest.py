#!/usr/bin/env python3
"""Round 3 checks. No API calls.

    python3 tests/round3_selftest.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check6"


def set_week(page, week: str) -> None:
    page.locator("#slider").evaluate(
        """(slider, week) => {
          const weeks = state.mode === "now" ? state.nowPack.weeks : flankWeeks().map((row) => row.week);
          slider.value = String(weeks.indexOf(week));
          slider.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
        week,
    )
    page.wait_for_timeout(400)


def hover_place(page, place: str) -> None:
    page.evaluate(
        """(place) => {
          const node = [...document.querySelectorAll(".incident-dot")].find((item) => item.getAttribute("data-place") === place);
          if (!node) throw new Error("missing icon " + place);
          node.dispatchEvent(new PointerEvent("pointerenter", { bubbles: true, pointerType: "mouse" }));
        }""",
        place,
    )
    page.wait_for_timeout(200)


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")
        if page.locator("#skip-doors").is_visible():
            page.locator("#skip-doors").click()
        page.locator("#mode-now").click()
        page.wait_for_function("document.getElementById('mode-now').getAttribute('aria-pressed') === 'true'")

        titles = page.evaluate("() => document.querySelectorAll('#map-svg title, #map-panel [title], #map-svg [title]').length")
        if titles:
            problems.append("map still has a native title")

        set_week(page, "2026-08-10")
        page.locator("#country-LV").click()
        page.wait_for_timeout(300)
        hover_place(page, "Balvi Municipality")
        card = page.locator("#incident-card")
        if card.get_attribute("hidden") is not None:
            problems.append("Balvi hover card did not open")
        balvi = card.inner_text()
        if "Balvi" not in balvi or "Officially confirmed" not in balvi:
            problems.append("Balvi card text is wrong")
        page.screenshot(path=str(SHOTS / "latvia-balvi-confirmed.png"))

        reported = page.evaluate(
            """() => {
              const node = document.querySelector(".incident-dot.status-confirmed");
              if (!node) return null;
              const halo = node.querySelector("circle.halo");
              const path = node.querySelector("path");
              return {
                halo: halo && halo.getAttribute("fill"),
                fill: path && path.getAttribute("fill"),
              };
            }"""
        )
        if not reported or reported.get("halo") != "#1c1917" or reported.get("fill") != "#ffffff":
            problems.append("confirmed icon is not solid white on a dark halo")

        set_week(page, "2026-10-12")
        page.locator("#country-LT").click()
        page.wait_for_timeout(300)
        place = page.evaluate(
            """() => {
              const node = document.querySelector(".incident-dot.status-reported");
              return node ? node.getAttribute("data-place") : "";
            }"""
        )
        if not place:
            problems.append("no reported icon in the Lithuania week of 12 October")
        else:
            style = page.evaluate(
                """(place) => {
                  const node = [...document.querySelectorAll(".incident-dot")].find((item) => item.getAttribute("data-place") === place);
                  const ring = node && node.querySelector("circle.ring");
                  return ring ? { stroke: ring.getAttribute("stroke"), dash: ring.getAttribute("stroke-dasharray") } : null;
                }""",
                place,
            )
            if not style or style.get("stroke") != "#f59e0b" or not style.get("dash"):
                problems.append("reported icon is not an amber dashed outline")
            hover_place(page, place)
            if card.count() != 1:
                problems.append("more than one hover card")
            if place not in card.inner_text():
                problems.append("second hover did not replace the card")
            page.screenshot(path=str(SHOTS / "lithuania-reported-hover.png"))

        page.locator("#country-EE").click()
        page.wait_for_timeout(300)
        facts = page.locator("#country-facts")
        if facts.get_attribute("hidden") is not None:
            problems.append("country facts card is hidden")
        links = facts.locator("a")
        if links.count() < 3:
            problems.append("country facts are missing source links")
        page.screenshot(path=str(SHOTS / "estonia-facts.png"))

        page.locator("#russia-square").click()
        page.wait_for_timeout(400)
        background = page.locator("#inside-background").inner_text()
        if "2026" not in background:
            problems.append("Now poll does not show 2026")
        if "2021" in background and "May 2026" not in background:
            problems.append("Now poll is still the 2021 poll")
        page.screenshot(path=str(SHOTS / "russia-poll-now.png"))

        page.locator("#mode-replay").click()
        page.wait_for_function("document.getElementById('mode-replay').getAttribute('aria-pressed') === 'true'")
        set_week(page, "2021-09-06")
        page.locator("#russia-square").click()
        page.wait_for_timeout(400)
        replay = page.locator("#inside-background").inner_text()
        if "2021" not in replay:
            problems.append("replay poll is not 2021")
        if "May 2026" in replay:
            problems.append("replay shows the 2026 poll")
        browser.close()
    if problems:
        print("FAIL")
        for item in problems:
            print("- " + item)
        return 1
    print("PASS round 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
