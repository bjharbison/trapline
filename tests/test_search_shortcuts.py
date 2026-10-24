"""Graph search and keyboard shortcuts.

Typing in the search box dims non-matching nodes and links on the canvas (the entity list was
already filtered), Enter zooms to the best match and selects it, Esc clears. The type filter dims
the canvas too. Single-key shortcuts (?, /, F, +, -, 0, P, E, Esc) work outside inputs and never
fire while typing; Ctrl+Enter analyses from inside the text box. The help modal opens from ? and
the topbar button.

    python3 tests/test_search_shortcuts.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

TEXT = (pathlib.Path(__file__).parent / "fixtures" / "offline_sample.txt").read_text()
K = "d3.zoomTransform(d3svg.node()).k"
OPACITY = "() => { const o = {}; d3g.selectAll('g.node').each(function(d){ o[d.id] = +this.getAttribute('opacity'); }); return o; }"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.set_viewport_size({"width": 1200, "height": 720})

    print("shortcuts before analysis")
    check(not pg.is_visible("#help"), "help hidden on load")
    pg.keyboard.press("?")
    check(pg.is_visible("#help"), "? opens help")
    pg.keyboard.press("Escape")
    check(not pg.is_visible("#help"), "Esc closes help")
    pg.click("#btn-help")
    check(pg.is_visible("#help"), "topbar ? button opens help")
    pg.click("#help button.btn-sm")
    check(not pg.is_visible("#help"), "✕ closes help")
    pg.focus("#text-input")
    pg.keyboard.type("Alpha? /f")
    check(not pg.is_visible("#help"), "? while typing does not open help")
    check(pg.evaluate("document.activeElement.id") == "text-input", "/ while typing does not steal focus")
    check(pg.evaluate("document.getElementById('text-input').value") == "Alpha? /f", "typed characters reach the text box")
    pg.keyboard.press("f")  # no analysis yet: zoomFit must not be reached with no graph
    pg.fill("#text-input", TEXT)
    pg.keyboard.press("Control+Enter")
    pg.wait_for_function("state.analysis && d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    check(pg.evaluate("!!state.analysis"), "Ctrl+Enter inside the text box runs the analysis")
    pg.wait_for_timeout(800)
    nodes = pg.evaluate("state.analysis.nodes.map(n => ({id: n.id, name: n.name, type: n.type, mentions: n.mentions}))")
    top = max(nodes, key=lambda n: n["mentions"])
    first_word = top["name"].split()[0]
    matching = [n["id"] for n in nodes if first_word.lower() in n["name"].lower()]
    check(1 <= len(matching) < len(nodes), f"search term {first_word!r} matches a strict subset ({len(matching)} of {len(nodes)})")

    print("graph search")
    pg.evaluate("document.activeElement.blur()")  # focus is still in the text box after Ctrl+Enter
    pg.keyboard.press("Escape")  # nothing selected: no-op
    pg.keyboard.press("/")
    check(pg.evaluate("document.activeElement.id") == "search-input", "/ focuses the search box")
    pg.keyboard.type(first_word)
    op = pg.evaluate(OPACITY)
    check(all(op[i] == 1 for i in matching), "matching nodes stay lit")
    check(all(op[n["id"]] < 0.2 for n in nodes if n["id"] not in matching), "non-matching nodes are dimmed")
    lk = pg.evaluate("() => { const r = {lit: 0, dim: 0}; d3g.selectAll('line.link').each(function(d){ (+this.getAttribute('opacity') === 1 ? r.lit++ : r.dim++); }); return r; }")
    check(lk["dim"] > 0, f"links not between matches are dimmed ({lk})")
    check(pg.text_content("#entity-count").startswith(f"{len(matching)} of"), "entity list count agrees with the canvas")
    k0 = pg.evaluate(K)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(700)
    check(pg.evaluate("state.selectedNode && state.selectedNode.id") == top["id"], "Enter selects the best (most mentioned) match")
    check(pg.evaluate(K) >= 1.2 - 1e-6 and pg.evaluate(K) > k0, "Enter zooms in on the match")
    pg.keyboard.press("Escape")
    check(pg.evaluate("document.getElementById('search-input').value") == "" and pg.evaluate("state.search") == "", "Esc in the search box clears it")
    check(pg.evaluate("document.activeElement.id") != "search-input", "Esc leaves the search box")
    op = pg.evaluate(OPACITY)
    check(all(v == 1 for v in op.values()), "clearing the search relights every node")
    pg.focus("#search-input"); pg.keyboard.type("zzzqqq-no-such-entity"); pg.keyboard.press("Enter")
    check(pg.evaluate("document.getElementById('toast').textContent").startswith("No entity"), "no match → toast, no crash")
    pg.keyboard.press("Escape")

    print("type filter dims the canvas")
    other_type = next(t for t in ["org", "place", "person", "event", "other"] if any(n["type"] == t for n in nodes))
    pg.evaluate("t => setTypeFilter(t)", other_type)
    op = pg.evaluate(OPACITY)
    check(all((op[n["id"]] == 1) == (n["type"] == other_type) for n in nodes), "only nodes of the filtered type stay lit")
    pg.evaluate("setTypeFilter('all')")
    check(all(v == 1 for v in pg.evaluate(OPACITY).values()), "'all' relights every node")

    print("graph shortcuts")
    pg.evaluate("document.activeElement.blur()")
    k = pg.evaluate(K)
    pg.keyboard.press("+"); pg.wait_for_timeout(400)
    check(pg.evaluate(K) > k, "+ zooms in")
    pg.keyboard.press("-"); pg.wait_for_timeout(400)
    check(abs(pg.evaluate(K) - k) < 0.05 * k, "- zooms back out")
    pg.keyboard.press("0"); pg.wait_for_timeout(500)
    check(abs(pg.evaluate(K) - 1) < 1e-6, "0 resets the zoom")
    pg.keyboard.press("f"); pg.wait_for_timeout(700)
    check(pg.evaluate(K) < 1, "F fits the graph")
    pg.evaluate("id => selectNodeById(id)", top["id"])
    pg.keyboard.press("p")
    check(pg.evaluate("id => !!state.pinnedNodes[id]", top["id"]), "P pins the selected entity")
    pg.keyboard.press("p")
    check(pg.evaluate("id => !state.pinnedNodes[id]", top["id"]), "P again unpins")
    pg.keyboard.press("e")
    check(pg.is_visible("#edit-name") and pg.evaluate("document.activeElement.id") == "edit-name", "E opens the editor with focus in the name")
    pg.keyboard.press("Escape")
    check(not pg.is_visible("#edit-name") and pg.evaluate("!!state.selectedNode"), "Esc in the editor cancels the edit, keeps the entity")
    pg.keyboard.press("Escape")
    check(pg.evaluate("!state.selectedNode"), "Esc then closes the detail panel")
    check(pg.evaluate("document.getElementById('detail').style.display") == "none", "detail panel hidden")

    check(not errors, f"no page errors ({errors})")
    b.close()

sys.exit(1 if failures() else 0)
