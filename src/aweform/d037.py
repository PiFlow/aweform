"""D-037 evaluator-only audit of endogenous D-027 predictor signals.

The accepted D-031R1 Arm-B organism is replayed unchanged.  Instrumentation
retains only the pre-action D-027 weights and visible observation at eligible
false-contact SEEK decisions.  S1--S6 are computed after replay from those
captured decision states; none reaches the controller, learner, environment,
reward, or information path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np

from . import d025, d027, d031r1, d032, d033, d034, d036
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D037_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D037_HORIZON: Final[int] = 70_000
D037_TARGET_HORIZONS: Final[tuple[int, ...]] = (64, 256, 1024)
D037_ALPHA_GRID: Final[tuple[float, ...]] = (1.0e-6, 1.0e-4, 1.0e-2, 1.0)
D037_FIXED_ALPHA: Final[float] = 1.0e-2
D037_BRIDGE_HISTORIES: Final[tuple[int, ...]] = (4, 8, 16)
D037_BRIDGE_FAMILIES: Final[tuple[str, ...]] = (
    "ALT",
    "NO_FORWARD_PROGRESS",
)
D037_OSCILLATION_MIN_RUN: Final[int] = 16
D037_OSCILLATION_WINDOWS: Final[tuple[tuple[str, int], ...]] = (
    ("before", -16),
    ("at", 0),
    ("after", 16),
)
D037_SIGNALS: Final[tuple[str, ...]] = (
    "S1_chosen_action_predicted_forward",
    "S2_best_predicted_forward",
    "S3_best_second_margin",
    "S4_forward_population_std",
    "S5_centered_consequence_frobenius_norm",
    "S6_candidate_weight_frobenius_norm",
)
D037_CANDIDATE_ACTIONS: Final[tuple[Action, ...]] = d031r1.D031R1_STEERING_ACTIONS
D037_ACCEPTED_D031R1_ARTIFACT: Final[str] = d033.D033_ACCEPTED_D031R1_ARTIFACT
D037_INVALIDATED_PROTOCOL_SHA: Final[str] = "b0d8d1ef315f66503742d2ac2ceb0ab47effc52f"
D037_INVALIDATED_ARTIFACT_SHA256: Final[str] = (
    "cc3cad6739c9242176ced06bed63601a7396bd3c568222993ab95f8e1579bf49"
)
D037_INVALIDATED_ARTIFACT_SIZE: Final[int] = 587491
D037_INVALIDATION_REASON: Final[str] = (
    "invalidated after official-output inspection found that per-seed scalar "
    "correlations were retained but the required pooled scalar correlations and "
    "numeric per-fold target class counts were not serialized"
)

_SIGNAL_COUNT: Final[int] = len(D037_SIGNALS)
_VISIBLE_WIDTH: Final[int] = len(d027.D027_CHANNELS)
_ACTION_WIDTH: Final[int] = len(Action)
_OUTPUT_WIDTH: Final[int] = len(d027.D027_OUTPUTS)


def _validate_seeds(seeds: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D037_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-037 requires exactly the reused development seeds "
            f"{D037_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D037_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-037 may execute only the reused development seeds "
            f"{D037_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str:
    if (
        value is None
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            "D-037 official output requires an exact clean executable protocol SHA"
        )
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _number_summary(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "sample_count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
        }
    ordered = sorted(values)
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p10_nearest_rank": ordered[max(1, math.ceil(0.10 * len(ordered))) - 1],
        "p90_nearest_rank": ordered[max(1, math.ceil(0.90 * len(ordered))) - 1],
    }


def _correlation(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if (
        len(actual) < 2
        or float(np.std(actual)) == 0.0
        or float(np.std(predicted)) == 0.0
    ):
        return None
    return float(np.corrcoef(actual, predicted)[0, 1])


def _binary_metrics(
    actual: np.ndarray, probability: np.ndarray
) -> dict[str, float | None]:
    if not len(actual):
        return {"brier_score": None, "balanced_accuracy": None, "auroc": None}
    brier = float(np.mean((probability - actual) ** 2))
    if len(np.unique(actual)) < 2:
        return {"brier_score": brier, "balanced_accuracy": None, "auroc": None}
    predicted = probability >= 0.5
    balanced = float(
        np.mean([np.mean(predicted[actual == label] == label) for label in (0.0, 1.0)])
    )
    order = np.argsort(probability, kind="mergesort")
    ranks = np.empty(len(actual), dtype=float)
    sorted_values = probability[order]
    start = 0
    while start < len(actual):
        end = start + 1
        while end < len(actual) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + end + 1) / 2.0
        start = end
    positives = actual == 1.0
    negatives = actual == 0.0
    auroc = float(
        (ranks[positives].sum() - positives.sum() * (positives.sum() + 1) / 2)
        / (positives.sum() * negatives.sum())
    )
    return {
        "brier_score": brier,
        "balanced_accuracy": balanced,
        "auroc": auroc,
    }


@dataclass(frozen=True, slots=True)
class _DecisionData:
    seed: int
    trace: tuple[d025.D025TransitionTrace, ...]
    visible_before: np.ndarray
    eligible_indices: np.ndarray
    signals_by_index: np.ndarray


@dataclass(frozen=True, slots=True)
class _Target:
    indices: np.ndarray
    progress: np.ndarray
    reacquired: np.ndarray
    status_counts: dict[str, int]


def _weight_tensor(weights: tuple[float, ...]) -> np.ndarray:
    expected = _ACTION_WIDTH * _OUTPUT_WIDTH * d027.D027_FEATURE_DIMENSION
    if len(weights) != expected:
        raise ValueError(f"D-037 expected {expected} predictor weights")
    return np.asarray(weights, dtype=float).reshape(
        (_ACTION_WIDTH, _OUTPUT_WIDTH, d027.D027_FEATURE_DIMENSION)
    )


def _signals_for_capture(capture: d033._CapturedPreAction) -> np.ndarray:
    if capture.historical_action not in D037_CANDIDATE_ACTIONS:
        raise RuntimeError(
            "D-037 eligible SEEK decision selected a non-steering action"
        )
    if capture.predictions is None or capture.prediction_query_read_only is not True:
        raise RuntimeError("D-037 candidate predictions were not captured read-only")
    predictions = np.asarray(
        [capture.predictions[action] for action in D037_CANDIDATE_ACTIONS],
        dtype=float,
    )
    forward = predictions[:, d031r1.D031R1_FORWARD_OUTPUT_INDEX]
    ordered = np.sort(forward)[::-1]
    chosen_position = D037_CANDIDATE_ACTIONS.index(capture.historical_action)
    return np.asarray(
        (
            forward[chosen_position],
            float(np.max(forward)),
            float(ordered[0] - ordered[1]),
            float(np.std(forward)),
            float(np.linalg.norm(predictions - np.mean(predictions, axis=0))),
            float(
                np.linalg.norm(
                    _weight_tensor(capture.learner_weights)[
                        [
                            list(Action).index(action)
                            for action in D037_CANDIDATE_ACTIONS
                        ]
                    ]
                )
            ),
        ),
        dtype=float,
    )


def _decision_data(
    seed: int,
    trace: tuple[d025.D025TransitionTrace, ...],
    captures: list[d033._CapturedPreAction],
) -> _DecisionData:
    trace_data = d036._trace_data(seed, trace)
    expected_indices = np.flatnonzero(trace_data.eligible)
    indices = np.asarray(
        [capture.transition - 1 for capture in captures], dtype=np.int64
    )
    if not np.array_equal(indices, expected_indices):
        raise RuntimeError(
            "D-037 pre-action capture set did not equal eligible support"
        )
    signals_by_index = np.full((len(trace), _SIGNAL_COUNT), np.nan, dtype=float)
    for index, capture in zip(indices.tolist(), captures, strict=True):
        signals_by_index[index] = _signals_for_capture(capture)
    return _DecisionData(
        seed=seed,
        trace=trace,
        visible_before=trace_data.visible_before,
        eligible_indices=indices,
        signals_by_index=signals_by_index,
    )


def _target(data: _DecisionData, horizon: int) -> _Target:
    trace_data = d036._trace_data(data.seed, data.trace)
    target = d036._target_data(trace_data, 1, horizon)
    return _Target(
        target.indices, target.progress, target.reacquired, target.status_counts
    )


def _feature_rows(
    data: _DecisionData, indices: np.ndarray, augmented: bool
) -> np.ndarray:
    current = data.visible_before[indices]
    if augmented:
        return np.concatenate((current, data.signals_by_index[indices]), axis=1)
    return np.asarray(current, dtype=float)


def _fit_ridge(features: np.ndarray, target: np.ndarray) -> np.ndarray:
    design = np.concatenate((np.ones((len(features), 1)), features), axis=1)
    penalty = np.eye(design.shape[1]) * D037_FIXED_ALPHA
    penalty[0, 0] = 0.0
    return np.asarray(
        np.linalg.solve(design.T @ design + penalty, design.T @ target), dtype=float
    )


def _predict_ridge(features: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    design = np.concatenate((np.ones((len(features), 1)), features), axis=1)
    return np.asarray(design @ coefficients, dtype=float)


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, object]:
    return {
        "sample_count": len(actual),
        "mae": float(np.mean(np.abs(predicted - actual))) if len(actual) else None,
        "correlation": _correlation(actual, predicted),
    }


def _scalar_support(
    data: _DecisionData, target: _Target
) -> dict[str, dict[str, object]]:
    values = data.signals_by_index[target.indices]
    return {
        name: {
            "sample_count": len(values),
            "correlation": _correlation(target.progress, values[:, index]),
        }
        for index, name in enumerate(D037_SIGNALS)
    }


def _evaluate_horizon(
    data_by_seed: dict[int, _DecisionData], horizon: int
) -> dict[str, object]:
    targets = {seed: _target(data, horizon) for seed, data in data_by_seed.items()}
    folds: list[dict[str, object]] = []
    for held_out in D037_DEFAULT_DEVELOPMENT_SEEDS:
        held_target = targets[held_out]
        fold: dict[str, object] = {
            "held_out_seed": held_out,
            "sample_count": len(held_target.indices),
            "target_status_counts": held_target.status_counts,
            "target_class_balance": {
                "negative": int(np.sum(~held_target.reacquired)),
                "positive": int(np.sum(held_target.reacquired)),
            },
            "scalar_progress_correlations": _scalar_support(
                data_by_seed[held_out], held_target
            ),
            "models": {},
        }
        model_records: dict[str, object] = cast(dict[str, object], fold["models"])
        for model_name, augmented in (("S0", False), ("S0_PLUS_S1_S6", True)):
            training_features = np.concatenate(
                [
                    _feature_rows(data_by_seed[seed], targets[seed].indices, augmented)
                    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ],
                axis=0,
            )
            training_progress = np.concatenate(
                [
                    targets[seed].progress
                    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ]
            )
            progress = _predict_ridge(
                _feature_rows(data_by_seed[held_out], held_target.indices, augmented),
                _fit_ridge(training_features, training_progress),
            )
            train_classes = np.concatenate(
                [
                    targets[seed].reacquired.astype(float)
                    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ]
            )
            classification: dict[str, object]
            if len(np.unique(train_classes)) < 2:
                classification = {
                    "status": "untestable_training_class_balance",
                    "metrics": {
                        "sample_count": 0,
                        "brier_score": None,
                        "balanced_accuracy": None,
                        "auroc": None,
                    },
                }
            else:
                probability = 1.0 / (
                    1.0
                    + np.exp(
                        -np.clip(
                            _predict_ridge(
                                _feature_rows(
                                    data_by_seed[held_out],
                                    held_target.indices,
                                    augmented,
                                ),
                                _fit_ridge(training_features, train_classes),
                            ),
                            -40.0,
                            40.0,
                        )
                    )
                )
                classification = {
                    "status": "fit",
                    "metrics": {
                        "sample_count": len(probability),
                        **_binary_metrics(
                            held_target.reacquired.astype(float), probability
                        ),
                    },
                }
            model_records[model_name] = {
                "feature_dimension": int(training_features.shape[1]),
                "selected_alpha": D037_FIXED_ALPHA,
                "progress": _regression_metrics(held_target.progress, progress),
                "reacquisition": classification,
            }
        baseline = cast(dict[str, object], model_records["S0"])
        augmented_record = cast(dict[str, object], model_records["S0_PLUS_S1_S6"])
        baseline_progress = cast(dict[str, object], baseline["progress"])
        augmented_progress = cast(dict[str, object], augmented_record["progress"])
        fold["same_sample_augmented_minus_baseline_mae"] = (
            cast(float, augmented_progress["mae"])
            - cast(float, baseline_progress["mae"])
            if augmented_progress["mae"] is not None
            and baseline_progress["mae"] is not None
            else None
        )
        folds.append(fold)
    pooled: dict[str, object] = {}
    pooled_progress = [
        targets[seed].progress for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
    ]
    pooled_scalar_values = np.concatenate(
        [
            data_by_seed[seed].signals_by_index[targets[seed].indices]
            for seed in data_by_seed
        ],
        axis=0,
    )
    pooled_progress_values = np.concatenate(pooled_progress, axis=0)
    pooled["scalar_progress_correlations"] = {
        name: {
            "sample_count": len(pooled_progress_values),
            "correlation": _correlation(
                pooled_progress_values, pooled_scalar_values[:, offset]
            ),
        }
        for offset, name in enumerate(D037_SIGNALS)
    }
    pooled["target_class_balance"] = {
        "negative": int(
            sum(
                np.sum(~targets[seed].reacquired)
                for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
            )
        ),
        "positive": int(
            sum(
                np.sum(targets[seed].reacquired)
                for seed in D037_DEFAULT_DEVELOPMENT_SEEDS
            )
        ),
    }
    for model_name in ("S0", "S0_PLUS_S1_S6"):
        records = [
            cast(dict[str, object], cast(dict[str, object], fold["models"])[model_name])
            for fold in folds
        ]
        progress_records = [
            cast(dict[str, object], record["progress"]) for record in records
        ]
        maes = [
            cast(float, row["mae"])
            for row in progress_records
            if row["mae"] is not None
        ]
        correlations = [
            cast(float, row["correlation"])
            for row in progress_records
            if row["correlation"] is not None
        ]
        pooled[model_name] = {
            "fold_count": len(records),
            "mean_held_out_progress_mae": float(np.mean(maes)) if maes else None,
            "mean_held_out_progress_correlation": (
                float(np.mean(correlations)) if correlations else None
            ),
        }
    pooled["mean_same_sample_augmented_minus_baseline_mae"] = float(
        np.mean(
            [
                cast(float, fold["same_sample_augmented_minus_baseline_mae"])
                for fold in folds
                if fold["same_sample_augmented_minus_baseline_mae"] is not None
            ]
        )
    )
    return {"horizon": horizon, "folds": folds, "pooled": pooled}


def _matched_index(
    data: _DecisionData, anchor_index: int, excluded: set[int]
) -> int | None:
    candidates = [
        int(index)
        for index in data.eligible_indices.tolist()
        if int(index) not in excluded
    ]
    if not candidates:
        return None
    distances = [
        float(
            np.sum(
                (data.visible_before[index] - data.visible_before[anchor_index]) ** 2
            )
        )
        for index in candidates
    ]
    return min(
        zip(candidates, distances, strict=True), key=lambda pair: (pair[1], pair[0])
    )[0]


def _bridge_records(data_by_seed: dict[int, _DecisionData]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS:
        data = data_by_seed[seed]
        traces = data.trace
        anchor_indices: set[int] = set()
        selections: list[tuple[str, int, d034._TriggerSelection | None]] = []
        for family in D037_BRIDGE_FAMILIES:
            for history in D037_BRIDGE_HISTORIES:
                selection = d034._find_trigger(traces, family, history)
                index = (
                    d036._anchor_index(traces, selection)
                    if selection is not None
                    else None
                )
                if index is not None:
                    anchor_indices.add(index)
                selections.append((family, history, selection))
        for family, history, selection in selections:
            index = (
                d036._anchor_index(traces, selection) if selection is not None else None
            )
            record: dict[str, object] = {
                "seed": seed,
                "family": family,
                "history": history,
                "status": "anchor_available"
                if index is not None
                else "anchor_unavailable",
                "d034_trigger_label_used_as_feature": False,
                "d034_on_off_outcome_used_as_feature": False,
            }
            if index is None:
                records.append(record)
                continue
            matched = _matched_index(data, index, anchor_indices)
            record["anchor_trace_index"] = index
            record["anchor_transition"] = traces[index].transition_index
            record["anchor_signal_values"] = dict(
                zip(D037_SIGNALS, data.signals_by_index[index].tolist(), strict=True)
            )
            if matched is None:
                record["matched_non_anchor_status"] = "unavailable"
            else:
                record["matched_non_anchor_status"] = "matched"
                record["matched_trace_index"] = matched
                record["matched_transition"] = traces[matched].transition_index
                record["matched_signal_values"] = dict(
                    zip(
                        D037_SIGNALS,
                        data.signals_by_index[matched].tolist(),
                        strict=True,
                    )
                )
                record["signal_delta_anchor_minus_match"] = {
                    name: float(
                        data.signals_by_index[index, offset]
                        - data.signals_by_index[matched, offset]
                    )
                    for offset, name in enumerate(D037_SIGNALS)
                }
            records.append(record)
    return records


def _bridge_summary(records: list[dict[str, object]]) -> dict[str, object]:
    matched = [
        record
        for record in records
        if record.get("matched_non_anchor_status") == "matched"
    ]
    pooled: dict[str, object] = {}
    for name in D037_SIGNALS:
        deltas = [
            cast(dict[str, float], record["signal_delta_anchor_minus_match"])[name]
            for record in matched
        ]
        pooled[name] = {
            "paired_count": len(deltas),
            "delta_summary": _number_summary(deltas),
            "anchor_greater_count": sum(value > 0.0 for value in deltas),
            "anchor_equal_count": sum(value == 0.0 for value in deltas),
            "anchor_lower_count": sum(value < 0.0 for value in deltas),
        }
    per_seed: dict[str, object] = {}
    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS:
        per_seed[str(seed)] = {
            "anchor_record_count": sum(
                record.get("seed") == seed for record in records
            ),
            "matched_count": sum(
                record.get("seed") == seed
                and record.get("matched_non_anchor_status") == "matched"
                for record in records
            ),
        }
    return {
        "matching_rule": (
            "Within seed, exclude every D-034 anchor and select the smallest-index "
            "eligible ordinary false-contact SEEK state minimizing squared distance "
            "on the current six-channel visible observation only; no trigger label, "
            "outcome, target, hidden state, or future quantity is used."
        ),
        "availability": {
            "record_count": len(records),
            "anchor_available_count": sum(
                record["status"] == "anchor_available" for record in records
            ),
            "matched_non_anchor_available_count": len(matched),
            "matched_non_anchor_unavailable_count": sum(
                record.get("matched_non_anchor_status") == "unavailable"
                for record in records
            ),
        },
        "per_seed": per_seed,
        "pooled": pooled,
    }


def _oscillation_onset(data: _DecisionData) -> tuple[int, int] | None:
    turns = {Action.TURN_LEFT, Action.TURN_RIGHT}
    eligible = set(data.eligible_indices.tolist())
    actions = [row.action for row in data.trace]
    for start in data.eligible_indices.tolist():
        if actions[start] not in turns:
            continue
        end = start
        while (
            end + 1 in eligible
            and actions[end + 1] in turns
            and actions[end + 1] is not actions[end]
        ):
            end += 1
        if end - start + 1 >= D037_OSCILLATION_MIN_RUN:
            return start, end - start + 1
    return None


def _window_summary(data: _DecisionData, indices: list[int]) -> dict[str, object]:
    if not indices:
        return {name: _number_summary([]) for name in D037_SIGNALS}
    values = data.signals_by_index[np.asarray(indices, dtype=np.int64)]
    return {
        name: _number_summary(values[:, offset].tolist())
        for offset, name in enumerate(D037_SIGNALS)
    }


def _oscillation_records(
    data_by_seed: dict[int, _DecisionData],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for seed in D037_DEFAULT_DEVELOPMENT_SEEDS:
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
            "windows": {},
            "matched_control_status": "unavailable" if matched is None else "matched",
        }
        windows = cast(dict[str, object], record["windows"])
        for label, offset in D037_OSCILLATION_WINDOWS:
            indices = list(range(start + offset, start + offset + 16))
            if any(
                index < 0
                or index >= len(data.trace)
                or index not in set(data.eligible_indices.tolist())
                for index in indices
            ):
                windows[label] = {"status": "unavailable"}
            else:
                windows[label] = {
                    "status": "available",
                    "start_trace_index": indices[0],
                    "summary": _window_summary(data, indices),
                }
        if matched is not None:
            record["matched_control_trace_index"] = matched
            record["matched_control_transition"] = data.trace[matched].transition_index
            record["matched_control_signal_values"] = dict(
                zip(D037_SIGNALS, data.signals_by_index[matched].tolist(), strict=True)
            )
            record["onset_minus_matched_signal_values"] = {
                name: float(
                    data.signals_by_index[start, offset]
                    - data.signals_by_index[matched, offset]
                )
                for offset, name in enumerate(D037_SIGNALS)
            }
        records.append(record)
    return records


def _oscillation_summary(records: list[dict[str, object]]) -> dict[str, object]:
    pooled: dict[str, list[np.ndarray]] = {
        label: [] for label, _ in D037_OSCILLATION_WINDOWS
    }
    for record in records:
        if record.get("status") != "onset_available":
            continue
        windows = cast(dict[str, object], record["windows"])
        for label, _ in D037_OSCILLATION_WINDOWS:
            window = cast(dict[str, object], windows[label])
            if window.get("status") == "available":
                summary = cast(dict[str, object], window["summary"])
                pooled[label].append(
                    np.asarray(
                        [
                            cast(float, cast(dict[str, object], summary[name])["mean"])
                            for name in D037_SIGNALS
                        ],
                        dtype=float,
                    )
                )
    summary_out: dict[str, object] = {}
    for label, values in pooled.items():
        if not values:
            summary_out[label] = {"status": "unavailable"}
        else:
            matrix = np.asarray(values)
            summary_out[label] = {
                "status": "available",
                "seed_window_count": len(values),
                "mean_signal_values": dict(
                    zip(D037_SIGNALS, np.mean(matrix, axis=0).tolist(), strict=True)
                ),
            }
    matched = [
        cast(dict[str, float], record["onset_minus_matched_signal_values"])
        for record in records
        if record.get("matched_control_status") == "matched"
    ]
    return {
        "definition": (
            "first contiguous run in the ordinary Arm-B trace whose decisions are "
            "all eligible false-contact SEEK decisions and whose actions strictly "
            "alternate TURN_LEFT/TURN_RIGHT, with minimum length 16; onset is the "
            "first action of that run"
        ),
        "availability": {
            "seed_count": len(records),
            "onset_available_count": sum(
                record.get("status") == "onset_available" for record in records
            ),
            "matched_control_available_count": len(matched),
        },
        "windows": summary_out,
        "onset_minus_matched_control": {
            name: _number_summary([row[name] for row in matched])
            for name in D037_SIGNALS
        },
    }


def _replay_for_seed(
    seed: int, accepted: dict[str, object]
) -> tuple[list[dict[str, object]], _DecisionData]:
    gates: list[dict[str, object]] = []
    for role in ("A", "B"):
        result, trace, instrumentation = d033._run_capture(
            seed,
            role=role,
            horizon=D037_HORIZON,
            capture_eligible_decisions=role == "B",
            seed_validator=_validate_seed,
        )
        expected = dict(
            d033._accepted_arm(
                accepted,
                seed,
                "LEARNED_" + ("WITH_DETRAP" if role == "A" else "NO_DETRAP"),
            )
        )
        expected["_weights"] = d033._flatten_final_weights(expected)
        comparison = d032._compare_identity_fields(
            result, expected, include_private_weights=True
        )
        if not bool(comparison["all_identity_fields_exact"]):
            raise RuntimeError(f"D-037 accepted {role} replay gate failed for {seed}")
        gates.append(
            {
                "seed": seed,
                "arm": "LEARNED_WITH_DETRAP" if role == "A" else "LEARNED_NO_DETRAP",
                "all_identity_fields_exact": True,
                "checked_identity_fields": comparison["checked_fields"],
                "mismatched_identity_fields": comparison["mismatched_fields"],
                "instrumented_replay_exact": True,
            }
        )
        if role == "B":
            data = _decision_data(seed, trace, instrumentation.decision_captures)
    if "data" not in locals():
        raise RuntimeError("D-037 Arm-B decision data was not captured")
    return gates, data


def _strip_private(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _strip_private(item)
            for key, item in value.items()
            if not isinstance(key, str) or not key.startswith("_")
        }
    if isinstance(value, list):
        return [_strip_private(item) for item in value]
    return value


def run_d037_audit(
    seeds: tuple[int, ...] | list[int] = D037_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D037_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    validated = _validate_seeds(seeds)
    if horizon != D037_HORIZON:
        raise ValueError("D-037 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    accepted = d033._accepted_artifact()
    data_by_seed: dict[int, _DecisionData] = {}
    replay_gates: list[dict[str, object]] = []
    for seed in validated:
        gates, data = _replay_for_seed(seed, accepted)
        replay_gates.extend(gates)
        data_by_seed[seed] = data
    bridge = _bridge_records(data_by_seed)
    oscillation = _oscillation_records(data_by_seed)
    evaluations = {
        str(horizon_value): _evaluate_horizon(data_by_seed, horizon_value)
        for horizon_value in D037_TARGET_HORIZONS
    }
    pooled_signal_values = np.concatenate(
        [
            data.signals_by_index[data.eligible_indices]
            for data in data_by_seed.values()
        ],
        axis=0,
    )
    return {
        "schema_version": 1,
        "experiment": "D-037",
        "title": "Endogenous prediction-state recruitment-signal audit",
        "implementation_protocol_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D037_HORIZON,
        "support": {
            "source": "accepted D-031R1 Arm-A/Arm-B replay via D-033 capture support",
            "accepted_artifact": D037_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": hashlib.sha256(
                (
                    Path(__file__).resolve().parents[2] / D037_ACCEPTED_D031R1_ARTIFACT
                ).read_bytes()
            ).hexdigest(),
            "fresh_development_or_exp_seeds_used": False,
        },
        "invalidated_prior_output": {
            "implementation_protocol_sha": D037_INVALIDATED_PROTOCOL_SHA,
            "artifact_sha256": D037_INVALIDATED_ARTIFACT_SHA256,
            "artifact_size_bytes": D037_INVALIDATED_ARTIFACT_SIZE,
            "reason": D037_INVALIDATION_REASON,
        },
        "freeze": {
            "candidate_signals": {
                "S0": (
                    "current six visible channels: energy, beacon.left, "
                    "beacon.forward, beacon.right, charging_contact, thermal"
                ),
                "S1": (
                    "predicted delta_beacon_forward for the unchanged "
                    "controller's selected steering action"
                ),
                "S2": (
                    "maximum predicted delta_beacon_forward over TURN_LEFT, "
                    "TURN_RIGHT, MOVE_FORWARD"
                ),
                "S3": (
                    "largest minus second-largest predicted "
                    "delta_beacon_forward over those three actions"
                ),
                "S4": (
                    "population standard deviation sqrt(mean((x-mean(x))^2)) "
                    "over those three forward predictions"
                ),
                "S5": (
                    "Frobenius norm sqrt(sum((P[a,c]-mean_a(P[a,c]))^2)) "
                    "of the centered 3-by-6 predicted consequence matrix"
                ),
                "S6": (
                    "Frobenius norm sqrt(sum(w^2)) of the existing "
                    "3-by-6-by-7 candidate-action weight tensor"
                ),
            },
            "signal_names": list(D037_SIGNALS),
            "candidate_actions": [action.name for action in D037_CANDIDATE_ACTIONS],
            "eligibility": (
                "mode_before == SEEK and current visible charging_contact == "
                "false; mode_after and all transition outcomes ignored"
            ),
            "decision_time_inputs": (
                "current six-channel visible observation, existing pre-action "
                "D-027 weights, and read-only candidate predictions; no "
                "synthetic history"
            ),
            "target_horizons": list(D037_TARGET_HORIZONS),
            "target_definition": (
                "visible beacon_forward at final observation in the unchanged "
                "continuation minus current pre-action visible beacon_forward; "
                "reacquisition is any false-to-true contact in the window"
            ),
            "target_null_policy": (
                "termination, truncation, and lifetime-boundary windows remain "
                "explicit and are excluded only from affected metrics"
            ),
            "ridge": (
                "intercept plus S0 current observation, or intercept plus S0 "
                "and S1..S6; alpha 0.01 fixed from predeclared grid "
                "[1e-6,1e-4,1e-2,1.0], intercept unpenalized, "
                "leave-one-seed-out"
            ),
            "bridge": (
                "D-034 ALT_4/8/16 and NO_FORWARD_PROGRESS_4/8/16; same-seed "
                "nearest ordinary eligible non-anchor matched on current S0 "
                "only, squared distance and smallest-index tie break"
            ),
            "oscillation_onset": (
                "first contiguous eligible false-contact SEEK run of strict "
                "alternating left/right actions with at least 16 actions; "
                "fixed windows before/at/after are 16 decisions each"
            ),
            "organism_boundary_unchanged": True,
        },
        "causal_order": [
            "exact accepted Arm-A/Arm-B replay gate",
            "ordinary Arm-B pre-action eligible decision capture",
            "evaluator-only S1-S6 computation and future target construction",
            "seed-held-out descriptive ridge comparison",
            "D-034 matched bridge diagnostic",
            "oscillation-onset diagnostic",
        ],
        "replay_gates": replay_gates,
        "trace_inventory": [
            {
                "seed": seed,
                "transition_count": len(data.trace),
                "eligible_state_count": len(data.eligible_indices),
                "trace_digest": d036._trace_data(seed, data.trace).trace_digest,
                "visible_channels": list(d027.D027_CHANNELS),
                "actions": [action.name for action in Action],
            }
            for seed, data in data_by_seed.items()
        ],
        "signal_distributions": {
            name: _number_summary(pooled_signal_values[:, offset].tolist())
            for offset, name in enumerate(D037_SIGNALS)
        },
        "per_seed_signal_distributions": {
            str(seed): {
                "eligible_state_count": len(data.eligible_indices),
                "signals": {
                    name: _number_summary(
                        data.signals_by_index[data.eligible_indices, offset].tolist()
                    )
                    for offset, name in enumerate(D037_SIGNALS)
                },
            }
            for seed, data in data_by_seed.items()
        },
        "evaluations": evaluations,
        "d034_bridge": bridge,
        "d034_bridge_summary": _bridge_summary(bridge),
        "oscillation_onset": oscillation,
        "oscillation_onset_summary": _oscillation_summary(oscillation),
        "interpretation_categories": {
            "useful_endogenous_signal": (
                "predeclared predictor-state signals generalize across seeds, "
                "improve over S0 on the same support, and align descriptively "
                "with bridge/onset states"
            ),
            "current_observation_already_explains_it": (
                "S0 performs comparably and additions provide no stable gain"
            ),
            "weak_or_unstable_endogenous_signal": (
                "some descriptive association exists but held-out or "
                "bridge/onset coherence is inconsistent"
            ),
            "no_supported_endogenous_signal": (
                "no predeclared predictor-state signal adds useful stable "
                "information on this support"
            ),
            "target_unsupported": (
                "preserve null or untestable status where support is inadequate"
            ),
        },
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "causal_signal_authorized": False,
            "organism_behavior_changed": False,
            "headline": (
                "Pending descriptive execution; scalar predictor-state audit only."
            ),
        },
    }


def write_d037_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    artifact = _strip_private(run_d037_audit(executed_commit_sha=executed_commit_sha))
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-037 endogenous-signal audit."
    )
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d037_json(args.output, args.executed_commit_sha)
    print(f"D-037 result written to {args.output}")


if __name__ == "__main__":
    main()
