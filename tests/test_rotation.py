from agri_data.rotation import (
    estimate_moisture_carryover, estimate_residue_dynamics,
    evaluate_rotation_sequence,
)


def test_moisture_carryover_is_bounded():
    result = estimate_moisture_carryover(500, 200, 150, 100)
    assert result["soil_moisture_carryover_mm"] == 125


def test_residue_estimate_decreases_over_time():
    now = estimate_residue_dynamics("ragi", 2.0, days_after_harvest=0)
    later = estimate_residue_dynamics("ragi", 2.0, days_after_harvest=120)
    assert later["residue_remaining_kg_ha"] < now["residue_remaining_kg_ha"]


def test_rotation_sequence_has_transition_scores():
    result = evaluate_rotation_sequence(["ragi", "pigeonpea", "groundnut"])
    assert len(result["transitions"]) == 2
    assert result["rotation_class"] in {"strong", "acceptable", "weak", "insufficient_data"}
