from __future__ import annotations

import numpy as np
import pytest

from aweform.d045 import D045_MAX_WHEEL_DELTA_RAD
from aweform.d046 import D046ConsequencePredictor
from aweform.d061 import D061_SEEDS, run_d061_lifetime, validate_d061_seeds
from aweform.d061_visualizer import adapt_d061_trace
from aweform.development_visualizer import build_development_html_replay


def test_d061_seeds_use_formal_reservation_guard() -> None:
    assert validate_d061_seeds() == (22053,)
    assert validate_d061_seeds(D061_SEEDS) == D061_SEEDS
    with pytest.raises(ValueError):
        validate_d061_seeds((50001, 22054, 22055))


def test_d046_predictor_starts_zero_and_updates_from_actual_transition() -> None:
    learner = D046ConsequencePredictor()
    before = learner.weight_digest()
    assert all(value == 0.0 for value in learner.weights)
    observation = np.zeros(8, dtype=np.float32)
    prediction = learner.predict(observation, (0.0, 0.0))
    next_observation = np.ones(8, dtype=np.float32) * 0.1
    learner.update_from_transition(
        observation, (0.0, 0.0), next_observation, prediction
    )
    assert learner.weight_digest() != before


def test_d061_short_run_has_zero_reward_empty_info_and_legal_actions() -> None:
    result = run_d061_lifetime(22053, "L", horizon=32)
    assert result["transitions"] == 32
    assert result["reward_zero"] is True
    assert result["info_empty"] is True
    assert result["float32_eight_channels"] is True
    assert result["legal_wheels"] is True
    assert result["learner_updates"] == 32
    assert result["learner_nonzero_weight_updates"] > 0
    assert result["horizon_censored"] is True


def test_d061_arms_match_through_warmup_and_reset_the_learner_per_lifetime() -> None:
    baseline = run_d061_lifetime(22053, "U", horizon=564)
    live = run_d061_lifetime(22053, "L", horizon=564)
    assert baseline["trace"] == live["trace"]
    assert (
        baseline["learner_final_weight_digest"] == live["learner_final_weight_digest"]
    )
    assert baseline["selected_action_differs_from_U_proposal"] == 0
    fresh = D046ConsequencePredictor()
    assert all(value == 0.0 for value in fresh.weights)


def test_d061_live_and_permuted_arms_get_equal_candidate_read_budgets() -> None:
    live = run_d061_lifetime(22053, "L", horizon=572)
    permuted = run_d061_lifetime(22053, "P", horizon=572)
    assert live["candidate_query_slots"] == 2
    assert permuted["candidate_query_slots"] == 2
    assert live["candidate_prediction_reads"] == 6
    assert permuted["candidate_prediction_reads"] == 6
    assert live["learner_updates"] == permuted["learner_updates"] == 572


@pytest.mark.parametrize("arm", ("U", "L", "P"))
@pytest.mark.parametrize("mode", ("NORMAL", "RETURN", "CHARGE"))
def test_saved_d061_frames_use_the_canonical_shared_renderer(
    arm: str, mode: str
) -> None:
    initial = {
        "position": (0.5, 0.5),
        "heading": 0.0,
        "energy_fraction": 0.8,
        "temperature_channel": 0.2875,
        "charging_contact": True,
    }
    trace = [
        {
            "transition": 100,
            "x": 0.5,
            "y": 0.5,
            "heading": 0.0,
            "symbolic_proposal": "MOVE_FORWARD",
            "action": [0.5, -0.5],
            "active_mode": mode,
            "energy_after": 0.79,
            "thermal": 0.2875,
            "charging_contact_after": True,
            "terminated": False,
            "truncated": False,
            "simulated_seconds": 10.0,
            "charging_contact_before": True,
            "events": [],
            "command_source": "PASS_THROUGH",
            "cycle_index": 0,
        }
    ]
    data = adapt_d061_trace(trace, seed=22053, arm=arm, initial_state=initial)
    assert data.frames[1].action == f"{arm}: [0.5, -0.5]"
    assert [frame.transition_index for frame in data.frames] == [0, 100]
    html = build_development_html_replay(
        (data,), schema="aweform.d061.test.v1", title="D-061 test"
    )
    assert "D-061 seed 22053" in html
    assert '"transition":100' in html


def test_d061_u_arm_replays_the_seeded_d053_explorer() -> None:
    result = run_d061_lifetime(22053, "U", horizon=8)
    trace = result["trace"]
    assert isinstance(trace, list)
    assert trace[0]["symbolic_proposal"] in {"MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT"}
    assert D045_MAX_WHEEL_DELTA_RAD > 0
