"""Shared helpers for Trapline's browser tests.

open_page() loads trapline.html in headless Chromium with the CDN libraries
served from tests/.vendor (run tests/vendor.sh first) and Google Fonts blocked,
so tests are deterministic and work without CDN access.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "trapline.html").as_uri()
VENDOR = ROOT / "tests" / ".vendor"

_failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        _failures.append(msg)


def failures():
    return list(_failures)


def route_vendor(ctx):
    """Serve CDN scripts from disk. Only these URLs are intercepted."""
    def serve(route):
        u = route.request.url
        for name in ("d3.min.js", "compromise.min.js"):
            if u.endswith(name):
                return route.fulfill(path=str(VENDOR / name), content_type="application/javascript")
        if "pdf.min.js" in u:
            return route.fulfill(body="", content_type="application/javascript")
        return route.abort()
    for pat in ("**/d3.min.js", "**/compromise.min.js", "**/pdf.min.js", "**/fonts.googleapis.com/**", "**/fonts.gstatic.com/**"):
        ctx.route(pat, serve)


def open_page(browser, extra_route=None):
    """Return (context, page, errors). errors collects uncaught page exceptions."""
    ctx = browser.new_context()
    route_vendor(ctx)
    if extra_route:
        extra_route(ctx)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(PAGE)
    pg.wait_for_function("typeof d3 !== 'undefined' && typeof nlp !== 'undefined'", timeout=20000)
    return ctx, pg, errors
