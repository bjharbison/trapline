"""eval/score.py: matching rules on synthetic data, the gold files' integrity, and the
LLM code path through the real page against a mocked endpoint (no model needed)."""
import json, os, pathlib, sys
from harness import check, failures, ROOT

sys.path.insert(0, str(ROOT / "eval"))
import score as S

print("normalization")
check(S.norm("U.S. Attorney's Office") == S.norm("US Attorney s Office"), "periods and punctuation ignored")
check(S.norm("The Ethics Commission") == S.norm("ethics commission"), "case and leading 'the' ignored")
check(S.norm("Okonkwo-Reyes") == S.norm("Okonkwo Reyes"), "hyphen = space")
check(S.norm("Halloran Trading") != S.norm("Halloran"), "no substring matching")

print("scoring")
gold = {"doc": "x", "entities": [
    {"name": "Teodora Vass", "type": "person", "aliases": ["Vass"]},
    {"name": "Meridale Construction", "type": "org", "aliases": []},
    {"name": "Port Anselm", "type": "place", "aliases": []}],
    "relations": [{"source": "Teodora Vass", "target": "Meridale Construction", "label": "met"}]}
p = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "trapline_eval_gold.json"
p.write_text(json.dumps(gold))
g, index, pairs = S.load_gold(p)
got = {"nodes": [{"id": "v", "name": "Vass", "type": "person"},            # alias seen first
                 {"id": "tv", "name": "teodora vass", "type": "other"},    # full name claims the match
                 {"id": "m", "name": "Meridale Construction.", "type": "org"},
                 {"id": "f", "name": "Fund", "type": "other"}],            # false positive
       "links": [{"source": "m", "target": "tv", "label": "met"},           # reversed order still matches
                 {"source": "v", "target": "m", "label": "co-occurs"},      # duplicate of the same pair
                 {"source": "v", "target": "tv", "label": "co-occurs"},     # both ends one entity -> FP
                 {"source": "f", "target": "m", "label": "paid"}]}          # FP endpoint
r = S.score(g, index, pairs, got)
check(set(r["matched"]) == {"Teodora Vass", "Meridale Construction"}, "matches by name, alias, case, punctuation")
check(r["matched"]["Teodora Vass"]["id"] == "tv", "full-name hit is the match, alias hit the duplicate")
check([n["id"] for n, _ in r["dups"]] == ["v"], "duplicate recorded")
check([n["id"] for n in r["fps"]] == ["f"] and [e["name"] for e in r["misses"]] == ["Port Anselm"], "FP and miss")
check(r["ent"][0] == 3 / 4 and r["ent"][1] == 2 / 3, f"entity P/R {r['ent'][:2]}")
check(r["type_ok"] == 1, "type agreement counted on matches")
(rp, rr, _), hit, dup, fp, miss = r["rel_all"]
check(len(hit) == 1 and len(dup) == 1 and len(fp) == 2 and not miss, "unordered pair match, dup, self-pair and FP-endpoint FPs")
check(rp == 2 / 4 and rr == 1.0, f"relation P/R {rp, rr}")
check(r["n_typed"] == 2 and r["rel_typed"][0][0] == 1 / 2, "typed-only score leaves out co-occurs")
md = S.md("<img src=x onerror=alert(1)>|*x*")
check("<" not in md and "\\|" in md and "\\*" in md, f"report escapes extracted strings: {md}")

bad = dict(gold, entities=gold["entities"] + [{"name": "Vass Holdings", "type": "org", "aliases": ["Vass"]}])
p.write_text(json.dumps(bad))
try: S.load_gold(p); check(False, "alias shared by two entities is refused")
except ValueError: check(True, "alias shared by two entities is refused")
p.unlink()

print("gold files")
for f in sorted((ROOT / "eval/gold").glob("*.json")):
    try:
        gg, _, _ = S.load_gold(f)
        ok = gg["status"] in ("DRAFT - needs Brian's review", "reviewed") and (ROOT / gg["doc"]).exists()
        types = all(e["type"] in ("person", "org", "place", "event", "other") for e in gg["entities"])
        check(ok and types, f"{f.name}: valid status, doc, types")
    except ValueError as e:
        check(False, f"{f.name}: {e}")

print("LLM path, mocked endpoint")
URL = "https://api.openai.com/v1/chat/completions"
GRAPH = {"nodes": [{"id": "vh", "name": "Viktor Halloran", "type": "person"},
                   {"id": "h", "name": "Halloran", "type": "person"},
                   {"id": "kt", "name": "Kasterline Trading", "type": "org"},
                   {"id": "x", "name": "<b>Bogus</b> Corp", "type": "org"}],
         "links": [{"source": "vh", "target": "kt", "relationship": "founded"},
                   {"source": "h", "target": "kt", "relationship": "owns"},
                   {"source": "kt", "target": "x", "relationship": "paid"}]}
seen = []

def route(ctx):
    def handle(rt):
        req = rt.request
        cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
        if req.method == "OPTIONS": return rt.fulfill(status=204, headers=cors)
        seen.append({"headers": req.headers, "body": json.loads(req.post_data)})
        rt.fulfill(status=200, headers=cors, body=json.dumps({"choices": [{"message": {"content": json.dumps(GRAPH)}}]}))
    ctx.route(URL, handle)

os.environ["TRAPLINE_EVAL_TEST_KEY"] = "sk-eval-SECRET"
res = S.main(["--endpoint", URL, "--model", "mock-model", "--key-env", "TRAPLINE_EVAL_TEST_KEY", "--only", "sanctions-filing", "--quiet"], route=route)
check(len(seen) == 1, f"one request sent ({len(seen)})")
if seen:
    body = seen[0]["body"]
    check(body["model"] == "mock-model", "model sent")
    check("Kasterline Trading" in body["messages"][1]["content"], "document text sent to the endpoint")
    check(seen[0]["headers"].get("authorization") == "Bearer sk-eval-SECRET", "key read from the named env var")
if res:
    name, gg, r = res[0]
    check(name == "sanctions-filing", "scored the selected document")
    check(len(r["matched"]) == 2 and len(r["dups"]) == 1 and len(r["fps"]) == 1, "LLM graph scored")
    check(r["ent"][0] == 3 / 4, f"entity precision {r['ent'][0]}")
    rel = r["rel_all"]
    check(len(rel[1]) == 1 and len(rel[2]) == 1 and len(rel[3]) == 1, "LLM links scored")
    rep = S.report(res, [], type("A", (), {"max_entities": None, "endpoint": URL})(), "LLM")
    check(S.BANNER in rep and "<b>" not in rep, "report has the DRAFT banner and escapes names")

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
