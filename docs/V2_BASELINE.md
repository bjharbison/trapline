# V2 baseline and compatibility gate

This document describes the baseline for [issue #16](https://github.com/bjharbison/trapline/issues/16). It does **not** claim V2 features have shipped.

## Protected reference points (verified 2026-11-02)

| Reference | Commit | Policy |
| --- | --- | --- |
| `release/v1` | `036516ca6d085a1302fe55c9f9d7f0a9e6d92faa` | Historical browser-only release; do not edit |
| `snapshot/pre-v2-2026-10-30` | `a9e8cf7c651e025d7183f8e004af7eccb6eb22ae` | Exact pre-V2 `main` snapshot; do not edit |
| `main` | `a9e8cf7c651e025d7183f8e004af7eccb6eb22ae` | Shipping GitHub Pages; no automatic V2 merge |
| `develop/v2-roadmap` | `785fea1a114b061568b8e6102ca33ee079eee464` | V2 integration baseline before issue #16 |

The original V1 branch and the pre-V2 snapshot intentionally differ. The current `main` is not a FastAPI app and does not provide SQL persistence. V2 changes must remain in reviewable feature branches until approved.

## Reproducible local test instructions

Requirements: Python 3.12+, git, internet access **only to download development dependencies**, and a browser-capable workstation. The application in its offline mode must not access external providers.

```bash
git clone https://github.com/bjharbison/trapline.git
cd trapline
git checkout feat/v2-baseline-ci-issue16
python3 -m pip install playwright==1.56.0
python3 -m playwright install chromium
bash tests/run_all.sh
```

`tests/run_all.sh` first calls `tests/vendor.sh` to fetch D3 and compromise.js development fixtures from their upstream public repositories. The harness then fulfills the app's CDN requests from local files and blocks Google Fonts. `tests/test_offline_build.py` tests the self-contained build with all network access aborted. The new `tests/test_offline_egress.py` aborts and records any **unexpected** network requests during default offline analysis.

To run just the offline privacy smoke test, first populate `tests/.vendor` using `bash tests/vendor.sh`, then:

```bash
python3 tests/test_offline_egress.py
```

The baseline in `tests/baseline_offline.json` is intentionally frozen. **Do not run `--update` or change the baseline merely to make CI green**; an intended extraction change requires a reviewed before/after diff.

## Automated PR gate

`.github/workflows/v2-browser-regression.yml` runs the complete existing Python Playwright browser suite (including exports, adversarial rendering, offline build, provider mocks and the new offline egress smoke) on pull requests targeting `develop/v2-roadmap` and on pushes to that integration branch. The job has read-only repository permissions, runs on Ubuntu 24.04 with Python 3.12 and Chromium, and does not deploy or change GitHub Pages.

This is a **V1 compatibility gate**, not V2 backend CI. When the FastAPI scaffold lands, add separate backend API, migration and backup/restore tests before calling V2.0 complete.

## Known gaps and risks

- The complete suite depends on GitHub-hosted browser/dependency downloads. CI may fail due to upstream availability or Playwright/browser compatibility; report the actual logs rather than assuming tests passed.
- Existing browser tests use stubbed PDF.js in parts of the suite; full real-PDF parsing and accessibility checks still need dedicated fixtures.
- No SQL persistence, FastAPI API, durable file store, backups, or V2 end-to-end test exists yet. These belong to issues #17–22.
- The suite is designed for a single-user local-first browser application. It does not prove a future backend is secure or that remote hosting is safe.
- A passing CI run on a PR is necessary but not sufficient for merging or promoting a release. Human review and V2 release gates remain required.

## Validation log

- **2026-11-02:** Confirmed protected reference SHAs via GitHub API, verified `main` remains at the pre-V2 snapshot, and inspected the existing `tests/run_all.sh`, harness, privacy/export tests and Actions history. Before this PR there were no open PRs and the repository's recent Actions runs were GitHub Pages deployments, not browser-test CI.
- **This change:** Adds CI configuration and an offline network-egress regression test. End-to-end execution and CI results must be recorded from an actual runner; do not infer a passing suite from source inspection.
