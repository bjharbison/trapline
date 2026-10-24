"""The graph auto-fits once when the layout settles, then leaves the user's zoom alone."""
import sys, pathlib
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

TEXT = (pathlib.Path(__file__).parent / "fixtures" / "offline_sample.txt").read_text()
K = "d3.zoomTransform(d3svg.node()).k"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.set_viewport_size({"width": 1200, "height": 720})
    pg.fill("#text-input", TEXT)
    pg.click("#btn-analyse")
    pg.wait_for_function("d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    pg.wait_for_timeout(800)
    fit = pg.evaluate(K)
    check(fit < 0.74, f"view auto-fits when the layout settles (k={fit:.3f})")
    for _ in range(2):
        pg.click("#zoom-ctrl .zoom-btn >> nth=0"); pg.wait_for_timeout(400)
    zoomed = pg.evaluate(K)
    check(zoomed > fit * 1.5, "zoom-in button zooms")
    # Clicking a node starts a drag, which reheats the simulation. It must not re-fit.
    xy = pg.evaluate("""(()=>{const r=document.querySelector('#graph-svg g.node circle:nth-of-type(3)').getBoundingClientRect();
      return [r.x+r.width/2, r.y+r.height/2];})()""")
    pg.mouse.click(*xy)
    pg.wait_for_function("d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    pg.wait_for_timeout(800)
    check(pg.evaluate("!!state.selectedNode"), "node click selects the node")
    check(abs(pg.evaluate(K) - zoomed) < 1e-6, "node click keeps the user's zoom")
    pg.evaluate("togglePin(state.selectedNode.id)")
    pg.wait_for_function("d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    pg.wait_for_timeout(800)
    check(abs(pg.evaluate(K) - zoomed) < 1e-6, "pinning keeps the user's zoom")
    pg.evaluate("closeDetail()")  # the detail panel sits over the zoom controls
    pg.click("#zoom-ctrl .zoom-btn >> nth=2"); pg.wait_for_timeout(800)
    check(abs(pg.evaluate(K) - zoomed) > 1e-3, "FIT button still fits")
    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
