# Aweform — Future Research Question: Return Reserve Margin

**Status:** non-authorizing future research note  
**Recorded:** 2026-09-25  
**Repository context:** ADR 0018 documentation candidate on branch `docs/adr-0018-innate-viability-floor`  
**Purpose:** preserve candidate mathematics for an assumption-bounded Level-1 energetic return decision without freezing a controller equation, trigger, safety factor, or organism-visible variable.

## Why this note exists

ADR 0018 permits a constitutive Level-1 energetic return mechanism but deliberately does **not** freeze its exact mathematics.

The engineering question is:

> Can Aweform estimate, from its authorized current body/energy state and charging-beacon signals, whether its remaining stored energy still provides a sufficient margin to return, dock, and begin charging under declared assumptions?

This note records one candidate family for later mechanism design. Nothing here authorizes runtime implementation, a new observation channel, a specific threshold, or a claim of guaranteed return.

## Existing beacon relationship

The retained idealized directional beacon uses the deterministic signal family:

```text
B = 1 / (1 + (d / s)^2)
```

For a valid non-zero signal, the corresponding probe-to-station distance can be inverted as:

```text
d = s * sqrt(1 / B - 1)
```

For the current three directional probes `B_L`, `B_F`, and `B_R`, with probe radius `r` and sensor angle `a`, D-016 used the evaluator-only analytic reconstruction:

```text
d_L = s * sqrt(1 / B_L - 1)
d_F = s * sqrt(1 / B_F - 1)
d_R = s * sqrt(1 / B_R - 1)

y = (d_R^2 - d_L^2) / (4 * r * sin(a))

x = (((d_L^2 + d_R^2) / 2) - d_F^2)
    / (2 * r * (1 - cos(a)))

D = sqrt(x^2 + y^2)
beta = atan2(y, x)
```

Here `D` is a candidate station-relative distance estimate and `beta` a candidate bearing/error estimate in the body frame.

These equations are **illustrative and non-normative**. ADR 0018 does not require a future implementation to use this reconstruction.

## Provenance boundary

D-016's reconstruction was explicitly evaluator-only. It never entered the historical organism controller.

Using the same or related mathematics in a future Level-1 return mechanism would therefore be an intentional category promotion:

> **evaluator-only diagnostic → designed constitutive Level-1 prior**

That promotion must be declared as engineered prior knowledge, not as learned or discovered competence.

Before any causal V0.5 use, the implementing D-stage must revalidate the mathematics against the exact current V0.5 beacon definitions, precision/quantization, body/probe geometry, and edge behaviour. D-016 is supporting precedent, not automatic organism permission.

## Candidate return-energy family

One possible assumption-bounded decomposition is:

```text
E_required =
    E_return_buffer
    + K * (
        E_turn(abs(beta))
        + E_travel(D)
        + E_terminal_dock
      )

return_margin = E_battery - E_required
```

A normalized diagnostic could be:

```text
return_margin_normalized = return_margin / battery_capacity
```

A future mechanism might choose a trigger related to the sign or hysteresis of this margin, but **no trigger form is authorized or frozen here**.

The terms are placeholders for engineering quantities, not free tuning knobs:

- `E_turn` — estimated energetic cost of necessary orientation/correction;
- `E_travel` — estimated energetic cost of translational return under declared assumptions;
- `E_terminal_dock` — allowance for local alignment/contact acquisition;
- `E_return_buffer` — decision-budget margin for bounded uncertainty, retries, and model error;
- `K` — an optional explicitly justified safety factor if the eventual mechanism needs one.

Every implemented term must be provenance-labelled as derived, measured, manufacturer-sourced, engineering estimate, or founder design choice as appropriate. Parameters must not be tuned post hoc merely to manufacture desired autonomous-return behaviour.

## Important distinction: this is not the dormancy reserve

`E_return_buffer` is a **return-decision budget term**.

It is not the protected low-power continuity reserve discussed in the future fainting/dormancy direction. A future backup clock/memory reserve would answer a different lifecycle question and remains separately unauthorized.

## Required numerical and validity work before implementation

Any implementing D-stage must explicitly define and test:

- `B -> 0` / very weak signals, where analytic distance tends toward infinity;
- saturated or floor-level readings;
- finite precision and quantization;
- equality/symmetry cases;
- invalid, absent, or non-finite beacon values;
- out-of-support geometry;
- behaviour near the dock where beacon geometry may be poorly conditioned for orientation;
- terminal docking without evaluator-only dock orientation, target heading, heading window, hidden pose, station coordinates, or true distance;
- actuator/energy-model uncertainty and the assumptions under which a return budget is considered sufficient;
- fallback or genuine failure semantics when the assumptions do not hold.

A future obstacle, degraded wheel, missing charger, invalid beacon, or changed environment cannot be hidden inside the phrase “safe return.” The return claim is only as strong as the explicitly declared assumptions.

## Current engineering intuition, not a frozen parameterization

The current V0.5 simulator is small relative to its battery capacity, so a first physically derived return threshold may be very low. That outcome would be informative. The ecology must not be retuned merely because a low threshold looks uninteresting.

Likewise, a larger safety factor or buffer is legitimate only when justified by declared uncertainty, retry cost, physical measurement, or engineering design requirements rather than by a desired behavioural result.

## Relationship to learning

The constitutive Level-1 return mechanism establishes only a baseline.

Later Level-2/Level-3 learning may separately investigate:

- more efficient routes;
- adaptive reserve strategy above the fixed baseline;
- robustness under environmental change;
- learned docking improvements;
- prediction of actuator/sensor degradation;
- decisions about elective departure, exploration, or optional energy expenditure.

Any such learned contribution must be evaluated above the Level-1 baseline and must not silently write into the Level-1 trigger unless a future reviewed boundary explicitly authorizes that pathway.

## Non-goals

This note does not authorize:

- a Level-1 controller implementation;
- a ninth organism-visible channel;
- true distance, pose, heading, or dock orientation as organism inputs;
- planning, MPC, search, RL, or reward;
- learned-state input into Level-1 viability decisions;
- obstacle navigation;
- physical hardware control;
- fainting/dormancy;
- D-049 or any successor stage.

## Bottom line

The candidate idea is to replace an arbitrary fixed battery percentage with an **assumption-bounded energetic return margin derived from the body's own authorized signals and declared engineering constants**.

The mathematics above is a research aid only. The eventual mechanism must earn its exact form through separately authorized implementation, validation, and review.
