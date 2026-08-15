# ADR 0003 — EXP-000 Body, Observation, and Action Contract

**Status:** Accepted

## Decision

The V0.1 EXP-000 environment has hidden simulator body state consisting of
`x`, `y`, heading in radians, and internal energy. Its four discrete actions
are `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, and `MOVE_FORWARD`.

The agent receives only internal energy plus three local directional resource
signals ordered as left, forward, and right. Absolute coordinates, heading,
and resource-source location remain privileged simulator state. The resource
field is static and renewable: harvesting does not deplete it.

Each transition applies the action to position/heading, samples resource at
the resulting body position, calculates harvest, applies harvest and basal and
action costs through the energy model, updates viability, and then emits the
next local observation. Reward is exactly `0.0`. Viability failure terminates
the episode; a finite horizon truncates an otherwise viable episode.

This establishes the V0.1 structural contract. World size, movement and sensor
geometry, costs, harvest rate, and horizon are configurable development values
until EXP-000 is frozen for confirmatory evaluation; this ADR does not
preregister their final numeric values.
