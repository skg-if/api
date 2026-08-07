import subprocess
import sys
import time
import os

import httpx
import yaml

PRISM_PORT = 4010
PROXY_BASE_URL = f"http://localhost:{PRISM_PORT}"
CONTAINER_NAME = "prism-live-validation"
NOT_FOUND_STATUSES = {404, 501}


def get_collection_paths(spec_path):
    """Return GET paths from the spec that have no {param} segment."""
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    paths = spec.get("paths", {})
    return sorted(p for p, ops in paths.items() if "{" not in p and "get" in ops)


def start_prism_container(spec_path, target_url):
    docker_command = [
        "docker", "run", "-d", "--rm",
        "--name", CONTAINER_NAME,
        "--platform", "linux/amd64",
        "--init",
        "-v", f"{os.path.abspath(spec_path)}:/tmp/skg-if-api.yaml",
        "-p", f"{PRISM_PORT}:4010",
        "stoplight/prism:4",
        "proxy", "-h", "0.0.0.0", "/tmp/skg-if-api.yaml", target_url, "--errors",
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
    """GET a collection path through the Prism proxy and classify the result."""
    url = PROXY_BASE_URL + path
    try:
        response = httpx.get(url, timeout=15)
    except httpx.HTTPError as exc:
        return "fail", f"Request error: {exc}"

    if response.status_code in NOT_FOUND_STATUSES:
        return "skip", f"{response.status_code} - endpoint not implemented on this server"

    if 200 <= response.status_code < 300:
        return "pass", f"{response.status_code}"

    return "fail", f"{response.status_code} - {response.text[:500]}"


def main():
    if len(sys.argv) != 3:
        print("Usage: validate_live_url.py <spec_path> <target_url>")
        sys.exit(1)

    spec_path, target_url = sys.argv[1], sys.argv[2]

    collection_paths = get_collection_paths(spec_path)
    if not collection_paths:
        print(f"No collection GET paths found in {spec_path}")
        sys.exit(1)

    print(f"Validating {target_url} against {spec_path}")
    print(f"Collection endpoints to check: {collection_paths}")

    start_prism_container(spec_path, target_url)
    try:
        if not wait_for_prism():
            print("Prism proxy did not become ready in time.")
            sys.exit(1)

        results = {}
        for path in collection_paths:
            status, detail = check_path(path)
            results[path] = (status, detail)
            icon = {"pass": "✅", "skip": "⏭️", "fail": "❌"}[status]
            print(f"{icon} {path}: {detail}")
    finally:
        stop_prism_container()

    passed = [p for p, (status, _) in results.items() if status == "pass"]
    skipped = [p for p, (status, _) in results.items() if status == "skip"]
    failed = [p for p, (status, _) in results.items() if status == "fail"]

    print(f"\nSummary: {len(passed)} passed, {len(skipped)} skipped, {len(failed)} failed")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
