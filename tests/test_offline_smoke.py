"""Offline (compromise.js) engine: runs end to end and its output is compared to a baseline.

The fixture is fictional and deliberately includes known weak spots (a pronoun
with the wrong antecedent nearby, "US"/"USS Cole", "Hale"/"Marcus Hale") so
extraction changes show up as a diff against tests/baseline_offline.json.

    python3 tests/test_offline_smoke.py            # check against baseline
    python3 tests/test_offline_smoke.py --update   # rewrite the baseline (do this
                                                   # only for an intended change,
                                                   # and say so in the PR)
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures, ROOT

FIXTURE = (ROOT / "tests/fixtures/offline_sample.txt").read_text()
BASELINE = ROOT / "tests/baseline_offline.json"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    check(pg.evaluate("state.engine") == "local", "offline engine is the default")
    pg.fill("#text-input", FIXTURE)
    pg.click("#btn-analyse")
    pg.wait_for_function("state.analysis && state.analysis.nodes && state.analysis.nodes.length > 0", timeout=30000)
    pg.wait_for_timeout(500)
    got = pg.evaluate("""() => ({
        nodes: state.analysis.nodes.map(n => n.name + ' [' + n.type + ']').sort(),
        links: state.analysis.links.map(l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            const name = id => (state.analysis.nodes.find(n => n.id === id) || {}).name || id;
            return name(s) + ' -> ' + name(t) + ' (' + (l.label || '') + ')';
        }).sort(),
    })""")
    check(len(got["nodes"]) >= 5, f"extracts entities ({len(got['nodes'])})")
    check(len(got["links"]) >= 2, f"extracts relationships ({len(got['links'])})")
    check(pg.text_content("#stat-nodes") == str(len(got["nodes"])), "stats bar matches the graph")
    check(not errors, f"no page errors {errors}")
    b.close()

if "--update" in sys.argv:
    BASELINE.write_text(json.dumps(got, indent=2) + "\n")
    print(f"baseline written: {len(got['nodes'])} nodes, {len(got['links'])} links")
elif BASELINE.exists():
    base = json.loads(BASELINE.read_text())
    for k in ("nodes", "links"):
        added = sorted(set(got[k]) - set(base[k])); removed = sorted(set(base[k]) - set(got[k]))
        for x in added: print(f"  + {k[:-1]}: {x}")
        for x in removed: print(f"  - {k[:-1]}: {x}")
        check(not added and not removed, f"{k} match baseline")
else:
    check(False, "no baseline — run with --update once")

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
