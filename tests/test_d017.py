"""Focused tests for the D-017 shadow rear-docking pose audit."""

from __future__ import annotations

import math

import pytest

from aweform import d014, d017
from aweform.development_visualizer import (
    DEVELOPMENT_VISUALIZATION_ADAPTERS,
    build_d017_development_visualization,
    build_development_visualization,
    build_development_visualization_figure,
)
from aweform.env import Action
from aweform.exp003_seed_policy import validate_exp003_development_seeds


def test_d017_seed_declaration_and_exact_guard() -> None:
    seeds = d017.D017_DEFAULT_DEVELOPMENT_SEEDS
    assert seeds == (18356, 18357, 18358)
    assert validate_exp003_development_seeds(seeds) == seeds
    assert d017._validate_d017_development_seeds(seeds) == seeds
    with pytest.raises(ValueError, match="only predeclared development seeds"):
        d017._validate_d017_development_seeds((18355,))
    with pytest.raises(ValueError, match="reserved for a formal experiment"):
        d017._validate_d017_development_seeds((50001,))


def test_declared_geometry_and_sweep_are_exact() -> None:
    assert d017.D017_BODY_LENGTH == 0.10
    assert d017.D017_BODY_WIDTH == 0.08
    assert d017.D017_REAR_X == -0.05
    assert d017.D017_CONTACT_LATERAL_OFFSET == 0.025
    assert d017.D017_FRONT_X == 0.05
    assert d017.D017_CONTACT_TOLERANCE == 0.01
    assert d017.D017_DOCK_ORIENTATIONS == (
        0.0,
        math.pi / 4.0,
        math.pi / 2.0,
        3.0 * math.pi / 4.0,
        math.pi,
        5.0 * math.pi / 4.0,
        3.0 * math.pi / 2.0,
        7.0 * math.pi / 4.0,
    )


@pytest.mark.parametrize("phi", d017.D017_DOCK_ORIENTATIONS)
def test_ideal_rear_docking_pose_has_zero_pair_error(phi: float) -> None:
    station = (0.37, 0.61)
    body, heading = d017.ideal_rear_docking_pose(station, phi)
    assert d017.shadow_pair_errors(body, heading, station, phi) == pytest.approx(
        (0.0, 0.0), abs=1e-15
    )


def test_shadow_geometry_is_translation_invariant() -> None:
    body = (0.21, 0.34)
    station = (0.72, 0.41)
    phi = 1.1
    errors = d017.shadow_pair_errors(body, 0.4, station, phi)
    shifted = (1.8, -0.7)
    shifted_errors = d017.shadow_pair_errors(
        (body[0] + shifted[0], body[1] + shifted[1]),
        0.4,
        (station[0] + shifted[0], station[1] + shifted[1]),
        phi,
    )
    assert shifted_errors == pytest.approx(errors, abs=1e-15)


def test_shadow_geometry_is_rotation_consistent() -> None:
    body = (0.21, 0.34)
    station = (0.72, 0.41)
    heading = 0.4
    phi = 1.1
    rotation = 0.8
    def rotate(point: tuple[float, float]) -> tuple[float, float]:
        return (
            point[0] * math.cos(rotation) - point[1] * math.sin(rotation),
            point[0] * math.sin(rotation) + point[1] * math.cos(rotation),
        )
    assert d017.shadow_pair_errors(
        rotate(body), heading + rotation, rotate(station), phi + rotation
    ) == pytest.approx(d017.shadow_pair_errors(body, heading, station, phi), abs=1e-15)


def test_rear_and_front_midpoint_formulas_agree_with_body_frame() -> None:
    body = (0.4, 0.2)
    station = (0.51, 0.31)
    heading = 0.7
    rear, front = d017.rear_front_midpoint_errors(body, heading, station)
    _, x_rel, y_rel, _ = d017.station_relative_geometry(body, heading, station)
    assert rear == pytest.approx(math.hypot(x_rel + 0.05, y_rel), abs=1e-15)
    assert front == pytest.approx(math.hypot(x_rel - 0.05, y_rel), abs=1e-15)


def test_tolerance_is_inclusive() -> None:
    assert 0.01 <= d017.D017_CONTACT_TOLERANCE
    station = (0.0, 0.0)
    body, heading = d017.ideal_rear_docking_pose(station, 0.0)
    assert all(
        error <= 0.01
        for error in d017.shadow_pair_errors(body, heading, station, 0.0)
    )


def test_entry_selection_excludes_initial_setup_and_charge_waits() -> None:
    result = d017.run_d017_probe((18356,), horizon=1000)
    run = result["results"][0]
    assert isinstance(run, dict)
    audit = run["docking_audit"]
    assert isinstance(audit, dict)
    entries = audit["entries"]
    assert isinstance(entries, list)
    assert audit["initial_post_contact_setup_excluded"] is True
    assert all(entry["transition_index"] > 1 for entry in entries)
    assert all(entry["action"] != Action.WAIT.name for entry in entries)
    assert all(entry["transition_index"] <= 1000 for entry in entries)


def test_d017_preserves_boundary_and_matches_d014_behavior() -> None:
    reference = d014._run_seed(18356, horizon=120)
    result = d017._run_seed(18356, horizon=120)
    for key in (
        "transitions",
        "terminated",
        "truncated",
        "termination_reason",
        "energy_termination",
        "thermal_termination",
        "minimum_normalized_energy",
        "final_normalized_energy",
        "maximum_thermal_state",
        "final_thermal_state",
        "action_counts",
        "mode_occupancy",
        "mode_entry_counts",
        "successful_physical_charger_exits",
        "low_energy_seek_entries",
        "successful_charging_contact_reacquisitions",
        "completed_autonomous_regulation_cycles",
    ):
        assert result[key] == reference[key]
    whole = d017.run_d017_probe((18356,), horizon=2)
    assert whole["organism_boundary"] == {"reward": 0.0, "info": {}}


def test_shadow_values_are_not_in_observation_or_learned_state() -> None:
    result = d017.run_d017_probe((18356,), horizon=1)
    assert result["organism_visible"]["shadow_values_visible"] is False  # type: ignore[index]
    assert result["learned"] == {"status": "none", "learner_instantiated": False}
    assert result["organism_boundary"] == {"reward": 0.0, "info": {}}


def test_shadow_geometry_does_not_consume_rng_or_change_behavior() -> None:
    reference = d014._run_seed(18357, horizon=160)
    diagnostic = d017._run_seed(18357, horizon=160)
    assert diagnostic["action_counts"] == reference["action_counts"]
    assert diagnostic["successful_charging_contact_reacquisitions"] == reference[
        "successful_charging_contact_reacquisitions"
    ]


def test_matched_orientation_is_rear_midpoint_error() -> None:
    station = (0.3, 0.6)
    body = (0.42, 0.49)
    heading = 0.9
    rear_error, _ = d017.rear_front_midpoint_errors(body, heading, station)
    plus, minus = d017.shadow_pair_errors(body, heading, station, heading)
    assert plus == pytest.approx(rear_error, abs=1e-15)
    assert minus == pytest.approx(rear_error, abs=1e-15)


def test_pooled_aggregate_preserves_fixed_sweep_distributions() -> None:
    result = d017.run_d017_probe((18356, 18357), horizon=10)
    aggregates = result["aggregates"]
    assert isinstance(aggregates, dict)
    pooled = aggregates["pooled"]
    assert isinstance(pooled, dict)
    distributions = pooled["fixed_orientation_max_pair_error_distributions"]
    assert isinstance(distributions, dict)
    assert set(distributions) == {str(phi) for phi in d017.D017_DOCK_ORIENTATIONS}


def test_d017_visualizer_uses_shared_adapter_and_fixed_phi_zero_overlay() -> None:
    assert DEVELOPMENT_VISUALIZATION_ADAPTERS["d017"] is (
        build_d017_development_visualization
    )
    data = build_development_visualization("d017", seed=18356, horizon=3)
    shadow = data.shadow_geometry
    assert shadow is not None
    assert shadow.dock_orientation == 0.0
    assert "EVALUATOR-ONLY SHADOW MORPHOLOGY" in data.source_label
    assert shadow.dock_contact_plus == pytest.approx((0.5, 0.525), abs=1e-15)
    assert shadow.dock_contact_minus == pytest.approx((0.5, 0.475), abs=1e-15)
    figure, animation = build_development_visualization_figure(data)
    assert len(figure.axes) == 2
    assert any(
        "EVALUATOR-ONLY SHADOW MORPHOLOGY" in text.get_text()
        for text in figure.axes[0].texts
    )
    animation.event_source.stop()
    import matplotlib.pyplot as plt

    plt.close(figure)


def test_d017_visualizer_rejects_non_d017_seed() -> None:
    with pytest.raises(ValueError):
        build_d017_development_visualization(seed=18355, horizon=1)
