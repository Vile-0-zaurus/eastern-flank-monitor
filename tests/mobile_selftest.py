#!/usr/bin/env python3
"""Mobile layout. No API calls.

    python3 tests/mobile_selftest.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-mobile"
DEVICES = [
    ("iphone-13", {"width": 390, "height": 844}, True),
    ("pixel-7", {"width": 412, "height": 915}, True),
    ("ipad", {"width": 810, "height": 1080}, True),
]


def check(page, name: str, lang: str) -> list[str]:
    problems = []
    page.goto(URL, wait_until="networkidle")
    if page.locator("#skip-doors").is_visible():
        page.locator("#skip-doors").click()
    page.locator("#mode-now").click()
    page.locator(f"[data-lang='{lang}']").click()
    page.locator("#slider").evaluate(
        """(slider) => {
          slider.value = String(state.nowPack.weeks.indexOf("2026-10-12"));
          slider.dispatchEvent(new Event("input", { bubbles: true }));
        }"""
    )
    page.wait_for_selector(".incident-dot", timeout=10000)
    page.wait_for_timeout(400)
    metrics = page.evaluate(
        """() => {
          const strip = document.getElementById("country-strip");
          const map = document.getElementById("map");
          const drawer = document.getElementById("drawer");
          const bodySize = parseFloat(getComputedStyle(document.body).fontSize);
          const stripStyle = getComputedStyle(strip);
          return {
            pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            stripOverflow: stripStyle.overflowX,
            stripWrap: stripStyle.flexWrap,
            stripCanScroll: strip.scrollWidth > strip.clientWidth + 1,
            mapTop: map.closest("#map-panel").getBoundingClientRect().top,
            drawerTop: drawer.getBoundingClientRect().top,
            bodySize: bodySize,
          };
        }"""
    )
    if metrics["pageOverflow"] > 1:
        problems.append(name + " page scrolls sideways")
    if metrics["stripOverflow"] != "auto" or metrics["stripWrap"] != "nowrap":
        problems.append(name + " tabs do not scroll in one row")
    if name.startswith("iphone") and not metrics["stripCanScroll"]:
        problems.append(name + " tabs fit without a scroll, so the row is not scrollable")
    if metrics["mapTop"] >= metrics["drawerTop"]:
        problems.append(name + " map is not above the briefing")
    if metrics["bodySize"] < 16:
        problems.append(name + " text is under 16px")
    page.evaluate(
        """() => {
          const node = document.querySelector(".incident-dot");
          node.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerType: "touch" }));
        }"""
    )
    page.wait_for_timeout(200)
    if page.locator("#incident-card").get_attribute("hidden") is not None:
        problems.append(name + " tap did not open the hover card")
    page.locator("#about-open").click()
    page.wait_for_timeout(200)
    fits = page.evaluate(
        """() => {
          const card = document.querySelector(".about-card");
          const box = card.getBoundingClientRect();
          return box.top >= 0 && box.bottom <= window.innerHeight + 1 && box.right <= window.innerWidth + 1;
        }"""
    )
    if not fits:
        problems.append(name + " About does not fit")
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    return problems


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        for device, viewport, touch in DEVICES:
            for lang in ("en", "lt"):
                context = browser.new_context(
                    viewport=viewport,
                    has_touch=touch,
                    is_mobile=device != "ipad",
                )
                page = context.new_page()
                problems.extend(check(page, device + "-" + lang, lang))
                context.close()
        browser.close()
    if problems:
        print("FAIL")
        for item in problems:
            print("- " + item)
        return 1
    print("PASS mobile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
