# CI workflows

## Validate Live Implementation

`workflows/validate_live_implementation.yml` checks a live, externally-hosted SKG-IF implementation against the OpenAPI spec. It puts a [Stoplight Prism](https://github.com/stoplightio/prism) proxy in front of your server and calls its collection endpoints (`/products`, `/persons`, `/organisations`, `/grants`, `/venues`, `/topics`, `/datasources`) through the proxy — Prism validates every real response against the spec's schemas, so any contract violation shows up as an error. Item endpoints (`/{local_identifier}`) are not checked yet.

This workflow only runs when triggered manually (`workflow_dispatch`) — it never runs on push or pull request.

### Running it

**From the GitHub UI:**
1. Go to the *Actions* tab → *Validate Live Implementation* (in the left sidebar).
2. Click *Run workflow*.
3. Fill in:
   - `target_url` — base URL of the live implementation to validate (defaults to the OpenCitations staging endpoint).
   - `spec_version` — which `openapi/ver/<spec_version>/skg-if-openapi.yaml` to validate against (defaults to `current`).
4. Click *Run workflow* and open the run to see the pass/skip/fail summary for each endpoint.

**From the CLI ([GitHub CLI](https://cli.github.com/)):**
```sh
gh workflow run validate_live_implementation.yml -f target_url=https://api-stg.opencitations.net/skg-if/v1/
```

### Reading the results

Each endpoint is reported as:
- ✅ **pass** — the response came back with a 2xx status and matched the spec's schema.
- ⏭️ **skip** — the server returned `404`/`501` for that endpoint, treated as "not implemented by this server" rather than a failure.
- ❌ **fail** — a genuine contract violation (Prism flagged the response, or it returned an unexpected error status). The job fails if any endpoint fails.

At least one endpoint must pass — if every endpoint comes back skipped (or failed), the job fails, since that usually means `target_url` is wrong or unreachable rather than a legitimately minimal implementation.

### Running it locally

Requires Docker and Python 3.12 with `httpx` and `pyyaml` installed — the script starts and stops its own Prism container:

```sh
pip install httpx pyyaml
python .github/scripts/validate_live_url.py openapi/ver/current/skg-if-openapi.yaml <target_url>
```
