# Notes for Brian's review

Everything in `eval/gold/` is a Claude draft. This file lists what needs your call before any score is treated as real.

## 1. The federal documents have no text yet

The plan was five U.S. government press releases (public domain) in `eval/docs/`. Claude found and chose five, but couldn't save their text. The web-fetch tool in the automated run returns summaries only and won't reproduce a page word for word, even a public-domain one. Claude didn't fetch the pages another way. Annotating from summaries would make the gold describe a different text, so there is no gold for these yet.

What's there: one file per document with the header filled in (title, agency, date, source URL, public-domain line) and an empty body.

| File | Topic | Estimated length |
|---|---|---|
| `doj-nicholson-russian-agents-2009.txt` | espionage / foreign agent | ~680 words |
| `doj-venezuela-money-laundering-2022.txt` | bribery / money laundering | ~440 words |
| `doj-sdny-prc-agent-2024.txt` | foreign agent / transnational repression | ~850 words |
| `doj-sdny-export-control-2024.txt` | export control / smuggling | ~1,300 words |
| `treasury-ofac-crimea-ukraine-2016.txt` | sanctions | ~1,100 words |

The lengths are the fetch tool's estimates. Check that each one falls in 400–1,500 words once the text is pasted in.

**To do:** open each source URL, paste the press-release body (no site navigation) under the `---` line, and check that the title and date match. A later run can then draft gold files from the text in the repo.

In the meantime, the scorer was built and run against the three **fictional** samples in `examples/`, so the harness is exercised end to end. Those are Trapline's own files, so redistributing them is not a question.

## 2. Gold decisions to confirm

Claude drafted all three gold files. A second agent that hadn't seen the drafting checked two of them (`sanctions-filing`, `threat-intel-report`) against the guidelines.

**Applied from that review:**

- Removed Marta Ellingsen — Office of Financial Restrictions. The text says the Office makes no finding against her, which is not a relationship.
- Added Lina Petravicius — Riga ("met with Lina Petravicius in Riga"). The gold already had Halloran — Riga from the same sentence.
- Added Amberway Components — Istanbul ("shipped the goods to Bosphor Line Logistics in Istanbul"), to apply the place rule the same way as Taskiran — Riga.
- Added Northfold Security — GLASSWICK ("a loader we track as GLASSWICK", where "we" is Northfold).
- Added notes on the weaker relations that were kept (see each gold file's `notes`).

**Not applied (your call):**

- *COPPER LANTERN — Gdansk / Rotterdam / Hamburg.* "The campaign targeted freight forwarders and port operators in Gdansk, Rotterdam and Hamburg." Claude left these out because the campaign targets firms in those cities, and the firms are linked to their cities directly. If you include them, add all three.
- *Kestrel Port Services — Northfold Security.* The text says Kestrel's incident lead partnered with Northfold. Claude linked the person (Annika Voorhees) only. The org-level link is one step removed.
- *COPPER LANTERN — Varnholt Exchange.* "Payments for the stolen data were routed to Varnholt Exchange" doesn't say who routed them. The reviewer pointed out that this is about as indirect as COPPER LANTERN — Kestrel, which Claude kept. Keep both or drop both. Claude kept Kestrel because the text links that intrusion to the campaign ("link the two intrusions").
- *EU (threat-intel).* It appears only inside a quoted forum ad. It's kept as a place under "if the text names it, it counts". Drop it if quoted material shouldn't count.
- *Yusuf Demirel — Office of Financial Restrictions.* The sentence is passive ("His alert was later provided to the Office"). Kept, with a note.
- *The nine "designated" relations in sanctions-filing.* These come from the opening sentence plus the section headings, not one sentence per entity. Kept, because the notice is explicit that each listed party is designated. They make up a quarter of that file's relations, so they move its relation recall a lot.

**Not independently checked:** `investigative-report.json`. The reviewer saw only the other two files. Read it with the same rules in mind, especially Meridale Construction — Larkmoor Harbor Restoration Fund ("won the largest restoration contract"; the contract belongs to the fund only by context).

## 3. Rules worth a second look

- **"Trapline" is annotated** in all three fictional files because the closing disclaimers name it. That's one guaranteed miss per document for the offline engine. It's correct under "annotate the whole text", but you may prefer to exclude boilerplate disclaimers. If so, change GUIDELINES.md and the gold files together.
- **Duplicates count as correct for precision** (they name a real entity), but they don't add recall. This follows the rule that a leftover duplicate is less bad than a false merge. If you'd rather punish fragmentation, count them as false positives in `score.py` (`score()`, the `ent` line) and say so in GUIDELINES.md.
- **No partial-name credit.** "Kasterline" doesn't match "Kasterline Trading" unless the gold lists it as an alias, and the guidelines only allow aliases that appear in the text. This is deliberate: fuzzy matching in the scorer would hide the alias-fragmentation errors the eval should show.
