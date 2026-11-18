# V1 JSON export contract for V2 compatibility

**Recorded:** 2026-11-18 · **Scope:** Issue #16 baseline, supporting later issue #22.
**Reference code:** `trapline.html` on `develop/v2-roadmap`.
**Test:** `python3 tests/test_json_export_contract.py`.

## What the current V1 exporter actually writes

The **JSON** export path calls `JSON.stringify(state.analysis, null, 2)`. It does not produce a versioned investigation backup. Synthetic regression coverage executes this exact function in an isolated Chromium page, without loading CDN assets or contacting any server.

- Root graph fields in the test: `id`, `title`, `source`, `summary`, `nodes`, and `links`. These are examples of actual serialized fields, **not** an exhaustive schema.
- Nodes retain IDs, names, entity types, confidence, mention counts, descriptions and any serializable graph/layout fields present on their objects.
- Link `source`/`target` may be **ID strings** or **objects with an `id`**, e.g. D3-mutated endpoint objects; importers must normalize either shape cautiously, validate referenced entity IDs, and avoid trusting arbitrary nested fields.
- Link relationship, strength, confidence and an array of evidence sentences are retained where present.
- Text containing angle brackets, quotes and Unicode survives as JSON data. The exporter does not HTML-render these values.
- Filename follows `trapline_<source slug>_<YYYY-MM-DD>.json`; MIME type is `application/json`.
- No `schema_version` is supplied. Values absent from `state.analysis` are not exported: independent UI state such as `state.pinnedNodes`, current selection, provider configuration and API key are **not** a workspace backup, even though some D3 positions may exist on exported nodes.

**Do not assume this export round-trips the full V1 UI.** It cannot by itself guarantee reconstruction of pins, filters, browser session state, input text, original source files, or historical edits. The V2.0 exit gate requires complete V2 investigation state and original documents to survive a restart. That is distinct from legacy JSON compatibility.

## Acceptance work still required under #22

1. Define strict, versioned **V2** JSON format and an explicit *unversioned legacy V1* detection path.
2. Enforce byte/depth/collection limits, safe types, unique node IDs, valid link endpoints and evidence provenance; treat document content as untrusted, never as commands.
3. Define a deterministic conversion for object-vs-ID endpoints and reject ambiguous/dangling references. Never invent unsupported evidence or silently merge ambiguous entities.
4. Test V1 synthetic exports through a *real* V2 importer and V2 JSON export/import round trips, including corrupt and malicious payloads. No importer is implemented yet.
5. Verify complete investigation backup/restore separately: SQLite metadata, content-addressed blobs, edits and coordinates/pins, checksum consistency, crash/retry recovery.

## Test scope and limitations

The new test runs `doExport('json')` from the live V1 HTML source, with mocked `dl()`/UI and a synthetic graph. It asserts stable serialization, source immutability, endpoint variants, evidence, secret isolation **when secret values remain outside `state.analysis`**, and no outbound network requests.

This is **not** a full-page menu/download test, a security proof for arbitrary graph content, an import/parity test, or a V2.0 release gate. Existing V1 browser regression tests remain authoritative for current UI behavior. No shipping code, deployment or protected branch is changed.
