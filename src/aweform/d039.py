"""D-039 shadow-only one-scalar recurrent predictor readiness audit.

The accepted D-031R1 Arm-B lifetime is executed unchanged.  A local wrapper
records the unchanged pre-update D-027 prediction for the actually executed
action and maintains one evaluator-only scalar, ``h``.  The wrapper never
passes ``h`` to the controller, D-027, the environment, RNG, reward, or info.
All other work in this module is post-hoc analysis of the completed trace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final, cast
from unittest.mock import patch

import numpy as np

from . import d025, d026, d027, d031r1, d032, d033, d034, d036
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D039_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D039_HORIZON: Final[int] = 70_000
D039_TARGET_HORIZONS: Final[tuple[int, ...]] = (64, 256, 1024)
D039_FIXED_ALPHA: Final[float] = d036.D036_FIXED_ALPHA
D039_RECURRENCE_ALPHA: Final[float] = d027.D027_LEARNING_RATE
D039_BRIDGE_FAMILIES: Final[tuple[str, ...]] = ("ALT", "NO_FORWARD_PROGRESS")
D039_BRIDGE_LENGTHS: Final[tuple[int, ...]] = (4, 8, 16)
D039_OSCILLATION_MIN_RUN: Final[int] = 16
D039_OSCILLATION_WINDOWS: Final[tuple[tuple[str, int], ...]] = (
    ("before", -16),
    ("at", 0),
    ("after", 16),
)
D039_ACCEPTED_D031R1_ARTIFACT: Final[str] = d033.D033_ACCEPTED_D031R1_ARTIFACT

_FORWARD_INDEX: Final[int] = d027.D027_OUTPUTS.index("delta_beacon_forward")
_ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.name for action in Action)
_MODES: Final[tuple[str, ...]] = tuple(mode.name for mode in d026.D026Mode)


def _validate_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D039_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-039 requires exactly the reused development seeds "
            f"{D039_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D039_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-039 may execute only the reused development seeds "
            f"{D039_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str:
    if (
        value is None
        or len(value) != 40
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError(
            "D-039 official output requires an exact clean executable protocol SHA"
        )
    return value


def _number_summary(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {
            "sample_count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
        }
    ordered = sorted(float(value) for value in values)
    return {
        "sample_count": len(ordered),
        "minimum": min(ordered),
        "maximum": max(ordered),
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
    }


def _correlation(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if (
        len(actual) < 2
        or float(np.std(actual)) == 0.0
        or float(np.std(predicted)) == 0.0
    ):
        return None
    return float(np.corrcoef(actual, predicted)[0, 1])


def _visible(observation: d027.D027Observation) -> tuple[float, ...]:
    return (
        observation.energy,
        observation.beacon.left,
        observation.beacon.forward,
        observation.beacon.right,
        float(observation.charging_contact),
        observation.thermal,
    )


@dataclass(slots=True)
class _Pending:
    transition: int
    h_before: float
    mode_before: d026.D026Mode
    action: Action | None = None


@dataclass(frozen=True, slots=True)
class _ScalarStep:
    transition: int
    h_before: float
    h_after: float
    baseline_prediction: float
    recurrent_prediction: float
    observed_delta: float
    action: Action
    mode_before: d026.D026Mode


class _Instrumentation:
    def __init__(self) -> None:
        self.h = 0.0
        self.pending: _Pending | None = None
        self.steps: list[_ScalarStep] = []
        self.transition_count = 0
        self.update_count = 0
        self.initialization_count = 1
        self.recurrence_equivalence_checks = 0

    def begin_decision(
        self, controller: d026.D026Controller, observation: d027.D027Observation
    ) -> None:
        if self.pending is not None:
            raise RuntimeError("D-039 decision remained pending across transitions")
        self.pending = _Pending(
            transition=self.transition_count + 1,
            h_before=self.h,
            mode_before=controller.mode,
        )
        if not math.isfinite(self.h):
            raise RuntimeError("D-039 recurrent scalar became non-finite")
        if not isinstance(observation, d027.D027Observation):
            raise RuntimeError("D-039 received a non-visible observation")

    def finish_decision(self, action: Action) -> None:
        if self.pending is None:
            raise RuntimeError("D-039 action was not preceded by a decision capture")
        self.pending.action = action

    def record_transition(
        self,
        predictor: d027.D027ActionConsequencePredictor,
        observation: d027.D027Observation,
        next_observation: d027.D027Observation,
    ) -> d027.D027Prediction:
        pending = self.pending
        if pending is None or pending.action is None:
            raise RuntimeError("D-039 update was not paired with the executed action")
        if pending.transition != self.transition_count + 1:
            raise RuntimeError("D-039 transition timing diverged")
        prediction = predictor.predict(observation, pending.action)
        observed_delta = next_observation.beacon.forward - observation.beacon.forward
        p = prediction.values[_FORWARD_INDEX]
        h_before = pending.h_before
        recurrent = p + h_before
        direct = h_before + D039_RECURRENCE_ALPHA * (observed_delta - recurrent)
        equivalent = (
            1.0 - D039_RECURRENCE_ALPHA
        ) * h_before + D039_RECURRENCE_ALPHA * (observed_delta - p)
        if not math.isclose(direct, equivalent, rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError("D-039 recurrence forms diverged")
        self.recurrence_equivalence_checks += 1
        self.h = direct
        self.steps.append(
            _ScalarStep(
                transition=pending.transition,
                h_before=h_before,
                h_after=self.h,
                baseline_prediction=p,
                recurrent_prediction=recurrent,
                observed_delta=observed_delta,
                action=pending.action,
                mode_before=pending.mode_before,
            )
        )
        self.pending = None
        return prediction


class _D039Learner(d027.D027ActionConsequencePredictor):
    instrumentation: ClassVar[_Instrumentation | None] = None

    def __init__(self) -> None:
        super().__init__()
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-039 learner instrumentation was not initialized")
        self._d039_instrumentation = instrumentation

    def observe_transition(
        self,
        observation: d027.D027Observation,
        action: Action,
        next_observation: d027.D027Observation,
    ) -> d027.D027LearningUpdate:
        instrumentation = self._d039_instrumentation
        prediction = instrumentation.record_transition(
            self, observation, next_observation
        )
        update = super().observe_transition(observation, action, next_observation)
        if (
            update.action is not action
            or update.prediction[_FORWARD_INDEX] != prediction.values[_FORWARD_INDEX]
        ):
            raise RuntimeError("D-039 changed the executed-action D-027 update")
        instrumentation.update_count += 1
        instrumentation.transition_count += 1
        return update


class _D039Controller(d026.D026Controller):
    instrumentation: ClassVar[_Instrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-039 controller instrumentation was not initialized")
        instrumentation.begin_decision(self, observation)
        action = super().act(observation)
        instrumentation.finish_decision(action)
        return action


class _D039NoDetrapController(d031r1.D031R1NoDetrapController):
    instrumentation: ClassVar[_Instrumentation | None] = None

    def act(self, observation: d027.D027Observation) -> Action:
        instrumentation = type(self).instrumentation
        if instrumentation is None:
            raise RuntimeError("D-039 no-detrap instrumentation was not initialized")
        instrumentation.begin_decision(self, observation)
        action = super().act(observation)
        instrumentation.finish_decision(action)
        return action


def _run_shadow_arm(
    seed: int, *, horizon: int, trace: list[d025.D025TransitionTrace]
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...], _Instrumentation]:
    instrumentation = _Instrumentation()
    original_initial_environment = d031r1._initial_environment
    _D039Controller.instrumentation = instrumentation
    _D039NoDetrapController.instrumentation = instrumentation
    _D039Learner.instrumentation = instrumentation

    def initial_environment(
        requested_horizon: int, requested_seed: int
    ) -> tuple[d026.D026Env, np.ndarray, object]:
        return original_initial_environment(requested_horizon, requested_seed)

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(d031r1, "_initial_environment", initial_environment)
        )
        stack.enter_context(patch.object(d026, "D026Controller", _D039Controller))
        stack.enter_context(
            patch.object(d031r1, "D031R1NoDetrapController", _D039NoDetrapController)
        )
        stack.enter_context(
            patch.object(d027, "D027ActionConsequencePredictor", _D039Learner)
        )
        result = d031r1._run_arm(
            seed,
            arm="LEARNED_NO_DETRAP",
            horizon=horizon,
            evaluator_diagnostics=True,
            trace_sink=trace,
            seed_validator=_validate_seed,
        )
    _D039Controller.instrumentation = None
    _D039NoDetrapController.instrumentation = None
    _D039Learner.instrumentation = None
    if instrumentation.pending is not None:
        raise RuntimeError("D-039 left a pending pre-action state")
    if (
        instrumentation.update_count != result["transitions"]
        or instrumentation.transition_count != result["transitions"]
    ):
        raise RuntimeError("D-039 instrumentation transition/update count diverged")
    if len(instrumentation.steps) != len(trace):
        raise RuntimeError("D-039 scalar trace length diverged from causal trace")
    return result, tuple(trace), instrumentation


@dataclass(frozen=True, slots=True)
class _TraceData:
    seed: int
    trace: tuple[d025.D025TransitionTrace, ...]
    trace_digest: str
    visible_before: np.ndarray
    visible_after: np.ndarray
    visible_after_forward: np.ndarray
    actions: np.ndarray
    eligible: np.ndarray
    reacquisition: np.ndarray
    terminated: bool
    truncated: bool
    h_before: np.ndarray
    h_after: np.ndarray
    baseline_prediction: np.ndarray
    recurrent_prediction: np.ndarray
    observed_delta: np.ndarray


def _trace_data(
    seed: int,
    trace: tuple[d025.D025TransitionTrace, ...],
    instrumentation: _Instrumentation,
) -> _TraceData:
    base = d036._trace_data(seed, trace)
    steps = instrumentation.steps
    if len(steps) != len(trace):
        raise RuntimeError("D-039 scalar and trace supports differ")
    return _TraceData(
        seed=seed,
        trace=trace,
        trace_digest=base.trace_digest,
        visible_before=base.visible_before,
        visible_after=cast(np.ndarray, base.visible_after),
        visible_after_forward=base.visible_after_forward,
        actions=base.actions,
        eligible=base.eligible,
        reacquisition=base.reacquisition,
        terminated=base.terminated,
        truncated=base.truncated,
        h_before=np.asarray([step.h_before for step in steps], dtype=float),
        h_after=np.asarray([step.h_after for step in steps], dtype=float),
        baseline_prediction=np.asarray(
            [step.baseline_prediction for step in steps], dtype=float
        ),
        recurrent_prediction=np.asarray(
            [step.recurrent_prediction for step in steps], dtype=float
        ),
        observed_delta=np.asarray([step.observed_delta for step in steps], dtype=float),
    )


def _error_summary(data: _TraceData, indices: np.ndarray) -> dict[str, object]:
    baseline_signed = data.baseline_prediction[indices] - data.observed_delta[indices]
    recurrent_signed = data.recurrent_prediction[indices] - data.observed_delta[indices]
    baseline_abs = np.abs(baseline_signed)
    recurrent_abs = np.abs(recurrent_signed)
    return {
        "sample_count": int(len(indices)),
        "baseline_mae": float(np.mean(baseline_abs)) if len(indices) else None,
        "recurrent_mae": float(np.mean(recurrent_abs)) if len(indices) else None,
        "recurrent_minus_baseline_mae": float(np.mean(recurrent_abs - baseline_abs))
        if len(indices)
        else None,
        "baseline_signed_error_mean": float(np.mean(baseline_signed))
        if len(indices)
        else None,
        "recurrent_signed_error_mean": float(np.mean(recurrent_signed))
        if len(indices)
        else None,
        "baseline_signed_error": _number_summary(baseline_signed.tolist()),
        "recurrent_signed_error": _number_summary(recurrent_signed.tolist()),
    }


def _one_step_summary(data: _TraceData) -> dict[str, object]:
    all_indices = np.arange(len(data.trace), dtype=np.int64)
    by_seed = _error_summary(data, all_indices)
    strata: dict[str, dict[str, object]] = {}
    strata["false_contact_seek"] = _error_summary(data, np.flatnonzero(data.eligible))
    for mode in _MODES:
        indices = np.asarray(
            [
                index
                for index, row in enumerate(data.trace)
                if row.mode_before.name == mode
            ],
            dtype=np.int64,
        )
        strata[f"mode_before:{mode}"] = _error_summary(data, indices)
    for quarter_index in range(4):
        start = quarter_index * d027.D027_WINDOW_SIZE
        stop = min((quarter_index + 1) * d027.D027_WINDOW_SIZE, len(data.trace))
        strata[f"lifetime_quarter:Q{quarter_index + 1}"] = _error_summary(
            data, np.arange(start, stop, dtype=np.int64)
        )
    for action in Action:
        indices = np.flatnonzero(data.actions == list(Action).index(action))
        strata[f"action:{action.name}"] = _error_summary(data, indices)
    delta = cast(float | None, by_seed["recurrent_minus_baseline_mae"])
    return {
        "all_transitions": by_seed,
        "strata": strata,
        "h": {
            "start": 0.0,
            "minimum_pre_action": float(np.min(data.h_before))
            if len(data.h_before)
            else None,
            "maximum_pre_action": float(np.max(data.h_before))
            if len(data.h_before)
            else None,
            "minimum_post_update": float(np.min(data.h_after))
            if len(data.h_after)
            else None,
            "maximum_post_update": float(np.max(data.h_after))
            if len(data.h_after)
            else None,
            "final": float(data.h_after[-1]) if len(data.h_after) else 0.0,
            "all_finite": bool(
                np.all(np.isfinite(data.h_before)) and np.all(np.isfinite(data.h_after))
            ),
        },
        "within_seed_sign": "improved"
        if delta is not None and delta < 0.0
        else "worsened"
        if delta is not None and delta > 0.0
        else "tie",
    }


def _pooled_error_summary(data_by_seed: dict[int, _TraceData]) -> dict[str, object]:
    merged = np.concatenate(
        [np.arange(len(data.trace), dtype=np.int64) for data in data_by_seed.values()]
    )
    baseline = np.concatenate(
        [data.baseline_prediction for data in data_by_seed.values()]
    )
    recurrent = np.concatenate(
        [data.recurrent_prediction for data in data_by_seed.values()]
    )
    observed = np.concatenate([data.observed_delta for data in data_by_seed.values()])
    pooled = _TraceData(
        seed=0,
        trace=tuple(),
        trace_digest="",
        visible_before=np.empty((len(observed), 6)),
        visible_after=np.empty((len(observed), 6)),
        visible_after_forward=np.empty(len(observed)),
        actions=np.zeros(len(observed), dtype=np.int8),
        eligible=np.zeros(len(observed), dtype=bool),
        reacquisition=np.zeros(len(observed), dtype=bool),
        terminated=False,
        truncated=False,
        h_before=np.zeros(len(observed)),
        h_after=np.zeros(len(observed)),
        baseline_prediction=baseline,
        recurrent_prediction=recurrent,
        observed_delta=observed,
    )
    return _error_summary(pooled, merged)


def _feature_rows(data: _TraceData, indices: np.ndarray, with_h: bool) -> np.ndarray:
    s0 = np.asarray(data.visible_before[indices], dtype=float)
    if with_h:
        return np.concatenate((s0, data.h_before[indices, None]), axis=1)
    return s0


def _fit_ridge(features: np.ndarray, target: np.ndarray) -> np.ndarray:
    design = np.concatenate((np.ones((len(features), 1)), features), axis=1)
    xx = design.T @ design
    xy = design.T @ target
    penalty = np.eye(xx.shape[0]) * D039_FIXED_ALPHA
    penalty[0, 0] = 0.0
    return np.linalg.solve(xx + penalty, xy)


def _predict_ridge(features: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    prediction = (
        np.concatenate((np.ones((len(features), 1)), features), axis=1) @ coefficients
    )
    return np.asarray(prediction, dtype=float)


def _binary_metrics(actual: np.ndarray, probability: np.ndarray) -> dict[str, object]:
    if len(actual) == 0 or len(np.unique(actual)) < 2:
        return {
            "status": "untestable_class_support",
            "sample_count": 0,
            "brier_score": None,
            "balanced_accuracy": None,
            "auroc": None,
        }
    predicted = probability >= 0.5
    balanced = float(
        np.mean([np.mean(predicted[actual == label] == label) for label in (0.0, 1.0)])
    )
    return {
        "status": "fit",
        "sample_count": int(len(actual)),
        "brier_score": float(np.mean((probability - actual) ** 2)),
        "balanced_accuracy": balanced,
        "auroc": d036._auroc(actual, probability),
    }


def _evaluate_horizon(
    data_by_seed: dict[int, _TraceData], horizon: int
) -> dict[str, object]:
    targets = {
        seed: d036._target_data(cast(d036._TraceData, data), 1, horizon)
        for seed, data in data_by_seed.items()
    }
    folds: list[dict[str, object]] = []
    for held_out in D039_DEFAULT_DEVELOPMENT_SEEDS:
        target = targets[held_out]
        fold: dict[str, object] = {
            "held_out_seed": held_out,
            "s0_sample_count": int(len(target.indices)),
            "s0_plus_h_sample_count": int(len(target.indices)),
            "identical_support": True,
            "target_status_counts": target.status_counts,
            "target_class_balance": {
                "negative": int(np.sum(~target.reacquired)),
                "positive": int(np.sum(target.reacquired)),
            },
            "models": {},
        }
        models = cast(dict[str, object], fold["models"])
        for name, with_h in (("S0", False), ("S0_PLUS_H", True)):
            train_x = np.concatenate(
                [
                    _feature_rows(data_by_seed[seed], targets[seed].indices, with_h)
                    for seed in D039_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ],
                axis=0,
            )
            train_y = np.concatenate(
                [
                    targets[seed].progress
                    for seed in D039_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ]
            )
            prediction = _predict_ridge(
                _feature_rows(data_by_seed[held_out], target.indices, with_h),
                _fit_ridge(train_x, train_y),
            )
            mae = (
                float(np.mean(np.abs(prediction - target.progress)))
                if len(target.progress)
                else None
            )
            model: dict[str, object] = {
                "feature_dimension": int(train_x.shape[1]),
                "selected_alpha": D039_FIXED_ALPHA,
                "progress": {
                    "sample_count": int(len(target.progress)),
                    "mae": mae,
                    "correlation": _correlation(target.progress, prediction),
                },
            }
            train_classes = np.concatenate(
                [
                    targets[seed].reacquired.astype(float)
                    for seed in D039_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ]
            )
            if len(np.unique(train_classes)) < 2:
                model["reacquisition"] = _binary_metrics(np.asarray([]), np.asarray([]))
            else:
                class_prediction = 1.0 / (
                    1.0
                    + np.exp(
                        -np.clip(
                            _predict_ridge(
                                _feature_rows(
                                    data_by_seed[held_out], target.indices, with_h
                                ),
                                _fit_ridge(train_x, train_classes),
                            ),
                            -40.0,
                            40.0,
                        )
                    )
                )
                model["reacquisition"] = _binary_metrics(
                    target.reacquired.astype(float), class_prediction
                )
            models[name] = model
        s0_mae = cast(
            dict[str, object], cast(dict[str, object], models["S0"])["progress"]
        )["mae"]
        h_mae = cast(
            dict[str, object], cast(dict[str, object], models["S0_PLUS_H"])["progress"]
        )["mae"]
        typed_s0_mae = cast(float | None, s0_mae)
        typed_h_mae = cast(float | None, h_mae)
        fold["paired_mae_delta"] = (
            typed_h_mae - typed_s0_mae
            if typed_s0_mae is not None and typed_h_mae is not None
            else None
        )
        folds.append(fold)
    deltas = [
        cast(float, fold["paired_mae_delta"])
        for fold in folds
        if fold["paired_mae_delta"] is not None
    ]
    model_summaries: dict[str, object] = {}
    for name in ("S0", "S0_PLUS_H"):
        records = [
            cast(dict[str, object], cast(dict[str, object], fold["models"])[name])[
                "progress"
            ]
            for fold in folds
        ]
        maes = [
            cast(float, cast(dict[str, object], record)["mae"])
            for record in records
            if cast(dict[str, object], record)["mae"] is not None
        ]
        correlations = [
            cast(float, cast(dict[str, object], record)["correlation"])
            for record in records
            if cast(dict[str, object], record)["correlation"] is not None
        ]
        model_summaries[name] = {
            "fold_count": len(records),
            "mean_held_out_mae": float(np.mean(maes)) if maes else None,
            "mean_held_out_correlation": float(np.mean(correlations))
            if correlations
            else None,
        }
    return {
        "horizon": horizon,
        "fixed_alpha": D039_FIXED_ALPHA,
        "folds": folds,
        "pooled": {
            **model_summaries,
            "mean_paired_s0_plus_h_minus_s0_mae": float(np.mean(deltas))
            if deltas
            else None,
            "improvement_count": sum(delta < 0.0 for delta in deltas),
            "worsening_count": sum(delta > 0.0 for delta in deltas),
            "tie_count": sum(delta == 0.0 for delta in deltas),
        },
    }


def _matched_index(
    data: _TraceData, anchor_index: int, excluded: set[int]
) -> int | None:
    candidates = [
        int(index)
        for index in np.flatnonzero(data.eligible).tolist()
        if int(index) not in excluded
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda index: (
            float(
                np.sum(
                    (data.visible_before[index] - data.visible_before[anchor_index])
                    ** 2
                )
            ),
            index,
        ),
    )


def _anchor_records(data_by_seed: dict[int, _TraceData]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for seed in D039_DEFAULT_DEVELOPMENT_SEEDS:
        data = data_by_seed[seed]
        selections: list[tuple[str, int, d034._TriggerSelection | None]] = []
        anchor_indices: set[int] = set()
        for family in D039_BRIDGE_FAMILIES:
            for length in D039_BRIDGE_LENGTHS:
                selection = d034._find_trigger(data.trace, family, length)
                index = (
                    d036._anchor_index(data.trace, selection)
                    if selection is not None
                    else None
                )
                if index is not None:
                    anchor_indices.add(index)
                selections.append((family, length, selection))
        for family, length, selection in selections:
            index = (
                d036._anchor_index(data.trace, selection)
                if selection is not None
                else None
            )
            record: dict[str, object] = {
                "seed": seed,
                "family": family,
                "length": length,
                "status": "anchor_available"
                if index is not None
                else "anchor_unavailable",
                "d034_label_used_in_h_update": False,
                "d034_outcome_used_in_h_update": False,
                "s0_only_matching": True,
            }
            if index is None:
                records.append(record)
                continue
            matched = _matched_index(data, index, anchor_indices)
            record.update(
                {
                    "anchor_trace_index": index,
                    "anchor_transition": data.trace[index].transition_index,
                    "anchor_h": float(data.h_before[index]),
                }
            )
            if matched is None:
                record["matched_non_anchor_status"] = "unavailable"
            else:
                delta = float(data.h_before[index] - data.h_before[matched])
                record.update(
                    {
                        "matched_non_anchor_status": "matched",
                        "matched_trace_index": matched,
                        "matched_transition": data.trace[matched].transition_index,
                        "matched_h": float(data.h_before[matched]),
                        "anchor_minus_matched_h": delta,
                        "contrast": "positive"
                        if delta > 0.0
                        else "negative"
                        if delta < 0.0
                        else "tie",
                    }
                )
            records.append(record)
    return records


def _summary_by_key(records: list[dict[str, object]], key: str) -> dict[str, object]:
    out: dict[str, object] = {}
    groups = sorted({str(record[key]) for record in records})
    for group in groups:
        available = [
            record
            for record in records
            if str(record[key]) == group
            and record.get("matched_non_anchor_status") == "matched"
        ]
        deltas = [
            float(cast(float, record["anchor_minus_matched_h"])) for record in available
        ]
        out[group] = {
            "paired_count": len(deltas),
            "delta_summary": _number_summary(deltas),
            "positive_count": sum(value > 0.0 for value in deltas),
            "negative_count": sum(value < 0.0 for value in deltas),
            "tie_count": sum(value == 0.0 for value in deltas),
        }
    return out


def _anchor_summary(records: list[dict[str, object]]) -> dict[str, object]:
    matched = [
        record
        for record in records
        if record.get("matched_non_anchor_status") == "matched"
    ]
    deltas = [
        float(cast(float, record["anchor_minus_matched_h"])) for record in matched
    ]
    return {
        "availability": {
            "record_count": len(records),
            "anchor_available_count": sum(
                record["status"] == "anchor_available" for record in records
            ),
            "matched_count": len(matched),
            "matched_unavailable_count": sum(
                record.get("matched_non_anchor_status") == "unavailable"
                for record in records
            ),
        },
        "by_family": _summary_by_key(records, "family"),
        "by_length": _summary_by_key(records, "length"),
        "pooled": {
            "paired_count": len(deltas),
            "delta_summary": _number_summary(deltas),
            "positive_count": sum(value > 0.0 for value in deltas),
            "negative_count": sum(value < 0.0 for value in deltas),
            "tie_count": sum(value == 0.0 for value in deltas),
        },
        "matching_rule": (
            "Same-seed ordinary eligible non-anchor state minimizing squared "
            "distance on current S0 only; smallest trace index tie-break; every "
            "D-034 anchor excluded."
        ),
    }


def _oscillation_onset(data: _TraceData) -> tuple[int, int] | None:
    turns = {Action.TURN_LEFT, Action.TURN_RIGHT}
    eligible = set(np.flatnonzero(data.eligible).tolist())
    actions = [row.action for row in data.trace]
    for start in np.flatnonzero(data.eligible).tolist():
        if actions[start] not in turns:
            continue
        end = start
        while (
            end + 1 in eligible
            and actions[end + 1] in turns
            and actions[end + 1] is not actions[end]
        ):
            end += 1
        if end - start + 1 >= D039_OSCILLATION_MIN_RUN:
            return start, end - start + 1
    return None


def _window_record(data: _TraceData, start: int, offset: int) -> dict[str, object]:
    indices = list(range(start + offset, start + offset + 16))
    if any(
        index < 0 or index >= len(data.trace) or not data.eligible[index]
        for index in indices
    ):
        return {"status": "unavailable"}
    values = data.h_before[np.asarray(indices, dtype=np.int64)]
    return {
        "status": "available",
        "start_trace_index": indices[0],
        "summary": _number_summary(values.tolist()),
    }


def _oscillation_records(
    data_by_seed: dict[int, _TraceData],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for seed in D039_DEFAULT_DEVELOPMENT_SEEDS:
        data = data_by_seed[seed]
        onset = _oscillation_onset(data)
        if onset is None:
            records.append({"seed": seed, "status": "onset_unavailable"})
            continue
        start, run_length = onset
        run_indices = set(range(start, start + run_length))
        matched = _matched_index(data, start, run_indices)
        record: dict[str, object] = {
            "seed": seed,
            "status": "onset_available",
            "onset_trace_index": start,
            "onset_transition": data.trace[start].transition_index,
            "run_length": run_length,
            "windows": {
                label: _window_record(data, start, offset)
                for label, offset in D039_OSCILLATION_WINDOWS
            },
            "matched_control_status": "matched"
            if matched is not None
            else "unavailable",
        }
        if matched is not None:
            record.update(
                {
                    "matched_control_trace_index": matched,
                    "matched_control_transition": data.trace[matched].transition_index,
                    "onset_h": float(data.h_before[start]),
                    "matched_control_h": float(data.h_before[matched]),
                    "onset_minus_matched_h": float(
                        data.h_before[start] - data.h_before[matched]
                    ),
                    "contrast": "positive"
                    if data.h_before[start] > data.h_before[matched]
                    else "negative"
                    if data.h_before[start] < data.h_before[matched]
                    else "tie",
                }
            )
        records.append(record)
    return records


def _oscillation_summary(records: list[dict[str, object]]) -> dict[str, object]:
    windows: dict[str, object] = {}
    for label, _ in D039_OSCILLATION_WINDOWS:
        values: list[float] = []
        for record in records:
            if record.get("status") != "onset_available":
                continue
            window = cast(
                dict[str, object], cast(dict[str, object], record["windows"])[label]
            )
            if window.get("status") != "available":
                continue
            summary = cast(dict[str, object], window["summary"])
            values.append(float(cast(float, summary["mean"])))
        windows[label] = {
            "status": "available" if values else "unavailable",
            "seed_window_count": len(values),
            "h_mean_summary": _number_summary(values),
        }
    deltas = [
        float(cast(float, record["onset_minus_matched_h"]))
        for record in records
        if record.get("matched_control_status") == "matched"
    ]
    return {
        "definition": (
            "First contiguous ordinary Arm-B run of at least 16 eligible "
            "false-contact SEEK decisions whose executed actions strictly "
            "alternate left/right; onset is the first action."
        ),
        "availability": {
            "seed_count": len(records),
            "onset_available_count": sum(
                record.get("status") == "onset_available" for record in records
            ),
            "matched_control_available_count": len(deltas),
        },
        "windows": windows,
        "onset_minus_matched_control": {
            "paired_count": len(deltas),
            "delta_summary": _number_summary(deltas),
            "positive_count": sum(value > 0.0 for value in deltas),
            "negative_count": sum(value < 0.0 for value in deltas),
            "tie_count": sum(value == 0.0 for value in deltas),
        },
    }


def _replay_for_seed(
    seed: int, accepted: dict[str, object]
) -> tuple[dict[str, object], _TraceData, dict[str, object]]:
    trace: list[d025.D025TransitionTrace] = []
    result, b_trace, instrumentation = _run_shadow_arm(
        seed, horizon=D039_HORIZON, trace=trace
    )
    expected = dict(d033._accepted_arm(accepted, seed, "LEARNED_NO_DETRAP"))
    expected["_weights"] = d033._flatten_final_weights(expected)
    comparison = d032._compare_identity_fields(
        result, expected, include_private_weights=True
    )
    if not bool(comparison["all_identity_fields_exact"]):
        raise RuntimeError(
            "D-039 accepted Arm-B replay gate failed for "
            f"{seed}: {comparison['mismatched_fields']}"
        )
    gate = {
        "seed": seed,
        "arm": "LEARNED_NO_DETRAP",
        "all_identity_fields_exact": True,
        "checked_identity_fields": comparison["checked_fields"],
        "mismatched_identity_fields": comparison["mismatched_fields"],
        "zero_false_contact_seek_delegation": cast(
            dict[str, object], result["isolation"]
        )["zero_false_contact_seek_delegation"],
        "zero_false_contact_seek_explorer_calls": cast(
            dict[str, object], result["isolation"]
        )["no_false_contact_seek_explorer_call"],
        "one_legacy_arbitration_draw_per_false_contact_seek_decision": cast(
            dict[str, object], result["isolation"]
        )["one_legacy_arbitration_draw_per_false_contact_seek_decision"],
    }
    if not all(
        bool(gate[key])
        for key in (
            "zero_false_contact_seek_delegation",
            "zero_false_contact_seek_explorer_calls",
            "one_legacy_arbitration_draw_per_false_contact_seek_decision",
        )
    ):
        raise RuntimeError(f"D-039 Arm-B boundary gate failed for {seed}")
    return result, _trace_data(seed, b_trace, instrumentation), gate


def _interpretation(
    one_step: dict[str, object],
    evaluations: Mapping[str, object],
    anchor: dict[str, object],
    oscillation: dict[str, object],
) -> list[str]:
    signs = cast(dict[str, int], one_step["within_seed_sign_counts"])
    predictive_one_step = (
        signs["improved"] > signs["worsened"] and signs["improved"] >= signs["tie"]
    )
    loso_deltas: list[float | None] = []
    for evaluation in evaluations.values():
        pooled = cast(dict[str, object], cast(dict[str, object], evaluation)["pooled"])
        loso_deltas.append(
            cast(float | None, pooled["mean_paired_s0_plus_h_minus_s0_mae"])
        )
    predictive_loso = bool(loso_deltas) and all(
        delta is not None and delta < 0.0 for delta in loso_deltas
    )
    predictive = predictive_one_step or predictive_loso
    anchor_pooled = cast(dict[str, object], anchor["pooled"])
    onset_pooled = cast(dict[str, object], oscillation["onset_minus_matched_control"])
    coherence = (
        int(cast(int, anchor_pooled["positive_count"]))
        > int(cast(int, anchor_pooled["negative_count"]))
        or int(cast(int, onset_pooled["positive_count"]))
        > int(cast(int, onset_pooled["negative_count"]))
    ) and (
        int(cast(int, anchor_pooled["paired_count"])) > 0
        or int(cast(int, onset_pooled["paired_count"])) > 0
    )
    if predictive and coherence:
        return [
            "One-scalar temporal predictive signal supported",
            "Recruitment/oscillation coherence supported descriptively",
        ]
    if predictive:
        return ["Predictive but not recruitment-coherent"]
    if coherence:
        return ["Recruitment-coherent without predictive support"]
    if signs["improved"] > 0 and signs["worsened"] > 0:
        return ["Weak or unstable one-scalar signal"]
    return ["No supported one-scalar temporal signal"]


def run_d039_audit(
    seeds: Sequence[int] = D039_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D039_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    validated = _validate_seeds(seeds)
    if horizon != D039_HORIZON:
        raise ValueError("D-039 requires the frozen 70,000-transition lifetime")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    accepted = d033._accepted_artifact()
    data_by_seed: dict[int, _TraceData] = {}
    gates: list[dict[str, object]] = []
    for seed in validated:
        _, data, gate = _replay_for_seed(seed, accepted)
        gates.append(gate)
        data_by_seed[seed] = data
    per_seed = {
        str(seed): _one_step_summary(data) for seed, data in data_by_seed.items()
    }
    seed_deltas = [
        cast(
            float,
            cast(dict[str, object], per_seed[str(seed)]["all_transitions"])[
                "recurrent_minus_baseline_mae"
            ],
        )
        for seed in validated
    ]
    pooled = _pooled_error_summary(data_by_seed)
    one_step = {
        "pooled": pooled,
        "per_seed": per_seed,
        "within_seed_sign_counts": {
            "improved": sum(delta < 0.0 for delta in seed_deltas),
            "worsened": sum(delta > 0.0 for delta in seed_deltas),
            "tie": sum(delta == 0.0 for delta in seed_deltas),
        },
        "within_seed_mae_deltas": {
            str(seed): delta for seed, delta in zip(validated, seed_deltas, strict=True)
        },
    }
    evaluations = {
        str(target_horizon): _evaluate_horizon(data_by_seed, target_horizon)
        for target_horizon in D039_TARGET_HORIZONS
    }
    anchor_records = _anchor_records(data_by_seed)
    anchor_summary = _anchor_summary(anchor_records)
    oscillation_records = _oscillation_records(data_by_seed)
    oscillation_summary = _oscillation_summary(oscillation_records)
    categories = _interpretation(
        one_step, evaluations, anchor_summary, oscillation_summary
    )
    return {
        "schema_version": 1,
        "experiment": "D-039",
        "title": "One-scalar shadow recurrent predictor readiness audit",
        "implementation_protocol_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D039_HORIZON,
        "support": {
            "source": "accepted D-031R1 Arm-B LEARNED_NO_DETRAP replay",
            "accepted_artifact": D039_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": hashlib.sha256(
                (
                    Path(__file__).resolve().parents[2] / D039_ACCEPTED_D031R1_ARTIFACT
                ).read_bytes()
            ).hexdigest(),
            "fresh_development_or_exp_seeds_used": False,
        },
        "freeze": {
            "initial_h": 0.0,
            "recurrence": (
                "h_next = h + alpha * (y - (p + h)) = (1-alpha)*h + alpha*(y-p)"
            ),
            "alpha": D039_RECURRENCE_ALPHA,
            "alpha_equals_d027_learning_rate": D039_RECURRENCE_ALPHA
            == d027.D027_LEARNING_RATE,
            "prediction": (
                "unchanged pre-update D-027 delta_beacon_forward prediction "
                "for the actually executed action"
            ),
            "target": (
                "actually experienced visible delta_beacon_forward after the "
                "real transition"
            ),
            "reset_semantics": (
                "initialized once per lifetime; never reset at mode, SEEK, "
                "logging, anchor, or analysis boundaries"
            ),
            "eligibility": (
                "D-036 exact pre-action mode_before == SEEK and visible "
                "charging_contact == false"
            ),
            "ridge_alpha": D039_FIXED_ALPHA,
            "organism_boundary_unchanged": True,
        },
        "replay_gates": gates,
        "trace_inventory": [
            {
                "seed": seed,
                "transition_count": len(data.trace),
                "eligible_state_count": int(np.sum(data.eligible)),
                "trace_digest": data.trace_digest,
                "visible_channels": list(d027.D027_CHANNELS),
                "actions": list(_ACTION_NAMES),
                "h_update_count": len(data.h_after),
                "recurrence_equivalence_checks": len(data.h_after),
            }
            for seed, data in data_by_seed.items()
        ],
        "one_step": one_step,
        "future_progress": evaluations,
        "d034_anchor_bridge": anchor_records,
        "d034_anchor_bridge_summary": anchor_summary,
        "d037_oscillation_onset": oscillation_records,
        "d037_oscillation_onset_summary": oscillation_summary,
        "interpretation_categories": [
            "One-scalar temporal predictive signal supported",
            "Recruitment/oscillation coherence supported descriptively",
            "Predictive but not recruitment-coherent",
            "Recruitment-coherent without predictive support",
            "Weak or unstable one-scalar signal",
            "No supported one-scalar temporal signal",
            "Target unsupported",
        ],
        "interpretation": {
            "categories": categories,
            "lane": "Development",
            "confirmatory_claim": False,
            "causal_signal_authorized": False,
            "organism_behavior_changed": False,
            "scalar_shadow_only": True,
            "d040_or_exp_or_causal_recruitment_started": False,
        },
    }


def write_d039_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    artifact = run_d039_audit(executed_commit_sha=executed_commit_sha)
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-039 one-scalar shadow recurrent predictor audit."
    )
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d039_json(args.output, args.executed_commit_sha)
    print(f"D-039 result written to {args.output}")


if __name__ == "__main__":
    main()
