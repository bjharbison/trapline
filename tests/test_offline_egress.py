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

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    unexpected = []
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
    check(not unexpected, f"no unexpected network requests during offline analysis: {unexpected[:5]}")
    check(not errors, f"no uncaught browser errors: {errors}")
    ctx.close()
    browser.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
