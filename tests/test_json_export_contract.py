"""V1 JSON export compatibility contract for future V2 importers (synthetic only).

Executes the actual doExport('json') function extracted from the shipping V1 HTML
inside an isolated browser page. No CDN, server, provider, or internet access is
needed. This is a *unit* contract: it does not test the export menu or V2 import.

    python3 tests/test_json_export_contract.py
"""
import json
import os
from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

GRAPH = {
    "id": "synthetic-graph-001",
    "title": "Fictional Northgate & Delta",
    "source": "synthetic/test",
    "summary": "Entirely fictional; <b>markup</b> stays data.",
    "nodes": [
        {"id": "varga", "name": "Elena Varga", "type": "person", "confidence": "high",
         "mentions": 2, "description": 'Synthetic "analyst" note <img src=x onerror=alert(1)>',
         "degree": 1, "x": 13.25, "y": -9.5},
        {"id": "northgate", "name": "Northgate Holdings", "type": "org",
         "confidence": "medium", "mentions": 1, "description": "Fictional organization", "degree": 1},
    ],
    "links": [
        {"source": {"id": "varga", "name": "Elena Varga", "x": 13.25},
         "target": {"id": "northgate", "name": "Northgate Holdings"},
         "relationship": "founded", "strength": 2, "confidence": "medium",
         "evidence": ["Elena Varga founded Northgate Holdings."]},
        {"source": "northgate", "target": "varga", "relationship": "mentions",
         "strength": 1, "confidence": "low", "evidence": []},
    ],
}


def actual_export_function():
    """Read the code under test; fail loudly if the V1 function moves/changes."""
    html = (ROOT / "trapline.html").read_text(encoding="utf-8")
    start = html.index("function doExport(type) {")
    end = html.index("\n// XML 1.0", start)
    code = html[start:end].strip()
    if not code.endswith("}"):
        raise AssertionError("V1 doExport extraction boundary changed")
    return code


class V1JsonExportContract(unittest.TestCase):
    def test_legacy_json_is_full_analysis_without_private_ui_state_or_egress(self):
        browser_path = os.environ.get("TRAPLINE_CHROMIUM")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=browser_path or None)
            context = browser.new_context()
            unexpected_requests = []
            context.route("**/*", lambda route: (unexpected_requests.append(route.request.url), route.abort()))
            page = context.new_page()
            page.set_content('<div id="export-menu" style="display:block"></div>')
            captured = page.evaluate("""({ code, graph }) => {
              const state = {
                analysis: graph, sna: { node_metrics: {} }, showExport: true,
                pinnedNodes: { varga: { x: 100, y: 200 } },
                apiKey: 'SYNTHETIC_TEST_SECRET_NOT_IN_EXPORT'
              };
              const downloads = [];
              const dl = (data, filename, mime) => downloads.push({ data, filename, mime });
              const toast = () => {};
              const before = JSON.stringify(state.analysis);
              // The only executed app code is the function loaded from trapline.html.
              new Function('state', 'dl', 'toast', 'document',
                code + '\\n doExport("json");')(state, dl, toast, document);
              return {
                downloads, before, after: JSON.stringify(state.analysis),
                showExport: state.showExport,
                menuDisplay: document.getElementById('export-menu').style.display
              };
            }""", {"code": actual_export_function(), "graph": GRAPH})
            context.close()
            browser.close()

        self.assertEqual(unexpected_requests, [], "V1 JSON export should not access the network")
        self.assertEqual(len(captured["downloads"]), 1)
        item = captured["downloads"][0]
        self.assertEqual(item["mime"], "application/json")
        self.assertRegex(item["filename"], r"^trapline_synthetic_test_\d{4}-\d{2}-\d{2}\.json$")
        exported = json.loads(item["data"])
        self.assertEqual(exported, GRAPH, "V2 importer must accept the complete legacy graph representation")
        self.assertEqual(captured["before"], captured["after"], "export must not change the graph")
        self.assertFalse(captured["showExport"])
        self.assertEqual(captured["menuDisplay"], "none")
        self.assertNotIn("SYNTHETIC_TEST_SECRET_NOT_IN_EXPORT", item["data"])
        self.assertNotIn("pinnedNodes", exported, "V1 JSON is not a full UI/workspace backup")
        self.assertNotIn("schema_version", exported, "V1 JSON exports are unversioned")
        self.assertIsInstance(exported["links"][0]["source"], dict)
        self.assertIsInstance(exported["links"][1]["source"], str)
        self.assertEqual(exported["links"][0]["evidence"][0],
                         "Elena Varga founded Northgate Holdings.")


if __name__ == "__main__":
    unittest.main()
