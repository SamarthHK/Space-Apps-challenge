# Bhumi agricultural intelligence frontend

Vite, vanilla JavaScript and Leaflet. The frontend now connects to a separately
deployed Python API for **private accounts, saved profile/field workflows and read-only source evidence**, not demo forecasts.
Read [progress.md](progress.md) for exact implemented and blocked capabilities,
and [frontendplan.md](frontendplan.md) for the remaining migration tasks.

## Start

Requires Node.js 22 or newer and npm. Restore dependencies with `npm ci`.
Copy `.env.example` to `.env.local` and set the public API origin and frontend
bind address. The API origin has no `/api/v1` suffix.

For the private Tailscale deployment from PowerShell:

```powershell
$ip = (tailscale ip -4).Trim()
$env:VITE_API_BASE_URL = "http://${ip}:8080"
$env:FRONTEND_HOST = $ip
npm run build
npm run preview
```

Open `http://<your-tailscale-ip>:1080`. Port 1080 is strict: a collision is an
error, not a silent switch. `npm run dev` uses the same host/port configuration.
Loopback-only development uses frontend `127.0.0.1`, API
`http://127.0.0.1:8080`. Use the same hostname for frontend/API cookie sessions.
Missing/invalid API configuration shows a clear error;
the application never falls back to bundled agricultural data.

The backend must allow the exact frontend origin and explicitly configure
project scope and its real PostgreSQL/PostGIS connection. See branch `backend`,
`docs/api-running.md`. This checkout neither imports Python nor needs a shared
filesystem. The generated API contract is pinned in `contracts/openapi.json`;
`contracts/source.json` records its backend commit and checksum.

## What is connected

Dashboard capability/field status, My Land stored boundary selection/map and
Land Analysis canonical observation/evidence inspection use the API.
Pending records retain source/units/time standards and are not called verified.
Missing/ambiguous geometry stays unavailable until a recorded version is selected.
The original satellite cockpit from `b59a73f` is restored: Esri World Imagery,
an optional OpenStreetMap basemap, Earth/center controls and a full-height map
that stays available before a boundary is selected. Tile loading/failure is
distinct from API failure. Neither basemap is presented as NDVI or AI analysis.

Account mode provides sign-up, sign-in and sign-out in the restored theme.
Profiles and plots belong to the authenticated account; no shared/donor records
are copied into the first signup. Cookie credentials and in-memory CSRF/owner
context are enabled only after account-mode discovery. Session revocation,
account switching and sign-out clear private browser state, including other tabs.
The backend's explicit shared compatibility mode still shows a shared-profile
warning and uses no authentication cookies. Conditional
saves preserve drafts on conflicts or failed requests. My Land supports field
create/edit/archive, map drawing, KML/KMZ/GeoJSON upload, nonmutating preview,
explicit confirmation, durable job monitoring and real geometry downloads.
Dashboard and map-toolbar shortcuts open drawing directly, with draggable
corner pegs, point counts and undo/finish/cancel controls. The original dashboard
cards, typography, profile grid and responsive cockpit surround actual API data.
Complex geometry can be edited as GeoJSON without dropping holes or polygon
parts. Drawing a replacement polygon is explicit; no fallback parcel is generated.
These actions never mark source data scientifically verified.

The backend must provision its separate workspace schema and run its import/
export worker; see `docs/private_workspace.md` in the backend. Controls follow
actual capability/worker readiness. Job IDs are saved in the page URL so
monitoring and downloads can resume after reload. No profile or agricultural
state is written to localStorage or sessionStorage. Lost field/job POST responses
reuse the same submission key only after an explicit retry; PATCH conflicts
require a deliberate reload. Authentication is not blindly replayed: an uncertain
signup offers explicit sign-in recovery.

Crop recommendations, markets, plans and
analytical satellite layers are still unavailable. Their navigation remains,
but old synthetic values and browser calculations no longer run.
Unused legacy data/service source files are retained for subsequent F10 cleanup;
they are not imported into the production build.

## Tests

```powershell
npm test
npm run build
$env:TEST_API_ORIGIN = $env:VITE_API_BASE_URL
npm run test:browser -- workspace.spec.js
```

The read-only browser cases start the production preview on `127.0.0.1:1080`, so the actual
API must also allow that origin. They need a prepared authentic field/canonical
evidence corpus and a build made with the same API origin. If Chromium is not
installed, run `npx playwright install chromium` after the runner reports it
missing. Tests check real API/geometry/evidence agreement, pagination, empty and
failure states, racing filters, all seven views, mobile navigation and inert
untrusted text. No fabricated agricultural provider response qualifies as evidence.

For the complete write suite, run the backend's
`python scripts\workspace_browser_acceptance.py --frontend <this-checkout> --mode both` with
its `AGRI_TEST_*` settings and Playwright Chromium installed. It copies scoped
authentic data into an owned test schema, provisions isolated application storage,
builds once, and starts its own API/worker/static preview for both access modes.
It also checks two-account privacy, session revocation, account-switch guards
and cross-tab state clearing. It sets the required
`TEST_WRITES_ISOLATED=1` guard. It refuses occupied ports, retains logs, and never
replaces your normal build or modifies the original canonical data.

To update the contract after a tested backend commit:
`node scripts\pin-contract.js <backend-checkout>`. This developer-only command
records the source commit and exact artifact checksum; deployments remain independent.

## Trust and limitations

Private deployment requires `AGRI_AUTH_MODE=accounts` on the backend and worker.
Do not turn on shared compatibility to recover a private deployment.
CORS is not authentication. Do not expose publicly or through Tailscale Funnel;
broader deployment needs HTTPS, account recovery/administration and operational
hardening. Cookies do not isolate ports; all services on the hostname must be
trusted. No cookies, tokens, DB credentials or provider secrets belong in Vite
configuration. Local host values are configured, not committed into source.

Current read pagination targets the small reference corpus. Scaling, complete
scientific validation and the full migration are not claimed by passing builds.
