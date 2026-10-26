# Annotation guidelines

These rules decide what goes in a gold file (`eval/gold/<doc>.json`) and how `score.py` compares Trapline's output to it. Annotate from the document text only. Don't add facts you know from elsewhere.

**Status.** Every gold file in this folder was drafted by Claude and is marked `"status": "DRAFT - needs Brian's review"`. Scores computed against a draft are not real numbers. See [README.md](README.md) for how a file becomes `"reviewed"`.

## Entities

An entity is a specific, named thing the text refers to. Annotate:

| Type | What counts | Examples |
|---|---|---|
| `person` | A named individual, including an online persona or handle used as a person | Harold James Nicholson, "fenwright" |
| `org` | A named organization: company, agency, court, bank, nonprofit, government, office within an agency | Kasterline Trading, Federal Bureau of Investigation, U.S. District Court for the District of Oregon |
| `place` | A named geographic location: city, country, region, named site | Riga, Cyprus, Port Anselm |
| `event` | A named event or law-enforcement operation | Operation Money Flight |
| `other` | Any other named thing: a law or executive order, malware, a named campaign, a product, a vessel | Aldermark Export Control Act, GLASSWICK, COPPER LANTERN |

Do **not** annotate:

- Dates and times ("March 3", "2019", "early June"). Trapline's offline engine extracts dates as `event` nodes; the scorer counts them as false positives on purpose, because a date isn't an entity.
- Generic nouns and roles without a name ("the defendant", "a freight agent", "the commission" in lower case, "the regional CERT").
- Money amounts, counts, case numbers, reference codes (OFR-EX-0042), statute citations by number alone.
- Titles on their own ("U.S. Attorney", "Chief Executive"). The person holding the title is the entity.
- Demonyms and adjectives ("Russian", "Venezuelan") unless they are part of a name. "Russian Federation" is a place; "Russian agents" is not an entity.

Annotate the whole text, including headers and closing disclaimers. If the text names it, it counts.

Countries and governments: when a country is named as a place ("traveled to Cyprus"), type it `place`. When the text names a government as an actor ("the Russian Federation paid"), still use one entity, typed `place`, with the government phrasing as an alias. One entity per real-world thing.

## Names and aliases

- `name` is the fullest form the text uses ("Viktor Halloran", not "Halloran").
- `aliases` lists every other form the text uses for the same entity: surnames alone ("Halloran"), acronyms ("FBI", "PDVSA", "OFAC"), short forms ("Ethics Commission"), and forms with or without a leading "the". Only list forms that actually appear in the text.
- Case and punctuation differences are the same entity and don't need separate aliases ("U.S." = "US", "Okonkwo-Reyes" = "Okonkwo Reyes"). The scorer normalizes them.
- An alias must point to exactly one entity in the document. If a surname is shared by two people in the text (a father and son), don't list the bare surname as an alias for either. The scorer refuses a gold file where one alias belongs to two entities.
- A false merge is worse than a leftover duplicate. When unsure whether two names are the same entity, keep them separate and note it in `notes`.

## Relationships

A relationship is a connection between two annotated entities that the text states: works for, met, owns, paid, charged, located in, founded, investigated, prosecuted by, and so on.

- Only stated connections. Two names in the same sentence are not related unless the sentence says how. ("Halloran and Taskiran were designated" is not a relationship between them.)
- Location counts when it's stated as a fact about the entity ("Amberway Components, a supplier based in Riga" → Amberway Components — Riga, `based in`).
- Direction is ignored for scoring. Write `source` and `target` in the natural reading order anyway.
- One entry per pair. If the text states several connections between the same two entities, join the labels: `"founded; owns"`.
- `source` and `target` use the entity's `name` exactly as written in the gold file.
- `label` is a short verb phrase. It's for the reviewer. The scorer doesn't compare labels.

## Gold file format

```json
{
  "status": "DRAFT - needs Brian's review",
  "doc": "examples/sanctions-filing.txt",
  "notes": ["anything a reviewer should look at"],
  "entities": [
    {"name": "Viktor Halloran", "type": "person", "aliases": ["Halloran"]}
  ],
  "relations": [
    {"source": "Viktor Halloran", "target": "Kasterline Trading", "label": "founded; owns"}
  ]
}
```

`doc` is the document path relative to the repository root.

## How the scorer matches

`score.py` runs Trapline on the document, then compares.

**Normalization.** Both sides are lower-cased, periods are removed, every run of other non-letter, non-digit characters becomes one space, and a leading "the " is dropped. "U.S. Attorney's Office" and "US Attorney s Office" normalize the same. This mirrors the page's own `nameKey()`, plus the article rule.

**Entities.** An extracted entity matches a gold entity when its normalized name equals the gold entity's normalized name or any normalized alias. There is no fuzzy or substring matching: "Halloran Trading" does not match "Viktor Halloran".

Each extracted entity is one of:

- **match**: the first extracted entity to hit a gold entity.
- **duplicate**: another extracted entity that hits a gold entity already matched ("Halloran" after "Viktor Halloran"). It names a real entity, so it counts as correct for precision, but it doesn't add recall. Duplicates are listed so fragmentation is visible.
- **false positive**: matches no gold entity.

A gold entity no extracted entity hits is a **miss**.

- Entity precision = (matches + duplicates) / extracted entities
- Entity recall = matched gold entities / gold entities
- F1 = 2PR / (P + R)

Type is not part of F1. The report gives type agreement on matched entities separately.

**Relations.** Each extracted link's two endpoints are mapped to gold entities through the entity matching above, then compared as an unordered pair. A link is:

- **match**: the first link to hit a gold relation pair.
- **duplicate**: another link that maps to the same gold pair (for example from a duplicate entity). Counted as correct for precision, like entity duplicates.
- **false positive**: either endpoint is a false-positive entity, both endpoints map to the same gold entity, or the pair isn't in the gold relations.

Relation precision, recall and F1 follow the same formulas. The report gives them twice: for all links, and for typed links only (leaving out the offline engine's `co-occurs` links, which are sentence co-occurrence, not stated relationships).

Overall scores are micro-averaged: counts are summed across documents before dividing.
