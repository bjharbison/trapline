"""GEXF export: downloaded through the real export menu and parsed with Python's XML parser.

Checks GEXF 1.3 structure, node/edge counts, every node attribute the CSV export carries,
edge label + weight, and that hostile strings (markup, quotes, XML-illegal characters)
come back as the same text instead of breaking the file.

    python3 tests/test_gexf.py
"""
import sys
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures, ROOT

NS = {"g": "http://gexf.net/1.3"}
HOSTILE = '<img src=x onerror=alert(1)> & "quotes"'
NODE_ATTRS = {"type", "confidence", "mentions", "description", "degree", "degree_centrality",
              "betweenness", "closeness", "eigenvector", "pagerank", "clustering"}

LOAD = """(g) => { state.analysis = g; state.selectedNode = null; state.pinnedNodes = {}; refreshAfterEdit(); }"""
GRAPH = {
    "id": "t", "title": "Test & <graph>", "summary": "", "source": "test",
    "nodes": [
        {"id": "hub", "name": HOSTILE, "type": "person", "confidence": "high", "mentions": 3,
         "description": "it's a \"role\" & <b>bold</b>\x01\x0b￾ end\nline two"},
        {"id": "b", "name": "Bravo", "type": "org", "confidence": "medium", "mentions": 1, "description": ""},
        {"id": "c", "name": "Charlie", "type": "place", "confidence": "low", "mentions": 1, "description": ""},
    ],
    "links": [
        {"source": "hub", "target": "b", "relationship": "pays <cash> & 'more'", "strength": 3, "confidence": "high"},
        {"source": "c", "target": "hub", "relationship": "co-occurs", "strength": 1, "confidence": "low"},
    ],
}


def export_gexf(pg):
    pg.click("#btn-export")
    with pg.expect_download() as d:
        pg.click("text=GEXF (Gephi)")
    dl = d.value
    return dl.suggested_filename, open(dl.path(), "rb").read()


def parse(raw):
    root = ET.fromstring(raw)
    nodes = root.findall("g:graph/g:nodes/g:node", NS)
    edges = root.findall("g:graph/g:edges/g:edge", NS)
    attrs = lambda el: {v.get("for"): v.get("value") for v in el.findall("g:attvalues/g:attvalue", NS)}
    return root, nodes, edges, attrs


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)

    print("offline fixture")
    pg.fill("#text-input", (ROOT / "tests/fixtures/offline_sample.txt").read_text())
    pg.click("#btn-analyse")
    pg.wait_for_function("state.analysis && state.analysis.nodes.length > 0", timeout=30000)
    want = pg.evaluate("""() => ({n: state.analysis.nodes.length, e: state.analysis.links.length,
        hale: (() => { const n = state.analysis.nodes.find(x => x.name === 'Marcus Hale'); return {id: n.id, m: state.sna.node_metrics[n.id], deg: n.degree, mentions: n.mentions}; })()})""")
    fname, raw = export_gexf(pg)
    check(fname.startswith("trapline_") and fname.endswith(".gexf"), f"filename matches export pattern ({fname})")
    try:
        root, nodes, edges, attrs = parse(raw)
        ok = True
    except ET.ParseError as e:
        ok = False; print("   ", e)
    check(ok, "export is well-formed XML")
    if ok:
        check(root.tag == "{http://gexf.net/1.3}gexf" and root.get("version") == "1.3", "GEXF 1.3 root")
        graph = root.find("g:graph", NS)
        check(graph.get("defaultedgetype") == "undirected", "undirected, like the SNA metrics")
        declared = {a.get("id") for a in root.findall("g:graph/g:attributes[@class='node']/g:attribute", NS)}
        check(declared == NODE_ATTRS, f"node attributes declared {sorted(declared)}")
        check(len(nodes) == want["n"], f"node count {len(nodes)} == {want['n']}")
        check(len(edges) == want["e"], f"edge count {len(edges)} == {want['e']}")
        check(all(set(attrs(n)) == NODE_ATTRS for n in nodes), "every node carries every attribute")
        hale = next((n for n in nodes if n.get("label") == "Marcus Hale"), None)
        check(hale is not None and hale.get("id") == want["hale"]["id"], "node id and label")
        if hale is not None:
            a = attrs(hale)
            check(abs(float(a["betweenness"]) - want["hale"]["m"]["betweenness"]) < 1e-5, "betweenness value exported")
            check(abs(float(a["pagerank"]) - want["hale"]["m"]["pagerank"]) < 1e-5, "pagerank value exported")
            check(int(a["degree"]) == want["hale"]["deg"] and int(a["mentions"]) == want["hale"]["mentions"], "degree + mentions exported")
        ids = {n.get("id") for n in nodes}
        check(all(e.get("source") in ids and e.get("target") in ids for e in edges), "every edge points at a node")
        check(all(e.get("label") and float(e.get("weight")) in (1.0, 2.0, 3.0) for e in edges), "edges have label + weight")

    print("hostile strings")
    pg.evaluate(LOAD, GRAPH)
    pg.evaluate("() => { const n = state.analysis.nodes[0]; n.description = n.description.replace(' end', String.fromCharCode(0xD800) + ' end'); }")
    fname, raw = export_gexf(pg)
    try:
        root, nodes, edges, attrs = parse(raw)
        ok = True
    except ET.ParseError as e:
        ok = False; print("   ", e)
    check(ok, "hostile export is well-formed XML")
    check(b"<img" not in raw, "no raw markup in the file")
    if ok:
        hub = next(n for n in nodes if n.get("id") == "hub")
        check(hub.get("label") == HOSTILE, "hostile name round-trips exactly")
        desc = attrs(hub)["description"]
        check(desc == "it's a \"role\" & <b>bold</b> end\nline two", f"illegal XML chars stripped, newline kept ({desc!r})")
        e0 = next(e for e in edges if e.get("source") == "hub")
        check(e0.get("label") == "pays <cash> & 'more'" and e0.get("weight") == "3", "edge label escaped, weight = strength")
        check(root.find("g:meta/g:description", NS).text == "Test & <graph>", "title escaped in meta")
    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
