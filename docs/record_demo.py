"""Record docs/demo.gif: offline engine, examples/investigative-report.txt.

Dev tooling only. Needs tests/vendor.sh to have run, Playwright + Chromium, and ffmpeg.
For the real UI fonts, install Oxanium and JetBrains Mono locally (the harness blocks Google Fonts).
Run: python3 docs/record_demo.py
"""
import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from harness import open_page
from playwright.sync_api import sync_playwright

TEXT = (ROOT / "examples" / "investigative-report.txt").read_text()
OUT = ROOT / "docs" / "demo.gif"
FPS = 10
W, H = 1200, 720

# A visible pointer, since screenshots don't show the mouse. Injected for the recording only.
CURSOR = """() => { const c=document.createElement('div'); c.id='rec-cursor';
  c.style.cssText='position:fixed;left:600px;top:400px;width:18px;height:18px;z-index:99999;pointer-events:none;transition:left .6s ease,top .6s ease';
  c.innerHTML='<svg width="18" height="18" viewBox="0 0 18 18"><path d="M1 1 L1 15 L5 11 L8 17 L10 16 L7 10 L13 10 Z" fill="#fff" stroke="#000" stroke-width="1"/></svg>';
  document.body.appendChild(c); }"""

def main():
    frames = pathlib.Path(tempfile.mkdtemp())
    n = [0]
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx, pg, errors = open_page(b)
        pg.set_viewport_size({"width": W, "height": H})
        pg.evaluate(CURSOR)

        def shot(k=1):
            for _ in range(k):
                pg.screenshot(path=str(frames / f"f{n[0]:04d}.png"))
                n[0] += 1
                pg.wait_for_timeout(1000 // FPS)

        def move(sel=None, xy=None, k=8):
            if sel:
                bb = pg.locator(sel).bounding_box()
                xy = (bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
            pg.evaluate("([x,y])=>{const c=document.getElementById('rec-cursor');c.style.left=x+'px';c.style.top=y+'px';}", list(xy))
            shot(k)
            return xy

        shot(8)
        move("#text-input")
        pg.fill("#text-input", TEXT)          # paste
        pg.evaluate("document.getElementById('text-input').scrollTop=0")
        shot(10)
        move("#btn-analyse")
        pg.click("#btn-analyse")
        # let the force layout run and settle (zoomFit fires on sim end)
        for _ in range(60):
            shot()
            if pg.evaluate("state.analysis && d3sim && d3sim.alpha() < d3sim.alphaMin()"):
                break
        shot(12)  # covers the 600 ms zoomFit transition that runs when the simulation ends
        # isolated nodes spread the fitted view; zoom in with the + button like a user would
        for _ in range(2):
            move("#zoom-ctrl .zoom-btn >> nth=0", k=4)
            pg.click("#zoom-ctrl .zoom-btn >> nth=0")
            shot(6)  # 300 ms zoom transition
        # most central node by betweenness
        nid = pg.evaluate("""() => { const m=state.sna.node_metrics;
          return [...state.analysis.nodes].sort((a,b)=>(m[b.id]?.betweenness||0)-(m[a.id]?.betweenness||0))[0].id; }""")
        box = pg.evaluate("""id => { const el=[...document.querySelectorAll('#graph-svg g.node')].find(g=>d3.select(g).datum().id===id);
          const r=el.querySelector('circle:nth-of-type(3)').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]; }""", nid)
        move(xy=box)
        pg.mouse.click(*box)
        shot(30)
        move("#tab-dupes")
        pg.click("#tab-dupes")
        shot(25)
        if errors:
            sys.exit(f"page errors: {errors}")
        ctx.close(); b.close()

    pal = frames / "pal.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.png"),
                    "-vf", "palettegen=max_colors=128:stats_mode=diff", str(pal)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.png"), "-i", str(pal),
                    "-lavfi", "paletteuse=dither=none:diff_mode=rectangle", "-loop", "0", str(OUT)], check=True)
    print(f"{n[0]} frames, {n[0]/FPS:.1f}s, {OUT.stat().st_size/1e6:.2f} MB -> {OUT}  (frames kept in {frames})")

if __name__ == "__main__":
    main()
