"""Unknown model name -> a hint to use List Models, not a bare "HTTP 404: model: Opus".

Mocks each provider's not-found error shape and checks Test Connection and Analyse
both show the hint. Other errors (wrong URL, a 400 that only mentions the model,
a bad key) must keep their own message.

    python3 tests/test_model_hint.py
"""
import json, sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
# provider: (status, body) the mock returns for model "Opus"
NOT_FOUND = {
    "anthropic":  (404, {"type": "error", "error": {"type": "not_found_error", "message": "model: Opus"}}),
    "openai":     (404, {"error": {"message": "The model `Opus` does not exist or you do not have access to it.", "code": "model_not_found"}}),
    "gemini":     (404, [{"error": {"code": 404, "message": "models/Opus is not found for API version v1main", "status": "NOT_FOUND"}}]),
    "openrouter": (400, {"error": {"message": "Opus is not a valid model ID", "code": 400}}),
    "xai":        (404, {"error": "The model Opus does not exist or your team does not have access to it."}),
    "local":      (404, {"error": "model \"Opus\" not found, try pulling it first"}),
}
HINT = 'Model "Opus" not found. Click List Models'
reply = {}

with sync_playwright() as p:
    b = p.chromium.launch()

    def handler(route):
        req = route.request
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        status, body = reply["now"]
        return route.fulfill(status=status, headers=CORS, body=body if isinstance(body, str) else json.dumps(body))

    hosts = ["**/api.anthropic.com/**", "**/api.openai.com/**", "**/generativelanguage.googleapis.com/**",
             "**/openrouter.ai/**", "**/api.x.ai/**", "http://localhost:11434/**", "**/llm.example.test/**"]
    ctx, pg, errors = open_page(b, lambda c: [c.route(h, handler) for h in hosts])
    pg.click("#pill-llm")

    def test(prov, resp, model="Opus"):
        reply["now"] = resp
        pg.select_option("#llm-provider", prov)
        if prov == "custom":
            pg.fill("#llm-url", "https://llm.example.test/v1/chat/completions")
        pg.fill("#llm-model", model)
        if prov != "local":
            pg.fill("#llm-key", "sk-test")
        pg.click("#btn-test")
        pg.wait_for_function("!document.getElementById('btn-test').disabled")
        return pg.text_content("#conn-status")

    print("not-found shapes")
    for prov, resp in NOT_FOUND.items():
        msg = test(prov, resp)
        check(HINT in msg, f"{prov}: hint shown ({msg!r})")

    print("analysis path")
    reply["now"] = NOT_FOUND["anthropic"]
    pg.fill("#text-input", "Alice Smith met Bob Jones in Paris. " * 10)
    pg.click("#btn-analyse")
    pg.wait_for_function("!document.getElementById('btn-analyse').disabled", timeout=15000)
    check(HINT in pg.text_content("#toast"), f"Analyse shows the hint ({pg.text_content('#toast')!r})")

    print("other errors keep their message")
    msg = test("custom", (404, "404 page not found"))
    check(HINT not in msg and "404" in msg, f"wrong URL is not called a model problem ({msg!r})")
    msg = test("anthropic", (400, {"type": "error", "error": {"type": "invalid_request_error",
               "message": "max_tokens: 16000 > 8192, the maximum for this model"}}))
    check(HINT not in msg and "max_tokens" in msg, f"other 400 that mentions the model is untouched ({msg!r})")
    msg = test("openai", (401, {"error": {"message": "Incorrect API key provided"}}))
    check("key rejected" in msg and HINT not in msg, f"bad key still says key rejected ({msg!r})")
    msg = test("anthropic", NOT_FOUND["anthropic"], model='<img src=x onerror=alert(1)>')
    check(pg.evaluate("document.querySelectorAll('img').length") == 0 and "<img" in msg, "hostile model name shown as text")

    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
