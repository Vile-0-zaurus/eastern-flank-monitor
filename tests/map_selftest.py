#!/usr/bin/env python3
"""Map icon size, label clearance, and country-tab zoom. No API calls.

    /home/supra/Projects/merdian/.venv/bin/python tests/map_selftest.py
"""
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
CODES = ("FI", "EE", "LV", "LT", "PL")


def icon_width(page) -> float:
    return page.evaluate(
        """() => {
          const circle = document.querySelector('.incident-dot circle');
          if (!circle) return 0;
          return circle.getBoundingClientRect().width;
        }"""
    )


def overlaps(page) -> int:
    return page.evaluate(
        """() => {
          const labels = [...document.querySelectorAll('.map-label')].map((node) => node.getBoundingClientRect());
          const dots = [...document.querySelectorAll('.incident-dot circle')].map((node) => node.getBoundingClientRect());
          let count = 0;
          dots.forEach((dot) => {
            labels.forEach((label) => {
              const hit = dot.left < label.right && dot.right > label.left && dot.top < label.bottom && dot.bottom > label.top;
              if (hit) count += 1;
            });
          });
          return count;
        }"""
    )


def main() -> int:
    problems = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="networkidle")
        if page.locator("#skip-doors").is_visible():
            page.locator("#skip-doors").click()
        page.locator("#mode-now").click()
        page.locator("#slider").evaluate(
            """(slider) => {
              slider.value = String(state.nowPack.weeks.indexOf('2026-10-12'));
              slider.dispatchEvent(new Event('input', { bubbles: true }));
            }"""
        )
        page.wait_for_function("document.querySelector('.incident-dot circle')")
        widths = []
        for factor in (1, 2, 4):
            page.evaluate(
                """(factor) => {
                  const view = mapView();
                  view.w = 860 / factor;
                  view.h = view.w * (1060 / 860);
                  view.x = -40;
                  view.y = -36;
                  applyMapView(document.getElementById('flank-map'));
                }""",
                factor,
            )
            page.wait_for_timeout(40)
            widths.append(icon_width(page))
        spread = max(widths) - min(widths)
        if spread > 2:
            problems.append("icon size changed with zoom " + str([round(item, 1) for item in widths]))
        for code in CODES:
            page.locator("#country-" + code).click()
            page.wait_for_function(
                "(code) => document.getElementById('flank-map').getAttribute('data-country-zoom') === code",
                arg=code,
                timeout=4000,
            )
            row = page.evaluate(
                """(code) => {
                  const path = document.querySelector("#flank-map [data-country='" + code + "']");
                  const box = path.getBBox();
                  const view = mapView();
                  const cx = box.x + box.width / 2;
                  const cy = box.y + box.height / 2;
                  const inside = cx >= view.x && cx <= view.x + view.w && cy >= view.y && cy <= view.y + view.h;
                  return { w: view.w, inside: inside, captions: document.querySelectorAll('.map-icon-label').length };
                }""",
                code,
            )
            if row["w"] >= 860 or not row["inside"]:
                problems.append(code + " tab did not zoom to the country")
            if overlaps(page):
                problems.append(code + " icon covers a country label")
        page.locator("#zoom-reset").click()
        page.wait_for_function(
            "() => !document.getElementById('flank-map').getAttribute('data-country-zoom') && Number(document.getElementById('flank-map').getAttribute('data-zoom')) === 860",
            timeout=4000,
        )
        browser.close()
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print("PASS map test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
