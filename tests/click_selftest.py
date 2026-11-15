#!/usr/bin/env python3
"""Click every country tab in both modes. No API calls.

    /home/supra/Projects/merdian/.venv/bin/python tests/click_selftest.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check2"
NOW_BANNER = "Snapshot: 3 Aug – 25 Oct 2026"
TABS = [
    ("FI", "Finland", "#country-FI"),
    ("EE", "Estonia", "#country-EE"),
    ("LV", "Latvia", "#country-LV"),
    ("LT", "Lithuania", "#country-LT"),
    ("PL", "Poland", "#country-PL"),
    ("RU", "Russia", "#russia-square"),
]
ORDER = [
    "Bottom line",
    "What happened",
    "What officials said",
    "What Russian media says",
    "What regional media says",
]


def headings(page) -> list[str]:
    return page.locator("#drawer h3").all_inner_texts()


def assert_tab(page, step: str, code: str, name: str, selector: str, *, now: bool) -> None:
    body = page.locator("body").inner_text()
    if "not in a separate file" in body:
        raise AssertionError(step + ": placeholder is visible")
    if "Dossier" in body:
        raise AssertionError(step + ": the word Dossier is visible")
    banner = page.locator("#banner").inner_text()
    if now and NOW_BANNER not in banner:
        raise AssertionError(step + ": banner is " + repr(banner))
    selected = page.locator(selector)
    if selected.get_attribute("aria-pressed") != "true":
        raise AssertionError(step + ": " + name + " tab is not selected")
    if "picked" not in (selected.get_attribute("class") or ""):
        raise AssertionError(step + ": " + name + " tab is not highlighted")
    land = page.locator("#flank-map [data-country='" + code + "']")
    if land.count() and "picked" not in (land.first.get_attribute("class") or ""):
        raise AssertionError(step + ": map shape for " + name + " is not highlighted")
    title = page.locator("#briefing-title").inner_text()
    if name not in title:
        raise AssertionError(step + ": briefing title is " + repr(title))
    bottom = page.locator("#bottom-line-text").inner_text().strip()
    if not bottom:
        raise AssertionError(step + ": bottom line is empty")
    found = headings(page)
    if code == "RU":
        if "Bottom line" not in found:
            raise AssertionError(step + ": Russia briefing headings " + repr(found))
        if "Inside Russia" not in page.locator("#inside-main").inner_text():
            raise AssertionError(step + ": Inside Russia cards are missing")
        if page.locator("#country-brief").is_visible():
            raise AssertionError(step + ": country sections are visible on Russia")
        return
    positions = []
    for label in ORDER:
        if label not in found:
            raise AssertionError(step + ": missing section " + label + " in " + repr(found))
        positions.append(found.index(label))
    if positions != sorted(positions):
        raise AssertionError(step + ": sections out of order " + repr(found))


def shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=True)


def set_now_week(page) -> None:
    page.locator("#slider").evaluate(
        """(slider) => {
          slider.value = String(state.nowPack.weeks.indexOf('2026-10-19'));
          slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
    )
    page.wait_for_function("document.getElementById('week-label').textContent.includes('October')")


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")
        if page.locator("#skip-doors").is_visible():
            page.locator("#skip-doors").click()
        page.locator("#mode-now").click()
        page.wait_for_function("document.getElementById('mode-now').getAttribute('aria-pressed') === 'true'")
        set_now_week(page)
        for code, name, selector in TABS:
            page.locator(selector).click()
            assert_tab(page, "now " + name, code, name, selector, now=True)
            if code == "LT":
                shot(page, "lithuania-2026-10-19.png")
            if code == "PL":
                shot(page, "poland.png")
            if code == "RU":
                shot(page, "russia.png")
        page.locator("#mode-replay").click()
        page.wait_for_function("document.getElementById('mode-replay').getAttribute('aria-pressed') === 'true'")
        for code, name, selector in TABS:
            page.locator(selector).click()
            assert_tab(page, "replay " + name, code, name, selector, now=False)
        browser.close()
    print("PASS click test")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL", exc)
        raise
