# T4 by hand — output-rendering injection

The automated test (`tests/test_adv_t4_render.py`) runs T4 in about a minute. This is the same test done by a person in about an hour, so the method is understood rather than watched. Do this before reading the test file; then read the test and check it against what you did.

**The mental model.** Every injection test is *sources → sinks*. Sources are anything an attacker controls: the pasted text, and, through the LLM engine, every field of the model's JSON. Sinks are every place a string is written out: entity list, detail panel, link detail, SVG labels and tooltips, the four exports. The question is whether any source reaches any sink unescaped. Nothing else.

**The tripwire.** Each payload in the fixture sets `window.__pwned` to its own tag if it ever executes. Before each step, in the browser console (F12 → Console):

```js
window.__pwned = null
```

and after each step:

```js
window.__pwned
```

`null` means nothing ran. Anything else names the payload that got through.

## Step 1 — Offline engine, hostile text (15 min)

Open `trapline.html` from `main`. Read `fixtures/t4-render-injection.txt` first: each odd-looking name carries a different payload. Paste it and Analyse.

When the graph settles: click every entity, every link, then the Flags and Dupes tabs. Check the tripwire.

Then count. Of the nine hostile names in the text, how many did the offline engine keep as entities? Write down which. (Expected: one or two. compromise.js only promotes strings that look like proper nouns, so it is a filter in its own right. That is a result, not a gap.)

## Step 2 — The LLM engine, where it matters (20 min)

The offline engine cannot produce a hostile `title`, `summary` or `description`; only a model can. A real model won't emit a payload on demand, so stand in for it. With any analysis loaded, in the console:

```js
state.analysis.title = 'Title\ntags: [injected]\nsource: "attacker"';
state.analysis.summary = '<script>window.__pwned="summary"</script>';
state.analysis.nodes[0].name = 'Marcus <img src=x onerror="window.__pwned=\'img\'"> Webb';
state.analysis.nodes[0].description = '"><svg onload="window.__pwned=\'svg\'">';
state.analysis.links[0].relationship = '\' onmouseover=\'window.__pwned="attr"\' x=\'';
refreshAfterEdit();
```

This is what a hostile model response looks like after `parseLLMResponse()` has run. Now:

1. Click node 0 in the list. Hover it on the canvas.
2. Click the ✎ (edit) button. The name goes into an `<input value="…">` — a classic attribute-breakout spot. Cancel.
3. Click link 0 on the canvas, or its row in the detail panel.
4. Check the tripwire.
5. DevTools → Elements → Ctrl+F `onerror`. Every hit should be inside text (`&lt;img src=x onerror=…`), never as a real attribute on an element.

## Step 3 — The exports, where the finding was (15 min)

With the hostile fields from step 2 still loaded, export all four formats. Open each in a text editor, not in the app it's meant for.

- **CSV:** find the `=HYPERLINK` cell. It should start with `'=`. The apostrophe is what stops a spreadsheet from evaluating it.
- **GEXF:** find `]]>`. It should read `]]&gt;`.
- **JSON:** should load in any parser; the payloads are just string values.
- **Markdown:** look at the top. Count the lines between the two `---`.

The Markdown is finding F-1. To see it live, do this step twice: once on the pre-fix page from the [`release/v1`](https://github.com/bjharbison/trapline/tree/release/v1) branch, once on `main`.

- Pre-fix: seven frontmatter lines, including `tags: [injected]` and a second `source:`. Open the file in Obsidian and look at the Properties panel. Those tags and that source are what the analyst would have seen, chosen by whoever wrote the document.
- Fixed: five lines, title on one line, inner quotes escaped.

The diff between those two files is the finding.

## Step 4 — Try to beat it (10 min)

Now that you know where `esc()` and `jsAttr()` sit, invent a payload the fixture doesn't have. Starting points:

- a name that is only a `javascript:` URL
- `<img…` (Unicode-escaped angle bracket)
- an `<a href="…">` in a description
- a 10,000-character name
- a name that is a valid Markdown image `![x](http://attacker.example/pixel.png)` — then open the export in Obsidian with the network tab open

Enter it through the ✎ editor on any node, then re-run steps 2–3 against it. Anything that gets through is your finding; add it to `FINDINGS.md` with the same columns.

## Afterwards

Read `tests/test_adv_t4_render.py`. `poke_every_sink()` is step 2; `check_exports()` is step 3; the mocked `localhost:11434` route is how the test gets a hostile model response without a model. Reading it after doing it by hand means you check the test against your understanding instead of the other way round.
