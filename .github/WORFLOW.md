# CI workflows

Github CI worflows available.

## Workflow 1 :  Validate SKG-IF Specs and JSON Files

Target audience: SKG-IF OpenAPI specifications __developers__

`workflows/validate_specs_and_jsons.yml` runs automatically on every push/PR that touches `openapi/ver/**/skg-if-openapi.yaml` or `openapi/ver/**/*.json`. It first lints the OpenAPI YAML with [Spectral](https://github.com/stoplightio/spectral) (`spectral:oas` ruleset, via `.spectral.yaml`), then, for each changed sample JSON file, validates its content against the spec.

That second check (`.github/scripts/validate_files.py`) spins up a throwaway FastAPI container serving the changed sample file and puts a Prism proxy in front of it configured with the corresponding spec version, then confirms the file resolves through the proxy with a 2xx response — the same "Prism as validator" pattern used by the manual live-implementation workflow below, just applied to committed sample data instead of a real server.

## Workflow 2 : Validate SKG-IF Live Implementation (manual workflow)

Target audience: SKG-IF OpenAPI specifications __implementers__

`workflows/validate_live_implementation.yml` checks a live, externally-hosted SKG-IF implementation against the OpenAPI spec. It puts a [Stoplight Prism](https://github.com/stoplightio/prism) proxy in front of your server and calls its collection endpoints (`/products`, `/persons`, `/organisations`, `/grants`, `/venues`, `/topics`, `/datasources`) through the proxy. Prism validates every real response against the spec's schemas, so any contract violation shows up as an error.

The workflow has two jobs: a `discover` job reads the spec and builds the list of endpoints to check, then a `validate` job runs once per endpoint (a GitHub Actions matrix) — each endpoint gets its **own job**, named after the target server's domain and the exact path (and query params) it hit, e.g. *"Validate api-stg.opencitations.net GET /products?filter=cf.search.title%3ACollections"*.

A separate `validate_product_by_id` job goes one step further for products specifically: it runs the `/products` list search, takes the first result's own `local_identifier` (resolving it to a full URL via the response's `@base`, if it isn't one already), and calls `GET /products/{local_identifier}` — proving the id an implementation just returned is itself resolvable.

This workflow only runs when triggered manually. it never runs on push/PR.

### Running the workflow

**From the GitHub UI:**

1. If you don't have access to the [skg-if/api](https://github.com/skg-if/api) *Actions* tab. __Fork__ [skg-if/api](https://github.com/skg-if/api) to your own GitHub account/org.
2. Go to the *Actions* tab → *Validate SKG-IF Live Implementation (manual)* (in the left sidebar).
3. Click *Run workflow*.
4. Fill in:
   - `target_url` — base URL of the live implementation to validate (defaults to the OpenCitations staging endpoint).
   - `spec_version` — which `openapi/ver/<spec_version>/skg-if-openapi.yaml` to validate against (defaults to `current`).
   - `exclude_endpoints` — comma-separated endpoint paths to skip entirely, e.g. `/venues,/topics` (defaults to `/venues`, since not every implementer supports it). Excluded endpoints get no job at all, and excluding `/products` also skips the `validate_product_by_id` chain.
5. Click *Run workflow* and open the run — each endpoint appears as its own job in the job list.

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
