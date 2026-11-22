#!/usr/bin/env python3
"""Switch every interface language. No API calls."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check3"
CODES = ("en", "fi", "et", "lv", "lt", "pl")
EXACT = "Built only from publicly available sources:"


def pack(code):
    return json.loads((ROOT / "frontend/i18n" / f"{code}.json").read_text(encoding="utf-8"))


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")
        if page.locator("#skip-doors").is_visible():
            page.locator("#skip-doors").click()
        for code in CODES:
            text = pack(code)
            page.locator(f'#lang-switch [data-lang="{code}"]').click()
            page.wait_for_function(
                "(code) => document.documentElement.lang === code",
                arg=code,
            )
            about = page.locator("#about-open").inner_text().strip()
            if about != text["about"]:
                raise AssertionError(code + " About button is " + repr(about))
            heading = page.locator("[data-i18n='heading_bottom']").inner_text().strip()
            if heading != text["heading_bottom"]:
                raise AssertionError(code + " heading is " + repr(heading))
            overflow = page.evaluate(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth + 8"
            )
            if overflow:
                raise AssertionError(code + " layout overflows")
            page.locator("#about-open").click()
            page.wait_for_function("document.getElementById('about-panel').hidden === false")
            exact = page.locator("#about-exact").inner_text().strip()
            if exact != text["about_exact"]:
                raise AssertionError(code + " About text mismatch")
            if code != "en" and exact.startswith(EXACT):
                raise AssertionError(code + " About text is still English")
            page.locator("#about-close").click()
            page.wait_for_function("document.getElementById('about-panel').hidden === true")
            if code != "en" and page.locator("#lang-note").is_hidden():
                raise AssertionError(code + " translation note is hidden")
        page.locator('#lang-switch [data-lang="lt"]').click()
        page.locator("#mode-now").click()
        page.locator("#slider").evaluate(
            """(slider) => {
              const index = state.nowPack.weeks.indexOf('2026-10-19');
              slider.value = String(index);
              slider.dispatchEvent(new Event('input', { bubbles: true }));
            }"""
        )
        page.locator("#country-LT").click()
        page.screenshot(path=str(SHOTS / "lithuania-lt.png"), full_page=True)
        page.locator('#lang-switch [data-lang="pl"]').click()
        page.locator("#country-LT").click()
        page.screenshot(path=str(SHOTS / "lithuania-pl.png"), full_page=True)
        page.locator("#russia-square").click()
        body = page.locator("#inside-main").inner_text()
        if "rubles per dollar" not in body and "official data not reachable" not in body:
            raise AssertionError("Russia tab missing economy line")
        page.screenshot(path=str(SHOTS / "russia-now-2026-10-19.png"), full_page=True)
        browser.close()
    print("PASS language switch")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL", exc)
        raise
