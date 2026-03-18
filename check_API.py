#!/usr/bin/env python3
"""
SKG-IF API checker. Two modes:

1. Static (default): validate cross-references in sample data files against
   the local file system — no running server needed.

2. Live (--live): run HTTP tests against the API stack. Requires the Docker
   stack to be running (cd testing && docker compose up).
   --base-url  Prism base URL  (default: http://localhost:4010)
   --fastapi   FastAPI base URL (default: http://localhost:8000)
   Use FastAPI directly for cases where Prism cannot route (e.g. full URL path params).

Run from the repo root:
    python check_API.py               # static only
    python check_API.py --live        # static + live
    python check_API.py --live --base-url http://localhost:4010 --fastapi http://localhost:8000

Live test coverage:
  - List endpoints     all 7 entity types return HTTP 200 with non-empty @graph
  - Pagination         page_size=1 returns 1 item; page=2 returns correct page meta
  - Detail (plain id)  products, persons, organisations, grants by short filename id
  - Detail (full URL)  percent-encoded full local_identifier URL via FastAPI direct
                       (Prism cannot route path params containing slashes)
  - embedding=false       cross-references remain as strings (default behaviour)
  - embedding=true        relevant_organisations[0], topics[].term, contributions[].by,
                       manifestations[].biblio.in all expand to inline entity objects
  - UNEXPANDABLE       missing cross-ref target is marked "<id> UNEXPANDABLE"
  - 404                unknown id returns HTTP 404
"""

import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import quote

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA = os.path.join(REPO_ROOT, "openapi", "ver", "current", "sample_data")

# Mirrors EXPAND_SPECS in openapi/docker_build/app.py — update both if cross-ref properties change.
# Each tuple: (path_segments, target_dirs)
# None in path_segments means "iterate list items at this position"
EXPAND_SPECS: dict[str, list[tuple[list, list[str]]]] = {
    "products": [
        (["topics", None, "term"],                               ["topics"]),
        (["contributions", None, "by"],                          ["persons", "organisations"]),
        (["contributions", None, "declared_affiliations", None], ["organisations"]),
        (["manifestations", None, "biblio", "in"],               ["venues"]),
        (["manifestations", None, "biblio", "hosting_data_source"], ["datasources"]),
        (["relevant_organisations", None],                       ["organisations"]),
        (["funding", None],                                      ["grants"]),
    ],
    "persons": [
        (["affiliations", None, "affiliation"],                  ["organisations"]),
    ],
    "grants": [
        (["beneficiaries", None],                                ["organisations"]),
        (["contributions", None, "by"],                          ["persons", "organisations"]),
        (["contributions", None, "declared_affiliations", None], ["organisations"]),
        (["funding_agency"],                                     ["organisations"]),
    ],
}

# Cross-references intentionally left unresolvable (for negative-case testing)
KNOWN_UNEXPANDABLE = {
    "org_does_not_exist",
}


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------

def file_exists(identifier: str, type_dirs: list[str]) -> bool:
    short = identifier.rstrip("/").split("/")[-1]
    candidates = [short, short + ".json"]
    if not identifier.startswith("http"):
        candidates = [identifier, identifier + ".json"] + candidates
    for type_dir in type_dirs:
        for candidate in candidates:
            if os.path.isfile(os.path.join(SAMPLE_DATA, type_dir, candidate)):
                return True
    return False


def collect_refs(entity, path: list, target_dirs: list[str]) -> list[tuple[str, list[str]]]:
    """Walk entity following path, collecting (identifier, target_dirs) for string leaves.
    Mirrors the traversal logic of _expand_at_path in app.py."""
    if not path:
        return []
    head, *tail = path
    results = []
    if head is None:
        if not isinstance(entity, list):
            return []
        for item in entity:
            if not tail:
                if isinstance(item, str):
                    results.append((item, target_dirs))
            else:
                results.extend(collect_refs(item, tail, target_dirs))
    else:
        if not isinstance(entity, dict):
            return []
        val = entity.get(head)
        if val is None:
            return []
        if not tail:
            if isinstance(val, str):
                results.append((val, target_dirs))
        else:
            results.extend(collect_refs(val, tail, target_dirs))
    return results


def check_file(filepath: str, type_name: str, specs) -> tuple[int, int, int]:
    """Returns (ok, known_missing, unexpected_missing) counts."""
    with open(filepath) as f:
        data = json.load(f)
    entities = data.get("@graph", [data])

    ok = known_missing = unexpected_missing = 0

    for entity in entities:
        for path, target_dirs in specs:
            for ref_id, dirs in collect_refs(entity, path, target_dirs):
                short = ref_id.rstrip("/").split("/")[-1]
                if file_exists(ref_id, dirs):
                    ok += 1
                    print(f"  [OK]      {'.'.join(str(s) for s in path if s)} -> {short}")
                elif short in KNOWN_UNEXPANDABLE:
                    known_missing += 1
                    print(f"  [SKIP]    {'.'.join(str(s) for s in path if s)} -> {short}  (intentionally missing)")
                else:
                    unexpected_missing += 1
                    print(f"  [MISSING] {'.'.join(str(s) for s in path if s)} -> {ref_id}  (targets: {dirs})")
    return ok, known_missing, unexpected_missing


def run_static_checks() -> bool:
    total_ok = total_known = total_missing = 0

    for type_name, specs in EXPAND_SPECS.items():
        type_dir = os.path.join(SAMPLE_DATA, type_name)
        if not os.path.isdir(type_dir):
            print(f"\n[WARN] directory not found: {type_name}/")
            continue
        files = sorted(f for f in os.listdir(type_dir) if f.endswith(".json"))
        if not files:
            print(f"\n[WARN] no JSON files in {type_name}/")
            continue
        for fname in files:
            print(f"\n{type_name}/{fname}")
            ok, known, missing = check_file(os.path.join(type_dir, fname), type_name, specs)
            if ok == 0 and known == 0 and missing == 0:
                print("  (no cross-references)")
            total_ok += ok
            total_known += known
            total_missing += missing

    print(f"\n{'='*50}")
    print(f"Cross-references resolved : {total_ok}")
    print(f"Intentionally missing     : {total_known}")
    print(f"Unexpected missing        : {total_missing}")

    if total_missing:
        print("\nFAIL — unexpected missing cross-references found")
        return False
    print("\nOK")
    return True


# ---------------------------------------------------------------------------
# Live HTTP checks
# ---------------------------------------------------------------------------

def get(url: str) -> tuple[int, dict | None]:
    """Returns (status_code, parsed_json_or_None)."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None
    except Exception as e:
        print(f"  [ERROR] request failed: {e}")
        return 0, None


def assert_test(description: str, url: str, expected_status: int, check_fn=None) -> bool:
    status, body = get(url)
    if status != expected_status:
        print(f"  [FAIL] {description}")
        print(f"         expected HTTP {expected_status}, got {status}  ({url})")
        return False
    if check_fn and not check_fn(body):
        print(f"  [FAIL] {description}")
        print(f"         assertion failed on response body  ({url})")
        return False
    print(f"  [OK]   {description}")
    return True


def run_live_checks(base: str, fastapi: str) -> bool:
    print(f"\nLive checks against {base}  (FastAPI direct: {fastapi})")
    print("=" * 50)

    passed = failed = 0

    def t(desc, url, status, fn=None):
        nonlocal passed, failed
        if assert_test(desc, url, status, fn):
            passed += 1
        else:
            failed += 1

    graph   = lambda r: isinstance(r, dict) and "@graph" in r
    nonempty = lambda r: isinstance(r.get("@graph"), list) and len(r["@graph"]) > 0

    # --- List endpoints: all entity types return a non-empty @graph ---
    print("\nList endpoints")
    for entity_type in ["products", "persons", "organisations", "venues", "datasources", "topics", "grants"]:
        t(f"GET /{entity_type}", f"{base}/{entity_type}", 200, nonempty)

    # --- Pagination ---
    print("\nPagination")
    t("page_size=1 returns exactly 1 item",
      f"{base}/products?page=1&page_size=1", 200,
      lambda r: r.get("meta", {}).get("items_count") == 1)
    t("page=2 returns next page meta",
      f"{base}/products?page=2&page_size=1", 200,
      lambda r: r.get("meta", {}).get("page") == 2)

    # --- Detail: plain id ---
    print("\nDetail endpoint — plain id")
    t("GET /products/product_expand_test",
      f"{base}/products/product_expand_test", 200,
      lambda r: r.get("@graph", [{}])[0].get("entity_type") == "product")
    t("GET /persons/pers_josiah_carberry",
      f"{base}/persons/pers_josiah_carberry", 200,
      lambda r: r.get("@graph", [{}])[0].get("entity_type") == "person")
    t("GET /organisations/org_brown_university",
      f"{base}/organisations/org_brown_university", 200,
      lambda r: r.get("@graph", [{}])[0].get("entity_type") == "organisation")
    t("GET /grants/grant_1",
      f"{base}/grants/grant_1", 200,
      lambda r: r.get("@graph", [{}])[0].get("entity_type") == "grant")

    # --- Detail: full URL (percent-encoded) — Prism may reject; use FastAPI directly ---
    print(f"\nDetail endpoint — full URL (via FastAPI {fastapi})")
    full_url = "https://w3id.org/skg-if/sandbox/skg-if-api/product_expand_test"
    encoded  = quote(full_url, safe="")
    t("GET /products/<full-url-encoded>",
      f"{fastapi}/products/{encoded}", 200,
      lambda r: r.get("@graph", [{}])[0].get("entity_type") == "product")

    # --- embedding=false (default): cross-refs remain as strings — list and detail ---
    print("\nembedding=false (default)")
    t("list: relevant_organisations are strings without expand",
      f"{base}/products/product_expand_test", 200,
      lambda r: isinstance(r["@graph"][0].get("relevant_organisations", [None])[0], str))
    t("detail: relevant_organisations are strings without expand",
      f"{base}/products/product_expand_test", 200,
      lambda r: isinstance(r["@graph"][0].get("relevant_organisations", [None])[0], str))

    # --- embedding=true: cross-refs expanded to objects — list and detail ---
    print("\nembedding=true")
    t("detail: relevant_organisations[0] is expanded to object",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: isinstance(r["@graph"][0].get("relevant_organisations", [None])[0], dict))
    t("list: relevant_organisations[0] is expanded to object",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: isinstance(r["@graph"][0].get("relevant_organisations", [None])[0], dict))
    t("topics[0].term is expanded to object",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: isinstance(r["@graph"][0].get("topics", [{}])[0].get("term"), dict))
    t("contributions[0].by is expanded to object",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: isinstance(r["@graph"][0].get("contributions", [{}])[0].get("by"), dict))
    t("manifestations[0].biblio.in is expanded to object",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: isinstance(r["@graph"][0].get("manifestations", [{}])[0].get("biblio", {}).get("in"), dict))

    # --- UNEXPANDABLE marker ---
    print("\nUNEXPANDABLE")
    t("missing cross-ref is marked UNEXPANDABLE",
      f"{base}/products/product_expand_test?embedding=true", 200,
      lambda r: any(
          isinstance(v, str) and "UNEXPANDABLE" in v
          for v in r["@graph"][0].get("relevant_organisations", [])
      ))

    # --- 404 ---
    print("\n404")
    t("unknown id returns 404", f"{base}/products/does_not_exist", 404)

    print(f"\n{'='*50}")
    print(f"Passed: {passed}  Failed: {failed}")
    if failed:
        print("\nFAIL")
        return False
    print("\nOK")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    live = "--live" in sys.argv
    base_url = next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--base-url"), "http://localhost:4010")
    fastapi_url = next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--fastapi"), "http://localhost:8000")

    print("=== Static cross-reference checks ===")
    static_ok = run_static_checks()

    if live:
        print("\n=== Live API checks ===")
        live_ok = run_live_checks(base_url, fastapi_url)
    else:
        live_ok = True
        print("\n(skip live checks — pass --live to enable)")

    sys.exit(0 if static_ok and live_ok else 1)


if __name__ == "__main__":
    main()
