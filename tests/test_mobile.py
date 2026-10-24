"""Phone layout and the entity-card ⋯ menu.

At phone width the panel stacks above the graph, the graph takes the full width, and Export is
reachable. Each entity card carries a ⋯ menu with Pin / Edit / Delete so an entity can be removed
without opening the detail panel.

    python3 tests/test_mobile.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

TEXT = (pathlib.Path(__file__).parent / "fixtures" / "offline_sample.txt").read_text()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.set_viewport_size({"width": 390, "height": 844})
    dialogs, accept = [], [True]
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept() if accept[0] else d.dismiss()))

    print("phone layout")
    pg.fill("#text-input", TEXT)
    pg.click("#btn-analyse")
    pg.wait_for_function("d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    pg.wait_for_timeout(500)
    box = pg.evaluate("(() => { const r = document.getElementById('graph-area').getBoundingClientRect(); return [r.x, r.width, r.y]; })()")
    check(box[0] == 0 and box[1] == 390, f"graph takes the full width ({box})")
    left = pg.evaluate("document.getElementById('left').getBoundingClientRect().bottom")
    check(abs(left - box[2]) < 2, "panel sits above the graph")
    ex = pg.evaluate("(() => { const r = document.getElementById('btn-export').getBoundingClientRect(); return [r.right, r.bottom, r.width]; })()")
    check(0 < ex[2] and ex[0] <= 390 and ex[1] <= 844, f"Export button is inside the viewport ({ex})")
    pg.click("#btn-export")
    check(pg.is_visible("#export-menu"), "Export menu opens on a phone")
    pg.keyboard.press("Escape"); pg.evaluate("document.getElementById('export-menu').style.display='none'")
    check(not pg.is_visible("#topbar .legend"), "colour legend hidden on a phone")
    check(pg.is_visible("#btn-help"), "help button still shown")

    print("card menu")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.evaluate("document.getElementById('left').scrollTop = 1e6")
    n = pg.evaluate("document.querySelectorAll('.entity-card .card-menu-btn').length")
    total = pg.evaluate("state.analysis.nodes.length")
    check(n == total, f"every card has a ⋯ button ({n} of {total})")
    first = pg.evaluate("document.querySelector('.entity-card').dataset.id || null")
    target = pg.evaluate("[...document.querySelectorAll('.entity-card')][0].querySelector('div:nth-child(2)').textContent")
    tid = pg.evaluate("name => state.analysis.nodes.find(n => n.name === name).id", target)
    pg.click(".entity-card >> nth=0 >> .card-menu-btn")
    check(pg.is_visible("#ctx-menu"), "⋯ opens the menu")
    check(pg.evaluate("!state.selectedNode"), "opening the menu does not select the entity")
    mb = pg.evaluate("(() => { const r = document.getElementById('ctx-menu').getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; })()")
    check(mb[0] >= 0 and mb[1] <= 390 and mb[2] >= 0 and mb[3] <= 844, f"menu stays inside the viewport ({mb})")
    pg.click("#ctx-menu button >> nth=0")
    check(pg.evaluate("id => !!state.pinnedNodes[id]", tid), "Pin pins the entity")
    check(not pg.is_visible("#ctx-menu"), "menu closes after an action")
    pg.click(".entity-card >> nth=0 >> .card-menu-btn")
    check(pg.text_content("#ctx-pin-label") == "Unpin", "menu shows Unpin for a pinned entity")
    pg.keyboard.press("Escape")
    check(not pg.is_visible("#ctx-menu"), "Esc closes the menu")
    pg.click(".entity-card >> nth=0 >> .card-menu-btn")
    pg.click("#ctx-menu button >> nth=1")
    check(pg.is_visible("#edit-name") and pg.evaluate("state.selectedNode && state.selectedNode.id") == tid, "Edit opens the editor for that entity")
    pg.evaluate("closeDetail()")
    pg.click(".entity-card >> nth=0 >> .card-menu-btn")
    pg.click("#ctx-menu button.danger")
    check(len(dialogs) == 1 and "Delete" in dialogs[0], "Delete asks first")
    check(pg.evaluate("id => !state.analysis.nodes.some(n => n.id === id)", tid), "Delete removes the entity")
    check(pg.evaluate("state.analysis.nodes.length") == total - 1, "one entity fewer")
    check(pg.evaluate("document.getElementById('detail').style.display") == "none", "no panel left open")
    accept[0] = False
    tid2 = pg.evaluate("document.querySelector('.entity-card') && state.analysis.nodes.find(n => n.name === document.querySelector('.entity-card div:nth-child(2)').textContent).id")
    pg.click(".entity-card >> nth=0 >> .card-menu-btn")
    pg.click("#ctx-menu button.danger")
    check(pg.evaluate("id => state.analysis.nodes.some(n => n.id === id)", tid2), "a dismissed confirm keeps the entity")

    check(not errors, f"no page errors ({errors})")
    b.close()

sys.exit(1 if failures() else 0)
