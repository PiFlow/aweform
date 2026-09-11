"""D-036 evaluator-only shadow short-history learnability audit.

The accepted D-031R1 organism is replayed unchanged.  This module constructs
post-hoc samples from its ordinary Arm-B trace and fits transparent linear
shadow models.  No shadow feature, target, prediction, or history reaches the
organism controller, learner, environment, reward, or information path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np

from . import d025, d026, d027, d033, d034
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D036_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D036_HORIZON: Final[int] = 70_000
D036_HISTORY_LENGTHS: Final[tuple[int, ...]] = (1, 4, 8, 16)
D036_TARGET_HORIZONS: Final[tuple[int, ...]] = (64, 256, 1024)
D036_ALPHA_GRID: Final[tuple[float, ...]] = (1.0e-6, 1.0e-4, 1.0e-2, 1.0)
D036_FIXED_ALPHA: Final[float] = 1.0e-2
D036_AUTHORITATIVE_BASE_SHA: Final[str] = "911acc5daefe2b1e3fcc7a683e9056740c6bca29"
D036_ACCEPTED_D031R1_ARTIFACT: Final[str] = d033.D033_ACCEPTED_D031R1_ARTIFACT
D036_BRIDGE_FAMILIES: Final[tuple[str, ...]] = (
    "ALT",
    "NO_FORWARD_PROGRESS",
)

_VISIBLE_WIDTH: Final[int] = len(d027.D027_CHANNELS)
_ACTION_WIDTH: Final[int] = len(Action)
_FEATURE_WIDTH_PER_STEP: Final[int] = _VISIBLE_WIDTH + _ACTION_WIDTH


def _validate_seeds(seeds: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    validated = validate_exp003_development_seeds(seeds)
    if validated != D036_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-036 requires exactly the reused development seeds "
            f"{D036_DEFAULT_DEVELOPMENT_SEEDS}; got {validated}"
        )
    return validated


def _validate_seed(seed: int) -> None:
    validated = validate_exp003_development_seeds((seed,))
    if validated[0] not in D036_DEFAULT_DEVELOPMENT_SEEDS:
        raise ValueError(
            "D-036 may execute only the reused development seeds "
            f"{D036_DEFAULT_DEVELOPMENT_SEEDS}; got {validated[0]}"
        )


def _validate_executed_commit_sha(value: str | None) -> str:
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(
            "D-036 official output requires an exact clean executable protocol SHA"
        )
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class _TraceData:
    seed: int
    trace_digest: str
    visible_before: np.ndarray
    actions: np.ndarray
    visible_after_forward: np.ndarray
    reacquisition: np.ndarray
    eligible: np.ndarray
    terminated: bool
    truncated: bool


@dataclass(frozen=True, slots=True)
class _TargetData:
    indices: np.ndarray
    progress: np.ndarray
    reacquired: np.ndarray
    status_counts: dict[str, int]


def _visible(observation: d027.D027Observation) -> tuple[float, ...]:
    return (
        observation.energy,
        observation.beacon.left,
        observation.beacon.forward,
        observation.beacon.right,
        float(observation.charging_contact),
        observation.thermal,
    )


def _trace_data(seed: int, trace: tuple[d025.D025TransitionTrace, ...]) -> _TraceData:
    visible_before = np.asarray(
        [
            _visible(cast(d027.D027Observation, getattr(row, "observation_before")))
            for row in trace
        ],
        dtype=float,
    )
    visible_after = np.asarray(
        [
            _visible(cast(d027.D027Observation, getattr(row, "observation")))
            for row in trace
        ],
        dtype=float,
    )
    actions = np.asarray(
        [list(Action).index(cast(Action, getattr(row, "action"))) for row in trace],
        dtype=np.int8,
    )
    eligible = np.asarray(
        [
            getattr(row, "mode_before") is d026.D026Mode.SEEK
            and getattr(row, "mode_after") is d026.D026Mode.SEEK
            and before[4] == 0.0
            and after[4] == 0.0
            for before, after, row in zip(
                visible_before, visible_after, trace, strict=True
            )
        ],
        dtype=bool,
    )
    reacquisition = np.asarray(
        [
            bool(getattr(row, "telemetry").charging_contact_after)
            and not bool(getattr(row, "telemetry").charging_contact_before)
            for row in trace
        ],
        dtype=bool,
    )
    if not trace:
        raise ValueError("D-036 cannot analyze an empty causal trace")
    return _TraceData(
        seed=seed,
        trace_digest=_digest(
            tuple(
                (
                    getattr(row, "transition_index"),
                    getattr(row, "action").name,
                    tuple(getattr(row, "observation_before")),
                    tuple(getattr(row, "observation")),
                )
                for row in trace
            )
        ),
        visible_before=visible_before,
        actions=actions,
        visible_after_forward=visible_after[:, 2],
        reacquisition=reacquisition,
        eligible=eligible,
        terminated=bool(getattr(trace[-1], "telemetry").terminated),
        truncated=bool(getattr(trace[-1], "telemetry").truncated),
    )


def _feature_matrix(data: _TraceData, history: int, indices: np.ndarray) -> np.ndarray:
    if history not in D036_HISTORY_LENGTHS:
        raise ValueError(f"unsupported D-036 history length: {history}")
    if np.any(indices < history - 1):
        raise ValueError("history prefix is unavailable and must not be padded")
    rows: list[np.ndarray] = []
    for offset in range(history - 1, -1, -1):
        row_indices = indices - offset
        visible = data.visible_before[row_indices]
        actions = np.zeros((len(indices), _ACTION_WIDTH), dtype=float)
        actions[np.arange(len(indices)), data.actions[row_indices]] = 1.0
        rows.append(np.concatenate((visible, actions), axis=1))
    return np.concatenate(rows, axis=1)


def _future_status(data: _TraceData, index: int, horizon: int) -> str:
    if index + horizon >= len(data.visible_after_forward):
        if data.terminated:
            return "termination"
        if data.truncated:
            return "truncation"
        return "null_lifetime_boundary"
    return "available"


def _target_data(data: _TraceData, history: int, horizon: int) -> _TargetData:
    eligible_indices = np.flatnonzero(data.eligible)
    indices = eligible_indices[eligible_indices >= history - 1]
    valid: list[int] = []
    progress: list[float] = []
    reacquired: list[bool] = []
    statuses = {
        "available": 0,
        "termination": 0,
        "truncation": 0,
        "null_lifetime_boundary": 0,
    }
    for index in indices.tolist():
        status = _future_status(data, index, horizon)
        statuses[status] += 1
        if status != "available":
            continue
        valid.append(index)
        progress.append(
            float(
                data.visible_after_forward[index + horizon]
                - data.visible_after_forward[index]
            )
        )
        reacquired.append(
            bool(np.any(data.reacquisition[index + 1 : index + horizon + 1]))
        )
    return _TargetData(
        indices=np.asarray(valid, dtype=np.int64),
        progress=np.asarray(progress, dtype=float),
        reacquired=np.asarray(reacquired, dtype=bool),
        status_counts=statuses,
    )


def _stats(
    data: _TraceData, history: int, target: _TargetData
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = np.concatenate(
        (
            np.ones((len(target.indices), 1)),
            _feature_matrix(data, history, target.indices),
        ),
        axis=1,
    )
    return (
        features.T @ features,
        features.T @ target.progress,
        features.T @ target.reacquired.astype(float),
    )


def _fit_ridge(xx: np.ndarray, xy: np.ndarray) -> np.ndarray:
    penalty = np.eye(xx.shape[0]) * D036_FIXED_ALPHA
    penalty[0, 0] = 0.0
    return np.linalg.solve(xx + penalty, xy)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return np.asarray(1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0))))


def _correlation(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if (
        len(actual) < 2
        or float(np.std(actual)) == 0.0
        or float(np.std(predicted)) == 0.0
    ):
        return None
    return float(np.corrcoef(actual, predicted)[0, 1])


def _auroc(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(np.unique(actual)) < 2:
        return None
    order = np.argsort(predicted, kind="mergesort")
    ranks = np.empty(len(predicted), dtype=float)
    sorted_values = predicted[order]
    start = 0
    while start < len(predicted):
        end = start + 1
        while end < len(predicted) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + end + 1) / 2.0
        start = end
    positives = actual == 1.0
    negatives = actual == 0.0
    return float(
        (ranks[positives].sum() - positives.sum() * (positives.sum() + 1) / 2)
        / (positives.sum() * negatives.sum())
    )


def _binary_metrics(
    actual: np.ndarray, probability: np.ndarray
) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "brier_score": float(np.mean((probability - actual) ** 2))
        if len(actual)
        else None,
        "balanced_accuracy": None,
        "auroc": _auroc(actual, probability),
    }
    if len(np.unique(actual)) == 2:
        predicted = probability >= 0.5
        recalls = [
            float(np.mean(predicted[actual == label] == label)) for label in (0.0, 1.0)
        ]
        metrics["balanced_accuracy"] = float(np.mean(recalls))
    return metrics


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, object]:
    return {
        "sample_count": len(actual),
        "mae": float(np.mean(np.abs(predicted - actual))) if len(actual) else None,
        "correlation": _correlation(actual, predicted),
    }


def _classification_metrics(
    actual: np.ndarray, probability: np.ndarray
) -> dict[str, object]:
    return {
        "sample_count": len(actual),
        "class_count": int(len(np.unique(actual))) if len(actual) else 0,
        **_binary_metrics(actual, probability),
    }


def _evaluate_horizon(
    data_by_seed: dict[int, _TraceData], horizon: int
) -> dict[str, object]:
    supports: dict[int, dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]] = {}
    targets: dict[int, dict[int, _TargetData]] = {}
    totals: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for history in D036_HISTORY_LENGTHS:
        supports[history] = {}
        targets[history] = {}
        total_xx: np.ndarray | None = None
        total_progress: np.ndarray | None = None
        total_class: np.ndarray | None = None
        for seed in D036_DEFAULT_DEVELOPMENT_SEEDS:
            target = _target_data(data_by_seed[seed], history, horizon)
            xx, progress_xy, class_xy = _stats(data_by_seed[seed], history, target)
            targets[history][seed] = target
            supports[history][seed] = (xx, progress_xy, class_xy)
            total_xx = xx if total_xx is None else total_xx + xx
            total_progress = (
                progress_xy if total_progress is None else total_progress + progress_xy
            )
            total_class = class_xy if total_class is None else total_class + class_xy
        assert (
            total_xx is not None
            and total_progress is not None
            and total_class is not None
        )
        totals[history] = (total_xx, total_progress, total_class)

    folds: list[dict[str, object]] = []
    for held_out in D036_DEFAULT_DEVELOPMENT_SEEDS:
        models: dict[int, dict[str, object]] = {}
        predictions: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for history in D036_HISTORY_LENGTHS:
            total_xx, total_progress, total_class = totals[history]
            held_xx, held_progress, held_class = supports[history][held_out]
            progress_beta = _fit_ridge(
                total_xx - held_xx, total_progress - held_progress
            )
            target = targets[history][held_out]
            features = np.concatenate(
                (
                    np.ones((len(target.indices), 1)),
                    _feature_matrix(data_by_seed[held_out], history, target.indices),
                ),
                axis=1,
            )
            progress_prediction = features @ progress_beta
            train_classes = np.concatenate(
                [
                    targets[history][seed].reacquired
                    for seed in D036_DEFAULT_DEVELOPMENT_SEEDS
                    if seed != held_out
                ]
            )
            if len(np.unique(train_classes)) >= 2:
                class_beta = _fit_ridge(total_xx - held_xx, total_class - held_class)
                class_prediction = _sigmoid(features @ class_beta)
                class_status = "fit"
                class_alpha: float | None = D036_FIXED_ALPHA
            else:
                class_prediction = np.full(len(target.indices), np.nan)
                class_status = "untestable_training_class_balance"
                class_alpha = None
            models[history] = {
                "held_out_seed": held_out,
                "history": history,
                "feature_dimension": history * _FEATURE_WIDTH_PER_STEP,
                "sample_count": len(target.indices),
                "target_status_counts": target.status_counts,
                "training_class_balance": {
                    "negative": int(np.sum(train_classes == 0)),
                    "positive": int(np.sum(train_classes == 1)),
                },
                "selected_alpha": D036_FIXED_ALPHA,
                "progress": _regression_metrics(target.progress, progress_prediction),
                "reacquisition": {
                    "status": class_status,
                    "selected_alpha": class_alpha,
                    "metrics": _classification_metrics(
                        target.reacquired.astype(float), class_prediction
                    )
                    if class_status == "fit"
                    else {
                        "sample_count": 0,
                        "class_count": 0,
                        "brier_score": None,
                        "balanced_accuracy": None,
                        "auroc": None,
                    },
                },
            }
            predictions[history] = (
                target.indices,
                progress_prediction,
                class_prediction,
            )
        baseline_indices, baseline_progress, _ = predictions[1]
        comparisons: dict[str, object] = {}
        for history in D036_HISTORY_LENGTHS:
            current_indices, current_progress, _ = predictions[history]
            common, baseline_positions, current_positions = np.intersect1d(
                baseline_indices, current_indices, return_indices=True
            )
            actual = targets[history][held_out].progress[current_positions]
            base_prediction = baseline_progress[baseline_positions]
            bounded_prediction = current_progress[current_positions]
            comparisons[f"H{history}_vs_H1"] = {
                "same_held_out_sample_count": len(common),
                "progress_mae_delta_history_minus_h1": (
                    float(
                        np.mean(np.abs(bounded_prediction - actual))
                        - np.mean(np.abs(base_prediction - actual))
                    )
                    if len(common)
                    else None
                ),
                "progress_correlation_history": _correlation(
                    actual, bounded_prediction
                ),
                "progress_correlation_h1": _correlation(actual, base_prediction),
            }
        folds.append(
            {
                "held_out_seed": held_out,
                "models": models,
                "same_held_out_sample_comparisons": comparisons,
            }
        )
    pooled: dict[str, object] = {}
    for history in D036_HISTORY_LENGTHS:
        rows = [
            cast(dict[int, dict[str, object]], fold["models"])[history]
            for fold in folds
        ]
        maes = [
            cast(float, cast(dict[str, object], row["progress"])["mae"])
            for row in rows
            if cast(dict[str, object], row["progress"])["mae"] is not None
        ]
        correlations = [
            cast(float, cast(dict[str, object], row["progress"])["correlation"])
            for row in rows
            if cast(dict[str, object], row["progress"])["correlation"] is not None
        ]
        class_metrics = [
            cast(
                dict[str, object],
                cast(dict[str, object], row["reacquisition"])["metrics"],
            )
            for row in rows
        ]

        def metric_values(name: str) -> list[float]:
            return [
                cast(float, metrics[name])
                for metrics in class_metrics
                if metrics[name] is not None
            ]

        pooled[f"H{history}"] = {
            "fold_count": len(rows),
            "mean_held_out_progress_mae": float(np.mean(maes)) if maes else None,
            "mean_held_out_progress_correlation": (
                float(np.mean(correlations)) if correlations else None
            ),
            "mean_held_out_brier_score": (
                float(np.mean(metric_values("brier_score")))
                if metric_values("brier_score")
                else None
            ),
            "mean_held_out_balanced_accuracy": (
                float(np.mean(metric_values("balanced_accuracy")))
                if metric_values("balanced_accuracy")
                else None
            ),
            "mean_held_out_auroc": (
                float(np.mean(metric_values("auroc")))
                if metric_values("auroc")
                else None
            ),
            "feature_dimension": history * _FEATURE_WIDTH_PER_STEP,
        }
    return {"horizon": horizon, "folds": folds, "pooled": pooled}


def _full_models(
    data_by_seed: dict[int, _TraceData], horizon: int
) -> dict[int, tuple[np.ndarray, np.ndarray | None, dict[int, _TargetData]]]:
    models: dict[int, tuple[np.ndarray, np.ndarray | None, dict[int, _TargetData]]] = {}
    for history in D036_HISTORY_LENGTHS:
        total_xx: np.ndarray | None = None
        total_progress: np.ndarray | None = None
        total_class: np.ndarray | None = None
        targets: dict[int, _TargetData] = {}
        class_targets: list[np.ndarray] = []
        for seed in D036_DEFAULT_DEVELOPMENT_SEEDS:
            target = _target_data(data_by_seed[seed], history, horizon)
            xx, progress_xy, class_xy = _stats(data_by_seed[seed], history, target)
            targets[seed] = target
            total_xx = xx if total_xx is None else total_xx + xx
            total_progress = (
                progress_xy if total_progress is None else total_progress + progress_xy
            )
            total_class = class_xy if total_class is None else total_class + class_xy
            class_targets.append(target.reacquired)
        assert total_xx is not None
        assert total_progress is not None
        assert total_class is not None
        progress_beta = _fit_ridge(total_xx, total_progress)
        class_beta = (
            _fit_ridge(total_xx, total_class)
            if len(np.unique(np.concatenate(class_targets))) == 2
            else None
        )
        models[history] = (progress_beta, class_beta, targets)
    return models


def _bridge_records(
    data_by_seed: dict[int, _TraceData],
    traces_by_seed: dict[int, tuple[d025.D025TransitionTrace, ...]],
    full_models: dict[
        int, tuple[np.ndarray, np.ndarray | None, dict[int, _TargetData]]
    ],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for seed in D036_DEFAULT_DEVELOPMENT_SEEDS:
        trace = traces_by_seed[seed]
        for family in D036_BRIDGE_FAMILIES:
            for history in (4, 8, 16):
                selection = d034._find_trigger(trace, family, history)
                if selection is None:
                    records.append(
                        {
                            "seed": seed,
                            "family": family,
                            "history": history,
                            "status": "anchor_unavailable",
                        }
                    )
                    continue
                index = selection.transition - 2
                model = full_models[history]
                progress_beta, class_beta, targets = model
                feature = np.concatenate(
                    (
                        np.ones((1, 1)),
                        _feature_matrix(
                            data_by_seed[seed],
                            history,
                            np.asarray([index], dtype=np.int64),
                        ),
                    ),
                    axis=1,
                )
                predicted_progress = float((feature @ progress_beta)[0])
                predicted_reacquisition = (
                    float(_sigmoid(feature @ class_beta)[0])
                    if class_beta is not None
                    else None
                )
                target = targets[seed]
                match = np.flatnonzero(target.indices == index)
                actual_progress = (
                    float(target.progress[match[0]]) if len(match) else None
                )
                actual_reacquisition = (
                    bool(target.reacquired[match[0]]) if len(match) else None
                )
                records.append(
                    {
                        "seed": seed,
                        "family": family,
                        "history": history,
                        "status": "anchor_available",
                        "anchor_transition": selection.transition,
                        "feature_digest": _digest(feature.tolist()),
                        "predicted_future_progress": predicted_progress,
                        "predicted_reacquisition_probability": predicted_reacquisition,
                        "predicted_failure_probability": (
                            1.0 - predicted_reacquisition
                            if predicted_reacquisition is not None
                            else None
                        ),
                        "actual_future_progress": actual_progress,
                        "actual_reacquired": actual_reacquisition,
                        "d034_trigger_label_used_as_feature": False,
                        "d034_on_off_outcome_used_as_feature": False,
                    }
                )
    return records


def _strip_private(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _strip_private(item)
            for key, item in value.items()
            if not key.startswith("_")
        }
    if isinstance(value, list):
        return [_strip_private(item) for item in value]
    return value


def run_d036_audit(
    seeds: tuple[int, ...] | list[int] = D036_DEFAULT_DEVELOPMENT_SEEDS,
    *,
    horizon: int = D036_HORIZON,
    executed_commit_sha: str | None = None,
) -> dict[str, object]:
    validated = _validate_seeds(seeds)
    if horizon != D036_HORIZON:
        raise ValueError("D-036 requires the frozen 70,000-transition horizon")
    executed_sha = _validate_executed_commit_sha(executed_commit_sha)
    accepted = d033._accepted_artifact()
    data_by_seed: dict[int, _TraceData] = {}
    traces_by_seed: dict[int, tuple[d025.D025TransitionTrace, ...]] = {}
    replay_gates: list[dict[str, object]] = []
    for seed in validated:
        replay, _a_trace, b_trace, _anchor, _checks = d034._reference_replay_for_seed(
            seed, accepted
        )
        replay_gates.append(replay)
        traces_by_seed[seed] = b_trace
        data_by_seed[seed] = _trace_data(seed, traces_by_seed[seed])
    evaluations = {
        str(target_horizon): _evaluate_horizon(data_by_seed, target_horizon)
        for target_horizon in D036_TARGET_HORIZONS
    }
    bridge_by_horizon = {
        str(target_horizon): _bridge_records(
            data_by_seed,
            traces_by_seed,
            _full_models(data_by_seed, target_horizon),
        )
        for target_horizon in D036_TARGET_HORIZONS
    }
    return {
        "schema_version": 1,
        "experiment": "D-036",
        "title": "Shadow short-history scaffold-recruitment learnability audit",
        "authoritative_base_sha": D036_AUTHORITATIVE_BASE_SHA,
        "implementation_protocol_sha": executed_sha,
        "development_seeds": list(validated),
        "horizon": D036_HORIZON,
        "support": {
            "source": "accepted D-031R1 Arm-A/Arm-B replay via D-034/D-033 support",
            "accepted_artifact": D036_ACCEPTED_D031R1_ARTIFACT,
            "accepted_artifact_sha256": hashlib.sha256(
                (
                    Path(__file__).resolve().parents[2] / D036_ACCEPTED_D031R1_ARTIFACT
                ).read_bytes()
            ).hexdigest(),
            "fresh_development_or_exp_seeds_used": False,
        },
        "freeze": {
            "history_lengths": list(D036_HISTORY_LENGTHS),
            "target_horizons": list(D036_TARGET_HORIZONS),
            "feature_encoding": (
                "flattened visible-before observations and one-hot executed "
                "action; six channels and four action codes per completed transition"
            ),
            "feature_dimensions": {
                f"H{history}": history * _FEATURE_WIDTH_PER_STEP
                for history in D036_HISTORY_LENGTHS
            },
            "prefix_policy": (
                "unavailable prefixes are counted and excluded; no synthetic padding"
            ),
            "learner": (
                "ridge linear regression for progress; ridge linear classifier "
                "transformed by sigmoid for reacquisition only when training has "
                "both classes"
            ),
            "alpha_grid": list(D036_ALPHA_GRID),
            "alpha_policy": (
                "fixed 0.01 selected before official output; no held-out tuning"
            ),
            "split_policy": "leave-one-seed-out across all 20 reused seeds",
            "target_definition": (
                "actual continuation after the completed decision: reacquisition "
                "within H transitions and beacon-forward change from the "
                "post-action observation to the post-H observation"
            ),
            "null_policy": (
                "termination, truncation, and lifetime-boundary windows remain "
                "explicit and are excluded only from the corresponding fit/metric"
            ),
            "bridge": (
                "post-hoc read-only D-034 ALT_4/8/16 and "
                "NO_FORWARD_PROGRESS_4/8/16 anchors; no trigger labels or ON/OFF "
                "outcomes as features"
            ),
            "organism_boundary_unchanged": True,
        },
        "causal_order": [
            "exact accepted Arm-A/Arm-B replay gate",
            "ordinary Arm-B trace capture",
            "evaluator-only eligibility and bounded future target construction",
            "seed-held-out shadow fit and evaluation",
            "full-support read-only D-034 bridge diagnostic",
        ],
        "replay_gates": replay_gates,
        "trace_inventory": [
            {
                "seed": seed,
                "trace_digest": data.trace_digest,
                "transition_count": len(data.visible_before),
                "eligible_state_count": int(np.sum(data.eligible)),
                "terminated": data.terminated,
                "truncated": data.truncated,
                "visible_channels": list(d027.D027_CHANNELS),
                "actions": [action.name for action in Action],
            }
            for seed, data in data_by_seed.items()
        ],
        "evaluations": evaluations,
        "d034_bridge": bridge_by_horizon,
        "interpretation_categories": {
            "history_adds_learnable_information": (
                "one or more bounded histories consistently improve held-out "
                "prediction over H1 without a single-seed driver"
            ),
            "current_state_is_sufficient": (
                "H1 matches bounded-history models within ordinary sampling variation"
            ),
            "history_signal_weak_or_unstable": (
                "some folds improve but pooled/generalization evidence is inconsistent"
            ),
            "target_unsupported": (
                "class balance or causal support is insufficient; report "
                "null/untestable"
            ),
            "bridge_coherence": (
                "successful-recruitment anchors descriptively fall in a learned "
                "high-risk/low-progress region more often than matched non-anchor "
                "states"
            ),
            "no_bridge_coherence": (
                "learnability exists but does not align with D-034 "
                "recruitment-success states"
            ),
        },
        "interpretation": {
            "lane": "Development",
            "confirmatory_claim": False,
            "causal_organism_memory_authorized": False,
            "d035abc_candidate_later_retests": True,
            "headline": "Pending execution; descriptive held-out learnability only.",
        },
    }


def write_d036_json(path: Path, executed_commit_sha: str | None = None) -> Path:
    artifact = _strip_private(run_d036_audit(executed_commit_sha=executed_commit_sha))
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the D-036 shadow learnability audit."
    )
    parser.add_argument("--executed-commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_d036_json(args.output, args.executed_commit_sha)
    print(f"D-036 result written to {args.output}")


if __name__ == "__main__":
    main()
