"""Edge provenance: every link remembers the sentence(s) it was extracted from.

Offline: each link's evidence is a real sentence of the analyzed text. LLM parser: model-quoted
evidence is kept only when it appears verbatim in the source text; invented quotes are replaced by a
sentence naming both entities, or dropped. UI: clicking a link (or a connection row in the entity
panel) opens the link detail with the evidence rendered as text, never as HTML. Exports: CSV, GEXF
and Markdown carry the evidence.

    python3 tests/test_provenance.py
"""
import csv, io, pathlib, sys
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

TEXT = (pathlib.Path(__file__).parent / "fixtures" / "offline_sample.txt").read_text()
HOSTILE = '<img src=x onerror=alert(1)> & "quotes"'
ENTITY_LABEL = 'x&quot;);window.__pwned=1;//&#39;'  # decoded by the attribute parser before the handler's JS runs
FOLD = "s => s.toLowerCase().replace(/[^\\p{L}\\p{M}\\p{N}]+/gu,' ').trim()"
LOAD = """(g) => { state.analysis = g; state.selectedNode = null; state.selectedLink = null; state.pinnedNodes = {}; refreshAfterEdit(); }"""

SRC = ("Elena Varga founded Northgate Holdings in 2019. The firm is based in Vienna. "
       "Northgate Holdings acquired Delta Freight last year. Marcus Hale leads Delta Freight.")
LLM_RAW = {
    "nodes": [{"id": "varga", "name": "Elena Varga", "type": "person"}, {"id": "ng", "name": "Northgate Holdings", "type": "org"},
              {"id": "delta", "name": "Delta Freight", "type": "org"}, {"id": "hale", "name": "Marcus Hale", "type": "person"},
              {"id": "vienna", "name": "Vienna", "type": "place"}],
    "links": [
        {"source": "varga", "target": "ng", "relationship": "founded", "evidence": "Elena Varga founded Northgate Holdings in 2019."},
        {"source": "ng", "target": "delta", "relationship": "acquired", "evidence": "Northgate secretly bought Delta in a cash deal."},
        {"source": "hale", "target": "varga", "relationship": "reports to", "evidence": "Hale reports to Varga."},
        {"source": "ng", "target": "vienna", "relationship": "located in", "evidence": ["The firm is based in Vienna.", 7, "The firm is based in Vienna.", "x"]},
        {"source": "hale", "target": "delta", "relationship": "leads", "evidence": HOSTILE + " Marcus Hale leads Delta Freight."},
        {"source": "varga", "target": "vienna", "relationship": "lives in", "evidence": "Northgate Holdings acquired Delta Freight last year."},
    ],
}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.set_viewport_size({"width": 1200, "height": 720})

    print("offline extraction")
    pg.fill("#text-input", TEXT)
    pg.click("#btn-analyse")
    pg.wait_for_function("d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    links = pg.evaluate("state.analysis.links.map(l => ({s: l.source.id||l.source, t: l.target.id||l.target, rel: l.relationship, ev: l.evidence}))")
    check(len(links) > 5, f"fixture yields links ({len(links)})")
    check(all(isinstance(l["ev"], list) and len(l["ev"]) >= 1 for l in links), "every offline link carries at least one sentence")
    check(all(len(l["ev"]) <= 3 for l in links), "evidence is capped at 3 sentences")
    in_text = pg.evaluate(f"""(ls) => {{ const fold = {FOLD}; const t = ' ' + fold(resolveCoref(document.getElementById('text-input').value)) + ' ';
      return ls.every(l => l.ev.every(e => t.includes(' ' + fold(e) + ' '))); }}""", links)
    check(in_text, "every offline sentence is a sentence of the analyzed (pronoun-resolved) text")
    names = pg.evaluate("Object.fromEntries(state.analysis.nodes.map(n => [n.id, n.name]))")
    co = [l for l in links if l["rel"] == "co-occurs"]
    both = pg.evaluate(f"(co) => co.every(l => l.ev.every(e => {{const f=' '+({FOLD})(e)+' '; return f.includes(' '+({FOLD})(l.sn)+' ') && f.includes(' '+({FOLD})(l.tn)+' ');}}))",
                       [{**l, "sn": names[l["s"]], "tn": names[l["t"]]} for l in co])
    check(co and both, "co-occurrence evidence names both entities")

    print("link detail from the canvas")
    pg.wait_for_timeout(300)
    n_hit = pg.evaluate("document.querySelectorAll('#graph-svg line.link-hit').length")
    check(n_hit == len(links), "one clickable hit line per link")
    pg.evaluate("zoomFit()"); pg.wait_for_timeout(800)
    # Click the midpoint of the first hit line that lies inside the canvas.
    clicked = pg.evaluate("""(() => {
      const box = document.getElementById('canvas').getBoundingClientRect();
      for (const el of document.querySelectorAll('#graph-svg line.link-hit')) {
        const r = el.getBoundingClientRect(), x = r.x + r.width/2, y = r.y + r.height/2;
        if (x > box.x+20 && x < box.right-300 && y > box.y+20 && y < box.bottom-20) { el.dispatchEvent(new MouseEvent('click', {bubbles: true, clientX: x, clientY: y})); return true; }
      }
      return false; })()""")
    check(clicked, "a link could be clicked")
    check(pg.evaluate("!!state.selectedLink && !state.selectedNode"), "clicking a link selects it, not a node")
    check(pg.is_visible("#detail blockquote.evidence"), "link detail shows the evidence")
    check(pg.evaluate("document.querySelector('#detail').textContent.includes('Link')"), "panel is labelled as a link")
    lit = pg.evaluate("d3g.selectAll('line.link').filter(d => isSelectedLink(d)).attr('stroke')")
    check("0, 200, 255" in lit or "0,200,255" in lit.replace(" ", ""), f"selected link is highlighted ({lit})")
    pg.click("#detail button.btn-sm >> nth=1")  # first endpoint button
    check(pg.evaluate("!!state.selectedNode && !state.selectedLink"), "endpoint button opens that entity")
    rows = pg.evaluate("document.querySelectorAll('#detail .conn-row').length")
    check(rows > 0, "entity panel lists connections as rows")
    pg.click("#detail .conn-row >> nth=0")
    check(pg.evaluate("!!state.selectedLink"), "clicking a connection row opens the link detail")
    pg.keyboard.press("Escape")
    check(pg.evaluate("!state.selectedLink && !state.selectedNode"), "Esc closes the link detail")

    print("new analysis clears the link selection")
    pg.evaluate("selectLink(state.analysis.links[0])")
    prev = pg.evaluate("state.analysis.id")
    pg.click("#btn-analyse")
    pg.wait_for_function("id => state.analysis.id !== id && d3sim.alpha() < d3sim.alphaMin()", arg=prev, timeout=30000)
    check(pg.evaluate("state.selectedLink === null") and pg.evaluate("document.getElementById('detail').style.display") == "none", "re-running Analyse drops the selected link and hides the panel")

    print("LLM evidence verification")
    g = pg.evaluate("([raw, src]) => parseLLMResponse(JSON.stringify(raw), src)", [LLM_RAW, SRC])
    ev = {(l["source"], l["target"]): l["evidence"] for l in g["links"]}
    check(ev[("varga", "ng")] == ["Elena Varga founded Northgate Holdings in 2019."], "verbatim quote is kept")
    check(ev[("ng", "delta")] == ["Northgate Holdings acquired Delta Freight last year."], f"invented quote is replaced by the sentence naming both ({ev[('ng','delta')]})")
    check(ev[("hale", "varga")] == [], "invented quote with no shared sentence → no evidence")
    check(ev[("ng", "vienna")] == ["The firm is based in Vienna."], f"arrays are filtered, deduped, non-strings dropped ({ev[('ng','vienna')]})")
    check(ev[("hale", "delta")] == ["Marcus Hale leads Delta Freight."], "hostile non-matching quote → located sentence instead")
    check(ev[("varga", "vienna")] == [], "a verbatim quote naming neither entity is not evidence")
    pg.evaluate(LOAD, g)
    pg.evaluate("selectLinkByKey('hale|varga|reports to')")
    check(pg.evaluate("document.querySelector('#detail').textContent.includes('unverified')"), "missing LLM evidence is called unverified in the panel")

    print("hostile evidence renders as text")
    h = {"id": "h", "title": "h", "summary": "", "source": "test",
         "nodes": [{"id": "a", "name": "A", "type": "person", "confidence": "high", "mentions": 1, "description": ""},
                   {"id": "b", "name": "B", "type": "org", "confidence": "high", "mentions": 1, "description": ""}],
         "links": [{"source": "a", "target": "b", "relationship": "pays <b>", "strength": 2, "confidence": "high", "evidence": [HOSTILE]},
                   {"source": "a", "target": "b", "relationship": ENTITY_LABEL, "strength": 1, "confidence": "low", "evidence": []}]}
    pg.evaluate(LOAD, h)
    pg.evaluate("selectLinkByKey('a|b|pays <b>')")
    check(pg.evaluate("document.querySelector('#detail blockquote.evidence').textContent") == HOSTILE, "evidence text round-trips")
    check(pg.evaluate("!document.querySelector('#detail img')"), "no element is created from hostile evidence")
    pg.evaluate("selectNodeById('a')")
    check(pg.evaluate("document.querySelector('#detail .conn-row').textContent.includes('pays <b>')"), "connection row shows the hostile label as text")
    check(pg.evaluate("!document.querySelector('#detail b')"), "no element is created from a hostile relationship label")
    pg.click("#detail .conn-row >> nth=0")
    check(pg.evaluate("state.selectedLink === 'a|b|pays <b>'"), "connection row with hostile label still opens its link")
    pg.evaluate("selectNodeById('a')")
    pg.click("#detail .conn-row >> nth=1")
    check(pg.evaluate("window.__pwned === undefined"), "HTML-entity payload in a label does not execute from the connection row")
    check(pg.evaluate("state.selectedLink") == "a|b|" + ENTITY_LABEL, "the entity-bearing label round-trips as the link key")

    print("exports carry evidence")
    pg.evaluate(LOAD, g)
    dls = []
    pg.on("download", lambda d: dls.append(d))
    pg.click("#btn-export")
    pg.click("text=CSV (nodes + edges)")
    pg.wait_for_timeout(1200)
    edges_dl = [d for d in dls if "edges" in d.suggested_filename]
    check(len(edges_dl) == 1, f"edges CSV downloaded ({[d.suggested_filename for d in dls]})")
    rows = list(csv.DictReader(io.StringIO(open(edges_dl[0].path(), encoding="utf-8").read()))) if edges_dl else [{}]
    check("evidence" in rows[0], "edges CSV has an evidence column")
    by = {(r["source_id"], r["target_id"]): r["evidence"] for r in rows}
    check(by[("varga", "ng")] == "Elena Varga founded Northgate Holdings in 2019.", "CSV evidence is the sentence")
    check(by[("hale", "varga")] == "", "CSV evidence is empty when none")
    pg.click("#btn-export")
    with pg.expect_download() as d3:
        pg.click("text=GEXF (Gephi)")
    root = ET.fromstring(open(d3.value.path(), "rb").read())
    NS = {"g": "http://gexf.net/1.3"}
    eattrs = {a.get("id") for a in root.findall(".//g:attributes[@class='edge']/g:attribute", NS)}
    check("evidence" in eattrs, "GEXF declares an evidence edge attribute")
    vals = [v.get("value") for e in root.findall(".//g:edge", NS) for v in e.findall("g:attvalues/g:attvalue[@for='evidence']", NS)]
    check("Elena Varga founded Northgate Holdings in 2019." in vals, "GEXF edge carries the sentence")
    pg.click("#btn-export")
    with pg.expect_download() as d4:
        pg.click("text=Markdown")
    md = open(d4.value.path(), encoding="utf-8").read()
    check("## Evidence" in md and "> Elena Varga founded Northgate Holdings in 2019." in md, "Markdown has an Evidence section with blockquotes")

    check(not errors, f"no page errors ({errors})")
    b.close()

sys.exit(1 if failures() else 0)
