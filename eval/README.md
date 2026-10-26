# Extraction eval

> **Draft.** The ground truth in `gold/` was drafted by Claude and hasn't been reviewed yet. Scores from it are not for publication. Gold files say `"status": "DRAFT - needs Brian's review"` until a person has checked them.

This folder measures how well Trapline's extraction matches hand-annotated ground truth: entity and relationship precision, recall and F1 for each document, plus every false positive and miss. It's dev tooling, like `tests/`. `trapline.html` doesn't depend on it.

| Path | What it is |
|---|---|
| `GUIDELINES.md` | What counts as an entity or relationship, and the exact matching rules the scorer uses. Read this before editing gold. |
| `docs/` | Source documents. Each has a header (title, agency, date, source URL, licence), then a `---` line, then the body. |
| `gold/<doc>.json` | Ground truth for one document. `doc` points at its text, which can live anywhere in the repo. |
| `score.py` | Runs the page on each gold file's document and scores the result. |
| `results/` | Saved reports. |
| `REVIEW_NOTES.md` | Open questions about the draft gold, and the missing document text. |

**Current state.** The five U.S. government press releases in `docs/` are headers only. Their text still has to be pasted in (see `REVIEW_NOTES.md`). Until then, gold exists only for the three fictional samples in `examples/`.

## Run it

Same setup as the tests (Python with Playwright and Chromium; `tests/vendor.sh` fetches the libraries once):

```bash
bash tests/vendor.sh
python3 eval/score.py                                    # offline engine, prints the report
python3 eval/score.py --out eval/results/offline-$(date +%F).md
python3 eval/score.py --max-entities 40                  # the page's Max entities field (default 25)
python3 eval/score.py --only sanctions                   # one document
```

The offline engine runs entirely in the headless browser. Nothing leaves the machine.

**LLM engine.** `--endpoint` runs the page's LLM mode instead. This sends each document's text to that URL, so point it at a local model unless you mean to send the documents somewhere else:

```bash
python3 eval/score.py --endpoint http://localhost:11434/v1/chat/completions --model qwen2.5:7b
OPENAI_API_KEY=sk-... python3 eval/score.py --endpoint https://api.openai.com/v1/chat/completions \
    --model gpt-4o-mini --key-env OPENAI_API_KEY
```

The key is read from the environment variable you name. It never goes on the command line. The page loads from `file://`, so a local Ollama needs `OLLAMA_ORIGINS` set to allow that origin, the same as in normal use. LLM mode reads only the first 5,000 characters of each document. Recall on longer documents is capped by that, and the report says so. Small local models are slow (raise `--timeout`) and invent entities, which shows up as false positives.

`tests/test_eval_score.py` checks the matching rules, the gold files' integrity, and the LLM code path against a mocked endpoint. It runs with `bash tests/run_all.sh`.

## Finalizing the gold

1. Read `REVIEW_NOTES.md` and settle each open question.
2. For each gold file, read the document and the JSON side by side. Fix entities, types, aliases and relations to follow `GUIDELINES.md`. Every alias must appear in the text. An alias that fits two entities is an error the scorer refuses.
3. When a file is right, change its status to `"status": "reviewed"`.
4. Re-run: `python3 eval/score.py --out eval/results/offline-$(date +%F).md`. `bash tests/run_all.sh` also validates every gold file.
5. Reports keep the DRAFT banner until the banner logic is changed. When every gold file is `reviewed`, edit `BANNER` in `score.py`, or make it depend on the statuses. That's a deliberate step, not an automatic one.

To add a federal document's gold, paste its text into `docs/<name>.txt` under the `---` line. Then write `gold/<name>.json` with `"doc": "eval/docs/<name>.txt"`. The scorer lists documents with no gold or no text under "Not scored".

## What the numbers mean

- Entity matching is exact after normalization (case, punctuation, a leading "the"). Partial names score as false positives unless the text uses them as an alias. That's on purpose, so alias fragmentation shows up.
- Relations are compared as unordered pairs. Labels aren't compared. The offline engine's `co-occurs` links count as relationship claims, because the graph shows them as edges. The report also scores typed links on their own.
- Dates count as false positives. The offline engine extracts them as `event` nodes, and the guidelines don't count dates as entities.
- Three short fictional documents are a smoke test of the harness, not a benchmark.
