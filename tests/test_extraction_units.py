"""Offline extraction units: findEntityId, resolveCoref, name cleaning, stoplist, self-loops.

Calls the page's own functions via page.evaluate. Negative cases matter most:
a false merge (two distinct entities collapsed) is worse than a leftover duplicate.

    python3 tests/test_extraction_units.py
"""
import sys
from playwright.sync_api import sync_playwright
from harness import open_page, check, failures

FIND = """([frag, names]) => {
    const map = Object.fromEntries(names.map(n => [n, slugify(n)]));
    return findEntityId(frag, names, map);
}"""

EXTRACT = """(text) => {
    document.getElementById('max-entities').value = 50;
    document.getElementById('min-mentions').value = 1;
    const a = extractEntities(text);
    return {nodes: a.nodes.map(n => ({id: n.id, name: n.name, type: n.type})), links: a.links};
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, errors = open_page(b)
    find = lambda frag, names: pg.evaluate(FIND, [frag, names])
    coref = lambda t: pg.evaluate("t => resolveCoref(t)", t)
    extract = lambda t: pg.evaluate(EXTRACT, t)

    print("findEntityId")
    check(find("US", ["Marcus", "USS Cole"]) is None, "'US' does not match 'Marcus' or 'USS Cole'")
    check(find("US", ["USS Cole", "US"]) == "us", "'US' still matches an entity named 'US' exactly")
    check(find("John", ["Johnson"]) is None, "'John' does not match 'Johnson'")
    check(find("John", ["Johnson", "John Smith"]) == "john_smith", "'John' matches 'John Smith' on a whole token")
    check(find("John", ["John Smith", "John Doe"]) is None, "ambiguous 'John' -> no match, not a guess")
    check(find("marcus hale,", ["Marcus Hale"]) == "marcus_hale", "exact match ignores case and punctuation")
    check(find("Hale", ["Marcus Hale", "Nathan Hale"]) is None, "ambiguous surname -> no match")
    check(find("Al", ["Al Jazeera"]) is None, "very short fragment refused")
    check(find("Marcus Hale the finance chief", ["Hale", "Marcus Hale"]) == "marcus_hale",
          "'Hale' inside 'Marcus Hale' is the same mention")
    check(find("Northgate Holdings paid Seaward Trading", ["Northgate Holdings", "Seaward Trading"]) is None,
          "fragment naming two entities -> no match")
    check(find("Varga", ["Elena Varga", "Varga"]) == "varga", "exact 'Varga' wins; not merged into 'Elena Varga'")

    print("resolveCoref")
    check(coref("Alice met Bob. She left.") == "Alice met Bob. She left.", "'Alice met Bob. She left.' unchanged")
    check(coref("Marcus Hale met Elena Varga. She left.") == "Marcus Hale met Elena Varga. Elena Varga left.",
          "She -> the only compatible person")
    check(coref("John Smith arrived. He left.") == "John Smith arrived. John Smith left.", "He -> sole antecedent")
    check(coref("John Smith arrived. She left.") == "John Smith arrived. She left.", "gender clash -> unchanged")
    check(coref("John Smith arrived. His car left.") == "John Smith arrived. His car left.", "possessive unchanged")
    check(coref("John Smith arrived. Later he left.") == "John Smith arrived. Later he left.", "mid-sentence pronoun unchanged")
    check(coref("John Smith arrived. They left.") == "John Smith arrived. They left.", "'They' unchanged")
    check(coref("Acme Corp grew. It hired staff.") == "Acme Corp grew. It hired staff.", "'It' unchanged")
    check(coref("The rain stopped. He left.") == "The rain stopped. He left.", "no antecedent in previous sentence -> unchanged")
    t = "Report one.\n\nJohn Smith arrived! Did he stay? no trailing stop"
    check(coref(t) == t, "text without resolvable pronouns comes back byte-identical (incl. unterminated tail)")

    print("names and stoplist")
    check(pg.evaluate("cleanName('Northgate Holdings,')") == "Northgate Holdings", "trailing comma stripped")
    check(pg.evaluate("cleanName('(Northgate Holdings.)')") == "Northgate Holdings", "surrounding punctuation stripped")
    check(pg.evaluate("cleanName('U.S.')") == "U.S.", "initialism keeps its final dot")
    check(pg.evaluate("nameKey('U.S.') === nameKey('US')"), "'U.S.' and 'US' share a key")
    check(pg.evaluate("nameKey('Marcus Hale') !== nameKey('Hale')"), "'Hale' and 'Marcus Hale' keep distinct keys")

    r = extract("Northgate Holdings, a broker, paid Brightwater Logistics. Investigators examined Northgate Holdings. "
                "Later the board of Northgate Holdings met. NORTHGATE HOLDINGS denied it.")
    ng = [n["name"] for n in r["nodes"] if n["name"].lower().startswith("northgate")]
    check(ng == ["Northgate Holdings"], f"case/punctuation variants collapse to one node {ng}")
    check(all(n["name"] == n["name"].strip(",.;: ") for n in r["nodes"]), "no node name keeps edge punctuation")

    r = extract("According to filings, Marcus Hale met Elena Varga in Rotterdam on March 3. In June, Hale resigned. "
                "On Monday, Varga flew to Cyprus. However, the inquiry continued in May.")
    names = {n["name"] for n in r["nodes"]}
    for junk in ("According", "June", "In June", "Monday", "On Monday", "May", "However", "March"):
        check(junk not in names, f"'{junk}' is not an entity")
    check("March 3" in names, "dated event 'March 3' kept")
    for real in ("Marcus Hale", "Elena Varga", "Rotterdam"):
        check(real in names, f"real entity '{real}' kept")
    check("Varga" not in names or "Elena Varga" in names, "'Varga' never replaces 'Elena Varga'")
    ids = [n["id"] for n in r["nodes"]]
    check(len(ids) == len(set(ids)), "node ids are unique")

    print("no false merge / no self-loops")
    r = extract("Marcus Hale met Elena Varga in Rotterdam. Varga runs Northgate Holdings. "
                "Hale later resigned. Elena Varga is the owner of Seaward Trading. elena varga signed. "
                "The USS Cole Foundation received a donation. US officials met Johnson.")
    by_name = {n["name"]: n["id"] for n in r["nodes"]}
    check("Elena Varga" in by_name and "elena varga" not in by_name, "lowercase variant merged into 'Elena Varga'")
    if "Varga" in by_name:
        check(by_name["Varga"] != by_name["Elena Varga"], "'Varga' stays a separate node (Dupes tab decides)")
    if "Hale" in by_name:
        check(by_name["Hale"] != by_name.get("Marcus Hale"), "'Hale' stays a separate node")
    check(all(l["source"] != l["target"] for l in r["links"]), "no self-loops")
    pair = lambda a, c: any({l["source"], l["target"]} == {by_name.get(a), by_name.get(c)} for l in r["links"])
    check(not pair("Elena Varga", "Northgate Holdings"), "'Varga runs Northgate' does not wire 'Elena Varga'")
    n = pg.evaluate("""() => { const map={'Elena Varga':'x','elena varga':'x','Rotterdam':'r'};
        return extractRelationships('Elena Varga met elena varga in Rotterdam.', map).filter(l=>l.source===l.target).length; }""")
    check(n == 0, "co-occurrence never links an id to itself")

    check(not errors, f"no page errors {errors}")
    b.close()

print(f"{len(failures())} failure(s)")
sys.exit(1 if failures() else 0)
