# AgriData

KML-based agricultural data collection, processing, storage, and crop-analysis
prototype for the NASA Space Apps Challenge.

## Run the sample pipeline

The project includes four Karnataka pilot plots and offline fallbacks for the
external data adapters, so the complete workflow can be demonstrated without API
credentials:

```bash
PYTHONPATH=src .venv/bin/python -c \
  'from agri_data.pipeline import run_pipeline; run_pipeline("data/input/farm_area.kml")'
```

Outputs are written to `data/processed`, `data/exports`, and the configured SQLite
database. Raw source responses are preserved under `data/raw`.

## Test

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

The main entry point is `agri_data.pipeline.run_pipeline`. It parses KML/KMZ
boundaries, calculates field geometry metrics, acquires soil/climate/water/
satellite data, derives indicators, records normalized observations, and writes
field and project reports. See [`docs/kml_workflow.md`](docs/kml_workflow.md) and
[`docs/data_dictionary.md`](docs/data_dictionary.md) for data conventions.
