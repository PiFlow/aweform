"""Model-free contracts for command-boundary persistent motor actuation."""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass
from pathlib import Path

from aweform.exp003_seed_policy import validate_exp003_development_seeds
from experiments.pymunk_contact_prototype.motor import (
    apply_persistent_curvature_force,
    begin_wheel_command,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "experiments/pymunk_contact_prototype/fixture.py"
FIXTURE_V4 = ROOT / "experiments/pymunk_contact_prototype/fixture_v4.py"
MOTOR = ROOT / "experiments/pymunk_contact_prototype/motor.py"
WORLD = ROOT / "experiments/pymunk230_obstacles/world.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _method(path: Path, name: str) -> ast.FunctionDef:
    return next(
        node
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _attribute_writes(method: ast.FunctionDef, attribute: str) -> list[ast.Assign]:
    return [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == attribute
            for target in node.targets
        )
    ]


def _top_level_step_loop(method: ast.FunctionDef) -> ast.For:
    return next(
        node
        for node in method.body
        if isinstance(node, ast.For)
        and isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Name)
        and node.iter.func.id == "range"
    )


def test_legacy_fixture_keeps_contact_flag_schedule_and_successor_is_versioned() -> (
    None
):
    fixture_tree = _tree(FIXTURE)
    v4_tree = _tree(FIXTURE_V4)
    legacy = next(
        node
        for node in fixture_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ContactWorld"
    )
    successor = next(
        node
        for node in v4_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ContactWorldV4"
    )
    assert "ContactWorld" in [
        base.id for base in successor.bases if isinstance(base, ast.Name)
    ]
    assert any(
        isinstance(node, ast.FunctionDef) and node.name == "_apply_motor_substep"
        for node in legacy.body
    )
    assert "_contact_seen_this_command" in ast.unparse(
        next(
            node
            for node in legacy.body
            if isinstance(node, ast.FunctionDef) and node.name == "_apply_motor_substep"
        )
    )
    assert not any(
        isinstance(node, ast.FunctionDef) and node.name == "advance"
        for node in successor.body
    )
    assert "suppress_velocity_refresh_after_contact=False" in ast.unparse(
        next(
            node
            for node in successor.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
    )


def test_successor_twist_is_set_once_before_substeps_and_never_contact_gated() -> None:
    advance = _method(FIXTURE, "advance")
    loop = _top_level_step_loop(advance)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_begin_motor_command"
        and node.lineno < loop.lineno
        for node in ast.walk(advance)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_apply_motor_substep"
        for node in ast.walk(loop)
    )
    successor_hook = _method(FIXTURE_V4, "_begin_motor_command")
    assert "begin_wheel_command" in ast.unparse(successor_hook)
    helper_begin = _method(MOTOR, "begin_wheel_command")
    assert len(_attribute_writes(helper_begin, "velocity")) == 1
    assert len(_attribute_writes(helper_begin, "angular_velocity")) == 1
    force_hook = _method(FIXTURE_V4, "_apply_motor_substep")
    assert "apply_persistent_curvature_force" in ast.unparse(force_hook)
    assert "_contact_seen_this_command" not in ast.unparse(force_hook)
    assert not _attribute_writes(force_hook, "velocity")
    callback = _method(FIXTURE, "_post_solve")
    assert not _attribute_writes(callback, "velocity")
    assert not _attribute_writes(callback, "angular_velocity")
    assert not _attribute_writes(callback, "force")


def test_obstacle_adapter_uses_shared_boundary_and_force_hooks_with_audits_intact() -> (
    None
):
    advance = _method(WORLD, "advance")
    loop = _top_level_step_loop(advance)
    assert "_begin_motor_command" in ast.unparse(advance)
    assert "_apply_motor_substep" in ast.unparse(loop)
    assert not any(
        isinstance(node, ast.If)
        and "_contact_seen_this_command" in ast.unparse(node.test)
        for node in ast.walk(advance)
    )
    assert "suppress_velocity_refresh_after_contact" not in ast.unparse(advance)
    assert "swept_crossing" in ast.unparse(advance)
    assert "self._contact_events" in ast.unparse(advance)


@dataclass
class _Body:
    angle: float = 0.0
    mass: float = 1.0
    velocity: tuple[float, float] = (0.0, 0.0)
    angular_velocity: float = 0.0
    force: tuple[float, float] = (0.0, 0.0)


def test_command_boundary_twist_and_persistent_force_for_all_wheel_modes() -> None:
    radius, track, duration = 0.045, 0.185, 0.1
    limit = 0.6457718232379019
    cases = (
        ((limit, limit), "straight"),
        ((-limit, -limit), "reverse"),
        ((limit, -limit), "spin"),
        ((limit, limit / 2), "mixed"),
    )
    for wheels, mode in cases:
        left, right = wheels
        speed = radius * (left + right) / (2 * duration)
        omega = radius * (right - left) / (track * duration)
        body = _Body(angle=0.37)
        begin_wheel_command(body, speed, omega, body.angle)
        command_velocity = body.velocity
        apply_persistent_curvature_force(body, omega)
        vx, vy = command_velocity
        assert body.velocity == command_velocity  # force law never overwrites v
        assert body.angular_velocity == omega
        assert body.force == (-body.mass * omega * vy, body.mass * omega * vx)
        if mode == "straight":
            assert omega == 0.0 and body.force == (0.0, 0.0)
        elif mode == "reverse":
            assert speed < 0 and omega == 0.0
        elif mode == "spin":
            assert speed == 0.0 and omega != 0.0 and body.force == (0.0, 0.0)
        else:
            assert speed != 0.0 and omega != 0.0 and body.force != (0.0, 0.0)


def test_prospective_space_step_budget_includes_probes_and_both_arms() -> None:
    declaration_path = (
        ROOT / "experiments/pymunk230_obstacles/exploratory-run-declaration.json"
    )
    declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    budget = declaration["space_step_budget"]
    safety_calls = budget["safety_probe_steps"]
    pair_calls = budget["paired_closed_loop_steps_at_maximum"]
    planned_calls = budget["planned_total"]
    hard_cap = budget["hard_total_cap"]
    assert safety_calls == 67_200
    assert pair_calls == 2_160_000
    assert planned_calls == safety_calls + pair_calls == 2_227_200
    assert planned_calls < hard_cap == 2_400_000
    assert declaration["paired_organism"]["seed"] == 23002
    assert validate_exp003_development_seeds([23002]) == (23002,)
    assert declaration["paired_organism"]["resolutions"] == [400, 800]
    assert declaration["paired_organism"]["logical_command_dt_s"] == 0.1


def test_persistent_centripetal_force_converges_for_forward_reverse_and_spin() -> None:
    # Explicit Euler integration of a = omega * J(v) is model-free: no Pymunk
    # Space, contact callback, or engine step is constructed here.
    for speed, omega in ((0.12, -1.1), (-0.08, 0.9)):
        duration = 0.1
        exact = (
            speed * math.sin(omega * duration) / omega,
            speed * (1 - math.cos(omega * duration)) / omega,
        )
        errors = []
        for steps in (400, 800):
            dt = duration / steps
            x = y = 0.0
            vx, vy = speed, 0.0
            theta = 0.0
            for _ in range(steps):
                # Persistent force changes velocity; it never assigns it.
                ax, ay = -omega * vy, omega * vx
                vx += ax * dt
                vy += ay * dt
                x += vx * dt
                y += vy * dt
                theta += omega * dt
            errors.append(math.hypot(x - exact[0], y - exact[1]))
            assert abs(theta - omega * duration) < 1e-12
        assert errors[1] < errors[0]
        assert errors[1] < 2e-5

    # Pure spin starts with zero linear speed; the held angular command alone
    # advances heading and the centripetal force remains exactly zero.
    speed, omega = 0.0, 2.0 * 0.045 * 0.6457718232379019 / 0.185 / 0.1
    vx = vy = x = y = theta = 0.0
    for _ in range(800):
        vx += -omega * vy * (0.1 / 800)
        vy += omega * vx * (0.1 / 800)
        x += vx * (0.1 / 800)
        y += vy * (0.1 / 800)
        theta += omega * (0.1 / 800)
    assert speed == 0.0 and x == y == vx == vy == 0.0
    assert math.isclose(theta, omega * 0.1, rel_tol=0.0, abs_tol=1e-12)
