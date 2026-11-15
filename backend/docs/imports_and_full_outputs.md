# Complete output and import workflow

> Historical documentation. These commands and modules have been retired.
> Do not run the sample workflow below as acceptance evidence. Current preparation
> commands and the unfinished full-export contract are documented in `README.md`.

Run the current source adapters:

```sh
PYTHONPATH=src .venv/bin/python -m agri_data data/input/farm_area.kml --mode live
```

Each run has an isolated directory under data/exports. The full/FIELD_ID directory
contains every normalized observation in observations.jsonl and a manifest with its
checksum and row count. Extra observation metadata is retained. The agricultural
profile remains a summary and now references that complete bundle. Raw imports are
stored byte-for-byte under data/raw/imports. These files are not committed to Git.

For user-provided measurements, create a JSON import plan:

```json
{"datasets": [{
  "id": "farm_lab_2025", "source_id": "my_laboratory", "domain": "soil",
  "field_name": "FarmLand", "path": "soil_samples.csv",
  "measurement_type": "measured",
  "variables": {"soil_ph": {"unit": "pH", "description": "Laboratory soil pH"}}
}]}
```

Paths are resolved relative to the plan. Field names must match exactly one KML
polygon. CSV columns use variable_id, value_numeric, value_text, observed_at,
depth_top_cm, depth_bottom_cm, and optional missing_reason. JSON input is an array
of the same records. Text measurements and unknown original columns are retained.
Units must match the registry; this importer does not guess unit conversions.

```sh
PYTHONPATH=src .venv/bin/python -m agri_data FarmLand.kml --import-plan imports.json --imports-only
```

The generic import path supports the fifteen domain identifiers defined in
sources/imports.py. It does not replace specialist sensor calibration, management
event tables, crop models, or live data connectors. Those remain outstanding.

Filter a full artifact into a new directory with the Python API:

```python
from agri_data.storage.full_output import filter_bundle
filter_bundle("data/exports/RUN/full/FIELD/observations.jsonl",
              "data/exports/RUN/filtered/soil",
              {"domain": ["soil"]})
```

Filters currently support exact field, domain, variable, source, measurement-type,
and quality-flag lists. Date/depth ranges and filtering CLI commands remain pending.
Full exports have no record limit. Filtered exports preserve the input checksum,
filter specification, and before/after counts. Existing destinations are rejected.
