"""Model-free contract checks for the attempt-4 motor schedule."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = (
    ROOT / "experiments/pymunk_contact_prototype/fixture.py",
    ROOT / "experiments/pymunk230_obstacles/world.py",
)


def _method(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
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


def test_each_adapter_sets_command_twist_once_before_substeps() -> None:
    for path in ADAPTERS:
        advance = _method(path, "advance")
        velocity = _attribute_writes(advance, "velocity")
        angular = _attribute_writes(advance, "angular_velocity")
        loops = [
            node
            for node in advance.body
            if isinstance(node, ast.For)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        ]
        assert len(velocity) == len(angular) == len(loops) == 1
        assert velocity[0].lineno < loops[0].lineno
        assert angular[0].lineno < loops[0].lineno
        source = ast.unparse(advance)
        assert "suppress_velocity_refresh_after_contact" not in source
        assert not any(
            isinstance(node, ast.If)
            and "_contact_seen_this_command" in ast.unparse(node.test)
            for node in ast.walk(advance)
        )


def test_callbacks_collect_contacts_without_motor_control() -> None:
    callback = _method(ADAPTERS[0], "_post_solve")
    callback_source = ast.unparse(callback)
    assert "_contact_seen_this_command = True" in callback_source
    assert not _attribute_writes(callback, "velocity")
    assert not _attribute_writes(callback, "angular_velocity")
    obstacle_advance = ast.unparse(_method(ADAPTERS[1], "advance"))
    assert "self._contact_events" in obstacle_advance
    assert "swept_crossing" in obstacle_advance


def test_reset_and_contact_flag_are_diagnostic_only() -> None:
    fixture = ADAPTERS[0]
    reset = ast.unparse(_method(fixture, "reset"))
    callback = ast.unparse(_method(fixture, "_post_solve"))
    assert "fresh.__dict__" in reset
    assert "_contact_seen_this_command" in callback
    # The flag is retained/reset for diagnostics, not consulted by either schedule.
    for path in ADAPTERS:
        assert not any(
            isinstance(node, ast.If)
            and "_contact_seen_this_command" in ast.unparse(node.test)
            for node in ast.walk(_method(path, "advance"))
        )
