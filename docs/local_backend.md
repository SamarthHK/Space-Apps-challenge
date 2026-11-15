# Local backend

Python 3.12 is selected in `.python-version`. `pyproject.toml` is authoritative;
`uv.lock` locks the graph and `requirements.txt` is generated, not edited separately.

```powershell
uv sync --locked --extra dev
uv run --no-sync pytest tests\api -q
uv run --no-sync uvicorn agri_data.api.app:create_app --factory --host 0.0.0.0 --port 8080
```

The API does not import the legacy demo pipeline. `/health` is liveness;
`/ready` returns 503 until real database/migrations are verified. `/api/v1/meta`
reports unavailable capabilities honestly. The old generated-data tests are not
scientific acceptance evidence and are not part of this new API test selector.

Use `.env.example` as configuration guidance, with secrets only in ignored `.env`
or process environment variables. Bind frontend development to port 1080, and
browse `http://localhost:1080` with API origin `http://localhost:8080`.
`0.0.0.0` is a bind address, not an allowed browser origin. Production requires
HTTPS origins, Secure cookies and an explicit PostgreSQL connection.

To update dependencies after editing the manifest:

```powershell
uv sync --extra dev
uv export --extra dev --no-hashes --no-emit-project --output-file requirements.txt
```
