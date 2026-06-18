# Trapline — Backlog

Features considered but not in the current v1 build. Captured so they aren't lost.

> **None of these block Phase 1.** v1 ships as-is. This is a parking lot for "would it improve Trapline?", not a to-do list for launch.

---

## Extraction quality (early post-launch)

These surfaced from a code read, not a feature wish. They affect accuracy, and two of them touch the project's core principle: never silently conflate distinct entities.

### Fix `findEntityId` substring matching
**What:** The partial-match branch returns a hit whenever either string contains the other (`n.includes(fragment) || fragment.includes(n)`). So "US" matches inside "USS Cole" and "Marcus," and "John" matches both "John Smith" and "Johnson."
**Why it matters:** During relationship extraction this silently wires edges to the wrong node — a false merge with no human in the loop, unlike the Dupes tab. Highest-value of these.
**Fix:** Require whole-token matching against word boundaries; refuse matches on very short fragments.

### Make `resolveCoref` conservative
**What:** It replaces every person-pronoun with the last-seen person across sentence boundaries, with no gender/number agreement and no ambiguity check. "Alice met Bob. She left." resolves "She" to Bob.
**Why it matters:** It can manufacture relationships that aren't in the text — injecting wrong facts, not just awkward grammar.
**Fix:** Only resolve a subject pronoun at sentence start when there's exactly one candidate antecedent; leave possessives and ambiguous cases alone. Worth measuring whether naive coref is net-positive at all once eval material exists.

> **Shipped in v1 (no longer backlog):** output escaping at all `innerHTML` sinks (`esc()`), plus CSV formula-injection neutralization, RFC 4180 quote-doubling, and YAML frontmatter escaping (`csvCell()` and the Markdown export). These were security hardening, not features — they live in `trapline.html`.

---

## Strong candidates

### Gephi / GEXF export
**What:** Export the network as a `.gexf` file for analysis in Gephi.
**Why it helps:** Gephi is the standard tool analysts move to for heavy layout and deeper SNA. Real audience fit.
**The catch:** None.
**Effort:** Low — a GEXF serializer already exists in the React `trapline_v2.html` prototype; mostly a port.
**Recommendation:** Add. Good first post-launch enhancement to v1.

---

## Plan for v2

### Remove the 5,000-character LLM input cap (chunked extraction)
**What:** v1 caps LLM-mode input at 5,000 characters per analysis (with a warning); offline mode already reads the full text. v2 removes the cap for both.
**Why it helps:** Real source material — reports, transcripts, leaked dumps — routinely runs far longer than 5,000 characters. A hard cap means the tail of a document is never analyzed.
**The catch:** A single-shot prompt to a small local model degrades on long input, and the browser's memory/context limits make large in-page handling fragile — which is exactly why v1 caps it.
**How v2 does it:** The FastAPI backend chunks the document, runs extraction per chunk, and merges entities/relationships across chunks (dedup on normalized names). Backend-mediated calls sidestep the browser constraints entirely, so arbitrarily long text can be analyzed without a hard limit.
**Recommendation:** v2. This is local-core, not network-periphery, and pairs directly with the server-side extraction already scaffolded.

### URL fetch (paste a link, auto-pull the article)
**What:** Enter a URL and have Trapline retrieve and analyze the page text.
**Why it helps:** This was the original "as easy as pasting a URL" vision. Lowest-friction input.
**The catch:** In a browser-only build, fetching arbitrary URLs requires a third-party CORS proxy (e.g. allorigins.win), which leaks the target URL to that proxy — directly at odds with the privacy promise.
**Recommendation:** Keep out of v1. The v2 roadmap already plans server-side scraping with Playwright (no third-party proxy), which is the privacy-safe way to deliver this. Build it there.

### Synology NAS / WebDAV storage
**What:** Save/sync analyses to a NAS over WebDAV.
**Why it helps:** Convenient for homelab users.
**The catch:** Niche (most analysts/journalists have no NAS), and adding credentials + a network target muddies the single-file, zero-setup, privacy-by-design story. v1's "export JSON, save anywhere" already covers the need.
**Recommendation:** Defer to v2 as one of several optional save targets (local / NAS / cloud), not a baked-in special case.

---

## Worth considering (later)

### Manual entity editing
**What:** Rename, re-type, or hand-merge entities directly in the UI.
**Why it helps:** Makes imperfect automated extraction trustworthy — the analyst can correct what the engine got wrong. Pairs naturally with the existing duplicate-merge tool.
**Recommendation:** Reasonable candidate even for a v1.x point release.

### Keyboard shortcuts + help modal
**What:** Hotkeys for common actions; an in-app help/reference panel.
**Why it helps:** Speed and discoverability for power users.
**Recommendation:** Polish. Explicitly low priority — do not let it delay shipping.
