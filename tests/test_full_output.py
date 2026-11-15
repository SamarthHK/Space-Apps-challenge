import json
import pytest
from agri_data.storage.full_output import write_bundle, filter_bundle, checksum


def test_complete_rows_unknown_metadata_and_filter_preservation(tmp_path):
    rows = [{"variable_id": "soil_ph", "value_numeric": i / 12345, "extra": {"depth": i}} for i in range(1500)]
    manifest = write_bundle(iter(rows), tmp_path / "full")
    source = tmp_path / "full/observations.jsonl"
    assert manifest["row_count"] == 1500
    assert [json.loads(line) for line in source.read_text().splitlines()] == rows
    digest = checksum(source)
    result = filter_bundle(source, tmp_path / "filtered", {"variable_id": ["missing"]})
    assert result["counts"] == {"input": 1500, "selected": 0}
    assert checksum(source) == digest
    with pytest.raises(FileExistsError):
        write_bundle([], tmp_path / "full")


def test_no_filter_retains_every_record(tmp_path):
    write_bundle([{"value_text": "unknown"}, {"value_numeric": None}], tmp_path / "full")
    result = filter_bundle(tmp_path / "full/observations.jsonl", tmp_path / "copy", {})
    assert result["row_count"] == 2
