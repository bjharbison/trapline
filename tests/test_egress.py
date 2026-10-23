"""The LLM panel says whether text stays on this machine, driven by the endpoint host."""
import sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

CASES = [
    ("http://localhost:11434/v1/chat/completions", "info"),
    ("http://127.0.0.1:1234/v1/chat/completions", "info"),
    ("http://[::1]:8000/v1/chat/completions", "info"),
    ("https://api.openai.com/v1/chat/completions", "warn"),
    ("http://ollama.tail1234.ts.net:11434/v1/chat/completions", "warn"),
    ("http://192.168.1.50:8000/v1/chat/completions", "warn"),
    ("http://localhost.evil.com/v1/chat/completions", "warn"),
    ("not a url", "warn"),
]

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    pg.click("#pill-llm")
    note = pg.locator("#egress-notice")
    check("notice-info" in note.get_attribute("class"), "default endpoint is local")
    for url, want in CASES:
        pg.fill("#llm-url", url)
        check(f"notice-{want}" in note.get_attribute("class"), f"{url} -> {want}")
    pg.fill("#llm-url", "https://api.openai.com/v1/chat/completions")
    pg.dispatch_event("#llm-url", "change")
    pg.reload(); pg.wait_for_function("typeof d3 !== 'undefined'")
    check("notice-warn" in note.get_attribute("class"), "warning correct after reload")
    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
