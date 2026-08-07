import argparse
import json
import subprocess
import sys
import time
import os
from urllib.parse import urlencode, quote

import httpx
import yaml

PRISM_PORT = 4010
PROXY_BASE_URL = f"http://localhost:{PRISM_PORT}"
CONTAINER_NAME = "prism-live-validation"
NOT_FOUND_STATUSES = {404, 501}

DEFAULT_QUERY_PARAMS = {
    "/products": {"filter": "cf.search.title:Collections"},
    "/grants": {"filter": "cf.search.title:The"},
    "/persons": {"filter": "cf.search.name:Smith"},
    "/datasources": {"filter": "cf.search.name:The"},
    "/organisations": {"filter": "cf.search.name:The"},
}


def get_collection_paths(spec_path):
    """Return GET paths from the spec that have no {param} segment, each combined with its default query string (if any)."""
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    paths = spec.get("paths", {})
    collection_paths = sorted(p for p, ops in paths.items() if "{" not in p and "get" in ops)
    result = []
    for path in collection_paths:
        params = DEFAULT_QUERY_PARAMS.get(path)
        result.append(f"{path}?{urlencode(params)}" if params else path)
    return result


def start_prism_container(spec_path, target_url):
    docker_command = [
        "docker", "run", "-d", "--rm",
        "--name", CONTAINER_NAME,
        "--platform", "linux/amd64",
        "--init",
        "-v", f"{os.path.abspath(spec_path)}:/tmp/skg-if-api.yaml",
        "-p", f"{PRISM_PORT}:4010",
        "stoplight/prism:4",
        "proxy", "-h", "0.0.0.0", "/tmp/skg-if-api.yaml", target_url.rstrip("/"), "--errors",
    ]
    subprocess.run(docker_command, check=True)


def stop_prism_container():
    subprocess.run(["docker", "stop", CONTAINER_NAME], check=False, capture_output=True)


def wait_for_prism(retries=15, retry_interval=2):
    for attempt in range(retries):
        try:
            httpx.get(PROXY_BASE_URL, timeout=2)
            return True
        except httpx.HTTPError:
            time.sleep(retry_interval)
    return False


def check_path(path):
    """GET a collection path (already containing any query string) through the Prism proxy and classify the result."""
    url = PROXY_BASE_URL + path
    try:
        response = httpx.get(url, timeout=15)
    except httpx.HTTPError as exc:
        return "fail", f"Request error: {exc}", None

    request_desc = str(response.request.url)

    if response.status_code in NOT_FOUND_STATUSES:
        return "skip", f"{response.status_code} - endpoint not implemented on this server ({request_desc})", response

    if 200 <= response.status_code < 300:
        return "pass", f"{response.status_code} ({request_desc})", response

    return "fail", f"{response.status_code} ({request_desc}) - {response.text[:500]}", response


def extract_full_product_id(list_response_json):
    """Resolve @graph[0]'s local_identifier to a full URL using @context's inline @base, if needed."""
    base = next(
        (c["@base"] for c in list_response_json.get("@context", []) if isinstance(c, dict) and "@base" in c),
        None,
    )
    graph = list_response_json.get("@graph") or []
    if not graph:
        return None

    item = graph[0]
    local_id = item if isinstance(item, str) else item.get("local_identifier")
    if not local_id:
        return None

    if local_id.startswith("http"):
        return local_id

    if not base:
        return None

    return base.rstrip("/") + "/" + local_id.lstrip("/")


def list_endpoints(spec_path):
    """Print the collection endpoints as a JSON matrix for a GitHub Actions dynamic matrix."""
    collection_paths = get_collection_paths(spec_path)
    if not collection_paths:
        print(f"No collection GET paths found in {spec_path}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps([{"path": path} for path in collection_paths]))


def check(spec_path, target_url, path):
    """Validate a single endpoint through its own Prism proxy instance."""
    print(f"Validating {target_url}{path} against {spec_path}")

    start_prism_container(spec_path, target_url)
    try:
        if not wait_for_prism():
            print("Prism proxy did not become ready in time.")
            sys.exit(1)

        status, detail, _ = check_path(path)
    finally:
        stop_prism_container()

    icon = {"pass": "✅", "skip": "⏭️", "fail": "❌"}[status]
    print(f"{icon} {path}: {detail}")

    if status == "fail":
        sys.exit(1)


def check_product_by_id(spec_path, target_url):
    """Run the /products list search, then use the first result's own id to validate GET /products/{id}."""
    icons = {"pass": "✅", "skip": "⏭️", "fail": "❌"}
    list_path = f"/products?{urlencode(DEFAULT_QUERY_PARAMS['/products'])}"
    print(f"Validating product-by-id chain against {target_url} ({spec_path})")

    start_prism_container(spec_path, target_url)
    try:
        if not wait_for_prism():
            print("Prism proxy did not become ready in time.")
            sys.exit(1)

        status, detail, response = check_path(list_path)
        print(f"{icons[status]} {list_path}: {detail}")

        if status == "fail":
            sys.exit(1)
        if status == "skip":
            return

        try:
            body = response.json()
        except ValueError:
            print("⏭️ Could not parse products list response as JSON - skipping id lookup")
            return

        product_id = extract_full_product_id(body)
        if not product_id:
            print("⏭️ No product with a resolvable id found in @graph - skipping id lookup")
            return

        id_path = f"/products/{quote(product_id, safe='')}"
        status, detail, _ = check_path(id_path)
        print(f"{icons[status]} {id_path}: {detail}")

        if status == "fail":
            sys.exit(1)
    finally:
        stop_prism_container()


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-endpoints")
    list_parser.add_argument("spec_path")

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("spec_path")
    check_parser.add_argument("target_url")
    check_parser.add_argument("path")

    check_product_by_id_parser = subparsers.add_parser("check-product-by-id")
    check_product_by_id_parser.add_argument("spec_path")
    check_product_by_id_parser.add_argument("target_url")

    args = parser.parse_args()

    if args.command == "list-endpoints":
        list_endpoints(args.spec_path)
    elif args.command == "check":
        check(args.spec_path, args.target_url, args.path)
    elif args.command == "check-product-by-id":
        check_product_by_id(args.spec_path, args.target_url)


if __name__ == "__main__":
    main()
