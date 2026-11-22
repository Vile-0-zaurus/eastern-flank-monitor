#!/usr/bin/env python3
"""Briefing dedup, dates, week label, zoom, and side labels. No API calls.

    /home/supra/Projects/merdian/.venv/bin/python tests/briefing_selftest.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/frontend/"
SHOTS = Path.home() / "Desktop" / "efm-check4"
TRANSLATED = ("Latvija", "Eesti", "Lietuva", "Polska", "Suomi", "Igaunija", "Estija", "Lenkija", "Somija", "Viro")


def clipped(page) -> bool:
    return page.evaluate(
        """() => {
          const el = document.getElementById('week-label');
          const range = document.createRange();
          range.selectNodeContents(el);
          const text = range.getBoundingClientRect();
          const box = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return style.overflow === 'hidden'
            || text.right > box.right + 1
            || text.bottom > box.bottom + 1
            || box.bottom > window.innerHeight + 1;
        }"""
    )


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
              const codes = ['en', 'fi', 'et', 'lv', 'lt', 'pl'];
              const out = {};
              codes.forEach((code) => { out[code] = formatDate('2026-09-14', code); });
              return out;
            }"""
        )
        english_date = dates["en"]
        if "Week" in english_date or "14" not in english_date:
            problems.append("English date is " + english_date)
        for code, text in dates.items():
            if code != "en" and text == english_date:
                problems.append(code + " date is still English: " + text)
            if "Week of" in text or "savaitė" in text or "Nädal" in text:
                problems.append(code + " date uses a week label: " + text)
        for width, height in ((1280, 800), (1920, 1080)):
            page.set_viewport_size({"width": width, "height": height})
            page.locator('#lang-switch [data-lang="lt"]').click()
            page.wait_for_function("document.documentElement.lang === 'lt'")
            if clipped(page):
                problems.append("week label clipped at " + str(width) + "x" + str(height))
        page.set_viewport_size({"width": 1280, "height": 800})
        page.locator('#lang-switch [data-lang="en"]').click()
        before = page.locator("#flank-map").get_attribute("data-zoom")
        page.locator("#zoom-in").click()
        after = page.locator("#flank-map").get_attribute("data-zoom")
        if not before or not after or int(after) >= int(before):
            problems.append("zoom did not change " + str(before) + " -> " + str(after))
        page.locator("#zoom-reset").click()
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-zoom') === '860'", timeout=4000)
        set_week(page, "2026-09-14")
        page.locator("#country-LV").click()
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-country-zoom') === 'LV'", timeout=4000)
        page.locator('#lang-switch [data-lang="lt"]').click()
        page.wait_for_function("document.documentElement.lang === 'lt'")
        bottom = page.locator("#bottom-line-text").inner_text()
        for name in TRANSLATED:
            if name in bottom:
                problems.append("English sentence contains " + name)
        page.screenshot(path=str(SHOTS / "latvia-lt-2026-09-14.png"), full_page=True)
        page.locator('#lang-switch [data-lang="en"]').click()
        page.wait_for_function("document.documentElement.lang === 'en'")
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-country-zoom') === 'LV'", timeout=4000)
        headlines = page.locator("#drawer .headline-en").all_inner_texts()
        if len(headlines) != len(set(headlines)):
            problems.append("duplicate headline in briefing " + str(headlines))
        sources = page.locator("#drawer .story-sources").all_inner_texts()
        merged = [row for row in sources if "ria.ru" in row and "aif.ru" in row]
        if not merged:
            problems.append("plant-closing sources were not merged: " + str(sources))
        plant = [row for row in headlines if "plant closing" in row.lower()]
        if len(plant) != 1:
            problems.append("plant closing shown " + str(len(plant)) + " times")
        page.screenshot(path=str(SHOTS / "latvia-merged-sources.png"), full_page=True)
        officials = page.locator("#officials li")
        if officials.count():
            missing = page.evaluate(
                """() => [...document.querySelectorAll('#officials li')].filter((item) => !item.querySelector('.side-label')).length"""
            )
            if missing:
                problems.append("official item missing a side label")
        else:
            found = page.evaluate(
                """() => {
                  const weeks = state.nowPack.weeks || [];
                  for (const week of weeks) {
                    const pool = (((state.nowHeadlines || {}).officials || {})[week] || {});
                    for (const code of Object.keys(pool)) {
                      if ((pool[code] || []).some((item) => item.english)) return { week, code };
                    }
                  }
                  return null;
                }"""
            )
            if not found:
                problems.append("no official item in the snapshot to check")
            else:
                set_week(page, found["week"])
                page.locator("#country-" + found["code"]).click()
                page.wait_for_timeout(400)
                missing = page.evaluate(
                    """() => [...document.querySelectorAll('#officials li')].filter((item) => !item.querySelector('.side-label')).length"""
                )
                if not page.locator("#officials li").count() or missing:
                    problems.append("official side label missing on " + found["week"])
        set_week(page, "2026-08-03")
        page.locator("#country-EE").click()
        page.wait_for_function("document.getElementById('flank-map').getAttribute('data-country-zoom') === 'EE'", timeout=4000)
        happened = page.locator("#region-events").inner_text()
        if "In the news" not in happened:
            problems.append("quiet Estonia week missing In the news")
        if "Nothing this week" in happened:
            problems.append("quiet Estonia week still says Nothing this week")
        news_text = page.locator("#country-news").inner_text()
        lead = page.locator("#region-events .headline-en").inner_text()
        if lead and lead in news_text:
            problems.append("In the news headline repeated in Russian media")
        page.screenshot(path=str(SHOTS / "estonia-quiet.png"), full_page=True)
        set_week(page, "2026-08-10")
        page.locator("#country-LV").click()
        page.locator(".incident-jump").first.click()
        page.wait_for_timeout(200)
        place = page.locator("#flank-map").get_attribute("data-focus-place")
        if place != "Balvi Municipality":
            problems.append("Balvi zoom place is " + str(place))
        page.screenshot(path=str(SHOTS / "balvi-zoom.png"), full_page=True)
        browser.close()
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print("PASS briefing test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
