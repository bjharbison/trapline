# Trapline V2–V3 Delivery Roadmap

**Status:** Approved direction; implementation pending  
**Updated:** 2026-10-30  
**Repository:** https://github.com/bjharbison/trapline  
**Primary integration branch:** `develop/v2-roadmap`  
**Untouched release:** `release/v1`  
**Frozen pre-V2 snapshot:** `snapshot/pre-v2-2026-10-30` at `a9e8cf7c651e025d7183f8e004af7eccb6eb22ae`  
**Shipping website:** GitHub Pages from existing `main` until explicitly changed.

## Product north star

Transform the V1 single-file, private-by-default text-to-graph utility into an accessible, persistent, evidence-grounded investigative workspace. Users can create investigations, ingest documents, analyze relationships, verify source evidence, save or resume work, and grow a body of connected knowledge over time. Keep the simple offline V1 download available permanently. No cloud account or cloud inference is required.

**Nonnegotiable guardrails:** local-first defaults; source provenance; no invented evidence; reversible analyst choices; preservation of V1; incremental deliverable PRs; quality/security/privacy gates. Public repository contains code and synthetic fixtures only, never genuine investigative documents, API secrets, private intelligence, or production database files.

## Actual baseline (2026-10-30)

- The repository's `main` has a self-contained `trapline.html` application and Playwright browser tests, but no Python/FastAPI backend, SQL persistence, or authenticated storage API.
- Existing `release/v1` branch is a historical stable version, not the same commit as current `main`.
- Existing `BACKLOG.md` identifies chunked extraction to lift the 5,000-character LLM cap; server-side URL fetching without third-party CORS proxy; optional NAS/WebDAV storage; manual entity merges; evidence consolidation; and offline extraction quality gaps.
- The README's statement that V2 is "in progress on main" is aspirational; V2 is now separately planned on `develop/v2-roadmap` to avoid breaking the shipping demo.
- No existing GitHub issues were found at the time the roadmap was created; issue tracking begins with the V2 work breakdown.

## Architecture

- **Web UI:** Reuse/refactor the present D3 visualization and entity-editor behaviors, with a project dashboard, document library, history, notes, and saved filters. Preserve mobile ergonomics.
- **Backend:** Python 3.12+, FastAPI, Pydantic, service layer, background-job abstraction, typed REST endpoints, explicit API versioning. Deploy locally with pip/uv and Docker Compose.
- **Database:** SQLite by default (SQLAlchemy + Alembic migrations), PostgreSQL-ready database URL for future multiuser use. Structured tables for investigations, documents, document versions, entities, aliases, mentions, relationships, evidence spans, analysis runs, model/config provenance, analyst edits, exports, and audit events. Foreign keys, indexes, referential integrity, case-aware matching, transactions.
- **Blob storage:** Content-addressed local filesystem per-instance with SQLite metadata, checksums, size limits, safe paths, deletion lifecycle, backups. Avoid large PDF binary blobs directly in SQL by default. Future optional NAS/WebDAV/S3-compatible adapter with explicit user configuration; no automatic cloud syncing.
- **LLM providers:** Existing offline rules, local OpenAI-compatible endpoints (Ollama, LM Studio, llama.cpp, vLLM) and opt-in cloud providers. Streaming progress, cancellation, bounded retries, chunking, resilient JSON/schema verification, per-run model provenance. Never persist provider secrets in plaintext.
- **Deployment/privacy:** Browser-only V1 remains unchanged; V2 defaults to a localhost-bound server without public auth exposure. Any remote access requires an explicit authentication/TLS threat-model review. No telemetry by default.
- **Data portability:** Versioned JSON export/import with validation and round-trip parity, alongside CSV, Obsidian Markdown and GEXF.

## Release train and exit criteria

### V2.0 — Persistent Investigations (highest priority)

Deliver:
1. Baseline verification: test V1 and document a reproducible smoke-test, freeze snapshot, and compatibility strategy.
2. API/backend scaffold, reproducible environment, container profile, CI tests and lint/type checks, health endpoint.
3. SQL migrations and local storage schema; create/list/open/update/archive investigations.
4. Safe document ingestion for text, CSV, text-based PDF; original files + extracted text, hashes, provenance, duplicates and error states; local-only default.
5. Save, restore, and autosave nodes, relationships, evidence, analyst edits, coordinates/pins and active investigation.
6. Dashboard and navigation; maintain current graph/exports; import existing V1 JSON exports when structure allows.
7. Explicit backup/restore, migration/rollback procedure and corruption recovery tests.

**V2.0 exit gate:** End-to-end synthetic scenario: create investigation → upload two documents → analyze → edit entity → close tab/server → reopen and see *all* original files, notes, graph, evidence and layout preserved; backup/restore and JSON round-trip verified; V1 still works and is not changed. No uncontrolled network egress in offline mode.

### V2.1 — Multi-Document Intelligence

Deliver: provenance per mention, source quotes with positions and document IDs, cross-document joins, analyst-confirmed alias merges/splits/undo, conservative duplicate suggestions and confidence flags, temporal relationship context, graph recalculation after edits, search/filter across investigations.

**V2.1 exit gate:** Two documents referencing the same subject connect with independently inspectable sources; ambiguous names never silently merge; undo and evidence aggregation verified by tests.

### V2.2 — Scalable/Streaming AI

Deliver: chunked ingestion beyond 5,000 characters; overlap/dedup strategy; async job queue with progress/streaming/cancellation; local and cloud provider adapters; schema validation/grounding; cost/token estimates where possible; model provenance; retry/rate-limit behavior; privacy indicators; regression evaluation on synthetic/public test corpora.

**V2.2 exit gate:** A long document's later sections are analyzed; cancel/resume does not corrupt state; unsupported claims cannot masquerade as verified evidence; local mode does not send source text to cloud.

### V2.3 — Optional Intelligence Connectors

Deliver: safe URL ingestion (server-side, no CORS proxy), documented ingestion adapters for crt.sh, Shodan, Censys and WiGLE as available, explicit opt-in per provider, citations/timestamps, quotas, key handling, legal/TOS review, source metadata and sync status. Optional NAS/WebDAV target only if core storage/backup is stable.

**V2.3 exit gate:** URL fetch protects against SSRF, local/private address access, unsafe redirects, massive responses, path traversal and malicious files; third-party calls are opt-in with origin displayed; tests with mocked sources, not secrets.

### V2.4 — Analyst Workspace & Graph Intelligence

Deliver: advanced graph search and saved queries, configurable layouts/filters and investigation views, comparison/timeline, high-quality dashboard, analytics with definitions and limitations, reports and sharing-safe exports, audit history and manual evidence review workflow.

**V2.4 exit gate:** Representative investigation can be operated end to end with evidence lineage, stable filters, persistent saved views, useful exports, accessible mobile/desktop UI, performance and privacy regression suite.

### V3+ — Explore after V2.4 exit

Prioritize only with user approval and demonstrated demand: optional PostgreSQL multiuser collaboration; roles/auditing; plugin SDK; vector/semantic retrieval with source grounding; scheduled authorized collection; local homelab/NAS synchronization; robust offline deployments; distributable desktop wrapper; image/PDF OCR with explicit resource and privacy budgets; time-series and geographic mapping. Avoid premature microservices, hosted SaaS dependency, or arbitrary autonomous collection.

## Build sequence (dependency order)

1. Baseline freeze and tests → 2. backend foundation → 3. SQL migrations → 4. secure document store → 5. investigations CRUD and restoration → 6. dashboard → 7. import/export + backup → 8. V2.0 acceptance.
9. Evidence model → 10. cross-document resolution and undo → 11. V2.1 gate.
12. chunked extraction → 13. stream/cancel/provider hardening → 14. V2.2 gate.
15. SSRF-safe URL ingestion → 16. per-provider connectors → 17. V2.3 gate.
18. graph analytics/saved queries → 19. polished investigation UX/reporting → 20. V2.4 gate.
21. V3 research memo, not unapproved production expansion.

Each issue should be small enough for a focused PR with code, tests, documentation, screenshot/API example where relevant, risk assessment, and explicit acceptance results. Dependents should not be started on assumptions about unmerged prerequisites.

## Engineering and security requirements

- PR-first: work on task-specific branch from `develop/v2-roadmap`; no force push, no automerge, no edits to `release/v1` or snapshot branches. No destructive database migration or deletion without user review.
- Avoid shared-file conflicts: one active implementation PR per subsystem and check active PRs before writing. Pull and reconcile recent integration commits before creating branches. Don't run concurrent autonomous commits to the same branch.
- For every schema change: Alembic forward migration, migration test, rollback/recovery notes, index/foreign-key checks, no silent data loss.
- For every ingestion path: content-length/max size, MIME/signature validation, canonicalization, decompression limits, file retention, safe filenames, no code execution of uploaded content, temporary-file cleanup.
- For LLM use: untrusted-document isolation, prompt-injection-aware extraction, evidence verification, no automatic external actions from document instructions, never log keys/documents.
- For URLs and connectors: deny private/loopback/metadata IPs and hostnames, DNS/redirect rebinding defenses, timeouts, response byte caps, robots/TOS/authorization review, secrets redaction.
- CI quality bar: unit/integration/browser tests; representative synthetic end-to-end smoke; deterministic fixtures; export round trips; offline egress test; formatting/type checks; accessibility/mobile smoke; migration/backup restore test.
- Decision gates: V2 release advancement only after explicit verification; avoid representing README or issues as shipped code.
- Developer experience: clear setup for novice developers; scripts and copy/paste instructions; no dependence on unexplained infrastructure.

## Autonomy operating agreement

**Build sprint:** select the highest-priority unblocked issue; read this roadmap and `BACKLOG.md`; implement a small tested change on a dedicated branch; open a PR to `develop/v2-roadmap`; include reproduction/tests, demo, risk and next step; never merge without user approval. If blocked, create/update specific issue and report blockers rather than making up completion.

**QA review:** review newest open PR and latest integrated code; run feasible tests, inspect security/privacy/compatibility and source citations, report verified vs not run, submit a review where appropriate, and create follow-ups. Do not merge or close the work automatically.

**Strategic review:** reconcile issues and PRs against exit gates; re-order/deconflict backlog, measure shipped work rather than planned claims, identify decisive blockers and propose the next issue. Keep a compact progress summary in updates/PR commentary; do not modify frozen release branches.

**Security review:** review ingestion and AI features for local-first/privacy failures, prompt injection, SSRF, secret exposure, unsafe file handling, SQL and migration data loss. Document prioritized issues and targeted regression tests. Never execute real internet-wide investigative scans or contact external intelligence services without consent.

## Open decisions / honest unknowns

- Whether to use SQLAlchemy synchronous vs asynchronous database sessions (initial simplicity favors sync SQLite with background jobs).
- Whether to embed the current `trapline.html` as legacy UI while migrating to bundled frontend components.
- Single-user localhost first is recommended; network/multi-user auth postponed until threat modeling and approval.
- Precise database import shape for historical exported JSON needs fixture analysis; no guarantees until verified.
- How to stage V2 hosting while GitHub Pages keeps serving V1.

## Completion reporting

For every recurring automation, report: branch/commit and PR URL; tests truly executed (and any failures); which release gate advanced; any dependency/blocker; whether the user needs to approve a merge. If no progress, say what prevented work. Never imply a scheduled task means a release has shipped.
