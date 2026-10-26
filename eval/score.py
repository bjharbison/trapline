"""Score Trapline's extraction against the gold files in eval/gold/.

Runs each gold file's document through trapline.html in headless Chromium (the
same harness as tests/), then matches entities by normalized name or alias and
relations as unordered pairs. Rules: eval/GUIDELINES.md.

    python3 eval/score.py                         # offline engine, print report
    python3 eval/score.py --out eval/results/x.md # also write the report
    python3 eval/score.py --endpoint URL --model NAME [--key-env VAR]
                                                  # LLM engine through the page

With --endpoint, each document's text is sent to that URL. Point it at a local
model unless you mean to send the documents elsewhere. The key is read from the
named environment variable, never from the command line.
"""
import argparse, datetime, json, os, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
GOLD = ROOT / "eval" / "gold"
BANNER = "Scored against DRAFT ground truth — not for publication."


def norm(s):
    """Close to the page's nameKey() (NFC, case, punctuation), plus a dropped leading 'the'."""
    s = unicodedata.normalize("NFC", s).strip().lower().replace(".", "")
    s = re.sub(r"[^\w]+|_", " ", s).strip()
    return re.sub(r"^the ", "", s)


def body(path):
    """Document text. Files with a header block keep the body after the first '---' line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    head = lines[:15]
    if "---" in head:
        lines = lines[head.index("---") + 1:]
    return "\n".join(lines).strip()


def load_gold(path):
    g = json.loads(path.read_text(encoding="utf-8"))
    index, names = {}, set()
    for e in g["entities"]:
        if e["name"] in names:
            raise ValueError(f"{path.name}: entity '{e['name']}' is listed twice")
        names.add(e["name"])
        for form in [e["name"]] + e.get("aliases", []):
            k = norm(form)
            if k in index and index[k] != e["name"]:
                raise ValueError(f"{path.name}: '{form}' belongs to both '{index[k]}' and '{e['name']}'")
            index[k] = e["name"]
    pairs = {}
    for r in g["relations"]:
        for end in (r["source"], r["target"]):
            if end not in names:
                raise ValueError(f"{path.name}: relation endpoint '{end}' is not a gold entity name")
        key = frozenset((r["source"], r["target"]))
        if len(key) < 2 or key in pairs:
            raise ValueError(f"{path.name}: relation {r['source']} — {r['target']} is a self-pair or listed twice (join labels with ';')")
        pairs[key] = r.get("label", "")
    return g, index, pairs


def prf(correct, total_pred, hit, total_gold):
    p = correct / total_pred if total_pred else 0.0
    r = hit / total_gold if total_gold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def score(gold, index, pairs, got):
    """got = {"nodes": [{id,name,type}], "links": [{source,target,label}]}"""
    types = {e["name"]: e["type"] for e in gold["entities"]}
    to_gold, matched, dups, fps = {}, {}, [], []
    canon = {norm(e["name"]): e["name"] for e in gold["entities"]}
    for n in got["nodes"]:  # full-name hits claim the match first, so "Vass" is the duplicate, not "Teodora Vass"
        to_gold[n["id"]] = index.get(norm(n["name"]))
        g = canon.get(norm(n["name"]))
        if g and g not in matched: matched[g] = n
    for n in got["nodes"]:
        g = to_gold[n["id"]]
        if g is None: fps.append(n)
        elif matched.get(g) is n: continue
        elif g in matched: dups.append((n, g))
        else: matched[g] = n
    misses = [e for e in gold["entities"] if e["name"] not in matched]
    ent = prf(len(matched) + len(dups), len(got["nodes"]), len(matched), len(gold["entities"]))
    type_ok = sum(1 for g, n in matched.items() if n["type"] == types[g])

    def rel(links):
        hit, dup, fp = {}, [], []
        for l in links:
            a, b = to_gold.get(l["source"]), to_gold.get(l["target"])
            key = frozenset((a, b)) if a and b and a != b else None
            if key is None or key not in pairs: fp.append(l)
            elif key in hit: dup.append(l)
            else: hit[key] = l
        miss = [k for k in pairs if k not in hit]
        return prf(len(hit) + len(dup), len(links), len(hit), len(pairs)), hit, dup, fp, miss

    typed = [l for l in got["links"] if l["label"] != "co-occurs"]
    return {"ent": ent, "matched": matched, "dups": dups, "fps": fps, "misses": misses,
            "type_ok": type_ok, "rel_all": rel(got["links"]), "rel_typed": rel(typed),
            "n_gold_rel": len(pairs), "n_nodes": len(got["nodes"]), "n_links": len(got["links"]), "n_typed": len(typed)}


EXTRACT_JS = """() => ({
    nodes: state.analysis.nodes.map(n => ({id: n.id, name: n.name, type: n.type})),
    links: state.analysis.links.map(l => ({
        source: typeof l.source === 'object' ? l.source.id : l.source,
        target: typeof l.target === 'object' ? l.target.id : l.target,
        label: l.relationship || l.label || ''})),
})"""


def run_page(pg, text, args):
    """Analyse one document on an open page and return its graph."""
    pg.evaluate("state.analysis = null")
    if args.endpoint:
        pg.click("#pill-llm")
        pg.fill("#llm-url", args.endpoint)
        pg.fill("#llm-model", args.model)
        pg.fill("#llm-key", os.environ.get(args.key_env, "") if args.key_env else "")
    if args.max_entities:
        pg.fill("#max-entities", str(args.max_entities))
    pg.fill("#text-input", text)
    pg.click("#btn-analyse")
    pg.wait_for_function("document.getElementById('btn-analyse').disabled === false", timeout=args.timeout * 1000)
    if not pg.evaluate("!!(state.analysis && state.analysis.nodes)"):
        raise RuntimeError("no graph: " + (pg.text_content("#toast") or "no message").strip())
    return pg.evaluate(EXTRACT_JS)


def pct(x): return f"{x * 100:.1f}%"


def md(s):
    """Extracted strings are untrusted: neutralize HTML and Markdown before they go in the report."""
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"[\r\n\u2028\u2029]+", " ", s)
    return re.sub(r"([\\`*_\[\]|#!~])", r"\\\1", s)


def report(results, skipped, args, engine):
    out = [f"# Trapline extraction eval: {md(engine)}", "", f"> **{BANNER}**", ">",
           "> Every gold file is a draft written by Claude and not yet reviewed by Brian. These numbers say how the",
           "> harness works, not how good Trapline is.", "",
           f"Date: {datetime.date.today().isoformat()}  ",
           f"Engine: {md(engine)}  ",
           f"Max entities: {args.max_entities or 'page default (25)'}  ",
           "Matching rules: [GUIDELINES.md](../GUIDELINES.md)", ""]
    fiction = [n for n, g, _ in results if g["doc"].startswith("examples/")]
    if fiction:
        out += [f"Fictional sample documents from `examples/` in this run: {', '.join(fiction)}.", ""]
    if args.endpoint:
        out += ["LLM mode analyses only the first 5,000 characters of each document, so recall on longer documents is capped.", ""]
    tot = {k: 0 for k in "nodes gold ematch edup ruse_all rgold rhit_all rdup_all ruse_t rhit_t rdup_t typeok".split()}
    rows = []
    for name, gold, r in results:
        (ep, er, ef) = r["ent"]
        (ap, ar, af), ahit, adup, _, _ = r["rel_all"]
        (tp, tr, tf), thit, tdup, _, _ = r["rel_typed"]
        rows.append(f"| {name} | {r['n_nodes']} / {len(gold['entities'])} | {pct(ep)} | {pct(er)} | {pct(ef)} | "
                    f"{r['n_links']} / {r['n_gold_rel']} | {pct(ap)} | {pct(ar)} | {pct(af)} | {pct(tf)} |")
        tot["nodes"] += r["n_nodes"]; tot["gold"] += len(gold["entities"])
        tot["ematch"] += len(r["matched"]); tot["edup"] += len(r["dups"]); tot["typeok"] += r["type_ok"]
        tot["ruse_all"] += r["n_links"]; tot["rgold"] += r["n_gold_rel"]
        tot["rhit_all"] += len(ahit); tot["rdup_all"] += len(adup)
        tot["ruse_t"] += r["n_typed"]; tot["rhit_t"] += len(thit); tot["rdup_t"] += len(tdup)
    ep, er, ef = prf(tot["ematch"] + tot["edup"], tot["nodes"], tot["ematch"], tot["gold"])
    ap, ar, af = prf(tot["rhit_all"] + tot["rdup_all"], tot["ruse_all"], tot["rhit_all"], tot["rgold"])
    tp, tr, tf = prf(tot["rhit_t"] + tot["rdup_t"], tot["ruse_t"], tot["rhit_t"], tot["rgold"])
    out += ["## Summary", "",
            "| Document | Entities (extracted / gold) | P | R | F1 | Links (extracted / gold) | P | R | F1 | F1 typed links |",
            "|---|---|---|---|---|---|---|---|---|---|", *rows,
            f"| **Overall (micro)** | {tot['nodes']} / {tot['gold']} | {pct(ep)} | {pct(er)} | {pct(ef)} | "
            f"{tot['ruse_all']} / {tot['rgold']} | {pct(ap)} | {pct(ar)} | {pct(af)} | {pct(tf)} |", "",
            f"Typed links only (leaving out `co-occurs`): {tot['ruse_t']} extracted, P {pct(tp)}, R {pct(tr)}.  ",
            f"Type agreement on matched entities: {tot['typeok']} / {tot['ematch']}.  ",
            f"Duplicate entities (a second name for an entity already matched): {tot['edup']}.", ""]
    if skipped:
        out += ["Not scored:", ""] + [f"- {s}" for s in skipped] + [""]
    for name, gold, r in results:
        _, _, adup, afp, amiss = r["rel_all"]
        names = {x["id"]: x["name"] for x in r["_nodes"]}
        out += [f"## {name}", "", f"Document: `{gold['doc']}`", "",
                f"**Entity false positives ({len(r['fps'])})**: " + (", ".join(f"{md(n['name'])} [{md(n['type'])}]" for n in r["fps"]) or "none"), "",
                f"**Entity misses ({len(r['misses'])})**: " + (", ".join(f"{md(e['name'])} [{e['type']}]" for e in r["misses"]) or "none"), "",
                f"**Duplicates ({len(r['dups'])})**: " + (", ".join(f"{md(n['name'])} → {md(g)}" for n, g in r["dups"]) or "none"), "",
                "**Type disagreements**: " + (", ".join(f"{md(g)} (gold {t}, got {md(n['type'])})" for g, n in r["matched"].items()
                                                       for t in [next(e['type'] for e in gold['entities'] if e['name'] == g)] if n['type'] != t) or "none"), "",
                f"**Relation false positives ({len(afp)})**: " + (", ".join(
                    f"{md(names.get(l['source'], l['source']))} — {md(names.get(l['target'], l['target']))} ({md(l['label'])})" for l in afp) or "none"), "",
                f"**Relation misses ({len(amiss)})**: " + (", ".join(" — ".join(md(x) for x in sorted(k)) for k in amiss) or "none"), ""]
    return "\n".join(out) + "\n"


def main(argv=None, route=None):
    """route: optional Playwright context hook, used by the tests to mock an endpoint."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", help="chat-completions URL; runs the LLM engine instead of offline")
    ap.add_argument("--model", help="model name (required with --endpoint)")
    ap.add_argument("--key-env", help="name of the environment variable that holds the API key")
    ap.add_argument("--max-entities", type=int, help="override the page's Max entities field (5-40)")
    ap.add_argument("--only", help="score only gold files whose name contains this")
    ap.add_argument("--timeout", type=int, default=180, help="seconds to wait per document")
    ap.add_argument("--out", help="also write the report to this file")
    ap.add_argument("--quiet", action="store_true", help="don't print the report")
    args = ap.parse_args(argv)
    if args.endpoint and not args.model:
        ap.error("--endpoint needs --model")
    if args.key_env and args.key_env not in os.environ:
        ap.error(f"environment variable {args.key_env} is not set")

    from playwright.sync_api import sync_playwright
    from harness import open_page

    golds, skipped = [], []
    for path in sorted(GOLD.glob("*.json")):
        if args.only and args.only not in path.stem: continue
        gold, index, pairs = load_gold(path)
        text = body(ROOT / gold["doc"])
        if not text:
            skipped.append(f"{path.stem}: document `{gold['doc']}` has no text yet"); continue
        golds.append((path.stem, gold, index, pairs, text))
    for doc in sorted((ROOT / "eval" / "docs").glob("*.txt")):
        if not any(g[1]["doc"] == f"eval/docs/{doc.name}" for g in golds) and not (GOLD / f"{doc.stem}.json").exists():
            skipped.append(f"{doc.stem}: no gold file" + ("" if body(doc) else " and no text yet"))

    engine = f"LLM ({args.model} at {args.endpoint})" if args.endpoint else "offline (compromise.js)"
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx, pg, errors = open_page(b, route)
        for name, gold, index, pairs, text in golds:
            print(f"== {name}", file=sys.stderr)
            try:
                got = run_page(pg, text, args)
            except Exception as e:  # one failed document (model error, timeout) shouldn't lose the rest
                skipped.append(f"{name}: run failed: {md(e)}"); continue
            r = score(gold, index, pairs, got)
            r["_nodes"] = got["nodes"]
            results.append((name, gold, r))
        b.close()
    if errors:
        print(f"page errors: {errors}", file=sys.stderr)
    text = report(results, skipped, args, engine)
    if not args.quiet:
        print(text)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
    return results


if __name__ == "__main__":
    main()
