# CI workflows

## Validate SKG-IF Specs and JSON Files

`workflows/validate_specs_and_jsons.yml` runs automatically on every push/PR that touches `openapi/ver/**/skg-if-openapi.yaml` or `openapi/ver/**/*.json`. It first lints the OpenAPI YAML with [Spectral](https://github.com/stoplightio/spectral) (`spectral:oas` ruleset, via `.spectral.yaml`), then, for each changed sample JSON file, validates its content against the spec.

That second check (`.github/scripts/validate_files.py`) spins up a throwaway FastAPI container serving the changed sample file and puts a Prism proxy in front of it configured with the corresponding spec version, then confirms the file resolves through the proxy with a 2xx response — the same "Prism as validator" pattern used by the manual live-implementation workflow below, just applied to committed sample data instead of a real server.

## Validate SKG-IF Live Implementation (manual workflow)

`workflows/validate_live_implementation.yml` checks a live, externally-hosted SKG-IF implementation against the OpenAPI spec. It puts a [Stoplight Prism](https://github.com/stoplightio/prism) proxy in front of your server and calls its collection endpoints (`/products`, `/persons`, `/organisations`, `/grants`, `/venues`, `/topics`, `/datasources`) through the proxy — Prism validates every real response against the spec's schemas, so any contract violation shows up as an error. Item endpoints (`/{local_identifier}`) are not checked yet.

It runs as two jobs: a `discover` job reads the spec and builds the list of endpoints to check, then a `validate` job runs once per endpoint (a GitHub Actions matrix) — each endpoint gets its **own job**, named after the target server's domain and the exact path (and query params) it hit, e.g. *"Validate api-stg.opencitations.net GET /products?filter=cf.search.title%3ACollections"*. That way a failing endpoint is immediately visible in the Actions run's job list, without digging through a combined log, and the domain in the name also makes it clear which server was tested when looking at run history or notifications. Each endpoint job starts its own short-lived Prism proxy container, so all endpoints are checked in parallel and one failing endpoint doesn't stop the others (`fail-fast: false`).

A separate `validate_product_by_id` job goes one step further for products specifically: it runs the `/products` list search, takes the first result's own `local_identifier` (resolving it to a full URL via the response's `@base`, if it isn't one already), and calls `GET /products/{local_identifier}` — proving the id an implementation just returned is itself resolvable, not just that each endpoint is independently schema-valid. It reports **skip** (not failure) if the list search has no results or no id it can resolve.

This workflow only runs when triggered manually (`workflow_dispatch`) — it never runs on push or pull request.

### If you're an implementer validating your own server

You need to run this from **your own fork**, not this repo directly (you won't have push/run access here). A few things to get right:

1. Fork [skg-if/api](https://github.com/skg-if/api) to your own GitHub account/org.
2. GitHub Actions are **disabled by default on forks** — go to your fork's *Settings → Actions → General* and enable them (or accept the banner prompt on the *Actions* tab).
3. `workflow_dispatch` workflows only become dispatchable once the workflow file exists on your fork's **default branch** (e.g. `main`) — GitHub uses the default branch to decide which workflows are runnable at all. If you only have this file on a feature branch, temporarily switch your fork's default branch to that feature branch (*Settings → General → Default branch*) so the workflow becomes dispatchable, run it, then switch the default branch back once you're done.
4. Trigger it (Actions tab → *Validate SKG-IF Live Implementation (manual)* → *Run workflow*, or `gh workflow run ... --repo <your-username>/api`) with your own `target_url`.

No repo secrets are needed — `target_url` is just a public endpoint you supply, so there's nothing else to configure.

### Running it

**From the GitHub UI:**
1. Go to the *Actions* tab → *Validate SKG-IF Live Implementation (manual)* (in the left sidebar).
2. Click *Run workflow*.
3. Fill in:
   - `target_url` — base URL of the live implementation to validate (defaults to the OpenCitations staging endpoint).
   - `spec_version` — which `openapi/ver/<spec_version>/skg-if-openapi.yaml` to validate against (defaults to `current`).
   - `exclude_endpoints` — comma-separated endpoint paths to skip entirely, e.g. `/venues,/topics` (defaults to `/venues`, since not every implementer supports it). Excluded endpoints get no job at all, and excluding `/products` also skips the `validate_product_by_id` chain.
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
python .github/scripts/validate_live_url.py list-endpoints openapi/ver/current/skg-if-openapi.yaml --exclude /venues

# check a single endpoint against a live implementation
python .github/scripts/validate_live_url.py check openapi/ver/current/skg-if-openapi.yaml <target_url> /products

# run the /products list -> get-by-id chained check
python .github/scripts/validate_live_url.py check-product-by-id openapi/ver/current/skg-if-openapi.yaml <target_url> --exclude /venues
```
