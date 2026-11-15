# Database schema

> Historical documentation, not the current storage contract. SQLite support was
> removed. Current shared PostgreSQL/PostGIS migrations are under
> `src/agri_data/contracts/migrations`; full domain schemas remain outstanding.

SQLite is the default development backend; PostgreSQL/PostGIS is supported by
setting `DATABASE_URL`. `fields` stores KML geometry as WKT in EPSG:4326,
`observations` is the normalized multi-domain fact table, and `source_assets`
tracks file checksums for provenance. Crop, biological-risk, rotation,
management, and sensor tables are kept separate from environmental observations.

Initialize and seed the schema with:

```python
from agri_data.storage import init_db
init_db()
```
