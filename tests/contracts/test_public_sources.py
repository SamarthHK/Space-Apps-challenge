"""Live public-source checks; use the india optional dependencies."""

from hashlib import sha256
import json
from pathlib import Path
import re

import pytest

from agri_data.contracts.assets import archive_response, system_trust_session


DES = "https://data.desagri.gov.in"


def test_native_tls_public_form_preserves_real_report_without_request_secrets(tmp_path):
    with system_trust_session() as session:
        form = archive_response(DES + "/website/crops-apy-report-web", tmp_path, session=session)
        text = Path(form["raw_path"]).read_text(encoding="utf-8")
        token = re.search(r'id="hdnrltoken"[^>]*value="([^"]+)"', text)[1]
        assert 'value="29"' in text and "Karnataka" in text and 'value="2020"' in text
        report = archive_response(
            DES + "/report/crop/horizontal_crop_vertical_year", tmp_path,
            session=session, method="POST", timeout=120,
            data={"reportformat": "horizontal_crop_vertical_year",
                  "fltrstates[]": ["29"], "fltrdistricts[]": [""],
                  "fltrcrops[]": ["1", "5"], "fltrseason[]": ["K"],
                  "fltrstartyear": "2020", "fltrendyear": "2020",
                  "fltrrptformat": "scrview", "_token": token},
        )
    payload = Path(report["raw_path"]).read_bytes()
    body = payload.decode("utf-8")
    assert all(label in body for label in (
        'id="apyreport"', "Karnataka", "Bagalkot", "2020 - 2021",
        "Maize", "Rice", "Area (Hectare)", "Production (Tonnes)", "Yield (Tonne/Hectare)",
    ))
    assert report["raw_sha256"] == sha256(payload).hexdigest()
    receipt = json.loads((tmp_path / (report["request_id"] + ".request.json")).read_bytes())
    assert receipt == report and report["request_method"] == "POST"
    assert token not in json.dumps(receipt)
    assert not {"cookies", "headers", "data", "_token"} & receipt.keys()


def test_default_acquisition_keeps_immutable_bytes_and_distinct_receipts(tmp_path):
    url = "https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet"
    first = archive_response(url, tmp_path, {"id": "1574"})
    original = Path(first["raw_path"]).read_bytes()
    second = archive_response(url, tmp_path, {"id": "1574"})
    assert b"Oryza sativa" in original and b"Rainfall (annual)" in original
    assert Path(first["raw_path"]).read_bytes() == original
    assert sha256(original).hexdigest() == first["raw_sha256"]
    assert first["request_id"] != second["request_id"]
    assert len(list(tmp_path.glob("*.request.json"))) == 2
    assert all(asset["fresh"] and asset["http_status"] == 200 for asset in (first, second))


def test_native_trust_cannot_be_used_with_certificate_verification_disabled():
    with system_trust_session() as session:
        with pytest.raises(ValueError, match="requires certificate verification"):
            session.get(DES + "/website/crops-apy-report-web", verify=False)


def test_public_redirect_receipt_keeps_original_source_without_temporary_credentials(tmp_path):
    url = "https://github.com/user-attachments/files/20961388/GAEZv5_Themes_Sub-themes_Variables.xlsx"
    with system_trust_session() as session:
        asset = archive_response(url, tmp_path, session=session)
    assert asset["requested_url"] == url
    assert asset["response_url"].startswith("https://objects.githubusercontent.com/")
    assert "x-amz-" not in json.dumps(asset).casefold()
    assert Path(asset["raw_path"]).read_bytes().startswith(b"PK")
