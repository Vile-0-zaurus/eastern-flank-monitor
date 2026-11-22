#!/usr/bin/env python3
"""Russia tab notes, fact card, and briefing checks. No API calls.

    python3 tests/russia_selftest.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check5"
TRANSLATED = ("Latvija", "Eesti", "Lietuva", "Polska", "Suomi", "Igaunija", "Estija", "Lenkija", "Somija", "Viro")


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
        dates = page.evaluate(
            """() => {
              const out = {};
              ['en', 'fi', 'et', 'lv', 'lt', 'pl'].forEach((code) => { out[code] = formatDate('2026-10-12', code); });
              return out;
            }"""
        )
        if "12" not in dates["en"]:
            problems.append("English date is " + dates["en"])
        for code, text in dates.items():
            if code != "en" and text == dates["en"]:
                problems.append(code + " date is still English")
        page.locator("#russia-square").click()
        page.wait_for_timeout(300)
        set_week(page, "2026-10-12")
        page.wait_for_timeout(200)
        note = page.locator("#inside-main-note").inner_text()
        if note != "Display only — does not change the reading.":
            problems.append("Russia note is " + note)
        briefing = page.locator("#inside-main").inner_text()
        for phrase in ("No model call", "median weekly count", "frozen window"):
            if phrase in briefing:
                problems.append("technical note still in the briefing: " + phrase)
        page.locator("#about-open").click()
        method = page.locator("#about-panel").inner_text()
        for phrase in ("No model call", "median weekly count", "frozen window", "22 November 2026"):
            if phrase not in method:
                problems.append("About method missing " + phrase)
        page.locator("#about-close").click()
        facts = page.locator("#country-facts li")
        if facts.count() < 8:
            problems.append("Russia fact card has " + str(facts.count()) + " facts")
        missing = page.evaluate(
            """() => [...document.querySelectorAll('#country-facts li')].filter((item) => !item.querySelector('a[href]')).length"""
        )
        if missing:
            problems.append("fact without a source link")
        if page.locator("#country-facts").is_hidden():
            problems.append("Russia fact card is hidden")
        page.screenshot(path=str(SHOTS / "russia-2026-10-12.png"), full_page=True)
        page.locator("#country-LV").click()
        set_week(page, "2026-09-14")
        page.wait_for_timeout(200)
        headlines = page.locator("#drawer .headline-en").all_inner_texts()
        if len(headlines) != len(set(headlines)):
            problems.append("duplicate headline " + str(headlines))
        sources = " ".join(page.locator("#drawer .story-sources").all_inner_texts())
        if "ria.ru" not in sources or "aif.ru" not in sources:
            problems.append("merged sources missing: " + sources)
        officials = page.locator("#officials li")
        if officials.count():
            bare = page.evaluate(
                """() => [...document.querySelectorAll('#officials li')].filter((item) => !item.querySelector('.side-label')).length"""
            )
            if bare:
                problems.append("official item missing a side label")
        bottom = page.locator("#bottom-line-text").inner_text()
        for name in TRANSLATED:
            if name in bottom:
                problems.append("English sentence contains " + name)
        page.screenshot(path=str(SHOTS / "merged-sources-2026-09-14.png"), full_page=True)
        browser.close()
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print("PASS russia test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
