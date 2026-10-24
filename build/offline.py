#!/usr/bin/env python3
"""Build trapline-offline.html: trapline.html with every library inlined, so it runs with no network at all.

    python3 build/offline.py                 # fetch the pinned libraries from the CDN URLs in trapline.html
    python3 build/offline.py --vendor DIR    # take libraries from DIR by filename instead (no network)
    python3 build/offline.py -o out.html

What it does, and nothing else:
  - every <script src="https://..."> is replaced by <script> with that file's contents (the exact version
    the page pins, fetched from the same URL, so the two builds never drift)
  - pdf.js's worker (pdf.worker.min.js, next to pdf.min.js) is added as a text/plain block that the page
    hands to pdf.js as a blob: URL
  - the Google Fonts <link> is removed; the page falls back to the system monospace / sans-serif fonts
  - a comment at the top records the versions and build date
Standard library only. The output is a single file; nothing in it loads from the network.
"""
import argparse, datetime, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trapline.html"


def fetch(url, vendor):
    name = url.rsplit("/", 1)[-1]
    if vendor:
        p = pathlib.Path(vendor) / name
        if not p.is_file():
            sys.exit(f"missing {p} (needed for {url})")
        return p.read_text(encoding="utf-8")
    print(f"  fetching {url}")
    with urllib.request.urlopen(url, timeout=60) as r:
        if r.status != 200:
            sys.exit(f"HTTP {r.status} for {url}")
        return r.read().decode("utf-8")


def inline_safe(js):
    """JS placed inside <script> must not contain the sequences that end script data early."""
    return re.sub(r"</(script)", r"<\\/\1", js, flags=re.I).replace("<!--", "<\\!--")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", help="directory holding d3.min.js, compromise.min.js, pdf.min.js, pdf.worker.min.js")
    ap.add_argument("-o", "--out", default=str(ROOT / "trapline-offline.html"))
    a = ap.parse_args()

    html = SRC.read_text(encoding="utf-8")
    tags = re.findall(r'<script src="(https://[^"]+)"></script>', html)
    if not tags:
        sys.exit("no CDN <script src> tags found in trapline.html")
    versions = []
    for url in tags:
        js = fetch(url, a.vendor)
        m = re.search(r"\d+\.\d+\.\d+", url)
        versions.append(f"{url.rsplit('/', 1)[-1]} {m.group(0) if m else '?'}")
        html = html.replace(f'<script src="{url}"></script>', "<script>\n" + inline_safe(js) + "\n</script>", 1)
        if url.endswith("pdf.min.js"):
            worker = fetch(url[: -len("pdf.min.js")] + "pdf.worker.min.js", a.vendor)
            html = html.replace("</head>", '<script type="text/plain" id="pdf-worker-src">\n' + inline_safe(worker) + "\n</script>\n</head>", 1)
    html, n = re.subn(r'<link href="https://fonts\.googleapis\.com[^"]*" rel="stylesheet">\n?', "", html)
    if re.search(r'(src|href)="https?://', html):
        sys.exit("an external src/href survived; refusing to write a build that is not offline")
    stamp = f"<!-- Trapline offline build · {datetime.date.today().isoformat()} · inlined: {', '.join(versions)} · fonts: system fallback · built by build/offline.py -->\n"
    out = pathlib.Path(a.out)
    out.write_text(html.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + stamp, 1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB; fonts link removed: {n})")


if __name__ == "__main__":
    main()
