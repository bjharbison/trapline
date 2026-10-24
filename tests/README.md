# Tests

Browser tests for `trapline.html`, run in headless Chromium with Playwright. They are dev tooling only; the app itself stays a single file with no build step.

```bash
pip install playwright && python3 -m playwright install chromium
bash tests/run_all.sh
```

`vendor.sh` fetches the same D3 and compromise.js builds the page loads from its CDN, so the tests run without CDN access.

| Test | What it covers |
|---|---|
| `test_offline_smoke.py` | The offline engine runs end to end on a fictional fixture. Its entities and links are compared to `baseline_offline.json`. |
| `test_extraction_units.py` | Offline extraction functions called directly: whole-token entity matching, conservative pronoun resolution, name cleaning and the non-entity stoplist, no self-loops, and no false merges. |
| `test_providers.py` | Every LLM provider preset, using mocked APIs. Covers URLs, headers, body quirks, model listing, key errors, and that the key is not stored by default. |
| `test_key_keep.py` | "Keep key for this tab": off by default (no storage, gone on reload); on, the key lives in sessionStorage only, comes back after a refresh, is invisible to another tab, and is forgotten on untick, clear, or provider switch. |
| `test_key_help.py` | The ? next to the API key field opens step-by-step key instructions for the selected provider (or typed URL), with links that open in a new tab, and sends nothing. |
| `test_model_hint.py` | An unknown model name ("Opus") gets a pointer to List Models, for every provider's not-found error shape, in Test Connection and Analyse. Wrong-URL 404s, other 400s and bad keys keep their own message. |
| `test_egress.py` | The panel warns whenever the endpoint isn't on this machine. |
| `test_view.py` | The graph fits itself to the view once when the layout settles. Clicking or pinning a node afterwards keeps the user's zoom. |
| `test_gexf.py` | GEXF export through the real menu, parsed with Python's XML parser: structure, counts, every node attribute, edge label/weight, and hostile strings (markup, quotes, XML-illegal characters) round-tripping as text. |
| `test_provenance.py` | Every offline link carries real sentences of the analyzed text; the LLM parser keeps only quotes that appear in the source and falls back to a sentence naming both entities; link click / connection row open the link detail; hostile evidence and labels render as text; CSV, GEXF and Markdown carry the evidence. |
| `test_search_shortcuts.py` | Search and type filter dim the canvas, Enter zooms to the best match, Esc clears; every shortcut (`?` `/` `F` `+` `-` `0` `P` `E` `Esc` `Ctrl+Enter`) works outside inputs and single keys never fire while typing. |
| `test_mobile.py` | Phone viewport: panel stacks above a full-width graph, Export is reachable, legend hidden; the ⋯ card menu pins, edits and deletes (with confirm) without the detail panel. |
| `test_editing.py` | Rename, retype and delete from the detail panel: stable ids, name-collision refusal (no silent merge), recomputed metrics/flags/dupes, pins kept, and a hostile name rendered as text in every panel. |

**Changing the baseline.** If an extraction change is intended, run `python3 tests/test_offline_smoke.py --update`. Commit the new baseline, and paste the +/- diff from the run before into the PR so the change can be reviewed.

**Demo GIF.** `docs/record_demo.py` re-records `docs/demo.gif` with the same harness and ffmpeg. Install the Oxanium and JetBrains Mono fonts locally first, because the harness blocks Google Fonts.
