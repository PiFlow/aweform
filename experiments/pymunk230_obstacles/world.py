"""Successor-only arena adapter around the frozen Pymunk prototype."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from experiments.pymunk_contact_prototype.fixture import (
    DT,
    HULL_CIRCUMRADIUS,
    ContactWorld,
    StepRecord,
    clipped_action,
    sinc,
)

from .audit import clearances_by_object, swept_crossing
from .geometry import add_arena


@dataclass(frozen=True)
class StepAudit:
    minimum_clearance_by_object_m: tuple[tuple[str, float], ...]
    crossing_detected: bool
    clearance_sampling_bound_m: float
    maximum_substep_path_bound_m: float


class ObstacleContactWorld(ContactWorld):
    """V3 body/contact mechanics with the seven static objects added.

    Reset intentionally reconstructs the base world, then reinstalls the arena
    and replaces the callback registration with this instance's bound method.
    This repairs the inherited temporary-instance callback target identified
    in the #231 package review; it does not alter the frozen #226 source.
    """

    def __init__(self, *, microsteps: int = 400) -> None:
        super().__init__(microsteps=microsteps)
        self.obstacle_shapes = add_arena(self.space, include_walls=False)
        for name, shapes in self.obstacle_shapes.items():
            for index, shape in enumerate(shapes):
                suffix = f"_{index:02d}" if name in {"A1", "A2", "A3"} else ""
                self._shape_names[id(shape)] = f"{name}{suffix}"
        self.last_audit = StepAudit((), False, 0.0, 0.0)

    def advance(self, action: Sequence[object]) -> StepRecord:
        """Advance inherited mechanics while independently auditing solids."""
        request, shaft = clipped_action(action)
        start = (float(self.body.position.x), float(self.body.position.y))
        start_angle = float(self.body.angle)
        distance = 0.045 * (shaft[0] + shaft[1]) / 2.0
        yaw = 0.045 * (shaft[1] - shaft[0]) / 0.185
        speed, omega = distance / DT, yaw / DT
        sub_dt = DT / self.microsteps
        clearance_minima: dict[str, float] = {}
        sampling_bound = 0.0
        maximum_substep_path_bound = 0.0
        crossed = False
        max_penetration = 0.0
        self._contact_seen_this_command = False
        self._contacts = []
        self._contact_events = []
        simultaneous: list[tuple[str, ...]] = []
        self.body.velocity = (
            speed * math.cos(start_angle),
            speed * math.sin(start_angle),
        )
        self.body.angular_velocity = omega
        for substep in range(self.microsteps):
            before = (float(self.body.position.x), float(self.body.position.y))
            before_angle = float(self.body.angle)
            before_clearances = clearances_by_object(before, before_angle)
            event_offset = len(self._contact_events)
            self._active_substep_index = substep
            self.space.step(sub_dt)
            self.engine_steps += 1
            after = (float(self.body.position.x), float(self.body.position.y))
            after_angle = float(self.body.angle)
            after_clearances = clearances_by_object(after, after_angle)
            middle = (
                (before[0] + after[0]) / 2.0,
                (before[1] + after[1]) / 2.0,
            )
            middle_angle = (before_angle + after_angle) / 2.0
            middle_clearances = clearances_by_object(middle, middle_angle)
            for gaps in (before_clearances, middle_clearances, after_clearances):
                for name, gap in gaps.items():
                    clearance_minima[name] = min(
                        clearance_minima.get(name, math.inf), gap
                    )
                    max_penetration = max(max_penetration, max(0.0, -gap))
            crossed |= swept_crossing(
                before_clearances, middle_clearances, after_clearances
            )
            path_bound = math.dist(before, after) + HULL_CIRCUMRADIUS * abs(
                after_angle - before_angle
            )
            maximum_substep_path_bound = max(maximum_substep_path_bound, path_bound)
            sampling_bound = max(sampling_bound, path_bound / 4.0)
            events = self._contact_events[event_offset:]
            simultaneous.append(
                tuple(sorted({"|".join(event.shape_pair) for event in events}))
            )
            max_penetration = max(
                max_penetration,
                max(
                    (event.maximum_contact_penetration for event in events),
                    default=0.0,
                ),
            )
        self.elapsed += DT
        self.logical_steps += 1
        end = (float(self.body.position.x), float(self.body.position.y))
        end_angle = float(self.body.angle)
        expected_distance = distance * sinc(yaw / 2.0)
        expected_dx = expected_distance * math.cos(start_angle + yaw / 2.0)
        expected_dy = expected_distance * math.sin(start_angle + yaw / 2.0)
        mismatch = math.hypot(
            end[0] - start[0] - expected_dx,
            end[1] - start[1] - expected_dy,
        )
        end_clearance = clearances_by_object(end, end_angle)
        self.last_audit = StepAudit(
            tuple(sorted(clearance_minima.items())),
            crossed,
            sampling_bound,
            maximum_substep_path_bound,
        )
        complete_events = tuple(self._contact_events)
        return StepRecord(
            request=request,
            shaft=shaft,
            start=start,
            start_angle=start_angle,
            end=end,
            end_angle=end_angle,
            velocity=(float(self.body.velocity.x), float(self.body.velocity.y)),
            angular_velocity=float(self.body.angular_velocity),
            elapsed=self.elapsed,
            step_count=self.engine_steps,
            max_penetration=max_penetration + sampling_bound,
            contact_count=sum(event.contact_points for event in complete_events),
            arbiter_count=len(complete_events),
            total_impulse=sum(event.impulse for event in complete_events),
            crossed_wall_or_post=crossed,
            body_shaft_mismatch=mismatch,
            end_penetration=max(0.0, -min(end_clearance.values())),
            contact_seen=bool(complete_events),
            minimum_clearance_m=min(clearance_minima.values(), default=math.inf),
            clearance_sampling_bound_m=sampling_bound,
            minimum_clearance_by_shape=tuple(sorted(clearance_minima.items())),
            end_clearance_by_shape=tuple(sorted(end_clearance.items())),
            contact_events=complete_events,
            simultaneous_contact_identities=tuple(simultaneous),
        )

    def reset(self, position: tuple[float, float], angle: float) -> None:
        super().reset(position, angle)
        self.obstacle_shapes = add_arena(self.space, include_walls=False)
        for name, shapes in self.obstacle_shapes.items():
            for index, shape in enumerate(shapes):
                suffix = f"_{index:02d}" if name in {"A1", "A2", "A3"} else ""
                self._shape_names[id(shape)] = f"{name}{suffix}"
        self.last_audit = StepAudit((), False, 0.0, 0.0)
        # Space registration on (None, None) replaces the inherited handler;
        # callbacks now mutate this live instance's event lists/refresh flag.
        self.space.on_collision(None, None, post_solve=self._post_solve)
