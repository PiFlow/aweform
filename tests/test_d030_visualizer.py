"""Focused tests for the D-030 three-arm visualizer tooling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import aweform.d024 as d024
import aweform.d030 as d030
import aweform.development_visualizer as visualizer
from aweform.development_visualizer import (
    adapt_d030_trace,
    d030_main,
    show_d030_development_visualizations,
)


def _one_step_trace() -> tuple[object, ...]:
    trace: list[object] = []
    d024._run_d024_seed(18365, horizon=1, trace=trace)
    return tuple(trace)


def test_d030_trace_seam_is_branch_disabled_and_preserves_terminal_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_trace = _one_step_trace()
    calls: list[tuple[str, bool]] = []

    def fake_run(
        seed: int,
        *,
        arm: str,
        horizon: int,
        evaluator_diagnostics: bool,
        trace_sink: list[object] | None = None,
    ) -> dict[str, object]:
        del seed, horizon
        calls.append((arm, evaluator_diagnostics))
        assert trace_sink is not None
        trace_sink.extend(source_trace)
        return {"transitions": len(source_trace)}

    monkeypatch.setattr(d030, "_run_arm", fake_run)
    monkeypatch.setattr(d030, "D030_HORIZON", 1)
    trace = d030.run_d030_lifetime_trace(
        18428, arm="PERMUTED_FORWARD", horizon=1
    )

    assert trace == source_trace
    assert calls == [("PERMUTED_FORWARD", False)]


def test_d030_adapter_reuses_causal_finite_body_renderer() -> None:
    data = adapt_d030_trace(
        _one_step_trace(), seed=18428, arm="REFERENCE_NO_INFLUENCE"
    )

    assert data.source_label == (
        "D-030 REFERENCE_NO_INFLUENCE causal lifetime"
    )
    assert data.causal_geometry is not None
    assert data.causal_geometry.contact_tolerance == d024.D024_CONTACT_TOLERANCE


def test_d030_cli_passes_seed_and_frozen_horizon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []
    shown: list[tuple[object, int]] = []
    fake_data = tuple(
        SimpleNamespace(source_label=f"D-030 {arm} causal lifetime")
        for arm in d030.D030_ARM_NAMES
    )

    def fake_build(*, seed: int, horizon: int) -> tuple[object, ...]:
        calls.append((seed, horizon))
        return fake_data

    def fake_show(data: object, *, interval_ms: int) -> tuple[object, ...]:
        shown.append((data, interval_ms))
        return ()

    monkeypatch.setattr(visualizer, "build_d030_development_visualizations", fake_build)
    monkeypatch.setattr(visualizer, "show_d030_development_visualizations", fake_show)

    assert d030_main(["--seed", "18429", "--interval-ms", "123"]) == 0
    assert calls == [(18429, d030.D030_HORIZON)]
    assert shown == [(fake_data, 123)]


def test_d030_show_builds_three_figures_before_one_blocking_show(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tuple(
        SimpleNamespace(source_label=f"D-030 {arm} causal lifetime")
        for arm in d030.D030_ARM_NAMES
    )
    events: list[tuple[str, str]] = []

    def fake_build(item: object, *, interval_ms: int) -> tuple[str, str]:
        del interval_ms
        events.append(("build", item.source_label))
        return ("figure", item.source_label)

    def fake_show() -> None:
        events.append(("show", ""))

    monkeypatch.setattr(
        visualizer, "build_development_visualization_figure", fake_build
    )
    monkeypatch.setattr(visualizer.plt, "show", fake_show)

    figures = show_d030_development_visualizations(data, interval_ms=1)

    assert figures == (
        "figure",
        "figure",
        "figure",
    )
    assert [kind for kind, _ in events] == ["build", "build", "build", "show"]
    assert [label for kind, label in events if kind == "build"] == [
        item.source_label for item in data
    ]
