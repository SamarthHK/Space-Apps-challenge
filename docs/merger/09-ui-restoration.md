# UI restoration and private plot delivery plan

Reference: frontend commit `b59a73f137d19ec20726902eb7aeb2186d02b6a2`.
Comparison baseline: frontend `622db94`, backend `973ac90`.

## Updated owner decisions

Restore the original appearance without replacing API-backed storage with the
old browser demo. The owner additionally selected:

- Private per-person accounts and plot ownership, replacing shared access for
  the hosted release.
- Save KML now, explicitly show AI as unavailable, and plan the missing
  field-to-model pipeline rather than inventing predictions.
- Host the frontend on port 1080 and backend on port 8080 after verifying the
  new release. Do not replace unrelated processes occupying those ports.

These decisions supersede the account-free target in the earlier handoff.
The historical audit and shared release remain recorded, not rewritten.

## What disappeared or regressed

| Original UI / evidence at `b59a73f` | Connected baseline | Restoration / dependency |
| --- | --- | --- |
| Font loading, globe branding, section headers and five dashboard metric cards (`index.html:7-104`) | Original palette remains in CSS, but typography loading and most structural markup were removed | Restore typography, shell, cards and spacing; populate only API-backed counts/selected-boundary measurements |
| Dashboard plot registration and map quick actions (`index.html:61-157`) | No direct dashboard path into drawing | Restore direct drawing/import shortcuts and a real saved-plot list |
| Full-height satellite cockpit (`index.html:166-320`, `src/main.js:111-150`) | Small street map that becomes hidden when no boundary is selected | Restore Esri World Imagery, a street-map alternative, Earth/fit controls, and a map visible before any plot exists |
| Corner-peg drawing toolbar and guidance (`src/main.js:219-293`) | Drawing requires finding a form below the map; there is little visual guidance | Restore visible draw/finish/cancel/undo controls, point count and draggable pegs; keep unsaved geometry visibly distinct |
| Plot registration modal and descriptive fields (`index.html:689-755`) | Name, project and geometry only | Restore a styled map-adjacent editor for supported fields; plan survey/administrative/irrigation metadata separately rather than presenting unsaved inputs |
| Satellite-pass list, NDVI/NDWI selector and trend chart (`index.html:198-318`) | Removed | Restore the panel structure and explicit unavailable states; actual dated imagery/index products require source APIs |
| Weather/forecast panel (`index.html:235-275`) | Removed | Restore its place in the cockpit, but show no invented forecasts; retain real canonical observations in Land Analysis |
| Soil/water/climate analysis cards (`index.html:330-425`) | Replaced by an evidence table and a brief unavailable note | Restore styled analysis cards around the real evidence inspector; lab and water submission APIs remain missing |
| Crop ranking, seasons and financial sensitivity (`index.html:430-502`) | Unavailable message | Restore a designed readiness/result area, not the old browser recommendation rules or fabricated profit numbers |
| Mandi selectors and commodity cards (`index.html:510-555`) | Unavailable message | Restore the page layout/empty state; actual prices, units, freshness and economics remain separate source work |
| Planting-plan cards, comparison metrics and creation form (`index.html:565-600`) | Unavailable message | Restore a designed empty state; private plan CRUD and its inputs remain a later milestone |
| Farmer profile grid and sidebar identity (`index.html:608-678`) | Shared profile fields in an unstyled flex form | Restore the grid and identity area, and make the hosted profile private to the authenticated account |
| Client-only KML download (`src/main.js:1433-1490`) | Genuine backend exports exist, but drawn plots use JSON creates | Submit drawn KML to the durable import/preview/confirmation workflow; retain original bytes and offer real backend downloads |

The old "Earth map" is a Leaflet satellite basemap, not a 3D globe. Restore that
actual behavior. Do not silently claim NDVI/NDWI analysis just by tinting a parcel.
The old KML writer also invented zero altitude and handled only the first outer
ring; retain the newer multipart/hole/original-altitude guarantees.

## Implementation sequence and exit gates

### U1. Restore the presentation and drawing cockpit

Reuse the original neutral/deep-green theme and layout classes. Keep the current
race-safe API client, source evidence, version selection, conflict handling and
durable jobs. The map must render with no fields, ambiguous boundary versions,
or a backend failure. No fallback parcel or provider data is generated.

Gate: existing reads/profile/field browser flows still pass, with additional
coverage for the always-visible Earth map, direct drawing controls, satellite/
street switching, dashboard navigation and narrow-screen layout. Commit this
tested presentation increment before changing ownership.

### U2. Add private account and storage isolation

Adapt the authenticated donor's Argon2 password hashing, opaque revocable
sessions, CSRF checks and database-backed authentication limits. Add sign-up,
sign-in and sign-out without seeded credentials or localStorage tokens.

Each account receives a server-assigned workspace and canonical project.
Resolve both from the session on every request; never accept an owner/workspace
ID from browser input. Reuse the existing workspace-scoped profile, assets,
idempotency and job storage, plus project-scoped field/evidence repositories.
The worker must process each registered account with that same scope.

Keep the old shared mode as an explicit compatibility mode; the new hosted
release must enable accounts. Existing shared data and donor private records
are not copied into whichever account signs up first.

Gate: two real PostgreSQL-backed accounts cannot read or modify each other's
profiles, fields, observations, import previews, jobs or exports, including
guessed IDs and foreign project submissions. Verify password/session handling,
CSRF, expiration/revocation, rollback and persistence across app restart.

### U3. Save drawn KML through the backend

Draw/drag/review a real boundary, name it, and submit a genuine KML file with
an idempotency key. The backend stores original bytes and performs a nonmutating
preview. Show server-calculated measurements and require explicit confirmation
before the field is committed. Keep the import/job identity for reconnect.

Retain original geometry, all parts/holes and supplied altitude. Escape labels
as XML text; do not add an invented elevation. Subsequent field edits retain
version history. Existing KML/KMZ/GeoJSON imports and backend exports remain.

Gate: a private account draws a plot, submits actual KML bytes, confirms it,
reloads/signs in again, and retrieves the same persisted geometry while a second
account sees none of its private records. Lost acknowledgments must not create
duplicates. AI stays explicitly unavailable; no nonfunctional analysis job is
described as successfully queued or completed.

### U4. Publish and host the verified pair

Export/pin the implemented OpenAPI artifact, run focused API/unit/browser
regressions, and commit the backend and frontend increments. Build into an
owned deployment directory rather than replacing another server's artifact.
Start and verify API 8080, frontend 1080 and the account-aware worker before
retiring only this session's superseded services.

## Missing feature plans after this restoration

| Priority | Missing capability | Required work and proof |
| --- | --- | --- |
| P1 | Arbitrary-field AI input assembly | Define an as-of date, crop/context/management input contract, field-to-weather acquisition and coverage, unit normalization, provenance and supported-region checks; never turn coordinates into invented agronomic features |
| P1 | Model adapter and persisted analysis | Version an input/model contract; add account-scoped snapshot jobs, model-bundle verification, honest failure/unsupported states, result lineage and restart/idempotency cases |
| P1 | Plot metadata | Add versioned survey/location/irrigation/soil-context fields with explicit provenance and missingness; distinguish farmer declarations from laboratory observations |
| P2 | Soil and water submissions | Account-scoped lab reports, units/depth/date/source validation, revisions and observation linkage; no remotely inferred N/P/K |
| P2 | Satellite scene/index products | Acquire real scene metadata and imagery, cloud masks, explicit boundary/date selection, NDVI/NDWI processing and unavailable coverage; independent geometry/product readback |
| P2 | Weather and trends | Field-matched observed versus forecast data with units/time standards/freshness; render actual time series without fabricated gaps |
| P3 | Manual planting plans | Private CRUD, crop/season/boundary snapshots and version conflicts independent of AI output; no invented costs or profits |
| P3 | Markets and economics | Authorized fresh market feeds, price units/source dates, reviewed economic methods and explicit uncertainty before restoring rankings/sliders |
| P3 | Account operations | Password recovery/administration and deployment lifecycle policy; cross-host HTTPS/session configuration before public or broader deployment |

### Why the current model is not a KML analysis service

The concurrently developed backend's `contracts\outcome_model.py:330-362`
accepts a fully assembled feature record. It checks crop, categorical support
and numeric training ranges. Its report explicitly sets
`operational_recommendation_ready` to false (`outcome_model.py:297-312`).
The training context is two English research sites, not arbitrary parcels.

Required inputs include crop/cultivar/previous crop/rotation context, preplant
management and date-bounded weather features. KML supplies geometry, not those
facts. The UI must therefore say **KML saved; AI analysis unavailable**, not
pretend that a boundary upload has produced a crop recommendation.

## Delivery status

Planning and source comparison are complete. U1-U4 implementation and their
verification results will be recorded here as each tested increment is committed.
