# CI workflows

## Validate Live Implementation

`workflows/validate_live_implementation.yml` checks a live, externally-hosted SKG-IF implementation against the OpenAPI spec. It puts a [Stoplight Prism](https://github.com/stoplightio/prism) proxy in front of your server and calls its collection endpoints (`/products`, `/persons`, `/organisations`, `/grants`, `/venues`, `/topics`, `/datasources`) through the proxy — Prism validates every real response against the spec's schemas, so any contract violation shows up as an error. Item endpoints (`/{local_identifier}`) are not checked yet.

It runs as two jobs: a `discover` job reads the spec and builds the list of endpoints to check, then a `validate` job runs once per endpoint (a GitHub Actions matrix) — each endpoint gets its **own job**, named after the exact path (and query params) it hit, e.g. *"Validate GET /products?filter=cf.search.title%3ACollections"*. That way a failing endpoint is immediately visible in the Actions run's job list, without digging through a combined log. Each endpoint job starts its own short-lived Prism proxy container, so all endpoints are checked in parallel and one failing endpoint doesn't stop the others (`fail-fast: false`).

This workflow only runs when triggered manually (`workflow_dispatch`) — it never runs on push or pull request.

### Running it

**From the GitHub UI:**
1. Go to the *Actions* tab → *Validate Live Implementation* (in the left sidebar).
2. Click *Run workflow*.
3. Fill in:
   - `target_url` — base URL of the live implementation to validate (defaults to the OpenCitations staging endpoint).
   - `spec_version` — which `openapi/ver/<spec_version>/skg-if-openapi.yaml` to validate against (defaults to `current`).
4. Click *Run workflow* and open the run — each endpoint appears as its own job in the job list.

**From the CLI ([GitHub CLI](https://cli.github.com/)):**
```sh
gh workflow run validate_live_implementation.yml -f target_url=https://api-stg.opencitations.net/skg-if/v1/
```

### Reading the results

Each endpoint's job is reported as:
- ✅ **pass** — the response came back with a 2xx status and matched the spec's schema.
- ⏭️ **skip** — the server returned `404`/`501` for that endpoint, treated as "not implemented by this server" rather than a failure.
- ❌ **fail** — a genuine contract violation (Prism flagged the response, or it returned an unexpected error status).

If `target_url` is wrong or unreachable, every endpoint job will simply show as skipped — that's visible at a glance in the job list.

### Running it locally

Requires Docker and Python 3.12 with `httpx` and `pyyaml` installed — the script starts and stops its own Prism container per endpoint:

```sh
pip install httpx pyyaml

# list the endpoints the spec declares (used by the workflow's discover job)
python .github/scripts/validate_live_url.py list-endpoints openapi/ver/current/skg-if-openapi.yaml

# check a single endpoint against a live implementation
python .github/scripts/validate_live_url.py check openapi/ver/current/skg-if-openapi.yaml <target_url> /products
```
