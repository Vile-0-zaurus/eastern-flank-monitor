#!/usr/bin/env python3
"""Map clarity: five-week window, no badges, hover card, status marks.

    python3 tests/map_clarity_selftest.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check5"
NAMES = {
    "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus",
    "Ukraine", "Western Russia", "Kaliningrad", "Crimea",
}


def set_week(page, week: str) -> None:
    page.locator("#slider").evaluate(
        """(slider, week) => {
          const index = state.nowPack.weeks.indexOf(week);
          if (index < 0) throw new Error('missing week ' + week);
          slider.value = String(index);
          slider.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        week,
    )


def main() -> int:
    problems = []
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("pageerror", lambda exc: problems.append("page " + str(exc)))
        page.goto(URL, wait_until="networkidle")
        if page.locator("#skip-doors").is_visible():
            page.locator("#skip-doors").click()
        page.locator("#mode-now").click()
        set_week(page, "2026-10-12")
        page.wait_for_timeout(250)
        if page.locator(".incident-badge, .incident-count").count():
            problems.append("count badge is still on the map")
        extra = page.evaluate(
            """(names) => [...document.querySelectorAll('#flank-map text')].map((node) => node.textContent.trim()).filter((text) => text && !names.includes(text))""",
            list(NAMES),
        )
        if extra:
            problems.append("map text besides country names: " + str(extra))
        old = page.evaluate(
            """() => [...document.querySelectorAll('.incident-dot')].map((node) => node.getAttribute('data-date')).filter((date) => date && date < '2026-09-14')"""
        )
        if old:
            problems.append("old incidents still visible: " + str(old))
        set_week(page, "2026-09-21")
        page.locator("#country-PL").click()
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-country-zoom') === 'PL'", timeout=4000)
        page.screenshot(path=str(SHOTS / "poland-2026-09-21.png"), full_page=True)
        set_week(page, "2026-08-10")
        page.locator("#country-LV").click()
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-country-zoom') === 'LV'", timeout=4000)
        places = page.evaluate(
            """() => [...document.querySelectorAll('.incident-dot')].filter((node) => {
              const box = node.getBoundingClientRect();
              return box.width > 0 && box.bottom > 0 && box.top < window.innerHeight && box.right > 0 && box.left < window.innerWidth;
            }).map((node) => node.getAttribute('data-place'))"""
        )
        if not places:
            problems.append("no visible icons in the Latvia week of 10 August")
        for place in places:
            status = page.locator(".incident-dot[data-place='" + place + "']").get_attribute("data-status")
            halo = page.locator(".incident-dot[data-place='" + place + "'] circle.halo").get_attribute("fill")
            path_fill = page.locator(".incident-dot[data-place='" + place + "'] path").get_attribute("fill")
            ring = page.locator(".incident-dot[data-place='" + place + "'] circle.ring")
            if halo != "#1c1917":
                problems.append("icon missing a dark halo")
            if status == "confirmed" and path_fill != "#ffffff":
                problems.append("confirmed icon is not solid white")
            if status == "reported" and ring.count() == 0:
                problems.append("reported icon has no dashed ring")
            page.evaluate(
                """(place) => {
                  const node = [...document.querySelectorAll('.incident-dot')].find((item) => item.getAttribute('data-place') === place);
                  if (node) node.dispatchEvent(new PointerEvent('pointerenter', { bubbles: true, pointerType: 'mouse' }));
                }""",
                place,
            )
            page.wait_for_timeout(40)
            card = page.locator("#incident-card")
            if card.get_attribute("hidden") is not None:
                problems.append("hover card hidden for " + place)
                continue
            text = card.inner_text()
            if place not in text:
                problems.append("card missing " + place)
            if "Officially confirmed" not in text and "Reported only" not in text:
                problems.append("card missing status for " + place)
        page.evaluate(
            """() => {
              const node = document.querySelector(".incident-dot[data-place='Balvi Municipality']");
              if (node) node.dispatchEvent(new PointerEvent('pointerenter', { bubbles: true, pointerType: 'mouse' }));
            }"""
        )
        if "Balvi Municipality" not in places:
            problems.append("Balvi icon is hidden in its own week")
        page.screenshot(path=str(SHOTS / "latvia-balvi-hover.png"), full_page=True)
        browser.close()
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print("PASS map clarity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
