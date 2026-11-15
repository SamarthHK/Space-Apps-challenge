# 05. Acceptance and release checklist

This document specifies future checks. No API, worker, provider, database or
browser integration test was executed during the documentation audit.

## Gate matrix

| Gate | Exercise | Required result |
| --- | --- | --- |
| G01 Reproducibility | Clean prefixed checkout; Python package/config discovery; independent frontend install/build | Reconciled locked dependencies; backend not required to build frontend; no workstation paths |
| G02 Contract/transport | OpenAPI compatibility; 200/201/202/204, errors, invalid JSON, timeout, abort, conflict, rate limit | One versioned schema, stable error envelope; no unsafe blind write retries |
| G03 Sessions/ownership | Two provisioned accounts, expiry/logout, CSRF, direct private field/job/asset/download URLs | No cross-account read/write; correct auth handling under actual frontend/API origins |
| G04 Empty bootstrap | Fresh user, zero fields/plans, previously cleared local arrays, backend offline | No crash, seed recreation, random first-field selection or sample-value flash before response |
| G05 Geometry | Authentic approved polygons with holes/multiple components; GeoJSON and KML/KMZ import/export | Same rings/components and geometry revision survive DB/browser/download; documented area tolerance |
| G06 Preview/idempotency | Parse, decline repair, accept selected candidates, repeat request, stale preview, worker/API restart | Preview alone creates no fields; exact replay returns same result; no partial/duplicate confirmation |
| G07 Measurement semantics | Inspected lab/SoilGrids records with units, basis, depth, dates and original bytes | Display -> API -> observation -> source reconciliation; total N not available N; modelled not lab-verified |
| G08 Missing/zero/quality | Authentic zero/censored/missing/rejected inputs; missing provider credentials | Distinct availability and validation; no fallback measurements or zero-as-missing substitution |
| G09 Context/races | Switch fields/scenes/periods while earlier requests finish | Responses cannot update another context; scene controls actual overlay; old field data not relabelled |
| G10 Series/forecast | Authentic negative NDVI and gaps, empty/single-point state; explicit forecast validity | No clipping/interpolation across gaps; separate rainfall time basis; history never masquerades as forecast |
| G11 Manual plans | Create/update/archive without recommendation; reload in another browser; stale version; excess area | Durable owned plan, real crop reference, ISO dates, 409 on lost update; unavailable finance is not zero |
| G12 Summaries/markets | Multiple pages and filters; dated observations, policy price, absent trend/costs | Complete filtered summaries; correct currency/quantity; no first-record recency assumption or invented deductions |
| G13 Persistence/jobs | Independent DB read after process restart; worker lease expiry/retry and export snapshot | Committed records survive; recoverable jobs; immutable versioned outputs and authorized download |
| G14 Production cleanup | Inspect source, built bundle and initial HTML; render API/user text | No legacy scientific seeds/local domain storage/reset/financial rules; safe rendering and honest unavailable panels |
| G15 Independent deployment | Static frontend on configured origin, API/worker/DB separately started; tile host/API outages | No shared filesystem assumption; CORS/auth/downloads work; basemap failure distinct from evidence failure |
| G16 Recovery | Restore integration-owned backup and prior compatible artifact in isolation | Documented recovery without deleting source work, shared volumes or new user data |

G05 must include the specific parser regression: a MultiGeometry containing
multiple Polygon children must not return the first child early, and holes must
survive in each component. Do not accept a simple rectangle area test as coverage.

G07/G08 positive scientific acceptance uses authentic records with inspected
provenance, consistent with the existing backend contract. Missing authentic
cases remain blocked; do not fabricate provider records to claim acceptance.
Pure transport/schema checks and intentionally invalid requests are separate
from evidence that scientific acquisition works.

## Commands and test placement

Existing commands, after entering the respective source checkout:

```powershell
# Frontend: existing package-lock.json and build script.
npm ci
npm run build

# Backend: existing pytest configuration provides src on the Python path.
python -m pytest tests\test_geo_and_processing.py tests\test_acquisition_modes.py
```

These illustrate existing interfaces, not commands executed for this
documentation-only change. Run installs only when establishing the chosen
validation environment or dependencies are missing. Existing backend tests
include synthetic/demo cases and prove legacy behavior only; they do not satisfy
authentic PostGIS/provider/API acceptance.

There is currently no frontend test or lint script and no backend API entrypoint.
Do not claim `npm test`, `uvicorn agri_data.api:app`, or the planned
`python -m agri_data validate` suites already work. Their exact interfaces must
be implemented, documented, and exercised in the owning phase.

Proposed additions: focused frontend client/adapter/state tests in P2, geometry
and import service/API tests in P3, record semantics tests in P4, plan tests in
P5, and browser journeys for the release. Use existing pytest; select minimal
frontend unit/browser tooling when introduced. Keep legacy tests distinct from
new real-DB/API acceptance.

Record exact command, source SHA, contract checksum, environment, outcome,
artifact references and blocker for each gate. Test status is
`not_run/pass/fail/blocked`; no check is passed merely because its file exists.
Do not commit raw personal farm reports, contact records or credentials as test
evidence. Store controlled evidence privately and commit non-sensitive manifests.

## Release definition

The non-AI integration is releasable only when:

- Approved source trees are consolidated with preserved history and independent
  frontend/backend builds.
- Authentication/profile, field/import/export, accepted first evidence slice and
  manual plans persist through real API/PostGIS readback and process restarts.
- All seven existing screen families remain navigable. Recommendation/scenario
  surfaces are explicitly deferred; source-blocked forecast/satellite/market
  panels are clearly unavailable under approved scope, not deceptively populated.
- No production screen, initial HTML or fallback supplies fabricated data.
- Relevant G01-G16 gates pass, with explicit approval for source-dependent panels
  remaining unavailable. Mandatory persistence/ownership/geometry gates cannot
  be waived by calling those core features unavailable.

Report integration readiness separately from complete scientific coverage.
Authentic source integration still blocked after release remains on the backlog;
AI/model readiness is not evaluated in this milestone.
