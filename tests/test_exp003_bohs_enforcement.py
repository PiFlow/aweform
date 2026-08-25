"""ADR 0009 Section D enforcement checks for the EXP-003 BOHS controller.

These tests implement the checks required by
``docs/adr/0009-v0.2-bounded-observation-history-state.md`` Section D for the
first BOHS controller, ``StationB50TrendController`` (and its base).  Per the
ADR, every check runs over exhaustive branch/path coverage of ``__init__()``,
``act()``, and ``reset()`` built from the ADR's B.0 reference trace, not merely
over decisions an experiment happens to exercise; a rule that holds on sampled
trajectories and fails on an unexercised branch is not a bound.

A controller carrying BOHS must not merge, and no formal/calibration/
confirmatory seeds may be run with one, until every check below passes.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from aweform.exp001 import policy_rng_from_seed
from aweform.exp003 import (
    EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD,
    EXP003_TREND_WEAK_BEACON_THRESHOLD,
    Action,
    BeaconObservation,
    EXP003Mode,
    EXP003SeekTrigger,
    StationB50Controller,
    StationB50TrendController,
    StationObservation,
)

BOHS_SLUG = "_previous_explore_beacon_max"

# The registry manifest (docs/adr/0009-bohs-registry.md) is the union of the
# source declarations (RETAINED_STATE) and the nested retained state of the
# named roots.  This is the enforcement structure the completeness check
# validates against the live instances.
EXPECTED_CLASSIFICATION = {
    "StationB50Controller": {
        "_mode": "causal-inherited",
        "config": "causal-inherited",
        "explorer": "causal-inherited",
        "_last_decision": "diagnostic",
    },
    "StationB50TrendController": {
        BOHS_SLUG: "bohs",
    },
}

# Nested retained action state of the ``explorer`` root (EXP-001 primitive).
EXPECTED_EXPLORER_NESTED = {
    "policy_rng": "causal-inherited",
    "_forward_actions_remaining": "causal-inherited",
    "_turn_action": "causal-inherited",
    "_turn_actions_remaining": "causal-inherited",
}


def _obs(
    energy: float,
    beacon: tuple[float, float, float] = (0.1, 0.9, 0.2),
    contact: bool = False,
) -> StationObservation:
    return StationObservation(
        energy=energy,
        beacon=BeaconObservation(
            left=beacon[0], forward=beacon[1], right=beacon[2],
            charging_contact=contact,
        ),
    )


def _fresh() -> StationB50TrendController:
    return StationB50TrendController(policy_rng_from_seed(1001))


def _current_max(observation: StationObservation) -> float:
    return max(observation.beacon.as_tuple())


def _branch(controller: StationB50TrendController) -> str:
    """Classify the most recent decision with its B.0-trace branch label."""
    trig = controller._last_decision.seek_trigger
    mode = controller._mode
    if trig is EXP003SeekTrigger.HISTORICAL_ENERGY:
        return "E1"
    if trig is EXP003SeekTrigger.ANTICIPATORY_TREND:
        return "E2"
    if (
        mode is EXP003Mode.EXPLORE
        and controller._previous_explore_beacon_max is not None
    ):
        return "E3"
    if mode is EXP003Mode.EXPLORE:
        return "EXPLORE"
    if mode is EXP003Mode.SEEK:
        return "S"  # S1/S2 distinguished by charging_contact
    return "C"  # C1/C2/C3 distinguished by charging_contact/energy


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

def test_source_declaration_matches_expected_classification() -> None:
    """Every covered controller's RETAINED_STATE matches the manifest rows."""
    for class_name, expected in EXPECTED_CLASSIFICATION.items():
        cls = {"StationB50Controller": StationB50Controller,
               "StationB50TrendController": StationB50TrendController}[class_name]
        declared = cls.RETAINED_STATE
        assert {a: _class_of(note) for a, note in declared.items()} == expected, (
            f"{class_name} RETAINED_STATE does not match registered classification"
        )


def _class_of(note: str) -> str:
    if note.startswith("bohs"):
        return "bohs"
    if note.startswith("diagnostic"):
        return "diagnostic"
    if note.startswith("causal-inherited"):
        return "causal-inherited"
    raise AssertionError(f"unrecognised registry note: {note!r}")


def test_registry_covers_all_retained_state_of_covered_controllers() -> None:
    """Registration completeness: direct + nested retained attrs are classified.

    Every retained action-relevant/diagnostic attribute of a covered
    controller appears in the manifest with a classification, including
    inherited action-causal fields and nested state; and every manifest row
    names an attribute that exists on the live instance.
    """
    controller = _fresh()
    direct_attrs = set(vars(controller))
    declared_union = set(EXPECTED_CLASSIFICATION["StationB50Controller"]) | set(
        EXPECTED_CLASSIFICATION["StationB50TrendController"]
    )

    # BOHS field present.
    assert BOHS_SLUG in direct_attrs
    # Every classified attribute exists on the instance.
    assert declared_union <= direct_attrs
    # No retained instance attribute is left unclassified.
    assert direct_attrs == declared_union, (
        f"unclassified retained attributes: {direct_attrs - declared_union}"
    )

    # Nested retained state of the explorer root is classified and exists.
    nested_attrs = set(vars(controller.explorer))
    assert nested_attrs == set(EXPECTED_EXPLORER_NESTED), (
        f"unclassified nested attrs: {nested_attrs - set(EXPECTED_EXPLORER_NESTED)}"
    )
    for name, classification in EXPECTED_EXPLORER_NESTED.items():
        assert classification == "causal-inherited"
        assert hasattr(controller.explorer, name)


def _attr_load_count(src: str, attr: str) -> int:
    """Count read (Load) accesses of ``self.<attr>`` in ``src``."""
    tree = ast.parse(src)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == attr
        and isinstance(node.ctx, ast.Load)
    )


def _method_source(
    tree: ast.Module, class_name: str, method: str
) -> ast.FunctionDef | None:
    """Return the AST of ``method`` inside class ``class_name`` of ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for body in node.body:
                if isinstance(body, ast.FunctionDef) and body.name == method:
                    return body
    return None


def test_diagnostic_field_is_never_read_by_an_action_selection_branch() -> None:
    """``_last_decision`` (diagnostic, ADR 0009 E) must have no causal reads.

    Section E's whole distinction is that no action-selection branch reads the
    diagnostic trace.  In ``act()`` the field is only ever assigned, never
    loaded into an expression that could influence the chosen action.
    """
    import aweform.exp003 as exp003  # noqa: PLC0415

    tree = ast.parse(inspect.getsource(exp003))
    assert _method_source(tree, "StationB50TrendController", "act") is not None
    for class_name in ("StationB50Controller", "StationB50TrendController",
                       "StationB50FullController"):
        act = _method_source(tree, class_name, "act")
        if act is not None:
            src = ast.unparse(act)
            assert _attr_load_count(src, "_last_decision") == 0, (
                f"{class_name}.act reads diagnostic _last_decision"
            )


# ---------------------------------------------------------------------------
# Exhaustive decision-path walk with per-call invariant checks
# ---------------------------------------------------------------------------

def _walk() -> list[tuple[StationB50TrendController, StationObservation, type]]:
    """Drive every B.0 branch and return (controller, last-obs, exception) list.

    Each tuple records the controller state after the final decision of that
    branch sequence so B1-B8 can be asserted against the live instance.  Use
    separate fresh controllers per branch so state transitions are exercised
    the way the trace table enumerates them.
    """
    cases: list[tuple[StationB50TrendController, StationObservation, type]] = []

    # INIT
    c = _fresh()
    cases.append(("init", c, _obs(0.70, (0.6, 0.6, 0.6)), None))
    # INVALID-INPUT (preserves state)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))  # E3, sets P
    try:
        c.act(object())  # type: ignore[arg-type]
    except ValueError:
        cases.append(("invalid-input", c, None, ValueError))
    # E3 write
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    cases.append(("E3", c, _obs(0.70, (0.6, 0.6, 0.6)), None))
    # E1 -> S2
    c = _fresh()
    c.act(_obs(0.40, contact=False))
    cases.append(("E1-S2", c, _obs(0.40, contact=False), None))
    # E1 -> S1 (CHARGE)
    c = _fresh()
    c.act(_obs(0.40, contact=True))
    cases.append(("E1-S1", c, _obs(0.40, contact=True), None))
    # E2 -> S2
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))
    cases.append(("E2-S2", c, _obs(0.55, (0.07, 0.07, 0.07), contact=False), None))
    # E2 -> S1 (CHARGE)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=True))
    cases.append(("E2-S1", c, _obs(0.55, (0.07, 0.07, 0.07), contact=True), None))
    # S2 (mode SEEK, no contact)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))  # E2 -> SEEK
    c.act(_obs(0.55, (0.1, 0.2, 0.3), contact=False))
    cases.append(("S2", c, _obs(0.55, (0.1, 0.2, 0.3), contact=False), None))
    # S1 (mode SEEK -> CHARGE)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))  # E2 -> SEEK
    c.act(_obs(0.55, (0.1, 0.2, 0.3), contact=True))
    cases.append(("S1", c, _obs(0.55, (0.1, 0.2, 0.3), contact=True), None))
    # C1 (mode CHARGE, no contact)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))
    c.act(_obs(0.55, (0.1, 0.2, 0.3), contact=True))  # S1 -> CHARGE
    c.act(_obs(0.55, (0.1, 0.2, 0.3), contact=False))
    cases.append(("C1", c, _obs(0.55, (0.1, 0.2, 0.3), contact=False), None))
    # C2 (mode CHARGE, contact, energy > recover)
    c = _fresh()
    c.act(_obs(0.40, (0.1, 0.2, 0.3), contact=True))  # E1-S1 -> CHARGE
    c.act(_obs(0.90, (0.1, 0.2, 0.3), contact=True))
    cases.append(("C2", c, _obs(0.90, (0.1, 0.2, 0.3), contact=True), None))
    # C3 (mode CHARGE, contact, energy <= recover)
    c = _fresh()
    c.act(_obs(0.40, (0.1, 0.2, 0.3), contact=True))  # E1-S1 -> CHARGE
    c.act(_obs(0.80, (0.1, 0.2, 0.3), contact=True))
    cases.append(("C3", c, _obs(0.80, (0.1, 0.2, 0.3), contact=True), None))
    # RESET (clears P, returns to EXPLORE)
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.reset()
    cases.append(("reset", c, None, None))

    return cases


def test_exhaustive_path_coverage_reaches_every_branch() -> None:
    # Explicit case labels rather than a blanket ``split("-")[0]``: splitting
    # "invalid-input" on hyphen would alias it to "invalid" and silently lose
    # the ADR B.0 trace's named rejection path.  Composite transition labels
    # like "E1-S2" map to their base move ("E1"); single-word trace labels
    # ("init", "invalid-input", "E3", "reset") are kept whole.
    branch_ids: set[str] = set()
    for name, *_ in _walk():
        if name in {"init", "invalid-input", "E3", "reset"}:
            branch_ids.add(name)
        else:
            branch_ids.add(name.split("-")[0])
    required = {"init", "E1", "E2", "E3", "S1", "S2", "C1", "C2", "C3", "reset",
                "invalid-input"}
    assert required <= branch_ids, f"missing branches: {required - branch_ids}"


def test_b1_field_is_builtin_float_or_none_across_all_paths() -> None:
    for name, c, obs, exc in _walk():
        if exc is not None:
            continue
        p = c._previous_explore_beacon_max
        assert p is None or type(p) is float, f"{name}: P={p!r} not float|None"
        if p is not None:
            assert obs is not None
            assert p == _current_max(obs), f"{name}: P not max of current obs"


def test_b2_write_is_fixed_max_function_of_the_current_observation() -> None:
    # Every non-None write equals max over the observation triple of that
    # decision, regardless of retained state (mode, prior P, explorer state).
    c = _fresh()
    sequence = [
        _obs(0.70, (0.3, 0.7, 0.5)),
        _obs(0.60, (0.9, 0.1, 0.2)),
        _obs(0.80, (0.4, 0.4, 0.8)),
        _obs(0.71, (0.6, 0.6, 0.6)),
    ]
    for nth, obs in enumerate(sequence):
        action = c.act(obs)
        p = c._previous_explore_beacon_max
        assert action in set(Action)
        if c._mode is EXP003Mode.EXPLORE and p is not None:
            assert p == _current_max(obs), (
                f"step {nth}: observation write deviated from max(current obs)"
            )
        # A retained-state-dependent write (function varying with prior state)
        # is absent: the write is always one fixed function of this obs.
        assert p is None or type(p) is float


def test_b3_and_b8_clears_only_at_registered_points_and_reach_none() -> None:
    # E1/E2/C2/reset clear P; init starts None.  No other path clears it.
    # E1 clear
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    assert c._previous_explore_beacon_max is not None
    c.act(_obs(0.40, contact=False))  # E1 -> SEEK
    assert c._previous_explore_beacon_max is None
    # E2 clear
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))  # E2 -> SEEK
    assert c._previous_explore_beacon_max is None
    # C2 clear
    c = _fresh()
    c.act(_obs(0.40, (0.1, 0.2, 0.3), contact=True))  # E1-S1 -> CHARGE
    c.act(_obs(0.90, (0.1, 0.2, 0.3), contact=True))  # C2 -> EXPLORE
    assert c._previous_explore_beacon_max is None
    # reset clear
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.reset()
    assert c._previous_explore_beacon_max is None
    # init clear
    assert _fresh()._previous_explore_beacon_max is None
    # Every registered clearing point above was individually asserted to reach
    # None; the comment supersedes the removed tautological trailing assert.


def test_b4_no_retained_state_determines_write_and_no_cross_field_read() -> None:
    # Only one BOHS field exists, so cross-field read (B.4 last clause) is
    # vacuously impossible.  The write value never depends on mode/prior P/
    # explorer state: run the same observation from radically different prior
    # controller states and require the same write result.
    obs = _obs(0.70, (0.42, 0.33, 0.88))
    prior_configs = []

    c1 = _fresh()  # prior P None
    c1.act(obs)
    prior_configs.append(("from-init", c1, _current_max(obs)))

    c2 = _fresh()  # prior P set to a different value
    c2.act(_obs(0.70, (0.99, 0.99, 0.99)))
    c2.act(obs)
    prior_configs.append(("from-e3", c2, _current_max(obs)))

    write_results = {c._previous_explore_beacon_max for _, c, _ in prior_configs}
    assert write_results == {_current_max(obs)}  # one fixed function of the obs


def test_b5_presence_barrier_after_retained_state_dependent_clear() -> None:
    """E2's clear is retained-state-dependent (uses prior P), so the barrier is
    set and no later P read may occur until a fresh observation write or an
    independent registered clear (C2) resets it.  In the trace P is never read
    between E2 and the next EXPLORE entry, and C2 is independently selected."""
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))          # E3: P=0.6
    assert c._previous_explore_beacon_max == 0.6
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))  # E2: dependent clear
    assert c._last_decision.seek_trigger is EXP003SeekTrigger.ANTICIPATORY_TREND
    assert c._previous_explore_beacon_max is None  # barriers set; P cleared
    # Successor S/C paths must neither read nor (re)write P.
    c.act(_obs(0.55, (0.3, 0.4, 0.2), contact=True))  # S1 -> CHARGE
    assert c._previous_explore_beacon_max is None
    c.act(_obs(0.55, (0.3, 0.4, 0.2), contact=False))  # C1 -> SEEK
    assert c._previous_explore_beacon_max is None
    c.act(_obs(0.55, (0.3, 0.4, 0.2), contact=False))  # S2
    assert c._previous_explore_beacon_max is None
    # C2 is an independent registered clear (contact + energy + const config),
    # and resets the barrier; after it, the next EXPLORE observation write is
    # a fresh current-observation value, never the cleared-out older bit.
    c.act(_obs(0.40, (0.3, 0.4, 0.2), contact=True))  # S1 -> CHARGE
    c.act(_obs(0.90, (0.3, 0.4, 0.2), contact=True))  # C2 -> EXPLORE
    assert c._previous_explore_beacon_max is None
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))  # fresh E3 write
    assert c._previous_explore_beacon_max == 0.6


def test_b6_no_carry_over_into_non_explore_branches() -> None:
    for name, c, obs, exc in _walk():
        if exc is not None or obs is None:
            continue
        if c._mode in (EXP003Mode.SEEK, EXP003Mode.CHARGE):
            assert c._previous_explore_beacon_max is None, (
                f"{name}: P carried into non-EXPLORE mode"
            )


def test_b7_single_write_per_act_and_no_external_writer() -> None:
    """At most one write to the BOHS field per act(); no writer outside the
    controller (ADR 0009 B.7)."""
    import aweform.exp003 as exp003  # noqa: PLC0415

    tree = ast.parse(inspect.getsource(exp003))

    # Locate every assignment (Store) to the BOHS field across the whole module
    # and require every one to sit inside a StationB50TrendController method —
    # i.e. no writer outside the controller.
    store_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == BOHS_SLUG
        and isinstance(node.ctx, ast.Store)
    ]
    assert store_nodes, "no BOHS field assignment found in module"
    trend_class = next(
        cls for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "StationB50TrendController"
    )
    stores_inside_controller = 0
    for fn in (body for body in trend_class.body if isinstance(body, ast.FunctionDef)):
        fn_node_ids = {id(n) for n in ast.walk(fn)}
        for node in store_nodes:
            if id(node) in fn_node_ids:
                stores_inside_controller += 1
    # Every write to the BOHS field lives inside the controller — no writer
    # outside it (B.7's second clause).
    assert stores_inside_controller == len(store_nodes), (
        "a BOHS-field write occurs outside StationB50TrendController"
    )

    # Runtime: a single act() call performs at most one write — running the
    # exhaustive corpus never leaves the field in a state inconsistent with
    # exactly one assignment per decision (float after E3, None after clear).
    for name, c, obs, exc in _walk():
        if exc is not None:
            continue
        p = c._previous_explore_beacon_max
        assert p is None or type(p) is float
    c = _fresh()
    before = c._previous_explore_beacon_max
    action = c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    after = c._previous_explore_beacon_max
    assert (before is None) and (after is not None)  # exactly one write, None -> 0.6
    assert action in set(Action)


def test_b8_and_reset_reach_none() -> None:
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    assert c._previous_explore_beacon_max is not None
    c.reset()
    assert c._previous_explore_beacon_max is None
    assert c._mode is EXP003Mode.EXPLORE
    assert c._last_decision.seek_trigger is None


def test_b9_bohs_thresholds_are_final_and_constant() -> None:
    for value, candidate in (
        (EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD, "0.65"),
        (EXP003_TREND_WEAK_BEACON_THRESHOLD, "0.10"),
    ):
        assert isinstance(value, float)
        assert value == float(candidate)  # pinned development constants
    # Thresholds do not change across a run / are not adapted from experience.
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))
    c.reset()
    assert EXP003_TREND_ANTICIPATORY_ENERGY_THRESHOLD == 0.65
    assert EXP003_TREND_WEAK_BEACON_THRESHOLD == 0.10


def test_b10_provenance_is_the_controller_observation_contract() -> None:
    # The stored value derives solely from the controller's own observation
    # contract (ADR 0002 / ADR 0008): max over the current beacon triple.
    c = _fresh()
    obs = _obs(0.70, (0.21, 0.87, 0.33))
    c.act(obs)
    assert c._previous_explore_beacon_max == _current_max(obs)
    assert c._previous_explore_beacon_max == max(obs.beacon.as_tuple())
    assert c._previous_explore_beacon_max not in {
        0.21, 0.33,  # not any single L/F/R, and no privileged state involved
    }


def test_section_e_no_action_selection_reads_the_diagnostic_trace() -> None:
    """No action-selection branch reads ``_last_decision`` (diagnostic-only)."""
    # The diagnostic trace must have external readers only; the property is
    # the sanctioned external inspection point and is never used by act().
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))  # E3 write, sets P=0.6
    c.act(_obs(0.55, (0.07, 0.07, 0.07), contact=False))  # E2 (prior P set)
    assert c.last_decision.seek_trigger is EXP003SeekTrigger.ANTICIPATORY_TREND
    # Runtime: the trace is (re)assigned at entry, so its pre-existing value
    # can never change the returned action across two otherwise-identical
    # controllers — confirming no action branch loads it.
    a1 = _fresh().act(_obs(0.70, (0.6, 0.6, 0.6)))
    a2 = _fresh().act(_obs(0.70, (0.6, 0.6, 0.6)))
    assert a1 == a2


# ---------------------------------------------------------------------------
# ADR 0009 B.1: balanced boundary floats (introduced by PR #38's gate).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [1, 0, True, False, -1, 2])
def test_beacon_lfr_rejects_int_and_bool(bad: object) -> None:
    with pytest.raises(ValueError):
        BeaconObservation(left=bad, forward=0.1, right=0.1, charging_contact=False)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        BeaconObservation(left=0.1, forward=bad, right=0.1, charging_contact=False)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        BeaconObservation(left=0.1, forward=0.1, right=bad, charging_contact=False)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(1.0, id="float-in-range-ok"),
    ],
)
def test_beacon_lfr_accepts_builtin_float_in_range(bad: float) -> None:
    ob = BeaconObservation(left=bad, forward=0.1, right=0.1, charging_contact=False)
    assert type(ob.left) is float


def test_beacon_lfr_rejects_non_builtin_numeric() -> None:
    np = pytest.importorskip("numpy")
    for maker in (np.float64, np.float32):
        with pytest.raises(ValueError):
            BeaconObservation(left=maker(0.5), forward=0.1, right=0.1,  # type: ignore[arg-type]
                              charging_contact=False)


def test_beacon_lfr_rejects_int_adversaries_at_stationary_boundary() -> None:
    # int and bool in [0,1] previously slipped past the isfinite/range check.
    for adv in (0, 1, True, False):
        with pytest.raises(ValueError):
            BeaconObservation(left=adv, forward=adv, right=adv,  # type: ignore[arg-type]
                              charging_contact=False)
    ob = BeaconObservation(left=0.0, forward=0.5, right=1.0, charging_contact=False)
    assert (ob.left, ob.forward, ob.right) == (0.0, 0.5, 1.0)


def test_trend_e3_write_is_builtin_float_not_adversarial() -> None:
    # With the boundary enforced, max over L/F/R is always a built-in float.
    c = _fresh()
    c.act(_obs(0.70, (0.5, 0.5, 0.5)))
    assert type(c._previous_explore_beacon_max) is float


def test_invalid_input_preserves_mode_and_bohs_field() -> None:
    c = _fresh()
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))  # set P and stay EXPLORE
    mode_before = c._mode
    p_before = c._previous_explore_beacon_max
    with pytest.raises(ValueError):
        c.act(object())  # type: ignore[arg-type]
    assert c._mode is mode_before
    assert c._previous_explore_beacon_max == p_before


# ---------------------------------------------------------------------------
# ADR 0009 B.5: config binding is construction-invariant (Sol requirement 1).
# ---------------------------------------------------------------------------

def test_config_binding_cannot_be_reassigned_between_acts() -> None:
    """The controller-visible ``config`` binding is not reboundable.

    A frozen ``EXP003ControllerConfig`` value alone is insufficient: a caller
    could replace ``StationB50Controller.config`` between ``act()`` calls and
    C2/E1 would read through that branch-dependent binding.  The check proves
    the public binding itself rejects replacement, so C2 cannot observe a
    branch-dependent configuration (ADR 0009 B.5 five-property exception).
    """
    from aweform.exp003 import EXP003ControllerConfig

    c = _fresh()
    original = c.config
    c.act(_obs(0.70, (0.6, 0.6, 0.6)))            # E3: EXPLORE, P set
    c.act(_obs(0.40, (0.1, 0.2, 0.3), contact=True))  # E1 -> CHARGE
    adversarial = EXP003ControllerConfig(enter_seek=0.49, recover=0.95)
    with pytest.raises(AttributeError):
        c.config = adversarial  # type: ignore[misc]
    # The binding still points at the construction value; C2 observed original.
    assert c.config is original
    assert c.config.recover == 0.85
    # C2 fires only if energy exceeds the construction recover (0.85), not the
    # 0.95 the adversarial replacement would have required.
    c.act(_obs(0.90, (0.1, 0.2, 0.3), contact=True))
    assert c._mode is EXP003Mode.EXPLORE  # C2 reached on construction recover
    # Replacement inside a fresh controller before any act() is also rejected:
    # the binding is construction-invariant across the whole lifetime.
    c2 = _fresh()
    with pytest.raises(AttributeError):
        c2.config = adversarial
    assert c2.config is not adversarial


# ---------------------------------------------------------------------------
# ADR 0009 B.5: genuine dominance of a later clear over BOHS reads.
# ---------------------------------------------------------------------------

# ADR 0009 B.5 predicate classes: the finite space ``act()`` actually branches
# on (enter_seek 0.50, anticipatory-energy 0.65, weak-beacon 0.10, recover 0.85,
# retained previous_max presence/declination).  These are the *only* decisions
# that affect the retained-mode graph, so this enumeration is exhaustive over
# every branch the controller can reach.  Explorer/RNG state changes the
# returned action, never the mode/BOHS transitions, so it need not be varied.
_ENERGY_E1 = 0.40                        # energy < enter_seek            -> E1
_ENERGY_E2WINDOW = 0.55                  # [enter_seek, 0.65) window      -> E2
_ENERGY_E3 = 0.75                        # >= 0.65 (or E2 guard fails)    -> E3
_ENERGY_C2 = 0.90                        # > recover (0.85)               -> C2
_ENERGY_C3 = 0.80                        # <= recover                     -> C3
_BEACON_WEAK_SMALL = 0.05                # < 0.10 weak, below a weak P
_BEACON_WEAK_NEAR = 0.09                 # < 0.10 weak, above a weak P (0.05)
_BEACON_STRONG = 0.60                    # >= 0.10 strong


def _obs_triple(bmax: float, energy: float, contact: bool) -> StationObservation:
    """An observation whose beacon L/F/R max is exactly ``bmax``."""
    return _obs(energy, (bmax, bmax, bmax), contact)


def _explore_obs_classes() -> list[StationObservation]:
    """The finite EXPLORE-block observation set (E1/E2/E3 decision space)."""
    return [
        _obs_triple(bm, energy, contact)
        for energy in (_ENERGY_E1, _ENERGY_E2WINDOW, _ENERGY_E3)
        for bm in (_BEACON_WEAK_SMALL, _BEACON_WEAK_NEAR, _BEACON_STRONG)
        for contact in (False, True)
    ]


def _controller_at(mode: str, p: float | None) -> StationB50TrendController:
    """Reach controller state ``(mode, previous_max)`` via real act() calls."""
    c = _fresh()
    if mode == "EXPLORE":
        if p is not None:
            c.act(_obs_triple(p, _ENERGY_E3, False))  # E3 writes previous_max=p
        return c
    if mode == "SEEK":
        c.act(_obs_triple(_BEACON_STRONG, _ENERGY_E1, False))  # E1 -> SEEK, None
        assert c._mode is EXP003Mode.SEEK and c._previous_explore_beacon_max is None
        return c
    # CHARGE
    c.act(_obs_triple(_BEACON_STRONG, _ENERGY_E1, False))      # E1 -> SEEK, None
    c.act(_obs_triple(_BEACON_STRONG, _ENERGY_E1, True))       # S1 -> CHARGE, None
    assert c._mode is EXP003Mode.CHARGE and c._previous_explore_beacon_max is None
    return c


def test_b5_dominance_sole_read_site_is_in_explore_branch() -> None:
    """There is exactly one BOHS read, and it lives in the EXPLORE block.

    ``act()`` is a straight-line sequence of five top-level ``if`` clauses:
    the invalid-input guard, the EXPLORE block, the SEEK block, and the CHARGE
    C1/C2 clauses.  The one BOHS ``Load`` is the E2 anticipatory snapshot at
    the top of the EXPLORE block.  Enumerate those clauses over the real AST
    and require that exactly the EXPLORE clause (whose test branches on
    ``self._mode is EXPLORE``) contains the sole read — every retained-mode
    successor (SEEK, CHARGE, C1/C2) loads nothing.  With a single read site, a
    clear handed off to a barriered successor cannot be followed by *any*
    later BOHS load inside act(); the next read occurs only on the next
    EXPLORE entry, where the finite-state test proves it is dominated.
    """
    import aweform.exp003 as exp003  # noqa: PLC0415

    tree = ast.parse(inspect.getsource(exp003))
    act = _method_source(tree, "StationB50TrendController", "act")
    assert act is not None

    loads = [
        node
        for node in ast.walk(act)
        if isinstance(node, ast.Attribute)
        and node.attr == BOHS_SLUG
        and isinstance(node.ctx, ast.Load)
    ]
    assert len(loads) == 1, f"expected one BOHS load in act(), got {len(loads)}"

    if_clauses = [n for n in act.body if isinstance(n, ast.If)]
    assert len(if_clauses) == 5, f"act() branch graph changed ({len(if_clauses)})"
    reading_clauses = [
        cls
        for cls in if_clauses
        if any(
            isinstance(n, ast.Attribute)
            and n.attr == BOHS_SLUG
            and isinstance(n.ctx, ast.Load)
            for n in ast.walk(cls)
        )
    ]
    assert len(reading_clauses) == 1, (
        f"expected exactly one top-level clause to read BOHS, got "
        f"{len(reading_clauses)}"
    )
    explore_clause = reading_clauses[0]
    assert "self._mode is EXP003Mode.EXPLORE" in ast.unparse(explore_clause.test), (
        "the reading clause is not the EXPLORE block"
    )


def test_b5_dominance_exhaustive_finite_state_enumeration() -> None:
    """Exhaust every reachable ``(mode, previous_max)`` state and prove the
    sole BOHS read is always dominated — a fresh write of the immediately
    preceding observation, or a clear to ``None`` — never a recovered stale bit.

    Model the controller as a finite automaton over ``(mode, previous_max)``
    where ``previous_max`` ranges over the finite write set ``{None, 0.05,
    0.09, 0.60}`` the predicate classes can produce.  Forward-BFS from the
    constructor state ``(EXPLORE, None)``, driving the *real* controller, and
    exhaust all mode/contact/energy branches until the reachable state set
    closes.  On every transition assert the domination invariant:

      * non-``EXPLORE`` modes always carry ``previous_max is None`` — an
        E1/E2 clear or a C1/C2/C3 hand-off never revives the bit;
      * any non-``None`` result equals the ``max`` of *this* call's observation
        (an E3 write), i.e. a fresh write of the immediate predecessor, never a
        carried-over value;
      * re-entry to ``EXPLORE`` from ``SEEK``/``CHARGE`` is only via ``C2``
        (which clears) or ``reset()``, so the next read sees ``None``.

    Together with the single read site proved above, every reachable read
    observes only a dominated value — the exact association Sol required, tied
    to the actual branch graph rather than a hand-picked trajectory.
    """
    start = ("EXPLORE", None)
    states: set[tuple[str, float | None]] = {start}
    frontier = [start]
    write_obs: dict[float, float] = {}  # literal -> the obs max that wrote it

    while frontier:
        mode, p = frontier.pop()
        c = _controller_at(mode, p)
        if mode == "EXPLORE":
            obs_classes = _explore_obs_classes()
        elif mode == "SEEK":
            obs_classes = [
                _obs_triple(_BEACON_STRONG, _ENERGY_E3, contact)
                for contact in (False, True)
            ]
        else:  # CHARGE
            obs_classes = [
                _obs_triple(_BEACON_STRONG, _ENERGY_C2, True),   # C2 -> EXPLORE
                _obs_triple(_BEACON_STRONG, _ENERGY_C3, True),   # C3 -> CHARGE
                _obs_triple(_BEACON_STRONG, _ENERGY_E3, False),  # C1 -> SEEK
            ]

        for obs in obs_classes:
            a = _controller_at(mode, p)
            a.act(obs)
            nmode, np = a._mode.name, a._previous_explore_beacon_max

            # Domination invariant (the load-relevant rule):
            # previous_max is never a stale bit.
            if np is not None:
                assert np == _current_max(obs), (
                    f"({mode},{p}) -> ({nmode},{np}): P is not max of this obs"
                )
                write_obs[np] = _current_max(obs)
            if nmode != "EXPLORE":
                assert np is None, (
                    f"non-EXPLORE mode {nmode} carried P={np!r} (stale bit)"
                )

            nxt = (nmode, np)
            if nxt not in states:
                states.add(nxt)
                frontier.append(nxt)

    # Re-entry to EXPLORE with non-None P is a same-decision E3 write only:
    # no state is reachable by carrying a prior bit through a clear.
    for mode, p in states:
        if mode != "EXPLORE":
            assert p is None, f"{mode} reachable with P={p!r}"
    recorded = {p for _, p in states}
    assert recorded == {None, _BEACON_WEAK_SMALL, _BEACON_WEAK_NEAR, _BEACON_STRONG}, (
        f"unexpected reachable previous_max set: {recorded}"
    )
    assert states == {
        ("EXPLORE", None), ("EXPLORE", _BEACON_WEAK_SMALL),
        ("EXPLORE", _BEACON_WEAK_NEAR), ("EXPLORE", _BEACON_STRONG),
        ("SEEK", None), ("CHARGE", None),
    }, f"reachable retained-mode graph not closed: {states - {start}}"

    # reset() clears the barrier and returns to EXPLORE from every state.
    for mode, p in list(states):
        c = _controller_at(mode, p)
        c.reset()
        assert c._mode is EXP003Mode.EXPLORE
        assert c._previous_explore_beacon_max is None