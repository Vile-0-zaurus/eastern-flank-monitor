# Now tab wiring, section 2

Date: 15 November 2026. No API calls. The Now database was opened read-only.

The Now dossier now reads `frontend/now-headlines.json`, built from `data/now/gkg-now.sqlite`. The chip still reads the attention counts in `frontend/now-view.json`, which come from the same database. A country with a chip count above zero has one to five dossier items, each with an English line written by hand.

`python3 tests/now_count_selftest.py` passed: 12 weeks, 5 countries.

Also in this section: regional media from Yle and BBC, incident dots active from their date, incident labels and source links, quiet weeks that stay inside the Now window, officials from Now headlines and incident sources, and the snapshot banner. Placeholder sentences about a missing file and sources listed under the map are gone.
