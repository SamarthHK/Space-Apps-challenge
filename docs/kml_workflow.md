# KML workflow

`agri_data.pipeline.run_pipeline` accepts a `.kml` or `.kmz` file, extracts polygon
placemarks, repairs validatable geometries, assigns stable `FIELD_XXXX` identifiers,
calculates metric area/perimeter, and uses each field's representative point for
point-query sources. Raw source responses remain under `data/raw`; normalized
observations are stored in SQLite/PostgreSQL and processed exports under `data/`.

Example:

```python
from agri_data.pipeline import run_pipeline
result = run_pipeline("data/input/farm_area.kml")
```

The default adapters support offline fallbacks so the sample workflow can be tested
without credentials. Production runs should record the source version and review
quality flags before using agricultural interpretations.
