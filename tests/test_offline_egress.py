"""Default offline analysis must not contact unapproved external hosts.

The existing test harness supplies D3/compromise.js from local fixtures and
blocks fonts. This test installs a deny-all fallback *before* those explicit
routes so any unexpected network request is recorded and aborted. It does not
make calls to LLM providers or intelligence services.

Run with: python3 tests/test_offline_egress.py
"""
import sys

from playwright.sync_api import sync_playwright

from harness import PAGE, ROOT, check, failures, route_vendor

FIXTURE = (ROOT / "tests" / "fixtures" / "offline_sample.txt").read_text(encoding="utf-8")
# The browser-only page intentionally references these assets, but the harness
# serves scripts from disk and aborts fonts. An unexpected URL must be reviewed,
# even if its filename matches a locally routed vendor script.
APPROVED_ASSET_URLS = {
    "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js",
    "https://cdn.jsdelivr.net/npm/compromise@14.14.4/builds/compromise.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js",
    "https://fonts.googleapis.com/css2?family=Oxanium:wght@400;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    unexpected = []
    observed_requests = []
    errors = []

    def deny_unexpected(route):
        url = route.request.url
        if url.startswith("file:"):
            route.continue_()
        else:
            unexpected.append(url)
            route.abort()

    # Playwright runs the most recently registered matching route first.
    # Register the deny-all fallback first, then the local vendor handlers.
    ctx.route("**/*", deny_unexpected)
    route_vendor(ctx)

    page = ctx.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: observed_requests.append(request.url))
    page.goto(PAGE)
    page.wait_for_function("typeof d3 !== 'undefined' && typeof nlp !== 'undefined'", timeout=20000)

    check(page.evaluate("state.engine") == "local", "offline extraction is selected by default")
    page.fill("#text-input", FIXTURE)
    page.click("#btn-analyse")
    page.wait_for_function(
        "state.analysis && state.analysis.nodes && state.analysis.nodes.length > 0",
        timeout=30000,
    )
    check(page.evaluate("state.analysis.links.length") > 0, "synthetic text yields relationships")
    page.wait_for_timeout(500)
    unapproved_urls = sorted({
        url for url in observed_requests
        if not url.startswith(("file:", "data:", "blob:")) and url not in APPROVED_ASSET_URLS
    })
    check(not unapproved_urls, f"only reviewed asset URLs are requested: {unapproved_urls[:5]}")
    check(not unexpected, f"no unexpected network requests during offline analysis: {unexpected[:5]}")
    check(not errors, f"no uncaught browser errors: {errors}")
    ctx.close()
    browser.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
