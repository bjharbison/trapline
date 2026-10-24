"""API key help: the ? next to the key field opens per-provider instructions.

Checks the panel opens and closes, follows the selected provider (picked or typed URL),
links open in a new tab without an opener, and showing it makes no network request.

    python3 tests/test_key_help.py
"""
import sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

LINKS = {
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "openrouter": "https://openrouter.ai/keys",
    "xai": "https://console.x.ai",
}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    requests = []
    pg.on("request", lambda r: requests.append(r.url) if not r.url.startswith("file:") else None)
    pg.click("#pill-llm")

    print("toggle")
    check(not pg.is_visible("#key-help"), "help hidden by default")
    check("API key" in (pg.get_attribute("#key-help-btn", "title") or ""), "hover tooltip on the ? button")
    pg.click("#key-help-btn")
    check(pg.is_visible("#key-help") and pg.get_attribute("#key-help-btn", "aria-expanded") == "true", "click opens it")
    check("No key needed" in pg.text_content("#key-help"), "local: says no key is needed")
    check(pg.locator("#key-help a").count() == 0, "local: no signup link")

    print("per provider")
    for prov, url in LINKS.items():
        pg.select_option("#llm-provider", prov)
        a = pg.locator("#key-help a")
        check(pg.is_visible("#key-help"), f"{prov}: stays open across provider change")
        check(a.count() == 1 and a.get_attribute("href") == url, f"{prov}: links to {url}")
        check(a.get_attribute("target") == "_blank" and "noopener" in a.get_attribute("rel"), f"{prov}: new tab, no opener")
        check(pg.locator("#key-help li").count() >= 3, f"{prov}: step-by-step list")
        check("never saves it" in pg.text_content("#key-help"), f"{prov}: says the key is not saved")
    pg.select_option("#llm-provider", "custom")
    check("Your server decides" in pg.text_content("#key-help"), "custom: points at the server's docs")
    pg.fill("#llm-url", "https://api.openai.com/v1/chat/completions"); pg.dispatch_event("#llm-url", "input")
    check(pg.locator("#key-help a").get_attribute("href") == LINKS["openai"], "typed URL updates the help")

    pg.click("#key-help-btn")
    check(not pg.is_visible("#key-help") and pg.get_attribute("#key-help-btn", "aria-expanded") == "false", "click again closes it")
    check(not requests, f"showing help sends nothing {requests}")
    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
