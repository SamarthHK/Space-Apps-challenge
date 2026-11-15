import json
from pathlib import Path

from agri_data.api.app import create_app
from agri_data.api.settings import ApiSettings


def test_published_contract_matches_implemented_routes_and_auth():
    app = create_app(ApiSettings(_env_file=None, database_url=None))
    actual = app.openapi()
    published = json.loads(
        (Path(__file__).resolve().parents[2] / "docs" / "openapi.json").read_text()
    )
    assert actual == published
    profile = actual["paths"]["/api/v1/me/profile"]
    assert profile["get"]["security"] == [{"SessionCookie": []}]
    parameters = {parameter["name"] for parameter in profile["patch"]["parameters"]}
    assert {"Origin", "X-CSRF-Token"} <= parameters
    assert "/api/v1/fields" not in actual["paths"]
    assert actual["components"]["schemas"]["LoginRequest"]["properties"]["password"]["writeOnly"]
