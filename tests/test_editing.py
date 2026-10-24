"""Manual entity editing from the detail panel: rename, retype, delete.

Drives the real UI (✎ button, inputs, Save/Delete). Checks that ids stay stable,
a rename onto an existing name is refused (merging stays a Dupes action), metrics,
flags and dupes are recomputed, pins survive, and a hostile name renders as text
in every panel, never as HTML.

    python3 tests/test_editing.py
"""
import sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

HOSTILE = '<img src=x onerror=alert(1)> & "quotes"'
LOAD = """(g) => { state.analysis = g; state.selectedNode = null; state.pinnedNodes = {}; refreshAfterEdit(); }"""
N = lambda i, name, t: {"id": i, "name": name, "type": t, "confidence": "high", "mentions": 2, "description": ""}
L = lambda s, t: {"source": s, "target": t, "relationship": "knows", "strength": 2, "confidence": "medium"}
GRAPH = {
    "id": "t", "title": "t", "summary": "", "source": "test",
    "nodes": [N("alpha", "Alpha", "person"), N("bravo", "Bravo", "org"), N("charlie", "Charlie", "place"),
              N("delta", "Delta", "person"), N("echo", "Echo", "org"),
              N("ltd", HOSTILE + " Ltd", "person")],
    "links": [L("alpha", "bravo"), L("alpha", "charlie"), L("alpha", "delta"), L("delta", "echo"), L("alpha", "ltd")],
}
NAMES = "() => Object.fromEntries(state.analysis.nodes.map(n => [n.id, n.name]))"
METRIC = "([id, k]) => state.sna.node_metrics[id] ? state.sna.node_metrics[id][k] : null"


def edit(pg, node_id, name=None, type_=None):
    pg.evaluate("id => selectNodeById(id)", node_id)
    if not pg.is_visible("#edit-name"):  # a refused save leaves the editor open
        pg.click("#detail button[title='Edit entity']")
    if name is not None:
        pg.fill("#edit-name", name)
    if type_ is not None:
        pg.select_option("#edit-type", type_)
    pg.click("#edit-save")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    dialogs, accept = [], [False]
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept() if accept[0] else d.dismiss()))
    pg.evaluate(LOAD, GRAPH)

    print("rename")
    pg.evaluate("() => { const pin = {x: 123, y: 45}; state.pinnedNodes.bravo = pin; updatePins(); }")
    edit(pg, "alpha", name="  Alpha   Prime ")
    names = pg.evaluate(NAMES)
    check(names["alpha"] == "Alpha Prime", f"renamed, whitespace collapsed ({names['alpha']!r})")
    check(pg.evaluate("state.analysis.links.filter(l => (l.source.id||l.source) === 'alpha' || (l.target.id||l.target) === 'alpha').length") == 4, "id stable, edges kept")
    check(pg.evaluate("state.selectedNode && state.selectedNode.id") == "alpha", "renamed entity stays selected")
    check(pg.evaluate("state.selectedNode === state.analysis.nodes.find(n => n.id === 'alpha')"), "selection points at the live node")
    check(pg.evaluate("state.pinnedNodes.bravo && state.pinnedNodes.bravo.x") == 123, "pin kept after re-render")
    check(pg.evaluate("d3g.selectAll('g.node').filter(d => d.id === 'bravo').datum().fx") == 123, "pinned node still fixed in the graph")
    check(not pg.is_visible("#edit-name"), "edit form closes after save")

    print("retype")
    pg.evaluate("setTypeFilter('place')")
    edit(pg, "charlie", type_="event")
    check(pg.evaluate("state.analysis.nodes.find(n => n.id === 'charlie').type") == "event", "type changed")
    check(pg.evaluate("state.filterType") == "all", "empty type filter falls back to all")
    check("event" in pg.text_content("#type-filters"), "type filter list updated")
    check("event" in pg.text_content("#detail").lower(), "detail shows new type")

    print("name collision")
    before = pg.evaluate(NAMES)
    for clash in ("echo", "ECHO.", "alpha prime"):
        edit(pg, "delta", name=clash)
        check(pg.evaluate(NAMES) == before, f"rename to {clash!r} refused, nothing merged")
        check(pg.is_visible("#edit-name"), "editor stays open so the name can be fixed")
    check("Dupes" in pg.text_content("#toast"), f"user told to use Dupes ({pg.text_content('#toast')!r})")
    check(pg.evaluate("state.analysis.nodes.length") == 6, "no node removed")
    edit(pg, "delta", name="DELTA")
    check(pg.evaluate(NAMES)["delta"] == "DELTA", "case change of its own name allowed")

    print("hostile name renders as text")
    pg.evaluate("() => { window.__alerted = false; window.alert = function () { window.__alerted = true; }; }")
    edit(pg, "alpha", name=HOSTILE)
    check(pg.evaluate(NAMES)["alpha"] == HOSTILE, "hostile name stored verbatim")
    pg.wait_for_timeout(300)
    check(pg.evaluate("document.querySelectorAll('img').length") == 0, "no <img> element anywhere")
    check(not pg.evaluate("window.__alerted"), "no script ran")
    check(HOSTILE in pg.text_content("#entity-list"), "entity list shows it as text")
    check(HOSTILE in pg.text_content("#detail"), "detail panel shows it as text")
    pg.click("#detail button[title='Edit entity']")
    check(pg.input_value("#edit-name") == HOSTILE, "edit input holds it verbatim")
    pg.click("#detail button:has-text('Cancel')")
    check(pg.evaluate("state.dupes.length") == 1 and HOSTILE in pg.text_content("#dupe-list"), "dupes panel shows it as text")
    check(HOSTILE in pg.text_content("#flag-list"), "flags panel shows it as text")
    check(pg.text_content("#stat-bridge") == HOSTILE[:13] + "…", "stats bar shows it as text")
    labels = pg.evaluate("d3g.selectAll('g.node').filter(d => d.id === 'alpha').selectAll('text').nodes().map(t => t.textContent)")
    check(HOSTILE[:17] + "…" in labels, "graph label shows it as text")
    check(pg.evaluate("d3g.selectAll('g.node').filter(d => d.id === 'alpha').select('title').text()").startswith(HOSTILE), "graph tooltip shows it as text")
    check(pg.evaluate("document.querySelectorAll('img').length") == 0, "still no <img> after opening the editor")

    print("delete")
    pg.evaluate("selectNodeById('alpha')")
    pg.click("#detail button[title='Edit entity']")
    pg.click("#edit-delete")
    check(pg.evaluate("state.analysis.nodes.length") == 6, "cancelled confirm deletes nothing")
    check(HOSTILE in (dialogs[-1] if dialogs else ""), "confirm names the entity (as plain text)")
    bt_delta = pg.evaluate(METRIC, ["delta", "betweenness"])
    accept[0] = True
    pg.evaluate("state.pinnedNodes.alpha = {x: 1, y: 1}")
    pg.click("#edit-delete")
    check(pg.evaluate("state.analysis.nodes.some(n => n.id === 'alpha')") is False, "node removed")
    check(pg.evaluate("state.analysis.links.length") == 1, "its edges removed (5 -> 1)")
    check(pg.evaluate(METRIC, ["alpha", "degree_centrality"]) is None, "metrics no longer list it")
    check(pg.evaluate("state.analysis.nodes.find(n => n.id === 'bravo').degree") == 0, "degrees recomputed")
    check(pg.evaluate(METRIC, ["delta", "betweenness"]) != bt_delta, "betweenness recomputed")
    check(pg.evaluate("state.dupes.length") == 0, "dupes recomputed")
    check(not any(f["node_id"] == "alpha" for f in pg.evaluate("state.flags")), "flags recomputed")
    check(pg.evaluate("state.selectedNode") is None and not pg.is_visible("#detail"), "selection cleared, detail closed")
    check("alpha" not in pg.evaluate("Object.keys(state.pinnedNodes)") and "bravo" in pg.evaluate("Object.keys(state.pinnedNodes)"), "deleted node's pin dropped, others kept")
    check(pg.text_content("#stat-nodes") == "5" and pg.text_content("#stat-edges") == "1", "stats bar updated")
    check(pg.evaluate("d3g.selectAll('g.node').size()") == 5, "graph re-rendered without it")

    print("dupes merge still works")
    pg.evaluate(LOAD, {**GRAPH, "nodes": GRAPH["nodes"][:5] + [N("alpha2", "Alpha Inc", "person")],
                       "links": GRAPH["links"][:4] + [L("alpha2", "echo")]})
    pg.evaluate("mergeDupes(0)")
    check(pg.evaluate("state.analysis.nodes.length") == 5 and pg.evaluate("state.dupes.length") == 0, "merge path unchanged")

    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
