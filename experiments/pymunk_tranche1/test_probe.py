from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

pytest.importorskip("pymunk")

from experiments.pymunk_tranche1.oracle import differential_drive_arc
from experiments.pymunk_tranche1.probe import (
    DT_SECONDS,
    ENCODER_QUANTUM_RAD,
    MAX_WHEEL_DELTA_RAD,
    PymunkProbe,
    quantize_encoder,
)

A = MAX_WHEEL_DELTA_RAD
B = A / 2.0
HEADINGS = (0.0, math.pi / 2.0, -math.pi / 2.0, math.pi)
XFAIL_REASON = (
    "frozen Tranche 1 gate FAIL preserved in "
    "experiments/pymunk_tranche1/results.json; see ADDENDUM.md"
)
COMMANDS = (
    ("zero", (0.0, 0.0)),
    ("forward", (A, A)),
    ("reverse", (-A, -A)),
    ("positive_spin", (-A, A)),
    ("negative_spin", (A, -A)),
    ("negative_yaw_arc", (A, B)),
    ("positive_yaw_arc", (B, A)),
)
CALIBRATION_CASES = [
    pytest.param(
        heading,
        amplitude,
        label,
        command,
        marks=(
            pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
            if label.endswith("yaw_arc") and amplitude > 0.25
            else ()
        ),
    )
    for label, command in COMMANDS
    for heading in HEADINGS
    for amplitude in (0.25, 0.5, 1.0)
]


@pytest.mark.parametrize(
    ("heading", "amplitude", "label", "command"), CALIBRATION_CASES
)
def test_frozen_one_interval_calibration(
    heading: float, amplitude: float, label: str, command: tuple[float, float]
) -> None:
    del label
    scaled = (amplitude * command[0], amplitude * command[1])
    probe = PymunkProbe()
    actual = probe.advance(scaled, heading=heading)
    expected_position, expected_heading = differential_drive_arc(
        (0.0, 0.0), heading, *scaled
    )
    assert probe.elapsed_seconds == DT_SECONDS
    assert math.dist(actual.position, expected_position) <= 1e-5
    assert abs(actual.heading - expected_heading) <= 1e-5
    assert actual.shaft_deltas == scaled


@pytest.mark.parametrize(
    ("heading", "command"),
    [
        pytest.param(
            heading, command, marks=pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
        )
        for heading in HEADINGS
        for command in ((A, 0.0), (0.0, A))
    ],
)
def test_one_wheel_stationary_calibration(
    heading: float, command: tuple[float, float]
) -> None:
    probe = PymunkProbe()
    actual = probe.advance(command, heading=heading)
    expected_position, expected_heading = differential_drive_arc(
        (0.0, 0.0), heading, *command
    )
    assert math.dist(actual.position, expected_position) <= 1e-5
    assert abs(actual.heading - expected_heading) <= 1e-5


@pytest.mark.parametrize(
    ("command", "expected"),
    [((2 * A, -3 * A), (A, -A)), ((-3 * A, 2 * A), (-A, A))],
)
def test_independent_clipping(
    command: tuple[float, float], expected: tuple[float, float]
) -> None:
    endpoint = PymunkProbe().advance(command)
    assert endpoint.shaft_deltas == expected


@pytest.mark.parametrize(
    "command",
    [
        (),
        (1.0,),
        (1.0, 2.0, 3.0),
        "12",
        ("bad", 0.0),
        (True, 0.0),
        (math.nan, 0.0),
        (0.0, math.inf),
        (-math.inf, 0.0),
    ],
)
def test_invalid_action_rejected_without_advancement(command: object) -> None:
    probe = PymunkProbe()
    with pytest.raises(ValueError):
        probe.advance(command)  # type: ignore[arg-type]
    assert probe.elapsed_seconds == 0.0
    assert tuple(probe.body.position) == (0.0, 0.0)


def test_tiny_signed_inputs_remain_unquantized_in_body_integration() -> None:
    command = (1e-15, -1e-15)
    endpoint = PymunkProbe().advance(command)
    assert endpoint.shaft_deltas == command
    assert endpoint.heading < 0.0
    assert endpoint.position == pytest.approx((0.0, 0.0), abs=1e-15)


@pytest.mark.parametrize(
    ("value", "expected_sign"),
    [
        (math.nextafter(0.5 * ENCODER_QUANTUM_RAD, 0.0), 0),
        (math.nextafter(0.5 * ENCODER_QUANTUM_RAD, math.inf), 1),
        (0.5 * ENCODER_QUANTUM_RAD, 1),
        (math.nextafter(-0.5 * ENCODER_QUANTUM_RAD, 0.0), 0),
        (math.nextafter(-0.5 * ENCODER_QUANTUM_RAD, -math.inf), -1),
        (-0.5 * ENCODER_QUANTUM_RAD, -1),
    ],
)
def test_encoder_half_quantum_boundaries(value: float, expected_sign: int) -> None:
    quantized = quantize_encoder(value)
    assert math.copysign(1.0, quantized) == (1.0 if expected_sign >= 0 else -1.0)
    assert abs(quantized) == abs(expected_sign) * ENCODER_QUANTUM_RAD


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
def test_known_vectors_and_pymunk_is_headless() -> None:
    assert "pygame" not in sys.modules
    forward = PymunkProbe().advance((A, A))
    assert forward.position == pytest.approx((0.029059732045705586, 0.0), abs=1e-5)
    positive_spin = PymunkProbe().advance((-A, A))
    negative_spin = PymunkProbe().advance((A, -A))
    assert positive_spin.heading == pytest.approx(math.pi / 10.0, abs=1e-5)
    assert negative_spin.heading == pytest.approx(-math.pi / 10.0, abs=1e-5)
    assert math.hypot(*positive_spin.position) <= 1e-5
    assert math.hypot(*negative_spin.position) <= 1e-5
    assert PymunkProbe().advance((0.0, 0.0)).position == (0.0, 0.0)
    results = json.loads(
        (Path(__file__).parent / "results.json").read_text(encoding="utf-8")
    )
    known_gate = next(
        gate for gate in results["gates"] if gate["id"] == "known-vectors"
    )
    assert known_gate["status"] == "PASS"


@pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
def test_reversal_swap_and_rotated_heading_symmetries() -> None:
    forward = PymunkProbe().advance((A, A))
    reverse = PymunkProbe().advance((-A, -A))
    assert reverse.position == pytest.approx(
        (-forward.position[0], -forward.position[1]), abs=1e-5
    )
    left = PymunkProbe().advance((A, B))
    right = PymunkProbe().advance((B, A))
    assert right.position == pytest.approx(left.position, abs=1e-5)
    assert right.heading == pytest.approx(-left.heading, abs=1e-5)
    rotated = PymunkProbe().advance((A, B), heading=math.pi / 2)
    assert rotated.position == pytest.approx(
        (-left.position[1], left.position[0]), abs=1e-5
    )
    assert rotated.heading == pytest.approx(left.heading + math.pi / 2, abs=1e-5)


def test_ten_versus_twenty_microstep_convergence() -> None:
    for _, command in COMMANDS:
        ten = PymunkProbe(microsteps=10).advance(command)
        twenty = PymunkProbe(microsteps=20).advance(command)
        assert math.dist(ten.position, twenty.position) <= 0.0001
        assert abs(ten.heading - twenty.heading) <= 1e-4
