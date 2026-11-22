# Housekeeping

Date: 22 November 2026. No API calls. No page changes.

The two scripts were one-off helpers. They only printed titles. They are not called by the Now build. The build files are scripts/now/build_now_headlines.py, scripts/now/apply_english.py, and scripts/now/build_now_view.py. The helpers were deleted.

tests/ui_selftest.py still opened the removed #why panel. Updating that long test was the harder path. It was moved to tests/retired/ui_selftest.py. The note says it was replaced by click_selftest.py.

Remaining self-tests, run after the move:

1. python3 tests/now_count_selftest.py — PASS, 12 weeks, 5 countries.
2. tests/click_selftest.py — PASS.
3. python3 tests/now_selftest.py — PASS. No video was recorded.
