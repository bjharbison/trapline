# Trapline — Entity Network Intelligence

**Paste text. Get a network. Nothing leaves your machine.**

**[Try it in your browser](https://bjharbison.github.io/trapline/)**: no install. The hosted copy runs the same single file, and analysis still happens entirely on your machine.

> Turn unstructured text into an interactive relationship graph for OSINT and investigative analysis — locally and privately, in your browser.

![Trapline demo: pasting a fictional report, analysing it, opening the most central entity, and checking duplicate suggestions](docs/demo.gif)

*Offline engine (the default), run on the fictional [investigative report](examples/investigative-report.txt). No model, no key, nothing sent anywhere.*

---

## Why Trapline is different

Most network-analysis tools assume you already know your starting point. Maltego, SpiderFoot, and similar tools pivot outward from a selector — a domain, an IP, a username — querying data sources to expand the picture. The newer text-to-graph tools work from prose instead, but they're built for engineers: stand up a database, run Docker, supply a cloud LLM key. Both approaches assume technical setup and a technical operator.

Trapline assumes neither. Open one HTML file, paste in an article or report, and you get an interactive relationship graph with the social-network metrics — degree, betweenness, closeness, PageRank — already calculated, so the key actors and the critical bridges between them are visible at a glance. There's no installation, no database, and no account. Extraction runs locally — using built-in offline analysis out of the box, or a local language model you point it at — so the source text never leaves your machine unless you choose to send it somewhere.

The point is to make link analysis usable without a link-analysis toolchain. If you can use a browser, you can map a network.

---

## Features

- **Two extraction engines, private by default** — built-in rule-based extraction (compromise.js) runs fully offline with no setup, no key, and no model download. For higher-quality results, point Trapline at a local model (Ollama, LM Studio, llama.cpp). If you choose to, you can instead use a cloud provider with your own API key: OpenAI, Anthropic (Claude), Google Gemini, OpenRouter, xAI (Grok), or any other OpenAI-compatible endpoint.
- **One-click model picker** — list the models actually installed on your LLM endpoint and choose from a dropdown, so you never have to remember exact tag names.
- **Paste or upload** — type/paste text directly, or load a `.txt`, `.csv`, or text-based `.pdf`. Files are parsed in your browser and never uploaded; scanned or image-only PDFs aren't supported yet (no OCR).
- **Interactive force-directed graph** — built on D3.js; node size reflects how central a node is, and confidence is shown visually.
- **Social network analysis, computed for you** — degree centrality, betweenness, closeness, eigenvector centrality, PageRank, and clustering coefficient, all calculated in-browser.
- **Cleanup tools** — flag anomalies, and detect and merge duplicate entities.
- **Edit entities** — fix what extraction got wrong: rename an entity, change its type, or delete it (with its connections) from the detail panel. Metrics, flags, and duplicate suggestions recompute after every edit. Renaming onto an existing entity's name (ignoring case and punctuation) is refused, never merged; when the Dupes tab can combine the two, the message says so.
- **Pin and arrange** — double-click nodes to pin them and lay the network out the way you want.
- **Exports** — CSV (nodes + edges, with SNA metrics), Obsidian-ready Markdown, raw JSON, and GEXF 1.3 for [Gephi](https://gephi.org/) (nodes carry type, confidence, mentions, description, and every SNA metric; edges carry the relationship label and strength as weight).

---

## Requirements

For the default offline mode, all you need is **a modern web browser** — that's it.

To use a language model for stronger extraction (optional), run a local OpenAI-compatible endpoint and point Trapline at it. For example, with [Ollama](https://ollama.com):

```bash
ollama pull qwen2.5:3b
```

Then set the endpoint to `http://localhost:11434/v1/chat/completions` in Trapline's config panel, click **List Models**, and pick `qwen2.5:3b` from the dropdown (or type a model name directly if your endpoint doesn't expose a list). LM Studio and llama.cpp work the same way.

**Using a cloud provider instead (optional).** Switch the engine to **LLM**, pick your provider from the **Provider** list, paste your API key, click **List Models**, and choose a model. The provider fills in the endpoint for you. **Custom OpenAI-compatible** takes any other endpoint that speaks the same format, such as your own vLLM server. Your key is used only for this tab and is never saved. Your text is sent to that provider, and you pay its usage charges. The panel shows a warning whenever this is the case.

> **Model size and memory:** small models (4B or under) run slowly on CPU — expect roughly 30–120 seconds per analysis, with lower quality than a frontier model, but fully private. The model also has to fit in RAM: a 3B model such as `qwen2.5:3b` or `llama3.2:3b` needs about 2–3 GB, while `gemma3:4b` needs ~4 GB. Ollama gates loading on *free* memory, so on a small or busy machine a 4B model can refuse to load even when the OS reports plenty of reclaimable cache available — if you see a memory error, switch to a 3B model.
>
> **Remote endpoints:** if the model runs on another machine rather than `localhost`, that endpoint must accept cross-origin requests from a local file. For Ollama, set `OLLAMA_HOST=0.0.0.0` so it listens beyond localhost and `OLLAMA_ORIGINS=*` so it accepts the request, and reach it over a private network such as Tailscale rather than exposing the port to the internet.
>
> First load fetches D3.js, compromise.js, and the UI fonts from a CDN, then caches them. The text you analyze is never sent to those CDNs — see [Privacy](#privacy).

---

## Quick start

1. Download `trapline.html`.
2. Open it in your browser (double-click, or drag it into a browser window).
3. Paste your text into the input panel — or click **Upload** to load a `.txt`, `.csv`, or text-based `.pdf`.
4. Click **Analyse**. Entities and relationships populate the graph.
5. Explore, refine, and export.

That's the whole setup. No build step, no server, and — in offline mode — nothing to install at all.

Want something to try first? [`examples/`](examples/) has three short, fictional sample inputs: a news investigation, a threat-intel bulletin, and a sanctions notice.

---

## Usage

- **Analyze text** — paste an article, report, or document (works best with 200–2000 words of continuous prose) and click Analyse.
- **Read the graph** — larger nodes are more central; use the SNA metrics to sort by betweenness or PageRank to find the actors that hold the network together.
- **Refine** — review flagged anomalies, merge duplicate entities, and click an entity then ✎ to rename, retype, or delete it.
- **Arrange** — double-click nodes to pin them in place.
- **Export** — send the network to CSV, Obsidian, JSON, or Gephi (GEXF) for downstream work.

---

## How it works

Everything below runs inside the page. The only network call Trapline makes with your text is the LLM request, and only when you choose that engine.

```mermaid
flowchart LR
    A[Pasted text or an uploaded txt, csv or pdf] --> B{Engine}
    B -->|default| C[Offline: compromise.js entities, relation patterns, same-sentence co-occurrence]
    B -->|optional| D[LLM: any OpenAI-compatible chat endpoint, first 5,000 characters]
    D --> E[Parse and sanitize the JSON reply]
    C --> F[SNA metrics]
    E --> F
    F --> G[Flags and duplicate suggestions]
    G --> H[D3 force graph, entity list, detail panel]
    H -.->|merge a duplicate| F
    H --> I[Export: CSV, Markdown, JSON]
```

- **Input.** Uploaded files are read in the browser and never uploaded. CSV rows are turned into labelled sentences. PDFs go through pdf.js, which pulls out the text layer only.
- **Offline engine.** A cautious pronoun pass first: a sentence-initial *He* or *She* is replaced only when exactly one matching person was named in the sentence before. compromise.js then tags people, organizations, places and other noun phrases, and a few regexes add dates and capitalized names it missed. Relationships come from verb patterns such as *founded*, *works for* or *met with*. Entities named in the same sentence get a weaker co-occurrence link.
- **LLM engine.** The text goes to the endpoint in the config panel with a prompt asking for strict JSON. The reply is cleaned up before use: code fences are stripped, cut-off JSON is salvaged where possible, types and confidence values are limited to known values, and links to unknown entities or self-links are dropped.
- **Metrics.** Degree, betweenness, closeness, eigenvector, PageRank and clustering are computed in plain JavaScript. They are recomputed after every merge.
- **Review.** Flags point out likely brokers, isolated entities, low-confidence entities and graphs that are mostly co-occurrence. Duplicate suggestions are only suggestions. Nothing merges until you click Merge.
- **Display.** Extracted names and labels are treated as untrusted and escaped before they reach the page.

---

## Privacy

Trapline is built to keep sensitive material on your machine. What leaves your device depends entirely on which extraction engine you choose:

- **Offline mode (default):** rule-based extraction runs entirely in your browser. Your text goes nowhere.
- **Local LLM:** if you point Trapline at a model running on your own machine (Ollama, LM Studio, llama.cpp), your text goes only to that local endpoint and no further.
- **Remote LLM (your choice):** if you configure a remote provider (OpenAI, Anthropic, Gemini, OpenRouter, xAI, or your own server elsewhere), your text is sent to that provider. This is the only mode in which your text leaves your machine, and it only happens if you set it up. Whenever the endpoint isn't on your own machine, the config panel shows a warning naming the host your text will go to. That includes a model on another computer on your LAN or Tailscale network.
- **Stored settings:** your engine choice, endpoint URL, and model name are saved in the browser's `localStorage` for convenience. An API key, if you enter one, is used only for live requests and is not written to disk — it lives in the page only while the tab is open.

---

## Limitations

Trapline v1 is an honest proof-of-concept of the text → graph pipeline, not a finished analytic platform. Known limits:

- **Extraction is imperfect.** Offline mode uses pattern- and rule-based NLP (compromise.js) and will miss entities or relationships that don't fit its patterns; coreference resolution is heuristic and can mis-attribute pronouns. Verify findings against the source.
- **Small local models hallucinate.** A 3–4B model will occasionally invent entities or relationships not present in the text. Larger or remote models reduce this but don't eliminate it.
- **LLM input is capped at 5,000 characters.** In LLM mode, longer text is truncated to the first 5,000 characters (you'll see a warning). Offline mode reads the full text. The cap is lifted in v2's server-side pipeline.
- **Edits are not undoable and not saved.** Deleting an entity asks first but can't be reversed, and running Analyse again starts over from the text. Export to keep a cleaned-up network (Trapline cannot load an export back in yet). You can only merge entities that the Dupes tab groups together.

---

## Roadmap

Trapline ships in two stages:

- **v1 — single-file HTML (current):** self-contained, in-browser, local extraction. This is the shipping prototype.
- **v2 — Python + web frontend (next):** a proper rebuild with a FastAPI backend, real scraping, structured data-source plugins (Shodan, WiGLE, Censys, crt.sh), and `pip` / Docker distribution.

<!-- TODO: link to a fuller ROADMAP.md if you want to publish one -->

---

## Built with

- [D3.js](https://d3js.org/) — force-directed graph rendering
- [compromise.js](https://github.com/spencermountain/compromise) — offline rule-based NLP
- [pdf.js](https://mozilla.github.io/pdf.js/) — in-browser text extraction from PDF files
- Any OpenAI-compatible LLM backend (Ollama, LM Studio, llama.cpp, OpenAI) — optional, for higher-quality extraction

---

## License

Released under the [MIT License](LICENSE) — free to use, modify, and distribute, including commercially, with attribution.

---

## Disclaimer

Trapline is a tool for analyzing information you are authorized to collect and use. You are responsible for complying with applicable laws and the terms of service of any source you analyze. Automated extraction can be imperfect — verify findings before relying on them.
