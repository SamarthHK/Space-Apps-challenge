# Bhumi agricultural intelligence frontend

Vite, vanilla JavaScript and Leaflet. The frontend now connects to a separately
deployed Python API for **read-only source inspection**, not demo forecasts.
Read [progress.md](progress.md) for exact implemented and blocked capabilities,
and [frontendplan.md](frontendplan.md) for the remaining migration tasks.

## Start

Requires Node.js 22 or newer and npm. Restore dependencies with `npm ci`.
Copy `.env.example` to `.env.local` and set the public API origin and frontend
bind address. The API origin has no `/api/v1` suffix.

For account-free Tailscale deployment from PowerShell:

```powershell
$ip = (tailscale ip -4).Trim()
$env:VITE_API_BASE_URL = "http://${ip}:8000"
$env:FRONTEND_HOST = $ip
npm run build
npm run preview
```

Open `http://<your-tailscale-ip>:1080`. Port 1080 is strict: a collision is an
error, not a silent switch. `npm run dev` uses the same host/port configuration.
Loopback-only development uses frontend `127.0.0.1`, API
`http://localhost:8000`. Missing/invalid API configuration shows a clear error;
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
Map tiles come from OpenStreetMap; tile failure is distinct from API failure.

Crop recommendations, markets, plans, profiles, writes/imports/exports and
analytical satellite layers are still unavailable. Their navigation remains,
but old synthetic values and browser calculations no longer run.
Unused legacy data/service source files are retained for subsequent F10 cleanup;
they are not imported into the production build.

## Tests

```powershell
npm test
npm run build
$env:TEST_API_ORIGIN = $env:VITE_API_BASE_URL
npm run test:browser
```

Browser tests start the production preview on `127.0.0.1:1080`, so the actual
API must also allow that origin. They need a prepared authentic field/canonical
evidence corpus and a build made with the same API origin. If Chromium is not
installed, run `npx playwright install chromium` after the runner reports it
missing. Tests check real API/geometry/evidence agreement, pagination, empty and
failure states, racing filters, all seven views, mobile navigation and inert
untrusted text. No fabricated agricultural provider response qualifies as evidence.

## Trust and limitations

No accounts were requested. Everyone permitted to reach the workspace through
Tailscale shares access. CORS is not authentication. Do not expose it publicly
or through Tailscale Funnel; a public deployment requires authentication and
HTTPS. No cookies, tokens, DB credentials or provider secrets belong in Vite
configuration. Local host values are configured, not committed into source.

Current read pagination targets the small reference corpus. Scaling, complete
scientific validation and the full migration are not claimed by passing builds.
