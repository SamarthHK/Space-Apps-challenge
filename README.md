# AgriData

The backend is being rewritten against **Plan.md**. Its current acceptance
override requires engineering health: nonredundant logical records, consistent
formats, accessible acquisition routes and reliable scripts. Scientific approval
is no longer a software-health gate. **The full feature inventory remains incomplete.**

## Engineering health

With the configured PostgreSQL/PostGIS server running and its connection
environment set (see below), use a new output directory:

```powershell
python -m agri_data health-check --config config\acceptance.yaml --output data\exports\engineering-health
```

This always makes fresh PDOK, NASA POWER and Rothamsted requests, runs the existing
boundary/weather/trial import paths, checks repeat-import behavior and canonical
deduplication, and reconciles Parquet/JSON/provenance relationships against real
PostgreSQL. Raw bytes are content-addressed; requests retain separate receipts.
It creates a candidate dataset under `dataset` and an atomic `health.json`.
Exit 0 means the named pipelines passed during that run; exit 2 means a failure
or blocked dependency. It does not start a database server automatically.

Pending scientific review and intentionally missing source values do not fail
engineering health. Missing decision timestamps/history and leakage concerns
still prevent claiming the dataset is ready to train. Unimplemented source and
feature families are not counted as working, and API uptime is not guaranteed.

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
measurements to combine in statistical calculations. Canonical reconciliation
now links those snapshots to one scientific observation when their content
agrees; historical source rows remain intact.

The family inventory is **not** a completed atomic-variable registry. It does
not infer missing scientific units, analytes, source mappings, tolerances or
expected values from feature names. Those require authentic source references.
Schema validation is not proof of scientific validity.

## Original strict-contract audit commands

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

These preserve the original scientific/full-inventory audit, not the new
engineering-health decision. Use `health-check` above for current acceptance.

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
coordinates. Topology repair requires `--allow-repair`, an authentic reviewed
`--repair-reference` KML with matching provider placemark IDs, and explicit
`--repair-area-tolerance-m2` / `--repair-shape-tolerance-m2` limits. The repaired
footprint must satisfy both projected-area difference and symmetric-difference
limits against that reference. Original geometry and repair evidence are retained.
The repaired-geometry path still needs authentic invalid-case acceptance evidence.
KMZ members are read without filesystem extraction;
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

## Canonical data and ML preparation

The first declared target is following-crop grain yield in kg/ha at the recorded
85% dry-matter basis. `config\ml_dataset.yaml` defines the example unit, prediction
timing, held-out-site/group/temporal requirements and readiness conditions.
This is an observational outcome task, not proof of causal rotation benefit.
This original preparation path remains deliberately blocked. The retrospective
multicrop modeling path below now trains real models under the engineering
requirements, without changing any source record's scientific approval status.

The additive migrations preserve old field IDs and every source-normalized
observation. `field_aliases` resolves the reviewed reference identity;
`canonical_observations` contains distinct scientific content;
`observation_evidence` and `acquisition_observations` retain every original
source row and retrieval. Changed values remain separate revisions under a
shared context ID. The accepted canonical view requires explicit validation;
reconciliation never approves a record automatically.

The initial three real NASA response snapshots reconciled to **2,555 canonical
weather observations**, with all **7,665 source records** retained. Later
acquisition counts are recorded in each health report. The field is represented
once in `canonical_fields`. NASA import jobs now complete after readback/export
and reconciliation, or record failure. Daily mean rainfall rate is explicitly
converted to a one-day accumulation in the canonical record, while the original
unit remains preserved. Product native resolution/scientific review is still
pending, so these are not automatically training-ready predictors.

With the database running:

```powershell
python -m agri_data reconcile-data --config config\acceptance.yaml
python -m agri_data acquire-trials --output data\raw\rotation-trials-new
```

`acquire-trials` prints the actual acquisition manifest. Import that path:

```powershell
python -m agri_data import-trials --config config\acceptance.yaml --manifest <printed-manifest-path>
python -m agri_data prepare-ml --config config\acceptance.yaml --contract config\ml_dataset.yaml --output data\exports\new-ml-snapshot
```

The workspace's archived trial manifest is recorded as `trial_corpus_manifest`
in `config\acceptance.yaml`. Point that setting at the newly acquired manifest
when reproducing the tests on another machine.

### Actual empirical outcomes

The Woburn Ley-arable experiment dataset provides **2,240 wheat plot-year rows
across 43 harvest years**, with **21 recorded rotation factor codes**. These
codes include historical changes/transitions; they are not 21 independently
verified complete crop sequences. The importer retains all five original CSV
resources, factor definitions, cultivar names, fertilizer context and notes.
Yield units come from the original workbook, not a guessed CSV convention.
CSV values are independently reconciled with the workbook at published CSV
precision.

The source contains **12 missing yields**, retained as missing. It also contains
duplicate `plot_code` values for distinct split plots; identity uses the recorded
year/block/main-plot/split-plot fields and flags the conflicting codes for review.
Rows with notes, including failed crops, estimated/missing yields and management
exceptions, are not silently accepted as clean labels.

**Attribution:** Contains data supplied by Rothamsted Research.

**Citation:** Glendining, M., Poulton, P., Macdonald, A., MacLaren, C., Clark, S.
(2022). Woburn Ley-arable experiment: yields of wheat as first test crop,
1976-2018. Electronic Rothamsted Archive, Rothamsted Research.
https://doi.org/10.23637/wrn3-wheat7618-01. CC-BY-4.0.

**Acknowledgement:** The Electronic Rothamsted Archive (e-RA), its datasets,
information and other resources, are part of the Rothamsted Long-Term Experiments -
National Bioscience Research Infrastructure (RLTE-NBRI), funded by the UK Research
and Innovation - Biotechnology and Biological Sciences Research Council (UKRI-BBSRC)
under award BBS/E/RH/23NB0007 (2023-2028). The RLTE-NBRI is also supported by the
Lawes Agricultural Trust.

### Snapshot contents and remaining gates

`prepare-ml` reads one repeatable database snapshot and writes `examples.parquet`,
`features.parquet`, `targets.parquet`, `splits.parquet`, `lineage.parquet`,
separate canonical `weather.parquet`, shared trial factor resources, field aliases,
source asset hashes, exclusions, schema, configuration and an atomic manifest.
IDs and file checksums make repeat exports reproducible without duplicating
factor descriptions or weather histories into every example.

**It currently exits 2 and reports `training_ready: false`.** All candidates are
withheld: decisions and precise preceding sequences are not documented/reviewed,
targets/features lack final scientific approval, and a single UK trial site
does not establish geographical generalization. The Dutch weather is deliberately
not joined to this UK trial. Actual in-season fertilizer applications are not
treated as plans known before sowing.

`load_training_snapshot` rejects preparation snapshots. Decision-feature checks
reject unknown availability, future realized support and unvalidated inputs;
split checks reject duplicate contexts, shared groups across partitions and
training labels unavailable before evaluation decisions. The positive full
training-loader path still requires an authentic approved corpus for acceptance.
No imputation, invented decision dates, artificial labels or model training is
performed by `prepare-ml`. Its original scientific approval rules are not the
engineering acceptance rules for the separate, explicitly retrospective
experiment below. Neither command claims an operational crop recommendation.

## Trained multicrop outcome pilot

AI/ML development and its data-preparation dependencies live on `backend-ai`.

The [India model plan](INDIA_MODEL_PLAN.md) covers Indian crops and fruits,
source-backed growing requirements, time-aligned features, competing model
architectures and crop-covered evaluation. It is a source-audited roadmap,
not a claim that Indian models have already been trained.

`outcome_data.py` acquires the official Broadbalk wheat, field bean, oat, forage
maize and potato spreadsheets plus the Woburn wheat trial. It preserves all
original fields, reference tables, missing yields and source notes. NASA POWER
history is queried at the two published experiment coordinates for 1981-2022,
not at the unrelated Dutch reference parcel.

The first expanded corpus has 12,580 source rows (including missing outcomes
and fallow records), 30,680 site/day weather rows and 212,570 nonmissing weather
values. It produces 8,964 eligible retrospective crop-season candidates.
The remaining 3,616 rows have explicit exclusion reasons, including dates
outside weather coverage, missing outcomes and identified source problems.
Source measurements and provider-modelled weather remain distinguished.

Migration 007 stores source-normalized modeling records and versioned dataset
membership in PostgreSQL. Independent SQL readback and Parquet roundtrips must
agree. Broadbalk's `2.1`/`21` and `2.2`/`22` aliases are resolved before splitting;
original plot labels stay in the source records. Repeat imports are idempotent.

`outcome_model.py` uses preplant 30/90/365-day weather summaries, crop/cultivar
and recorded prior-crop/rotation context, planting-day seasonality, and only
dated management applications preceding the cutoff. Coverage is retained for
inspection rather than counted as an extra predictor. Redundant rainfall means,
constant columns and entirely missing columns are excluded from model inputs.
Each fitted model uses 40-46 of the 48 candidate predictors. No soil measurement
is invented, and no post-planting weather or final harvested biomass is an input.

The cutoff is a retrospective policy: the day before recorded sowing. Source
publication/reanalysis retrieval took place later. This is **not** a historical
operational forecast or a claim that all features were available to farmers then.
Actual future fertilizer applications are not substituted for planned inputs.

### Reproduce

Run from the repository root. The ML dependencies are optional. Use a separate
environment rather than replacing the Python runtime used by a running API:

```powershell
$env:UV_PROJECT_ENVIRONMENT = ".local\ml-env"
uv sync --locked --extra ml --extra dev --python 3.12
$env:PYTHONPATH = "src"

# Set DATABASE_URL and PostgreSQL authentication for config\acceptance.yaml.
# Use the actual port of the existing acceptance server; do not restart another process.
$corpus = (& .local\ml-env\Scripts\python.exe -m agri_data acquire-outcomes `
  --contract config\outcome_model.yaml --output data\raw\multicrop-outcomes |
  ConvertFrom-Json).corpus

& .local\ml-env\Scripts\python.exe -m agri_data build-outcomes `
  --config config\acceptance.yaml --corpus $corpus --output data\exports\outcomes-new
& .local\ml-env\Scripts\python.exe -m agri_data train-outcomes `
  --dataset data\exports\outcomes-new --output data\exports\models-new
& .local\ml-env\Scripts\python.exe -m agri_data predict-outcome `
  --model data\exports\models-new --input data\exports\models-new\wheat.input.json
```

Use new output directories. Acquisition always makes fresh requests; rebuilding
from the recorded corpus replays its checksum-verified original bytes without
requesting the same NASA grid repeatedly. The published Broadbalk wheat ZIP link
was unavailable; the linked official XLSX route works and is used explicitly.

Prediction accepts a complete **prepared feature record**, not yet arbitrary KML
or a crop-ranking request. The generated `*.input.json` files are actual training
examples for verifying model reload, not artificial farms. Unknown crops/sites/
categories, absent feature columns and out-of-range numerical inputs are rejected.

### Evaluation and current limits

Four crop-specific CatBoost models were fitted. Whole Broadbalk treatment strips
and Woburn main plots are separated across train/validation/test, with later
years held out and a harvest-before-decision embargo. Of the candidates, 3,610
are training rows, 211 validation rows and 315 test rows; 4,828 remain withheld
because of these group/time reservations or insufficient crop-specific support.
Withheld source data are retained, not silently dropped or used for training.

Validation chooses between CatBoost and a training-only contextual mean baseline.
The no-weather ablation measures whether NASA-derived predictors help. Selection
does not use the test outcomes. Initial held-out MAE (kg/ha):

| Crop / target basis | CatBoost | Baseline | Validation-selected method |
| --- | ---: | ---: | --- |
| Wheat grain, 85% dry matter | 1,657 | 1,569 | CatBoost |
| Oat grain, 85% dry matter | 2,045 | 1,957 | Baseline |
| Forage maize whole crop, 100% dry matter | 2,914 | 3,047 | CatBoost |
| Potato tubers, fresh weight | 8,098 | 13,070 | CatBoost |

**The model does not consistently beat the baseline.** In particular, wheat's
validation improvement did not carry over to the held-out test. The small maize,
oat and potato evaluation groups also limit confidence. Field beans are acquired
but not fitted: only five recent harvest years overlap NASA coverage, and too
few training rows survive the group/time split. We do not weaken the split to
claim a fifth model.

`report.json` contains per-crop errors, year ranges, feature importance and
empirical validation-residual bands with measured test coverage. These bands
are not guaranteed confidence intervals. `examples.parquet` retains every
eligible candidate and its split/reason; `test_predictions.parquet` contains
baseline, fitted-model, selected-method and no-weather predictions. Manifests
record source dataset, configuration, code, model and dependency-lock hashes.

Current artifacts are `data\exports\multicrop-dataset-v3` and
`data\exports\multicrop-model-v3`. They remain research artifacts:
`operational_recommendation_ready: false`. Two English experiment sites do not
support a claim of global or Karnataka suitability. Different crop targets and
time cutoffs cannot be ranked as one shared-date crop-choice backtest. No
causal rotation benefits, multi-season soil transitions, or production
recommendation API have been implemented.

For the new real-data tests, install the ML extra, configure the database, and set:

```powershell
$env:AGRI_OUTCOME_DATASET = (Resolve-Path data\exports\multicrop-dataset-v3).Path
& .local\ml-env\Scripts\python.exe -m pytest tests\contracts\test_outcome_model.py
```

For the entire suite, also configure the existing API tests' `AGRI_TEST_*`
database/project settings. On a shared Windows machine, use a unique
`--basetemp` directory if the shared pytest temporary directory is locked.

All e-RA datasets are used under CC-BY-4.0. **Contains data supplied by Rothamsted
Research.** Full per-dataset citations and the RLTE-NBRI/UKRI-BBSRC/Lawes
Agricultural Trust acknowledgement are retained in the configuration, corpus
and exported reports; the source spreadsheets are retained without alteration.

## Structural checks

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests\contracts\test_plan_contract.py
```

These inspect the actual plan and incomplete-gate CLI behavior. They do not
fabricate agricultural records, run legacy tests or certify any scientific,
device, provider or database integration.
