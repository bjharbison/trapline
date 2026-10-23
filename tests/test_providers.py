"""Exercise every provider preset in headless Chromium with mocked provider APIs.

Checks, per provider: preset fills the URL, the request goes to the right
place with the right headers and body quirks, List Models hits the right URL
and filters non-chat models, a full analysis renders a graph, and the API key
never lands in localStorage.
"""
import json, sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

TEXT = ("Alice Smith met Bob Jones in Paris. Alice Smith works for Acme Corp. "
        "Bob Jones is the director of Acme Corp. ") * 8
GRAPH = {"title": "T", "summary": "S", "nodes": [
    {"id": "alice", "name": "Alice Smith", "type": "person"},
    {"id": "bob", "name": "Bob Jones", "type": "person"},
    {"id": "acme", "name": "Acme Corp", "type": "org"}],
    "links": [{"source": "alice", "target": "bob", "label": "met"},
              {"source": "alice", "target": "acme", "label": "works for"}]}
MODELS = {"data": [{"id": "chat-model-b"}, {"id": "chat-model-a"},
                   {"id": "text-embedding-3-small"}, {"id": "whisper-1"}]}

CASES = {
    # provider: (expected chat URL, expected models URL, body checks)
    "openai":     ("https://api.openai.com/v1/chat/completions", "https://api.openai.com/v1/models",
                   {"max_completion_tokens": 16000, "no": ["max_tokens", "temperature"]}),
    "anthropic":  ("https://api.anthropic.com/v1/chat/completions", "https://api.anthropic.com/v1/models",
                   {"max_tokens": 16000, "no": ["temperature", "max_completion_tokens"]}),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                   "https://generativelanguage.googleapis.com/v1beta/openai/models",
                   {"max_tokens": 16000, "temperature": 0.1}),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "https://openrouter.ai/api/v1/models",
                   {"max_tokens": 16000, "temperature": 0.1}),
    "xai":        ("https://api.x.ai/v1/chat/completions", "https://api.x.ai/v1/models",
                   {"max_tokens": 16000, "temperature": 0.1}),
}
KEY = "sk-test-SECRET-123"

with sync_playwright() as p:
    b = p.chromium.launch()
    seen = []

    def handler(route):
        req = route.request
        url = req.url
        if not any(h in url for h in ["openai.com", "anthropic.com", "googleapis.com/v1beta",
                                      "openrouter.ai", "x.ai", "localhost:11434"]):
            return route.fallback()
        seen.append({"url": url, "method": req.method, "headers": req.headers,
                     "body": json.loads(req.post_data) if req.post_data else None})
        cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        if req.headers.get("authorization", "").endswith("BADKEY") or req.headers.get("x-api-key") == "BADKEY":
            return route.fulfill(status=401, headers=cors, body=json.dumps({"error": {"message": "Invalid API key"}}))
        if url.endswith("/models"):
            return route.fulfill(status=200, headers=cors, body=json.dumps(MODELS))
        return route.fulfill(status=200, headers=cors, body=json.dumps(
            {"choices": [{"message": {"content": json.dumps(GRAPH)}}]}))
    ctx, pg, errors = open_page(b, lambda c: c.route("**/*", handler))

    print("default state")
    check(pg.evaluate("state.engine") == "local", "engine defaults to local NLP")
    pg.click("#pill-llm")
    check(pg.input_value("#llm-provider") == "local", "provider defaults to local")
    check(pg.get_attribute("#small-model-notice", "style").find("block") >= 0, "small-model notice shown for local")

    for prov, (chat_url, models_url, want) in CASES.items():
        print(prov)
        pg.fill("#llm-key", "leftover-key")
        pg.select_option("#llm-provider", prov)
        check(pg.input_value("#llm-url") == chat_url, "preset fills endpoint URL")
        check(pg.input_value("#llm-key") == "", "switching provider clears the key")
        check("notice-warn" in pg.get_attribute("#egress-notice", "class"), "leaves-machine warning shown")
        check("required" in pg.text_content("#llm-key-hint"), "key marked required")
        check("none" in pg.get_attribute("#small-model-notice", "style"), "small-model notice hidden")

        # missing key is caught before any request
        pg.fill("#llm-model", "chat-model-a")
        seen.clear(); pg.click("#btn-test")
        pg.wait_for_function("document.getElementById('btn-test').disabled===false")
        check("needs an API key" in pg.inner_text("#conn-status") and not seen, "no key -> clear error, nothing sent")

        # bad key -> readable error
        pg.fill("#llm-key", "BADKEY"); pg.click("#btn-test")
        pg.wait_for_function("document.getElementById('btn-test').disabled===false")
        check("key rejected" in pg.inner_text("#conn-status"), "401 -> 'key rejected' message")

        # list models
        pg.fill("#llm-key", KEY); seen.clear()
        pg.click("#btn-models")
        pg.wait_for_function("document.getElementById('conn-status').textContent.includes('found')")
        r = [s for s in seen if s["method"] == "GET"][0]
        check(r["url"] == models_url, f"models URL {r['url']}")
        opts = pg.eval_on_selector_all("#llm-model-select option", "o=>o.map(x=>x.value).filter(Boolean)")
        check(opts == ["chat-model-a", "chat-model-b"], f"non-chat models filtered, sorted: {opts}")
        if prov == "anthropic":
            check(r["headers"].get("x-api-key") == KEY and r["headers"].get("anthropic-version"), "anthropic models: x-api-key + version")
        else:
            check(r["headers"].get("authorization") == f"Bearer {KEY}", "models: Bearer key")

        # test connection
        seen.clear(); pg.click("#btn-test")
        pg.wait_for_function("document.getElementById('btn-test').disabled===false")
        check("Connected" in pg.inner_text("#conn-status"), "test connection succeeds")

        # full analysis
        pg.fill("#text-input", TEXT); seen.clear()
        pg.click("#btn-analyse")
        pg.wait_for_function("document.getElementById('stat-nodes').textContent==='3'", timeout=20000)
        r = [s for s in seen if s["method"] == "POST"][0]
        h, body = r["headers"], r["body"]
        check(r["url"] == chat_url, "analysis POSTs to chat URL")
        check(h.get("authorization") == f"Bearer {KEY}", "chat: Bearer key")
        if prov == "anthropic":
            check(h.get("anthropic-dangerous-direct-browser-access") == "true", "anthropic browser opt-in header")
        for k, v in want.items():
            if k == "no": check(all(x not in body for x in v), f"body omits {v}")
            else: check(body.get(k) == v, f"body {k}={v}")
        check(body["model"] == "chat-model-a", "model sent")
        check(KEY not in json.dumps(pg.evaluate("Object.assign({}, localStorage)")), "key not in localStorage")

    print("local regression")
    pg.select_option("#llm-provider", "local")
    check(pg.input_value("#llm-url") == "http://localhost:11434/v1/chat/completions", "local preset URL")
    check("notice-info" in pg.get_attribute("#egress-notice", "class"), "local -> private notice")
    pg.fill("#llm-model", "qwen2.5:3b"); seen.clear(); pg.click("#btn-analyse")
    pg.wait_for_function("document.getElementById('stat-nodes').textContent==='3'", timeout=20000)
    body = [s for s in seen if s["method"] == "POST"][0]["body"]
    check(body.get("max_tokens") == 3000 and body.get("temperature") == 0.1, "local body unchanged (3000, 0.1)")
    check("authorization" not in [s for s in seen if s["method"] == "POST"][0]["headers"], "no auth header without key")

    print("custom + reload")
    pg.select_option("#llm-provider", "custom")
    check(pg.input_value("#llm-url") == "", "custom clears URL for the user")
    pg.select_option("#llm-provider", "anthropic"); pg.fill("#llm-key", KEY)
    pg.reload(); pg.wait_for_function("typeof d3 !== 'undefined'"); pg.click("#pill-llm")
    check(pg.input_value("#llm-provider") == "anthropic", "provider restored from saved URL")
    check(pg.input_value("#llm-key") == "", "key gone after reload")
    pg.select_option("#llm-provider", "openai"); pg.fill("#llm-key", KEY)

    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
