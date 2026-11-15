# 02. Target architecture and Git consolidation

## Recommended architecture

Consolidate source in one repository while preserving independently built and
deployed frontend and backend applications. This is a recommendation for the
implementation phase, not a source move performed by this documentation branch.

```text
Space-Apps-challenge
  frontend
    package.json, package-lock.json, vite.config.js, index.html
    src
      api, adapters, state, views, map
  backend
    pyproject.toml, selected lock, config
    src
      agri_data
        api, schemas, services, repositories
        geo, sources, processing, storage, pipeline
    tests, migrations
  contracts
    openapi.json
  docs
    merger
  deploy
    compose.yaml
```

Final backend module layout must follow the baseline decision in D01. Do not
create empty directories as evidence of implementation.

```text
Browser -> static Vite artifact
Browser -> HTTPS /api/v1 -> FastAPI -> shared services -> PostgreSQL/PostGIS
                                            |
                                      durable jobs
                                            |
                                         worker
                                            |
                         source adapters + controlled asset storage

CLI ---------------------> same shared services
Leaflet -> configured external basemap (not a scientific scene)
```

No frontend imports of Python, direct SQL, local backend filesystem reads,
shared runtime source tree, or model process is required. Keep provider secrets
server-side. A same-site reverse proxy may route independently built artifacts
and API traffic, but embedding the frontend build in Python must not be required.

## Responsibility boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Browser | Forms, draw preview, rendering, locale, navigation, request state | Accepted scientific values, IDs, ownership, authoritative area, profits |
| API | Authentication, authorization, validation, DTOs, durable job submission | Provider downloads inside long synchronous requests or HTML rendering |
| Services/repositories | Domain rules, transactions, geometry revisions, accepted observations, plans | Browser camelCase compatibility objects |
| Worker | Bounded imports/acquisitions/exports, retries, leases, result metadata | Untracked background work or fabricated provider fallbacks |
| Database/assets | Durable state, lineage, private raw bytes/checksums, export manifests | Unreviewed browser demo seeds |
| Contract artifact | Wire schemas, enums, operations, version | Runtime implementation or proof of provider availability |

Retain sound parser, area, normalization and export helpers after focused fixes.
Refactor the pipeline rather than wrapping its current IO-heavy return value in
JSON. Keep CLI compatibility explicit; deprecate old behavior rather than
accidentally changing it during a directory move.

## Git strategy

The current `merger` branch starts at `main` and contains only these documents.
Do not merge entire backend/frontend branches into the same root: root README,
progress files, ignore rules and `src` would have competing meanings. Git may
auto-merge some of them without creating a correct application.

For implementation, after source owners commit approved changes:

1. Pin approved backend/frontend SHAs and the chosen rewrite status in an import
   manifest. Do not use moving branch names as the sole provenance.
2. Create disposable import branches in a fresh integration checkout. On each,
   use `git mv` to move that branch's tracked application files under its prefix
   (`backend` or `frontend`). Keep its commits as ancestors. Include dotfiles;
   inspect the exact tracked file list instead of moving arbitrary local files.
3. Commit each prefix-only relocation separately. Correct path-sensitive
   packaging/configuration in a subsequent commit so behavior changes remain
   reviewable. Do not rewrite or force-push the source branches.
4. Merge the prefixed backend import, then frontend import into the integration
   branch, preserving histories. Resolve the root README deliberately; retain
   the merger documents and place source plans under their owning prefix.
5. Reconcile root ignore/CI/deployment files explicitly. Never import local
   environments, caches, logs, raw personal reports, database files or secrets
   simply because they exist in the checkout.
6. Compare each imported tracked tree against its approved SHA plus documented
   relocation/path fixes. Record both source SHAs and merge commits.

Do not use `--allow-unrelated-histories` without inspecting ancestry; these are
branches of the same remote. Avoid bulk cherry-picks that lose the source
history/context or accidental copies of uncommitted work.

## Deployment and configuration

- Public browser setting: `VITE_API_BASE_URL` is the origin only; the transport
  appends `/api/v1` once. Define whether runtime public configuration can override
  a build-time value. Never bake a workstation address into source.
- Backend settings: explicit DB URL, allowed browser origins, session/CSRF
  settings, asset root, worker limits and source credentials. Maintain a
  non-secret example file; validate required settings at startup.
- Separate frontend build, API, worker and database services. API readiness
  checks database/schema, not every remote provider; report provider capability
  separately. Worker restart must not lose jobs.
- Reconcile Python dependencies into `pyproject.toml` plus one selected lock.
  Generate any requirements export rather than maintaining two graphs. Keep
  npm's existing lock; choose supported runtimes after compatibility checks.
- Replace fixed container names and checked-in example passwords. Use an
  isolated Compose project/volume, least-privilege application role and bounded
  loopback ports for local use. Do not start/stop shared database services during
  this planning task.
- Assets use backend-owned paths and opaque IDs in the API. Downloads and raster
  images must retain authorization; do not expose arbitrary local paths.

Git integration, independently deployable application integration, and complete
scientific coverage are separate deliverables.
