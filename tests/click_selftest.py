#!/usr/bin/env python3
"""Click the live page in order. No API calls.

Run with the machine Playwright, which is already installed:

    /home/supra/Projects/merdian/.venv/bin/python tests/click_selftest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path.home() / "Desktop" / "efm-check"
URL = "http://127.0.0.1:8080/frontend/"
NOW_BANNER = "Snapshot: 3 Aug – 25 Oct 2026 · attention and incidents only."
FORBIDDEN = "not in a separate file"


def dossier_title(page) -> str:
    parts = []
    for selector in ("#country-news-title", "#region-overview h2", "#inside-main h2", "#why-title"):
        node = page.locator(selector)
        if node.count() and node.first.is_visible():
            parts.append(node.first.inner_text())
    return " ".join(parts)


def assert_step(page, step: str, *, now: bool, chip: str | None, title: str) -> None:
    body = page.locator("body").inner_text()
    if FORBIDDEN in body:
        raise AssertionError(f"{step}: forbidden placeholder is visible")
    banner = page.locator("#banner").inner_text()
    if now and NOW_BANNER not in banner:
        raise AssertionError(f"{step}: banner is {banner!r}")
    if chip:
        selected = page.locator(chip)
        expect(selected).to_have_attribute("aria-pressed", "true")
        class_name = selected.get_attribute("class") or ""
        if "picked" not in class_name and chip != "#mode-now" and chip != "#mode-replay":
            raise AssertionError(f"{step}: {chip} is not highlighted ({class_name})")
    heading = dossier_title(page)
    if title not in heading:
        raise AssertionError(f"{step}: dossier title {heading!r} does not name {title}")


def shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="networkidle")
        page.locator("#skip-doors").click(timeout=2000) if page.locator("#skip-doors").is_visible() else None
        page.locator("#mode-now").click()
        page.wait_for_function("document.getElementById('mode-now').getAttribute('aria-pressed') === 'true'")
        assert_step(page, "a", now=True, chip=None, title="Region")
        shot(page, "a-now")

        page.locator("#country-LT").click()
        assert_step(page, "b", now=True, chip="#country-LT", title="Lithuania")
        shot(page, "b-lithuania")

        page.locator("#slider").evaluate(
            """(slider) => {
              const weeks = state.nowPack.weeks;
              slider.value = String(weeks.indexOf('2026-10-19'));
              slider.dispatchEvent(new Event('input', { bubbles: true }));
            }"""
        )
        page.wait_for_function("document.getElementById('week-label').textContent.includes('19') && document.getElementById('week-label').textContent.includes('October')")
        assert_step(page, "c", now=True, chip="#country-LT", title="Lithuania")
        shot(page, "c-week")

        page.locator("#country-PL").click()
        assert_step(page, "d", now=True, chip="#country-PL", title="Poland")
        shot(page, "d-poland")

        page.locator("#show-all").click()
        assert_step(page, "e", now=True, chip=None, title="Region")
        shot(page, "e-show-all")

        page.locator("#russia-square").click()
        assert_step(page, "f", now=True, chip="#russia-square", title="Inside Russia")
        shot(page, "f-russia")

        page.locator("#drawer-close").click()
        assert_step(page, "g", now=True, chip=None, title="Region")
        shot(page, "g-close")

        page.locator("#mode-replay").click()
        page.wait_for_function("document.getElementById('mode-replay').getAttribute('aria-pressed') === 'true'")
        assert_step(page, "h", now=False, chip=None, title="Region")
        shot(page, "h-replay")

        page.locator("#country-FI").click()
        assert_step(page, "i", now=False, chip="#country-FI", title="Finland")
        shot(page, "i-finland")
        browser.close()
    print("PASS click test")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL", exc)
        raise
