# 03. Actual contracts and the shared-profile bridge

**Existing baseline:** A/F `shared-workspace-1`, hash recorded in the audit.
**Proposed additions:** the profile/write contracts below. These routes do not
currently exist in A and must not be advertised as ready by documentation alone.

## Preserve the implemented read API exactly

All listed paths have `/api/v1` prefix.

| Operation | Path | Actual response/behavior |
| --- | --- | --- |
| `getHealth` | `/health` | `{data: {status, contract_revision}, meta}`; liveness only |
| `getWorkspace` | `/workspace` | Access mode, contract revision, configured project IDs, capabilities |
| `listFields` | `/fields` | Page of FieldRecord; `limit` defaults to 50, maximum 200 |
| `getField` | `/fields/{field_id}` | Optional `boundary_id`; no current geometry guessed with multiple versions |
| `listObservations` | `/fields/{field_id}/observations` | `variable_id`, `validation_status` (all, pending, accepted, rejected), paired inclusive `start_date/end_date`, cursor/limit |
| `getObservation` | `/fields/{field_id}/observations/{canonical_observation_id}` | Canonical scientific record, validation, conflict flag, evidence count |
| `listObservationEvidence` | `/fields/{field_id}/observations/{canonical_observation_id}/evidence` | Paginated original source observations with provenance/time basis |

`GET /api/v1/openapi.json` is also served, but is not one of those seven
registered OpenAPI operations. Do not confuse B `/health`, `/ready`, `/meta`
or `/me/profile` with these paths.

Success: `{data: T, meta: {request_id, api_version: "v1"}}`.
Pages: same envelope with `data: T[]` and `meta.next_cursor`.
Errors: `{error: {code, message, details: [{path,code,message}], retryable}, meta}`.
Do not change this to the earlier merger plan's `{items,...}` or bare objects.

Capabilities currently use `capability_id`, `state: ready|blocked|not_implemented`,
`operation_ids`, `reason`. `profile` already reserves `getProfile/updateProfile`.
Keep the entry not implemented until the route exists, blocked if configured
storage is unavailable, and ready only after the required storage is usable.
Do not gate all existing reads on new profile configuration.

### Existing field/evidence semantics

- Field IDs are opaque source-based strings, not necessarily UUIDs. Keep
  `field_id`, `project_id`, `current_boundary_id`, `selected_boundary_id`,
  `boundary_versions` and `geometry_status`.
- Current geometry/metrics can legitimately be null. Geometry is stored
  GeoJSON; metric CRS, area and perimeter come from the backend. Selecting a
  boundary is a read choice, not an update of a persisted current pointer.
- Current observation requests are field-scoped, not filtered by the selected
  boundary. Keep their recorded geometry/spatial support visible; changing the
  map boundary must not imply observations were recomputed for that version.
- Observations are canonical records, not individual download receipts. Several
  source evidence records may support one canonical observation; conflicting
  scientific revisions stay distinct.
- `pending/accepted/rejected` must not become B's proposed validation vocabulary
  or a browser Boolean `hasSoilTest`.
- Provider-local times retain their `timezone`/time-standard context. Do not
  apply `Date(...).toISOString()` and invent UTC. Dates used for filters remain
  civil dates; interval-only filtering needs a separately specified extension.
- Canonical normalization can differ from the raw source representation. Keep
  original units/basis and exact lineage visible; do not blindly assert equality
  between normalized values and provider raw values.
- Transport state, capability state, validation and geometry availability are
  different axes. A ready API with only pending data is a valid inspection state.
- Missing source values are not Observation objects with null in every value
  column. Gap/feature-status persistence is later work; an empty filtered page
  does not establish complete source coverage.

## Proposed profile contract

Use `GET /api/v1/profile` (`getProfile`) and
`PATCH /api/v1/profile` (`updateProfile`), following A's existing proposed
operation registry. No `/auth/*`, `/me/profile`, cookies or CSRF session flow.

| Element | Proposed rule |
| --- | --- |
| Ownership | Server-configured shared workspace; no caller-supplied owner, project reassignment or hidden user |
| Response | `ProfileResponse = {data: SharedProfile, meta}` plus strong `ETag` |
| Resource | Server-owned `workspace_id`, `version >= 1`, audit timestamps and the nullable fields below; retain A's proposed workspace key rather than B's user/profile ID contract |
| GET | 200 for provisioned profile, stable ETag; no seed/create side effect. Missing setup is 503 with actionable capability reason |
| PATCH body | At least one permitted property; omitted means unchanged, explicit null clears nullable field; reject server-owned/unknown fields |
| PATCH precondition | Required `If-Match` from last successful profile read/write. 428 when absent; 412 for a stale/nonmatching version; define malformed header validation explicitly |
| Transaction | Atomic compare-and-update plus revision snapshot; one commit increments version once. No last-writer-wins fallback |
| PATCH success | 200 with new ProfileResponse and ETag |
| Invalid data | 422 in the shared error envelope with field details; limits/enums retain donor validation unless explicitly revised |
| Ambiguous network result | Preserve form edits; reload current server state before deliberate retry. No automatic PATCH retries |

Retain donor fields and limits: name/localized name/location strings (up to 200),
phone (32, existing syntax validation), soil-card reference (100), category
`small_marginal|medium|large`, language `en|kn`, risk
`conservative|balanced|progressive`, objective
`profit_maximization|low_water_risk|household_security`. All may be null.
These preferences are stored, not claims that recommendation methods use them.
The soil-card reference is not scientific verification.

Separate the response model from the patch model: B currently inherits Profile
from a patch requiring body `version`. In the shared contract, concurrency is
from `If-Match`; do not accept a second conflicting body version/ownership field.
An ETag format such as `"profile:<workspace-id>:<version>"` is a proposal to freeze in the
schema/tests, not a string clients should calculate themselves.

## Frontend adaptation, not replacement

Extend F's transport while preserving the existing `api.get()` response shape
and all current call sites. Add a response-aware path for profile GET/PATCH that
returns validated body plus ETag/header metadata. Do not inject hidden headers
into JSON or use P's incompatible callable client/ApiError constructor.

The profile adapter stores the last ETag and builds writable fields only.
On 412, preserve the user's edits and offer an explicit reload/compare; do not
blindly reapply them. Show server field errors from `error.details` and retain
request ID. After saving, update resource state/version without rerendering or
clearing the field/map/evidence state.

Extract P field definitions and safe DOM form rendering into a profile component
inside F's existing seven-view shell. Label it a **shared workspace profile**;
do not show a login page, "my private profile", or misleading user attribution.
Disabled/unimplemented profile state is replaced only when its capability is
ready. Other deferred screens remain unchanged.

## CORS and mutation rules

Keep `credentials: "omit"` and explicit trusted-network hosts/origins.
For profile integration, permit GET/PATCH/OPTIONS as appropriate and
`Content-Type`, `If-Match`, `X-Request-ID`; expose `ETag` and request ID.
Check Host and Origin, including Origin on state-changing browser requests;
do not rely on CORS alone as authorization. Preserve no-store responses and
sanitized errors, including preflight/412/428/503 paths.

POST/idempotency, multipart uploads, `Location`, `Content-Disposition` and Blob
downloads are introduced only with actual import/export/create operations.
Existing client code always parses JSON; it cannot yet consume 204 or binary
responses. Add those cases before exposing operations that use them.

All allowed clients share access; this mode is not suitable for public exposure.
Restrict canonical project scope on every nested read and later mutation.

## Versioning and compatibility gate

Both current validators forbid extra properties in their strict DTOs. An
"additive" field on an existing response can therefore break the deployed
frontend. Merely matching OpenAPI `info.version=1.0.0` is insufficient.

For the first profile increment, add new operation/schema definitions without
changing existing read responses. Updating the existing profile capability to
ready fits its current schema. Keep the deployed `shared-workspace-1` literal
compatible while those reads remain unchanged, and record the new artifact
hash/source commit. If a revision literal or old response shape must change,
ship an explicitly compatible client first or version the API; do not silently
invalidate bootstrap.

Backend exports its actual schemas, frontend pins identical bytes and consumes
the new ProfileResponse. CI checks both artifact provenance and representative
real responses. The same rule applies to error envelopes and provider-time
formats, not just endpoint names.

## Later operations: retain shared naming

Future jobs/imports/exports/soil/crops/plans follow A's operation registry:
`/boundary-imports`, `/jobs/{job_id}`, `/fields/{field_id}/exports`,
`/exports/{export_id}/download`, `/fields/{field_id}/soil-records`, `/crops`,
`/planting-plans`. Do not reintroduce the earlier `/plans` or global `/exports`
create paths from the superseded plan.

These remain proposals until implemented. Do not list routes as operational
because a CLI helper or capability ID exists. Model/recommendation/economic
contracts are not expanded in this integration.
