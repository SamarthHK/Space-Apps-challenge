# AgriData

The backend is being rewritten against **Plan.md**, the implementation and
acceptance authority. **The rewrite is incomplete and S01 is blocked.**
No connection, database, feature or end-to-end acceptance gate has passed for
this contract.

## Current implementation

`src/agri_data/contracts` contains independent preparation code:

- Exact extraction of all 297 feature families, 59 source categories,
  14 instrument categories, 11 steps and 68 acceptance-case templates.
- A typed observation transport schema with evidence-type, value, provenance,
  censoring, depth and derivation rules.
- Inventory, legacy-code audit, corpus audit, implementation ledger and reports.
- Fail-closed acceptance commands. They return exit code **2**, not success,
  while S01 prerequisites and atomic source mappings are unresolved.
- Fresh official RVO/PDOK parcel acquisition and NASA POWER daily requests,
  with immutable original responses, request receipts and a real KML translation.
- Versioned shared PostgreSQL/PostGIS migrations, contextual foreign keys,
  typed persistence, independent-process readback and reconciled
  JSONL/Parquet/GeoJSON/GeoPackage preparation exports.
- Reusable KML/KMZ ingestion with explicit source namespaces, stable field IDs,
  preserved metadata/original geometry, opt-in topology repair, projected
  area/perimeter and PostgreSQL-backed field exports.

The reference parcel is a real Dutch winter-wheat parcel, **not Karnataka
agronomic evidence**. Its 2025 NASA response contains seven daily parameters
(2,555 observations). These remain **pending**, excluded from the accepted
view, until scientific/product metadata and full acceptance requirements are
resolved. Regional gridded products are not ground measurements. Original
provider units are preserved; canonical scientific normalization is unfinished.
Distinct raw response snapshots remain distinct evidence, not independent
measurements to combine in statistical calculations.

The family inventory is **not** a completed atomic-variable registry. It does
not infer missing scientific units, analytes, source mappings, tolerances or
expected values from feature names. Those require authentic source references.
Schema validation is not proof of scientific validity.

## Acceptance commands

From the repository root, with the declared Python dependencies installed:

```powershell
$env:PYTHONPATH = "src"
python -m agri_data validate --suite connections --config config\acceptance.yaml
python -m agri_data validate --suite database --config config\acceptance.yaml
python -m agri_data validate --suite features --config config\acceptance.yaml
python -m agri_data validate --suite all --fresh --config config\acceptance.yaml
```

Currently all four commands emit a **blocked preparation report** under a
new `data\exports\<run_id>` directory. `--fresh` records the requested mode;
it does **not** claim any provider requests were executed before the gate.
The output is not the completed Section 4 agricultural export bundle.
Its manifest is published after the inventory, schema, audits and reports,
and includes their checksums.

The former positional-KML/demo CLI, legacy modules, generated-data tests and
baseline crop configuration have been removed. The original committed code is
preserved in Git and `.local\legacy-backend-5af5373.zip`. Existing user data,
raw assets and Git stashes are preserved, but are not automatically eligible
as acceptance evidence.

## Reproduce the current preparation

`uv.lock` locks dependency resolution. Install with `uv sync --locked --extra dev`
and use `uv run --locked python` for the commands below, or use a Python
environment with the declared dependencies. No notebook is required.

From the repository root, acquire **fresh** public provider data:

```powershell
python -m agri_data acquire-reference --output data\raw\authentic-reference
```

This prints the newly written corpus manifest path. The provider can change or
withdraw its parcel; acquisition then fails rather than generating a substitute.
Actual raw responses/manifests are local ignored artifacts. On another machine,
acquire them again and update the corpus paths in `config\acceptance.yaml`.

Configure a dedicated real PostgreSQL/PostGIS database matching the database,
user and schema in `config\acceptance.yaml`. Set `DATABASE_URL` and supply
authentication through a secret manager or `PGPASSFILE`. The CLI does not
automatically load `.env`. `docker-compose.yml` is an alternative requiring
explicit database/user/password environment variables; it was not the server
used for local evidence.

The current Windows workspace has an ignored persistent PostgreSQL 17.12
cluster with PostGIS 3.6.2. It is **stopped after verification**, not installed as
a system service. To start it in a terminal, keep that terminal open:

```powershell
$env:PATH = (Resolve-Path .local\postgres\postgresql\pgsql\bin).Path + ";" + $env:PATH
& .local\postgres\postgresql\pgsql\bin\postgres.exe -D .local\postgres\cluster -h 127.0.0.1 -p 55439
```

In a second terminal:

```powershell
$env:PYTHONPATH = "src"
$env:DATABASE_URL = "postgresql://agri_acceptance@127.0.0.1:55439/agri_acceptance"
$env:PGPASSFILE = (Resolve-Path .local\postgres\pgpass.conf).Path
python -m agri_data storage-proof --config config\acceptance.yaml --output data\exports\new-storage-proof
python -m pytest tests
```

Use a new output directory each run. Supply `--corpus <printed-manifest-path>`
to check a newly acquired corpus rather than the configured original one.
The proof returns success only for its limited preparatory checks, **not**
for the full database suite. It checks real commits, repeat import, independent
process values/metadata, geometry arithmetic, rollback and export roundtrips.
Failures leave a `failure.json`; they never become a passed acceptance report.
The tests also make a genuine refused TCP connection and attempt an invalid
relationship between existing authentic records in a rollback-only transaction.

Stop the owned database gracefully without removing persisted evidence:

```powershell
& .local\postgres\postgresql\pgsql\bin\pg_ctl.exe -D .local\postgres\cluster -m fast -w stop
```

## Import authentic field boundaries

With the database running and the same connection environment configured:

```powershell
python -m agri_data ingest-boundaries `
  data\raw\authentic-reference-corpus\55c39b30685bcb336aea24a6a5f5cc59b6ab3a2897eaa35727ff920d550a820a.kml `
  --config config\acceptance.yaml --project public_reference `
  --source-namespace "https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas" `
  --origin "RVO/PDOK; translated original parcel with archived acquisition provenance" `
  --output data\exports\new-boundary-import
```

Keep the project and source namespace stable across re-imports. Original
provider placemark IDs are retained; changing a boundary creates a new boundary
version rather than replacing its history. Original source bytes and geometry,
including altitude when present, remain separate from the 2D analysis footprint.
Origins supplied on this command are declarations, not automatic independent
provenance approval.

Imports reject unsupported/non-polygon geometry, unclosed rings and invalid
coordinates. Topology repair requires `--allow-repair`; originals and repair
reasons remain available. KMZ members are read without filesystem extraction;
remote links are not followed. Polar and antimeridian-spanning boundaries need
explicit projection handling and currently fail rather than receive guessed
area/distance results.

The actual reference parcel passes independent provider/GDAL geometry checks,
PostGIS readback/intersection/area/perimeter checks, repeat import and geographic
export reconciliation. Other KML/KMZ topology contexts and real raster/station
selection cases remain **unverified**, so S03 is not complete.

## Required S01 inputs

Declare actual evidence files in `config\acceptance.yaml`. Each corpus artifact
entry requires `path` and `origin`; paths resolve relative to the repository.
Provide real boundaries, crop/cultivar and season records, source records,
spatial assets, independent references, laboratory reports and device exports.
Do not supply generated examples. A checksum/file alone is insufficient:
independent provenance, meaning and expected-value review remains required.

For S02, configure a dedicated persistent PostgreSQL/PostGIS acceptance server
through the named environment variable, plus expected database/user and
acceptance schema. Never put passwords in configuration or version control.
SQLite, simulated devices and response mocks cannot substitute for evidence.

## Structural checks

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests\contracts\test_plan_contract.py
```

These inspect the actual plan and incomplete-gate CLI behavior. They do not
fabricate agricultural records, run legacy tests or certify any scientific,
device, provider or database integration.
