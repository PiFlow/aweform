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

from . import d025, d026, d027, d032, d033, d034
from .env import Action
from .exp003_seed_policy import validate_exp003_development_seeds

D036_DEFAULT_DEVELOPMENT_SEEDS: Final[tuple[int, ...]] = tuple(range(18468, 18488))
D036_HORIZON: Final[int] = 70_000
D036_HISTORY_LENGTHS: Final[tuple[int, ...]] = (1, 4, 8, 16)
D036_TARGET_HORIZONS: Final[tuple[int, ...]] = (64, 256, 1024)
D036_ALPHA_GRID: Final[tuple[float, ...]] = (1.0e-6, 1.0e-4, 1.0e-2, 1.0)
D036_FIXED_ALPHA: Final[float] = 1.0e-2
D036_AUTHORITATIVE_BASE_SHA: Final[str] = "911acc5daefe2b1e3fcc7a683e9056740c6bca29"
D036_INVALIDATED_PROTOCOL_SHA: Final[str] = (
    "3675be49a640b519ac42d956692b93778362bf60"
)
D036_INVALIDATED_ARTIFACT_SHA256: Final[str] = (
    "81260bf42f80bf42204939dbf19c304e69d131576a0803f43c53bb78ba63e343"
)
D036_INVALIDATED_ARTIFACT_SIZE: Final[int] = 621472
D036_INVALIDATION_REASON: Final[str] = (
    "invalidated after exact-current-HEAD review found that the scored decision "
    "feature included its own executed action and the mandatory D-034 bridge "
    "lacked a deterministic matched non-anchor comparison"
)
D036_ADDITIONAL_INVALIDATED_PROTOCOL_SHA: Final[str] = (
    "ae1b47e3d35b6198143a2138a00ac081fd62db1a"
)
D036_ADDITIONAL_INVALIDATED_ARTIFACT_SHA256: Final[str] = (
    "32df6a73953b90e109fcccf11de42bbfda63c3da5b1be846081039c91f053366"
)
D036_ADDITIONAL_INVALIDATED_ARTIFACT_SIZE: Final[int] = 936163
D036_ADDITIONAL_INVALIDATION_REASON: Final[str] = (
    "invalidated after exact-current-HEAD review found that sample eligibility "
    "depended on the scored transition's mode_after and post-action charging "
    "contact, which are unavailable at the pre-action decision state and can "
    "censor decisions based on the predicted continuation"
)
D036_ACCEPTED_D031R1_ARTIFACT: Final[str] = d033.D033_ACCEPTED_D031R1_ARTIFACT
D036_BRIDGE_FAMILIES: Final[tuple[str, ...]] = (
    "ALT",
    "NO_FORWARD_PROGRESS",
)

_VISIBLE_WIDTH: Final[int] = len(d027.D027_CHANNELS)
_ACTION_WIDTH: Final[int] = len(Action)
_FEATURE_WIDTH_PER_STEP: Final[int] = _VISIBLE_WIDTH + _ACTION_WIDTH


def _feature_dimension(history: int) -> int:
    """Return the explicit current-observation plus completed-history width."""
    if history == 1:
        return _VISIBLE_WIDTH
    return _VISIBLE_WIDTH + history * _FEATURE_WIDTH_PER_STEP


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
    visible_after: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class _TargetData:
    indices: np.ndarray
    progress: np.ndarray
    reacquired: np.ndarray
    status_counts: dict[str, int]


def _visible(
    observation: d027.D027Observation | tuple[float, ...],
) -> tuple[float, ...]:
    if isinstance(observation, tuple):
        return observation
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
        [_visible(getattr(row, "observation_before")) for row in trace],
        dtype=float,
    )
    visible_after = np.asarray(
        [_visible(getattr(row, "observation")) for row in trace],
        dtype=float,
    )
    actions = np.asarray(
        [list(Action).index(cast(Action, getattr(row, "action"))) for row in trace],
        dtype=np.int8,
    )
    eligible = np.asarray(
        [
            getattr(row, "mode_before") is d026.D026Mode.SEEK
            and before[4] == 0.0
            for before, row in zip(visible_before, trace, strict=True)
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
        visible_after=visible_after,
    )


def _completed_visible(data: _TraceData, indices: np.ndarray) -> np.ndarray:
    """Return organism-visible observations after the completed transitions."""
    if data.visible_after is not None:
        return np.asarray(data.visible_after[indices], dtype=float)
    # Keep the small test fixture/backward-compatible private data shape useful.
    visible = data.visible_before[indices].copy()
    visible[:, 2] = data.visible_after_forward[indices]
    return np.asarray(visible, dtype=float)


def _feature_matrix(data: _TraceData, history: int, indices: np.ndarray) -> np.ndarray:
    if history not in D036_HISTORY_LENGTHS:
        raise ValueError(f"unsupported D-036 history length: {history}")
    if history == 1:
        return np.asarray(data.visible_before[indices], dtype=float)
    if np.any(indices < history):
        raise ValueError("history prefix is unavailable and must not be padded")
    rows: list[np.ndarray] = [data.visible_before[indices]]
    for offset in range(history, 0, -1):
        row_indices = indices - offset
        visible = _completed_visible(data, row_indices)
        actions = np.zeros((len(indices), _ACTION_WIDTH), dtype=float)
        actions[np.arange(len(indices)), data.actions[row_indices]] = 1.0
        rows.append(np.concatenate((visible, actions), axis=1))
    return np.concatenate(rows, axis=1)


def _future_status(data: _TraceData, index: int, horizon: int) -> str:
    if index + horizon > len(data.visible_after_forward):
        if data.terminated:
            return "termination"
        if data.truncated:
            return "truncation"
        return "null_lifetime_boundary"
    return "available"


def _target_data(data: _TraceData, history: int, horizon: int) -> _TargetData:
    eligible_indices = np.flatnonzero(data.eligible)
    minimum_index = 0 if history == 1 else history
    indices = eligible_indices[eligible_indices >= minimum_index]
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
                data.visible_after_forward[index + horizon - 1]
                - data.visible_before[index, 2]
            )
        )
        reacquired.append(
            bool(np.any(data.reacquisition[index : index + horizon]))
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
                "feature_dimension": _feature_dimension(history),
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
            "feature_dimension": _feature_dimension(history),
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


def _anchor_index(
    trace: tuple[d025.D025TransitionTrace, ...], selection: object
) -> int | None:
    transition = getattr(selection, "transition")
    for index, row in enumerate(trace):
        if row.transition_index == transition:
            return index
    return None


def _d034_anchor_indices(
    trace: tuple[d025.D025TransitionTrace, ...],
) -> set[int]:
    indices: set[int] = set()
    for family in D036_BRIDGE_FAMILIES:
        for history in (4, 8, 16):
            selection = d034._find_trigger(trace, family, history)
            if selection is not None:
                index = _anchor_index(trace, selection)
                if index is not None:
                    indices.add(index)
    return indices


def _matched_non_anchor_index(
    data: _TraceData,
    history: int,
    anchor_index: int,
    excluded_anchor_indices: set[int],
) -> int | None:
    minimum_index = 0 if history == 1 else history
    candidates = np.asarray(
        [
            int(index)
            for index in np.flatnonzero(data.eligible)
            if index >= minimum_index and int(index) not in excluded_anchor_indices
        ],
        dtype=np.int64,
    )
    if not len(candidates):
        return None
    anchor_feature = _feature_matrix(
        data, history, np.asarray([anchor_index], dtype=np.int64)
    )[0]
    candidate_features = _feature_matrix(data, history, candidates)
    distances = np.sum((candidate_features - anchor_feature) ** 2, axis=1)
    order = np.lexsort((candidates, distances))
    return int(candidates[order[0]])


def _prediction(
    data: _TraceData,
    history: int,
    index: int,
    model: tuple[np.ndarray, np.ndarray | None, dict[int, _TargetData]],
) -> tuple[float, float | None]:
    progress_beta, class_beta, _ = model
    feature = np.concatenate(
        (
            np.ones((1, 1)),
            _feature_matrix(data, history, np.asarray([index], dtype=np.int64)),
        ),
        axis=1,
    )
    predicted_progress = float((feature @ progress_beta)[0])
    predicted_reacquisition = (
        float(_sigmoid(feature @ class_beta)[0]) if class_beta is not None else None
    )
    return predicted_progress, predicted_reacquisition


def _actual_target(
    target: _TargetData, index: int
) -> tuple[float | None, bool | None, str]:
    match = np.flatnonzero(target.indices == index)
    if len(match):
        position = int(match[0])
        return (
            float(target.progress[position]),
            bool(target.reacquired[position]),
            "available",
        )
    return None, None, "null_or_unavailable"


def _bridge_summary(records: list[dict[str, object]]) -> dict[str, object]:
    available = [
        record for record in records if record.get("status") == "anchor_available"
    ]
    matched = [
        record
        for record in available
        if record.get("matched_non_anchor_status") == "matched"
    ]
    progress_pairs = [
        record
        for record in matched
        if record.get("anchor_predicted_future_progress") is not None
        and record.get("matched_predicted_future_progress") is not None
    ]
    progress_lower = [
        record
        for record in progress_pairs
        if cast(float, record["anchor_predicted_future_progress"])
        < cast(float, record["matched_predicted_future_progress"])
    ]
    risk_pairs = [
        record
        for record in progress_pairs
        if record.get("anchor_predicted_failure_probability") is not None
        and record.get("matched_predicted_failure_probability") is not None
    ]
    coherent_pairs = [
        record
        for record in risk_pairs
        if cast(float, record["anchor_predicted_future_progress"])
        < cast(float, record["matched_predicted_future_progress"])
        and cast(float, record["anchor_predicted_failure_probability"])
        > cast(float, record["matched_predicted_failure_probability"])
    ]
    per_seed: dict[str, dict[str, object]] = {}
    for seed in D036_DEFAULT_DEVELOPMENT_SEEDS:
        seed_records = [record for record in records if record.get("seed") == seed]
        seed_progress = [
            record for record in progress_pairs if record.get("seed") == seed
        ]
        seed_risk = [record for record in risk_pairs if record.get("seed") == seed]
        seed_coherent = [
            record for record in coherent_pairs if record.get("seed") == seed
        ]
        per_seed[str(seed)] = {
            "anchor_records": len(seed_records),
            "anchor_available": sum(
                record.get("status") == "anchor_available" for record in seed_records
            ),
            "matched_non_anchor_available": sum(
                record.get("matched_non_anchor_status") == "matched"
                for record in seed_records
            ),
            "progress_comparison_count": len(seed_progress),
            "anchor_lower_predicted_progress_count": sum(
                cast(float, record["anchor_predicted_future_progress"])
                < cast(float, record["matched_predicted_future_progress"])
                for record in seed_progress
            ),
            "high_risk_low_progress_comparison_count": len(seed_coherent),
            "high_risk_low_progress_comparison_denominator": len(seed_risk),
            "mean_predicted_progress_delta_anchor_minus_match": (
                float(
                    np.mean(
                        [
                            cast(float, record["anchor_predicted_future_progress"])
                            - cast(float, record["matched_predicted_future_progress"])
                            for record in seed_progress
                        ]
                    )
                )
                if seed_progress
                else None
            ),
        }
    risk_fraction = len(coherent_pairs) / len(risk_pairs) if risk_pairs else None
    return {
        "matching_rule": (
            "Within the same seed, use eligible ordinary false-contact SEEK decision "
            "states with the required completed prefix, exclude every D-034 anchor "
            "index, minimize squared distance on the current visible observation plus "
            "prior completed visible/action rows, and break ties by smallest trace "
            "index. No target, D-034 label/outcome, or hidden state is used."
        ),
        "availability": {
            "record_count": len(records),
            "anchor_available_count": len(available),
            "anchor_unavailable_count": sum(
                record.get("status") == "anchor_unavailable" for record in records
            ),
            "matched_non_anchor_available_count": len(matched),
            "matched_non_anchor_unavailable_count": sum(
                record.get("matched_non_anchor_status") == "unavailable"
                for record in records
            ),
            "target_null_count": sum(
                record.get("anchor_target_status") != "available"
                or record.get("matched_target_status") != "available"
                for record in matched
            ),
        },
        "per_seed": per_seed,
        "pooled": {
            "matched_pair_count": len(matched),
            "progress_comparison_count": len(progress_pairs),
            "anchor_lower_predicted_progress_count": len(progress_lower),
            "anchor_lower_predicted_progress_fraction": (
                len(progress_lower) / len(progress_pairs) if progress_pairs else None
            ),
            "mean_predicted_progress_delta_anchor_minus_match": (
                float(
                    np.mean(
                        [
                            cast(float, record["anchor_predicted_future_progress"])
                            - cast(float, record["matched_predicted_future_progress"])
                            for record in progress_pairs
                        ]
                    )
                )
                if progress_pairs
                else None
            ),
            "high_risk_low_progress_comparison_count": len(coherent_pairs),
            "high_risk_low_progress_comparison_denominator": len(risk_pairs),
            "high_risk_low_progress_fraction": risk_fraction,
            "bridge_coherence": (
                risk_fraction > 0.5 if risk_fraction is not None else None
            ),
            "no_bridge_coherence": (
                risk_fraction <= 0.5 if risk_fraction is not None else None
            ),
            "binary_bridge_status": (
                "untestable_binary_target" if not risk_pairs else "available"
            ),
        },
    }


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
        excluded_anchor_indices = _d034_anchor_indices(trace)
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
                index = _anchor_index(trace, selection)
                if index is None:
                    records.append(
                        {
                            "seed": seed,
                            "family": family,
                            "history": history,
                            "status": "anchor_unavailable",
                            "anchor_unavailable_reason": "transition_not_in_trace",
                        }
                    )
                    continue
                model = full_models[history]
                _, _, targets = model
                matched_index = _matched_non_anchor_index(
                    data_by_seed[seed], history, index, excluded_anchor_indices
                )
                predicted_progress, predicted_reacquisition = _prediction(
                    data_by_seed[seed], history, index, model
                )
                target = targets[seed]
                actual_progress, actual_reacquisition, target_status = _actual_target(
                    target, index
                )
                record: dict[str, object] = {
                    "seed": seed,
                    "family": family,
                    "history": history,
                    "status": "anchor_available",
                    "anchor_transition": selection.transition,
                    "anchor_trace_index": index,
                    "anchor_feature_digest": _digest(
                        _feature_matrix(
                            data_by_seed[seed],
                            history,
                            np.asarray([index], dtype=np.int64),
                        ).tolist()
                    ),
                    "anchor_predicted_future_progress": predicted_progress,
                    "anchor_predicted_reacquisition_probability": (
                        predicted_reacquisition
                    ),
                    "anchor_predicted_failure_probability": (
                        1.0 - predicted_reacquisition
                        if predicted_reacquisition is not None
                        else None
                    ),
                    "anchor_actual_future_progress": actual_progress,
                    "anchor_actual_reacquired": actual_reacquisition,
                    "anchor_target_status": target_status,
                    "d034_trigger_label_used_as_feature": False,
                    "d034_on_off_outcome_used_as_feature": False,
                }
                if matched_index is None:
                    record.update(
                        {
                            "matched_non_anchor_status": "unavailable",
                            "matched_non_anchor_transition": None,
                            "matched_target_status": "null_or_unavailable",
                        }
                    )
                else:
                    matched_progress, matched_reacquisition = _prediction(
                        data_by_seed[seed], history, matched_index, model
                    )
                    (
                        matched_actual_progress,
                        matched_actual_reacquisition,
                        matched_status,
                    ) = _actual_target(
                        target,
                        matched_index,
                    )
                    record.update(
                        {
                            "matched_non_anchor_status": "matched",
                            "matched_non_anchor_transition": trace[
                                matched_index
                            ].transition_index,
                            "matched_non_anchor_trace_index": matched_index,
                            "matched_feature_digest": _digest(
                                _feature_matrix(
                                    data_by_seed[seed],
                                    history,
                                    np.asarray([matched_index], dtype=np.int64),
                                ).tolist()
                            ),
                            "matched_predicted_future_progress": matched_progress,
                            "matched_predicted_reacquisition_probability": (
                                matched_reacquisition
                            ),
                            "matched_predicted_failure_probability": (
                                1.0 - matched_reacquisition
                                if matched_reacquisition is not None
                                else None
                            ),
                            "matched_actual_future_progress": matched_actual_progress,
                            "matched_actual_reacquired": matched_actual_reacquisition,
                            "matched_target_status": matched_status,
                            "predicted_progress_delta_anchor_minus_match": (
                                predicted_progress - matched_progress
                            ),
                            "predicted_failure_probability_delta_anchor_minus_match": (
                                (1.0 - predicted_reacquisition)
                                - (1.0 - matched_reacquisition)
                                if predicted_reacquisition is not None
                                and matched_reacquisition is not None
                                else None
                            ),
                        }
                    )
                records.append(record)
    return records


def _exact_replay_for_seed(
    seed: int, accepted: dict[str, object]
) -> tuple[dict[str, object], tuple[d025.D025TransitionTrace, ...]]:
    """Gate one instrumented replay of each accepted arm and retain Arm-B."""
    arm_records: dict[str, object] = {}
    traces: tuple[d025.D025TransitionTrace, ...] | None = None
    for role, arm in (("A", "LEARNED_WITH_DETRAP"), ("B", "LEARNED_NO_DETRAP")):
        result, trace, _ = d033._run_capture(
            seed,
            role=role,
            horizon=D036_HORIZON,
            seed_validator=_validate_seed,
        )
        if role == "B":
            traces = trace
        expected = dict(d033._accepted_arm(accepted, seed, arm))
        expected["_weights"] = d033._flatten_final_weights(expected)
        comparison = d032._compare_identity_fields(
            result, expected, include_private_weights=True
        )
        if not bool(comparison["all_identity_fields_exact"]):
            raise RuntimeError(f"D-036 accepted {arm} replay gate failed for {seed}")
        arm_records[arm] = {
            "seed": seed,
            "arm": arm,
            "all_identity_fields_exact": True,
            "checked_identity_fields": comparison["checked_fields"],
            "mismatched_identity_fields": comparison["mismatched_fields"],
            "instrumented_replay_exact": True,
        }
    if traces is None:
        raise RuntimeError("D-036 Arm-B replay trace was not captured")
    return arm_records, traces


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
        replay, b_trace = _exact_replay_for_seed(seed, accepted)
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
    bridge_summaries = {
        horizon: _bridge_summary(records)
        for horizon, records in bridge_by_horizon.items()
    }
    return {
        "schema_version": 2,
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
        "invalidated_prior_output": {
            "implementation_protocol_sha": D036_INVALIDATED_PROTOCOL_SHA,
            "artifact_sha256": D036_INVALIDATED_ARTIFACT_SHA256,
            "artifact_size_bytes": D036_INVALIDATED_ARTIFACT_SIZE,
            "reason": D036_INVALIDATION_REASON,
        },
        "additional_invalidated_outputs": [
            {
                "implementation_protocol_sha": D036_ADDITIONAL_INVALIDATED_PROTOCOL_SHA,
                "artifact_sha256": D036_ADDITIONAL_INVALIDATED_ARTIFACT_SHA256,
                "artifact_size_bytes": D036_ADDITIONAL_INVALIDATED_ARTIFACT_SIZE,
                "reason": D036_ADDITIONAL_INVALIDATION_REASON,
            }
        ],
        "freeze": {
            "history_lengths": list(D036_HISTORY_LENGTHS),
            "target_horizons": list(D036_TARGET_HORIZONS),
            "eligibility": (
                "pre-action decision state only: mode_before is SEEK and the "
                "current visible charging_contact is false; mode_after and all "
                "post-action/current-transition outcomes are ignored"
            ),
            "feature_encoding": (
                "H1 is the current six-channel visible-before observation only; "
                "H4/H8/H16 append the prior 4/8/16 completed one-hot "
                "executed-action and post-action visible-observation pairs"
            ),
            "feature_dimensions": {
                f"H{history}": _feature_dimension(history)
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
                "actual causal continuation from each eligible pre-action decision: "
                "reacquisition within H transitions and beacon-forward change from "
                "the current pre-action observation to the final observation in the "
                "unchanged H-transition continuation"
            ),
            "null_policy": (
                "termination, truncation, and lifetime-boundary windows remain "
                "explicit and are excluded only from the corresponding fit/metric"
            ),
            "bridge": (
                "post-hoc read-only D-034 ALT_4/8/16 and "
                "NO_FORWARD_PROGRESS_4/8/16 anchors, each paired within seed to the "
                "nearest eligible non-anchor ordinary-support feature vector with "
                "smallest-index tie break; no trigger labels or ON/OFF outcomes as "
                "features"
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
        "d034_bridge_summary": bridge_summaries,
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
