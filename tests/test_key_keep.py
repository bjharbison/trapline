"""The API key is memory-only unless "Keep key for this tab" is ticked.

Default: nothing in any storage, key gone after reload. Ticked: key in sessionStorage only (never
localStorage), restored after reload with the box still ticked, invisible to a second tab, and
forgotten when the box is unticked, the field is cleared, or the provider changes.

    python3 tests/test_key_keep.py
"""
import sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

KEY = "sk-test-KEEP-ME-123456"
STORES = "() => ({ss: sessionStorage.getItem('trapline_llm_key'), ls: Object.keys(localStorage).filter(k => (localStorage.getItem(k)||'').includes('KEEP-ME'))})"


def reload(pg):
    pg.reload(); pg.wait_for_function("typeof d3 !== 'undefined'"); pg.click("#pill-llm")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.click("#pill-llm"); pg.select_option("#llm-provider", "anthropic")

    print("default: memory only")
    check(not pg.is_checked("#llm-key-keep"), "box unticked by default")
    pg.fill("#llm-key", KEY)
    st = pg.evaluate(STORES)
    check(st["ss"] is None and st["ls"] == [], f"untick: key in no storage ({st})")
    reload(pg)
    check(pg.input_value("#llm-key") == "", "untick: key gone after reload")
    check("not saved unless" in pg.text_content("#llm-key-hint"), "hint says when it is saved")

    print("opt in")
    pg.fill("#llm-key", KEY); pg.check("#llm-key-keep")
    st = pg.evaluate(STORES)
    check(st["ss"] == KEY, "ticked: key in sessionStorage")
    check(st["ls"] == [], "ticked: key never in localStorage")
    reload(pg)
    check(pg.input_value("#llm-key") == KEY and pg.is_checked("#llm-key-keep"), "ticked: key and box restored after reload")
    pg2 = ctx.new_page(); pg2.goto(pg.url); pg2.wait_for_function("typeof d3 !== 'undefined'"); pg2.click("#pill-llm")
    check(pg2.input_value("#llm-key") == "" and pg2.evaluate("sessionStorage.getItem('trapline_llm_key')") is None, "a second tab does not see the key")
    pg2.close()

    print("forgetting")
    pg.uncheck("#llm-key-keep")
    check(pg.evaluate(STORES)["ss"] is None, "unticking removes it from sessionStorage")
    check(pg.input_value("#llm-key") == KEY, "unticking leaves the field for this session")
    pg.check("#llm-key-keep"); pg.fill("#llm-key", "")
    check(pg.evaluate(STORES)["ss"] is None, "clearing the field removes it")
    pg.fill("#llm-key", KEY)
    check(pg.evaluate(STORES)["ss"] == KEY, "typing it again stores it while ticked")
    pg.select_option("#llm-provider", "openai")
    check(pg.input_value("#llm-key") == "" and pg.evaluate(STORES)["ss"] is None, "switching provider forgets it")
    reload(pg)
    check(pg.input_value("#llm-key") == "", "nothing comes back after it was forgotten")

    check(not errors, f"no page errors ({errors})")
    b.close()

sys.exit(1 if failures() else 0)
