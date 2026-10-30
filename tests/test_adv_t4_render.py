"""Adversarial T4: output-rendering injection (adversarial/README.md).

Every string an attacker can put in front of the analyst — entity name, type, description,
relationship label, evidence, title, summary — is pushed through both engines into every sink:
the entity list, detail panel, link detail, flags, dupes, SVG labels and tooltips, and the four
exports. The LLM path is mocked so the model itself returns hostile fields, which the offline
path cannot produce (title/summary/description are model-authored there).

Pass: no payload executes, nothing leaves the page, every payload is inert text in every sink,
and the Markdown frontmatter still parses as exactly the keys Trapline writes.

    python3 tests/test_adv_t4_render.py
"""
import json
import sys
import pathlib
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures, ROOT

FIXTURE = (ROOT / "adversarial" / "fixtures" / "t4-render-injection.txt").read_text()
LLM_URL = "http://localhost:11434/v1/chat/completions"

P = {  # one payload per field, each sets a distinct marker if it ever runs
    "img":   "<img src=x onerror=\"window.__pwned='img'\">",
    "svg":   "\"><svg onload=\"window.__pwned='svg'\">",
    "attr":  "' onmouseover='window.__pwned=\"attr\"' x='",
    "js":    "javascript:window.__pwned='js'",
    "yaml":  "Title\ntags: [injected]\nsource: \"attacker\"",
    "wiki":  "Elena ]] <script>window.__pwned='wiki'</script> [[ Varga",
    "xml":   "]]> <script>window.__pwned='xml'</script>",
    "csv":   "=HYPERLINK(\"http://evil.example\")",
    "md":    "[click](javascript:window.__pwned='md') ![x](x)",
}
HOSTILE_LLM = {
    "title": P["yaml"],
    "summary": "<script>window.__pwned='summary'</script> " + P["md"],
    "nodes": [
        {"id": P["svg"], "name": "Marcus " + P["img"] + " Webb", "type": P["attr"], "description": P["svg"] + " founder", "mentions": "3<b>", "confidence": P["js"]},
        {"id": "harbor", "name": "Harbor " + P["svg"] + " Logistics", "type": "org", "description": P["md"]},
        {"id": "delta", "name": "Delta " + P["csv"] + " Freight", "type": "org", "description": P["xml"]},
        {"id": "varga", "name": P["wiki"], "type": "person", "description": P["attr"]},
        {"id": "vass", "name": "Teodora Vass", "type": "person", "description": "x"},
    ],
    "links": [
        {"source": P["svg"], "target": "harbor", "relationship": P["img"], "strength": "3<b>", "confidence": "high",
         "evidence": "Marcus Webb now leads Delta Freight."},
        {"source": "harbor", "target": "delta", "relationship": P["attr"], "evidence": P["svg"] + " not in text"},
        {"source": "varga", "target": "vass", "relationship": P["md"], "evidence": "Elena Varga reports to Marcus Webb."},
        {"source": "delta", "target": "vass", "relationship": "paid " + P["xml"], "evidence": ["Teodora Vass founded Northgate Holdings.", P["img"]]},
    ],
}
EGRESS_OK = ("file://", "localhost:11434", "about:blank", "data:", "blob:")


def egress(reqs):
    return [u for u in reqs if not any(u.startswith(p) or p in u for p in EGRESS_OK)
            and not any(u.endswith(n) for n in ("d3.min.js", "compromise.min.js", "pdf.min.js"))
            and "fonts.g" not in u]


def arm(pg):
    pg.evaluate("() => { window.__pwned = null; for (const f of ['alert','confirm','prompt']) window[f] = () => { window.__pwned = f; }; }")


def pwned(pg):
    return pg.evaluate("window.__pwned")


def settle(pg):
    pg.wait_for_function("d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)


def poke_every_sink(pg, label):
    """Open every panel that renders entity-derived strings."""
    ids = pg.evaluate("state.analysis.nodes.map(n => n.id)")
    for i in ids:
        pg.evaluate("id => selectNodeById(id)", i)
        pg.evaluate("() => { if (!state.editing) toggleEdit(); }")   # edit form puts the name in a value attribute
        pg.evaluate("() => { if (state.editing) toggleEdit(); }")
    keys = pg.evaluate("state.analysis.links.map(l => linkKey(l))")
    for k in keys:
        pg.evaluate("k => selectLinkByKey(k)", k)
    for t in ("flags", "dupes", "entities"):
        pg.click(f"#tab-{t}")
    pg.evaluate("() => { const n = d3g.selectAll('g.node').nodes()[0]; if (n) n.dispatchEvent(new MouseEvent('mouseover', {bubbles: true})); }")
    pg.click("#btn-help"); pg.keyboard.press("Escape")
    check(pwned(pg) is None, f"{label}: nothing executed after visiting every panel (pwned={pwned(pg)!r})")
    # No live handler or script made it into the DOM or the SVG
    live = pg.evaluate("""() => {
        const bad = [];
        document.querySelectorAll('#panel-entities *, #detail *, #panel-flags *, #panel-dupes *, svg *, #help-modal *').forEach(el => {
            for (const a of el.attributes) if (/^on/i.test(a.name) && /__pwned/.test(a.value)) bad.push(a.name);
            if (el.tagName.toLowerCase() === 'script' && /__pwned/.test(el.textContent)) bad.push('script');
            if (el.tagName.toLowerCase() === 'img' && el.getAttribute('src') === 'x') bad.push('img');
            const h = el.getAttribute && (el.getAttribute('href') || el.getAttribute('xlink:href'));
            if (h && /^\\s*javascript:/i.test(h)) bad.push('href');
        });
        return bad; }""")
    check(live == [], f"{label}: no payload element or handler in the DOM/SVG ({live})")


def exports(pg):
    out = {}
    for label, fmt in (("CSV (nodes + edges)", "csv"), ("Markdown", "md"), ("JSON", "json"), ("GEXF (Gephi)", "gexf")):
        pg.click("#btn-export")
        with pg.expect_download() as d:
            pg.click(f"text={label}")
        out[fmt] = open(d.value.path(), "rb").read().decode("utf-8")
        if fmt == "csv":  # second file follows 300ms later
            with pg.expect_download() as d2:
                pass
            out["csv_edges"] = open(d2.value.path(), "rb").read().decode("utf-8")
    return out


def check_exports(pg, label, names):
    ex = exports(pg)
    # GEXF: parses, and every hostile name survives as text
    try:
        root = ET.fromstring(ex["gexf"].encode())
        labels = [n.get("label") for n in root.iter() if n.tag.endswith("node")]
        check(all(any(n in l for l in labels) or n in ex["gexf"] for n in names), f"{label}: GEXF keeps names as text")
        check("<script" not in ex["gexf"], f"{label}: GEXF has no script element (text was escaped)")
    except ET.ParseError as e:
        check(False, f"{label}: GEXF is well-formed XML ({e})")
    # CSV: formula cells neutralized
    for line in ex["csv"].splitlines() + ex["csv_edges"].splitlines():
        for cell in line.split('","'):
            c = cell.strip('"')
            check(not c.startswith(("=", "+", "-", "@")), f"{label}: CSV cell cannot start a formula ({c[:30]!r})")
    # JSON: round-trips
    j = json.loads(ex["json"])
    check(isinstance(j.get("nodes"), list), f"{label}: JSON parses")
    # Markdown: frontmatter is exactly Trapline's keys, nothing injected
    md = ex["md"]
    check(md.startswith("---\n"), f"{label}: Markdown starts with frontmatter")
    fm = md.split("\n---\n", 1)[0].splitlines()[1:]
    keys = [l.split(":", 1)[0] for l in fm]
    check(keys == ["title", "date", "source", "nodes", "edges"], f"{label}: frontmatter keys are exactly title/date/source/nodes/edges ({keys})")
    check(all(l.startswith(("title: \"", "source: \"")) or ":" in l for l in fm), f"{label}: frontmatter values stay on their own line")
    check(not any(l.startswith("tags:") for l in fm), f"{label}: YAML injection via title did not become a frontmatter key")
    try:
        import yaml
        doc = yaml.safe_load(md.split("\n---\n", 1)[0].lstrip("-\n"))
        check(set(doc) == {"title", "date", "source", "nodes", "edges"}, f"{label}: PyYAML parses frontmatter to exactly five keys ({sorted(doc)})")
    except ImportError:
        print("  skip PyYAML parse (not installed)")
    return ex


with sync_playwright() as p:
    b = p.chromium.launch()
    reqs = []

    def handler(route):
        u = route.request.url
        reqs.append(u)
        if u.startswith(LLM_URL):
            cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
            if route.request.method == "OPTIONS":
                return route.fulfill(status=204, headers=cors)
            return route.fulfill(status=200, headers=cors, body=json.dumps(
                {"choices": [{"message": {"content": json.dumps(HOSTILE_LLM)}}]}))
        return route.fallback()

    ctx, pg, errors = open_page(b, lambda c: c.route("**/*", handler))
    pg.set_viewport_size({"width": 1200, "height": 720})
    arm(pg)

    print("offline engine, hostile fixture")
    pg.fill("#text-input", FIXTURE)
    pg.click("#btn-analyse")
    settle(pg)
    n = pg.evaluate("state.analysis.nodes.length")
    check(n > 3, f"offline extraction produced a graph ({n} nodes)")
    hostile_names = pg.evaluate("state.analysis.nodes.map(n => n.name).filter(n => /[<>\"'=\\[\\]]/.test(n))")
    print(f"  offline kept {len(hostile_names)} names with markup/quotes: {hostile_names[:4]}")
    poke_every_sink(pg, "offline")
    check_exports(pg, "offline", hostile_names)
    check(egress(reqs) == [], f"offline: no request left the page ({egress(reqs)})")
    check(errors == [], f"offline: no page errors ({errors[:2]})")

    print("LLM engine, hostile model output")
    reqs.clear(); arm(pg)
    pg.evaluate("setEngine('llm')")
    pg.select_option("#llm-provider", "local")
    pg.fill("#llm-model", "qwen2.5:3b")
    pg.click("#btn-analyse")
    pg.wait_for_function("state.analysis && state.analysis.source && state.analysis.source.startsWith('LLM')", timeout=20000)
    settle(pg)
    nodes = pg.evaluate("state.analysis.nodes.map(n => ({id: n.id, name: n.name, type: n.type, conf: n.confidence, m: n.mentions}))")
    check(all(n["type"] in ("person", "org", "place", "event", "other") for n in nodes), "LLM: type coerced to the enum")
    check(all(n["conf"] in ("high", "medium", "low") for n in nodes), "LLM: confidence coerced to the enum")
    check(all(isinstance(n["m"], int) for n in nodes), "LLM: mentions coerced to int")
    check(all(__import__("re").fullmatch(r"[a-z0-9_]{1,40}", n["id"]) for n in nodes), f"LLM: ids slugged ({[n['id'] for n in nodes]})")
    links = pg.evaluate("state.analysis.links.map(l => ({rel: l.relationship, ev: l.evidence, s: l.strength}))")
    check(all(l["s"] in (1, 2, 3) for l in links), "LLM: strength coerced")
    unverified = [l for l in links if not l["ev"]]
    print(f"  {len(unverified)} of {len(links)} links had their evidence rejected as not-in-text")
    poke_every_sink(pg, "LLM")
    llm_names = [n["name"] for n in nodes]
    ex = check_exports(pg, "LLM", llm_names)
    check(P["yaml"].split("\n")[0] in ex["md"], "LLM: title text survives in Markdown")
    check(egress(reqs) == [], f"LLM: only the configured endpoint was contacted ({egress(reqs)})")
    check(errors == [], f"LLM: no page errors ({errors[:2]})")

    print("hostile names via the editor")
    for payload in P.values():
        pg.evaluate("id => selectNodeById(id)", nodes[0]["id"])
        if not pg.is_visible("#edit-name"):
            pg.click("#detail button[title='Edit entity']")
        pg.fill("#edit-name", payload.replace("\n", " ")[:200])
        pg.click("#edit-save")
    poke_every_sink(pg, "editor")

    b.close()

f = failures()
print(f"\n{len(f)} failure(s)" if f else "\nT4 PASS: no execution, no egress, every payload inert in every sink")
sys.exit(1 if f else 0)
