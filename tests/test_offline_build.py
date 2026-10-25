"""The offline build: build/offline.py inlines every library and the result runs with the network cut.

Builds from a vendor directory (the tests' D3 and compromise.js, plus stub pdf.js files that contain the
sequences which could end a <script> early), opens the result with every non-file request aborted, and
checks: no src/href points at the network, no request leaves the page, extraction runs end to end, and
pdf.js gets its worker from a blob: URL.

    python3 tests/test_offline_build.py
"""
import pathlib, re, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright
from harness import check, failures, ROOT, VENDOR

TEXT = (ROOT / "tests" / "fixtures" / "offline_sample.txt").read_text()
STUB_PDF = 'window.pdfjsLib={GlobalWorkerOptions:{},getDocument(){throw new Error("stub")}};var trap="</script><!--";'
STUB_WORKER = 'self.onmessage=function(){};var w="</SCRIPT>";'

tmp = pathlib.Path(tempfile.mkdtemp())
vendor = tmp / "vendor"; vendor.mkdir()
for f in ("d3.min.js", "compromise.min.js"):
    shutil.copy(VENDOR / f, vendor / f)
(vendor / "pdf.min.js").write_text(STUB_PDF)
(vendor / "pdf.worker.min.js").write_text(STUB_WORKER)
out = tmp / "trapline-offline.html"

print("build")
r = subprocess.run([sys.executable, str(ROOT / "build" / "offline.py"), "--vendor", str(vendor), "-o", str(out)], capture_output=True, text=True)
check(r.returncode == 0, f"offline.py exits 0 ({r.stdout.strip()} {r.stderr.strip()})")
html = out.read_text()
check(html.startswith("<!DOCTYPE html>\n<!-- Trapline offline build"), "build stamp at the top")
check(not re.search(r'(src|href)="https?://', html), "no src/href to the network")
check("fonts.googleapis.com" not in html, "fonts link removed")
check('id="pdf-worker-src"' in html and "<\\/SCRIPT>" in html, "worker inlined with </script> escaped")
check(html.count("<script>") >= 4, "three libraries plus the page's own script are inline")

print("runs with the network cut")
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    leaked = []
    def gate(route):
        if route.request.url.startswith("file:"):
            route.continue_()
        else:
            leaked.append(route.request.url); route.abort()
    ctx.route("**/*", gate)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(out.as_uri())
    pg.wait_for_function("typeof d3 !== 'undefined' && typeof nlp !== 'undefined' && typeof pdfjsLib !== 'undefined'", timeout=20000)
    check(pg.evaluate("trap") == "</script><!--", "a library string containing </script> survives inlining intact")
    pg.fill("#text-input", TEXT); pg.click("#btn-analyse")
    pg.wait_for_function("state.analysis && d3sim && d3sim.alpha() < d3sim.alphaMin()", timeout=30000)
    n = pg.evaluate("state.analysis.nodes.length")
    check(n > 10, f"extraction runs offline ({n} entities)")
    src = pg.evaluate("pdfWorkerSrc()")
    check(src.startswith("blob:"), f"pdf.js worker comes from a blob: URL ({src[:20]})")
    check(pg.evaluate("pdfWorkerSrc() === pdfWorkerSrc()"), "worker blob URL is created once")
    check(leaked == [], f"no request left the page ({leaked[:3]})")
    check(not errors, f"no page errors ({errors})")
    b.close()

shutil.rmtree(tmp)
sys.exit(1 if failures() else 0)
