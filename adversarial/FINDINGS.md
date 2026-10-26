# Findings

Results of the tests in [README.md](README.md), in the order they were run. Severity: **Critical** breaks the privacy promise or executes code; **High** corrupts the analyst's picture without a visible signal; **Medium** needs an unusual setup or has a visible signal; **Low** is cosmetic or already documented.

| # | Test | Finding | Severity | Status | Fix | OWASP LLM 2025 | MITRE ATLAS |
|---|---|---|---|---|---|---|---|
| F-1 | T4 | A model-authored `title` containing newlines injected keys (`tags:`, a second `source:`) into the Markdown export's YAML frontmatter. The existing escape only swapped `"` for `'`. | Medium — needs the LLM engine and a model willing to emit a multi-line title; Obsidian would then show attacker-chosen tags and source on the note | Fixed | `yamlStr()` writes a real double-quoted YAML scalar (newlines collapsed, `\` and `"` escaped); the `#` heading is collapsed to one line | LLM05 Improper Output Handling | AML.T0051.001 → AML.T0048 |

## T4 — Output-rendering injection (Oct 26 2026)

**Result: no script execution, no egress, every payload inert, across every sink.** Test: `tests/test_adv_t4_render.py`. Fixture: `fixtures/t4-render-injection.txt`.

Nine payloads (`<img onerror>`, `"><svg onload>`, attribute breakout, `javascript:` URL, YAML newline injection, wikilink breakout with `<script>`, XML CDATA breakout, CSV formula, Markdown link/image) were placed in every model-controlled field — entity name, id, type, description, mentions, confidence, relationship label, strength, evidence, title, summary — and in the pasted text for the offline engine. Every sink was then exercised: entity list, detail panel (view and edit), link detail, flags, dupes, SVG node labels and link tooltips, help modal, and the CSV, Markdown, JSON and GEXF exports.

What held:

- `esc()` / `jsAttr()` at every `innerHTML` site; D3 `.text()` for SVG labels and tooltips. No handler attribute, `<script>`, or `javascript:` href reached the DOM or SVG from either engine or from the manual editor.
- `parseLLMResponse()` coerced `type`, `confidence`, `strength` to their enums, `mentions` to an integer, and ids to `[a-z0-9_]{1,40}`, so none of those fields can carry a payload past the parser at all.
- `verifyEvidence()` rejected 2 of 3 model-supplied evidence strings as not-in-text, including the one carrying a payload; the rejected link renders with the "unverified" notice.
- GEXF: well-formed XML, names preserved as text, CDATA breakout escaped. CSV: no cell can start a formula. JSON: round-trips.
- The offline engine is itself a filter: compromise.js kept only 1 of 9 hostile strings as an entity name (`Elena [[Varga`). The LLM path is where hostile fields actually arrive, which is why the test mocks the model.

What broke: F-1 above.

Not covered by T4 (deferred): PDF upload as a vector (pdf.js parses untrusted PDFs; that is pdf.js's threat model and the offline build pins its version), and the `?` help panel's provider links, which are static.
