# Trapline — Backlog

Features considered but not in the current v1 build. Captured so they aren't lost.

> **None of these block Phase 1.** v1 ships as-is. This is a parking lot for "would it improve Trapline?", not a to-do list for launch.

---

## Extraction quality

> **Shipped (offline engine, no longer backlog):**
> - `findEntityId` matches exactly (case/punctuation-insensitive) first, then only on whole tokens; short fragments are refused and ambiguous fragments return no match. "US" no longer hits "USS Cole" or "Marcus", "John" no longer hits "Johnson".
> - `resolveCoref` only replaces a sentence-initial He/She when the previous sentence names exactly one compatible person (presumed gender from compromise must not clash). Possessives, objects, mid-sentence pronouns, they/it and ambiguous cases are left alone. Still heuristic: a single antecedent of unknown gender is accepted.
> - Entity names drop surrounding punctuation, and case/punctuation-only variants are one entity ("Northgate Holdings," = "Northgate Holdings").
> - Small stoplist for non-entities: months, weekdays and discourse words ("According", "June", "In June"). Dated events like "March 3" are kept.
> - No self-loops; distinct entities never share a node id.
>
> Partial names ("Varga" vs "Elena Varga") are still separate nodes on purpose: that is alias normalization, a human decision in the Dupes tab. Worth measuring whether the remaining coref is net-positive once eval material exists.

### Still open (post-launch)
- **Surname-only relationship fragments.** If no "Varga" node survives the mention/entity filters, a typed relationship whose subject is just "Varga" is wired to the only matching full name ("Elena Varga"). Single-candidate whole-token matching is intended ("John" → "John Smith"), but it is an inference, not a fact in the text.
- **Name-inside-name co-occurrence.** "Okafor" co-occurs with "Daniel Okafor" in the same sentence because it matches inside the longer mention, which inflates centrality for partial-name nodes. Skip matches whose span falls inside a longer matched name.
- **Leading "The" still splits entities** ("The FBI" / "FBI"). The stoplist also drops a real one-word "May" (Theresa May referred to by surname).
- **Passive voice reverses typed links.** "The fund was founded in 2019 by Teodora Vass" yields *fund → founded → Teodora Vass*. The relation patterns read subject-verb-object only; a "was \<verb\> by" check would flip these. Seen on `examples/investigative-report.txt`.
- **Headings bleed into entities.** Title and heading lines have no sentence-ending punctuation, so they merge with the next sentence and produce names like "FICTIONAL EXAMPLE Subject". Treating line breaks as sentence boundaries would fix most of it.

## UI

- **Detail panel covers the zoom controls.** While an entity is selected, the panel sits over the +/−/FIT buttons; close the panel or use the scroll wheel to zoom. Move the controls left of the panel when it is open.

> **Shipped in v1.x (no longer backlog):**
> - **GEXF export** for Gephi: GEXF 1.3, undirected (matching how the SNA metrics are computed), node attributes for type, confidence, mentions, description, degree and every SNA metric; edges with relationship label (also as `kind`, so Gephi keeps parallel edges apart) and strength as weight. Strings are XML-escaped and XML-illegal characters are stripped.
> - **Manual entity editing** from the detail panel: rename, retype, delete. Ids stay stable; metrics, flags and dupes recompute; pins survive. A rename onto another entity's name (ignoring case and punctuation) is refused, and points to Dupes merge only when Dupes groups the pair.

> **Shipped in v1 (no longer backlog):** output escaping at all `innerHTML` sinks (`esc()`), plus CSV formula-injection neutralization, RFC 4180 quote-doubling, and YAML frontmatter escaping (`csvCell()` and the Markdown export). These were security hardening, not features — they live in `trapline.html`.

---

## Strong candidates

_None right now. GEXF export shipped; see Shipped above._

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

### Hand-merge any two entities
**What:** Merge two entities the Dupes tab didn't group (different types, or names that aren't substrings of each other, like "Elena Varga" / "E. Varga").
**Why it helps:** Rename/retype/delete shipped, and a rename onto an existing name is refused on purpose. This is the remaining piece of manual editing.
**Recommendation:** v1.x. Keep it an explicit two-entity pick, never name-similarity automation.

### Keyboard shortcuts + help modal
**What:** Hotkeys for common actions; an in-app help/reference panel.
**Why it helps:** Speed and discoverability for power users.
**Recommendation:** Polish. Explicitly low priority — do not let it delay shipping.
