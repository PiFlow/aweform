"""Direct Pymunk rigid-body fixture; no production Aweform imports."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Sequence, cast

import pymunk

MAX_DELTA = 0.6457718232379019
RADIUS = 0.045
TRACK = 0.185
LENGTH = 0.180
WIDTH = 0.215
MASS = 1.0
MOMENT = MASS * (LENGTH**2 + WIDTH**2) / 12.0
DT = 0.1
ROOM = 3.0
WALL_THICKNESS = 0.01
POST_RADIUS = 0.05
SLOP = 0.0001
ENCODER_QUANTUM = math.pi / 180.0
COLLISION_BIAS_10MS = 0.9**100
CLEARANCE_SAMPLES_PER_MICROSTEP = 64
HULL_CIRCUMRADIUS = math.hypot(LENGTH / 2, WIDTH / 2)
WALL_GEOMETRY = (
    (
        "wall_west",
        (
            (-WALL_THICKNESS, -WALL_THICKNESS),
            (0.0, -WALL_THICKNESS),
            (0.0, ROOM + WALL_THICKNESS),
            (-WALL_THICKNESS, ROOM + WALL_THICKNESS),
        ),
    ),
    (
        "wall_east",
        (
            (ROOM, -WALL_THICKNESS),
            (ROOM + WALL_THICKNESS, -WALL_THICKNESS),
            (ROOM + WALL_THICKNESS, ROOM + WALL_THICKNESS),
            (ROOM, ROOM + WALL_THICKNESS),
        ),
    ),
    (
        "wall_south",
        (
            (0.0, -WALL_THICKNESS),
            (ROOM, -WALL_THICKNESS),
            (ROOM, 0.0),
            (0.0, 0.0),
        ),
    ),
    (
        "wall_north",
        (
            (0.0, ROOM),
            (ROOM, ROOM),
            (ROOM, ROOM + WALL_THICKNESS),
            (0.0, ROOM + WALL_THICKNESS),
        ),
    ),
)


def sinc(x: float) -> float:
    return 1.0 if x == 0.0 else math.sin(x) / x


def quantize_encoder(delta: float) -> float:
    if not math.isfinite(delta):
        raise ValueError("encoder input must be finite")
    counts = math.floor(abs(delta) / ENCODER_QUANTUM + 0.5)
    return math.copysign(counts * ENCODER_QUANTUM, delta) if counts else 0.0


def parse_action(action: Sequence[object]) -> tuple[float, float]:
    try:
        action_length = len(action)
    except TypeError:
        raise ValueError(
            "action must contain exactly two finite wheel deltas"
        ) from None
    if isinstance(action, (str, bytes)) or action_length != 2:
        raise ValueError("action must contain exactly two finite wheel deltas")
    result: list[float] = []
    for value in action:
        if isinstance(value, (str, bytes, bool)):
            raise ValueError("wheel deltas must be finite non-boolean numbers")
        try:
            number = float(cast(float, value))
        except TypeError, ValueError, OverflowError:
            raise ValueError(
                "wheel deltas must be finite non-boolean numbers"
            ) from None
        if not math.isfinite(number):
            raise ValueError("wheel deltas must be finite non-boolean numbers")
        result.append(number)
    return result[0], result[1]


def clipped_action(
    action: Sequence[object],
) -> tuple[tuple[float, float], tuple[float, float]]:
    requested = parse_action(action)
    return requested, tuple(max(-MAX_DELTA, min(MAX_DELTA, x)) for x in requested)  # type: ignore[return-value]


def corners(
    position: tuple[float, float], angle: float
) -> tuple[tuple[float, float], ...]:
    c, s = math.cos(angle), math.sin(angle)
    return tuple(
        (position[0] + x * c - y * s, position[1] + x * s + y * c)
        for x, y in (
            (-LENGTH / 2, -WIDTH / 2),
            (-LENGTH / 2, WIDTH / 2),
            (LENGTH / 2, WIDTH / 2),
            (LENGTH / 2, -WIDTH / 2),
        )
    )


def circle_penetration(
    position: tuple[float, float],
    angle: float,
    center: tuple[float, float],
    radius: float,
) -> float:
    """Independent closest-point rectangle/circle overlap depth."""
    dx, dy = center[0] - position[0], center[1] - position[1]
    c, s = math.cos(angle), math.sin(angle)
    local_x, local_y = dx * c + dy * s, -dx * s + dy * c
    nearest_x = max(-LENGTH / 2, min(LENGTH / 2, local_x))
    nearest_y = max(-WIDTH / 2, min(WIDTH / 2, local_y))
    distance = math.hypot(local_x - nearest_x, local_y - nearest_y)
    if abs(local_x) <= LENGTH / 2 and abs(local_y) <= WIDTH / 2:
        distance = -min(LENGTH / 2 - abs(local_x), WIDTH / 2 - abs(local_y))
    return max(0.0, radius - distance)


def clearances_by_shape(
    position: tuple[float, float],
    angle: float,
    posts: tuple[tuple[float, float], ...] = (),
) -> dict[str, float]:
    pts = corners(position, angle)
    clearances = {
        "wall_west": min(x for x, _ in pts),
        "wall_east": min(ROOM - x for x, _ in pts),
        "wall_south": min(y for _, y in pts),
        "wall_north": min(ROOM - y for _, y in pts),
    }
    for index, center in enumerate(posts):
        dx, dy = center[0] - position[0], center[1] - position[1]
        c, s = math.cos(angle), math.sin(angle)
        local_x, local_y = dx * c + dy * s, -dx * s + dy * c
        nearest_x = max(-LENGTH / 2, min(LENGTH / 2, local_x))
        nearest_y = max(-WIDTH / 2, min(WIDTH / 2, local_y))
        distance = math.hypot(local_x - nearest_x, local_y - nearest_y)
        if abs(local_x) <= LENGTH / 2 and abs(local_y) <= WIDTH / 2:
            clearance = -POST_RADIUS - min(
                LENGTH / 2 - abs(local_x), WIDTH / 2 - abs(local_y)
            )
        else:
            clearance = distance - POST_RADIUS
        clearances[f"post_{index}"] = clearance
    return clearances


def wall_penetration(position: tuple[float, float], angle: float) -> float:
    return max(0.0, -min(clearances_by_shape(position, angle).values()))


@dataclass(frozen=True)
class ContactEvent:
    substep_index: int
    shape_pair: tuple[str, ...]
    contact_points: int
    impulse: float
    maximum_contact_penetration: float


@dataclass(frozen=True)
class StepRecord:
    request: tuple[float, float]
    shaft: tuple[float, float]
    start: tuple[float, float]
    start_angle: float
    end: tuple[float, float]
    end_angle: float
    velocity: tuple[float, float]
    angular_velocity: float
    elapsed: float
    step_count: int
    max_penetration: float
    contact_count: int
    arbiter_count: int
    total_impulse: float
    crossed_wall_or_post: bool
    body_shaft_mismatch: float
    end_penetration: float
    contact_seen: bool
    minimum_clearance_m: float
    clearance_sampling_bound_m: float
    minimum_clearance_by_shape: tuple[tuple[str, float], ...]
    end_clearance_by_shape: tuple[tuple[str, float], ...]
    contact_events: tuple[ContactEvent, ...]
    simultaneous_contact_identities: tuple[tuple[str, ...], ...]


class ContactWorld:
    """One deterministic room/post fixture advanced by Pymunk's Space.step."""

    def __init__(
        self,
        *,
        microsteps: int = 10,
        posts: tuple[tuple[float, float], ...] = (),
        collision_bias: float = COLLISION_BIAS_10MS,
        suppress_velocity_refresh_after_contact: bool = True,
    ) -> None:
        if microsteps not in (10, 20, 400, 800):
            raise ValueError("microsteps must be 10, 20, 400, or 800")
        if not math.isfinite(collision_bias) or collision_bias <= 0.0:
            raise ValueError("collision_bias must be finite and positive")
        self.microsteps = microsteps
        self.posts = posts
        self.collision_bias = collision_bias
        self.suppress_velocity_refresh_after_contact = (
            suppress_velocity_refresh_after_contact
        )
        self._contact_seen_this_command = False
        self.space = pymunk.Space(threaded=False)
        self.space.gravity = (0.0, 0.0)
        self.space.damping = 1.0
        self.space.iterations = 10
        self.space.collision_slop = SLOP
        self.space.collision_bias = collision_bias
        self.space.collision_persistence = 3
        self.space.sleep_time_threshold = math.inf
        self.space.idle_speed_threshold = 0.0
        self.body = pymunk.Body(MASS, MOMENT)
        self.hull = pymunk.Poly.create_box(self.body, (LENGTH, WIDTH))
        self.hull.friction = 0.0
        self.hull.elasticity = 0.0
        self.space.add(self.body, self.hull)
        self._shape_names: dict[int, str] = {id(self.hull): "hull"}
        static = self.space.static_body
        self.wall_geometry = WALL_GEOMETRY
        self._walls: list[pymunk.Poly] = []
        for name, vertices in self.wall_geometry:
            wall = pymunk.Poly(static, vertices)
            wall.friction = wall.elasticity = 0.0
            self._walls.append(wall)
            self._shape_names[id(wall)] = name
        shapes: list[pymunk.Shape] = list(self._walls)
        for index, center in enumerate(posts):
            post = pymunk.Circle(static, POST_RADIUS, center)
            post.friction = post.elasticity = 0.0
            shapes.append(post)
            self._shape_names[id(post)] = f"post_{index}"
        self.space.add(*shapes)
        self.elapsed = 0.0
        self.logical_steps = 0
        self.engine_steps = 0
        self.execution_guard: Callable[[], None] | None = None
        self._contacts: list[tuple[int, float]] = []
        self._contact_events: list[ContactEvent] = []
        self._active_substep_index = -1
        self.space.on_collision(None, None, post_solve=self._post_solve)

    def _post_solve(
        self, arbiter: pymunk.Arbiter, _space: pymunk.Space, _data: object
    ) -> None:
        impulse = arbiter.total_impulse.length
        contact_set = arbiter.contact_point_set
        shape_pair = tuple(
            sorted(
                self._shape_names.get(id(shape), "unknown") for shape in arbiter.shapes
            )
        )
        self._contact_seen_this_command = True
        self._contacts.append((len(contact_set.points), float(impulse)))
        self._contact_events.append(
            ContactEvent(
                self._active_substep_index,
                shape_pair,
                len(contact_set.points),
                float(impulse),
                max(
                    (max(0.0, -point.distance) for point in contact_set.points),
                    default=0.0,
                ),
            )
        )

    def _begin_motor_command(
        self, speed: float, omega: float, start_angle: float
    ) -> None:
        """Versioned actuator hook; legacy fixture performs no boundary update."""

    def _apply_motor_substep(self, speed: float, omega: float, h: float) -> None:
        """Historical #226 per-substep schedule, retained for the legacy class."""
        if not (
            self.suppress_velocity_refresh_after_contact
            and self._contact_seen_this_command
        ):
            theta = float(self.body.angle)
            half_yaw = omega * h / 2.0
            speed_mid = speed * sinc(half_yaw)
            theta_mid = theta + half_yaw
            self.body.velocity = (
                speed_mid * math.cos(theta_mid),
                speed_mid * math.sin(theta_mid),
            )
            self.body.angular_velocity = omega

    def reset(self, position: tuple[float, float], angle: float) -> None:
        if not all(math.isfinite(v) for v in (*position, angle)):
            raise ValueError("reset pose must be finite")
        fresh = ContactWorld(
            microsteps=self.microsteps,
            posts=self.posts,
            collision_bias=self.collision_bias,
            suppress_velocity_refresh_after_contact=self.suppress_velocity_refresh_after_contact,
        )
        fresh.body.position = position
        fresh.body.angle = angle
        self.__dict__.update(fresh.__dict__)

    def advance(self, action: Sequence[object]) -> StepRecord:
        request, shaft = clipped_action(action)
        start = (float(self.body.position.x), float(self.body.position.y))
        start_angle = float(self.body.angle)
        distance = RADIUS * (shaft[0] + shaft[1]) / 2.0
        yaw = RADIUS * (shaft[1] - shaft[0]) / TRACK
        speed, omega = distance / DT, yaw / DT
        h = DT / self.microsteps
        max_pen = 0.0
        crossed = False
        sampling_bound = 0.0
        minima: dict[str, float] = {}
        self._contact_seen_this_command = False
        self._contacts = []
        self._contact_events = []
        simultaneous: list[tuple[str, ...]] = []
        self._begin_motor_command(speed, omega, start_angle)
        for substep in range(self.microsteps):
            self._apply_motor_substep(speed, omega, h)
            before = (float(self.body.position.x), float(self.body.position.y))
            before_angle = float(self.body.angle)
            before_clearance = clearances_by_shape(before, before_angle, self.posts)
            self._active_substep_index = substep
            event_offset = len(self._contact_events)
            if self.execution_guard is not None:
                self.execution_guard()
            self.space.step(h)
            self.engine_steps += 1
            after = (float(self.body.position.x), float(self.body.position.y))
            after_angle = float(self.body.angle)
            after_clearance = clearances_by_shape(after, after_angle, self.posts)
            per_shape_samples: dict[str, list[float]] = {
                name: [] for name in before_clearance
            }
            for sample in range(CLEARANCE_SAMPLES_PER_MICROSTEP + 1):
                fraction = sample / CLEARANCE_SAMPLES_PER_MICROSTEP
                sample_position = (
                    before[0] + fraction * (after[0] - before[0]),
                    before[1] + fraction * (after[1] - before[1]),
                )
                sample_angle = before_angle + fraction * (after_angle - before_angle)
                for name, clearance in clearances_by_shape(
                    sample_position, sample_angle, self.posts
                ).items():
                    per_shape_samples[name].append(clearance)
            for name, samples in per_shape_samples.items():
                local_minimum = min(samples)
                minima[name] = min(minima.get(name, math.inf), local_minimum)
                max_pen = max(max_pen, max(0.0, -local_minimum))
                if (
                    before_clearance[name] >= 0.0
                    and after_clearance[name] > 0.0
                    and min(samples[1:-1], default=math.inf) < 0.0
                ):
                    crossed = True
            path_bound = (
                math.dist(before, after)
                + HULL_CIRCUMRADIUS * abs(after_angle - before_angle)
            ) / CLEARANCE_SAMPLES_PER_MICROSTEP
            sampling_bound = max(sampling_bound, path_bound)
            events = self._contact_events[event_offset:]
            pair_ids = tuple(sorted({"|".join(event.shape_pair) for event in events}))
            simultaneous.append(pair_ids)
            max_pen = max(
                max_pen,
                max(
                    (event.maximum_contact_penetration for event in events),
                    default=0.0,
                ),
            )
        self.elapsed += DT
        self.logical_steps += 1
        end = (float(self.body.position.x), float(self.body.position.y))
        angle = float(self.body.angle)
        half_yaw_total = yaw / 2.0
        expected_distance = distance * sinc(half_yaw_total)
        expected_dx = expected_distance * math.cos(start_angle + half_yaw_total)
        expected_dy = expected_distance * math.sin(start_angle + half_yaw_total)
        mismatch = math.hypot(
            (end[0] - start[0]) - expected_dx,
            (end[1] - start[1]) - expected_dy,
        )
        all_events = tuple(self._contact_events)
        end_clearances = clearances_by_shape(end, angle, self.posts)
        return StepRecord(
            request=request,
            shaft=shaft,
            start=start,
            start_angle=start_angle,
            end=end,
            end_angle=angle,
            velocity=(float(self.body.velocity.x), float(self.body.velocity.y)),
            angular_velocity=float(self.body.angular_velocity),
            elapsed=self.elapsed,
            step_count=self.engine_steps,
            max_penetration=max_pen,
            contact_count=sum(event.contact_points for event in all_events),
            arbiter_count=len(all_events),
            total_impulse=sum(event.impulse for event in all_events),
            crossed_wall_or_post=crossed,
            body_shaft_mismatch=mismatch,
            end_penetration=max(0.0, -min(end_clearances.values())),
            contact_seen=bool(all_events),
            minimum_clearance_m=min(minima.values(), default=math.inf),
            clearance_sampling_bound_m=sampling_bound,
            minimum_clearance_by_shape=tuple(sorted(minima.items())),
            end_clearance_by_shape=tuple(sorted(end_clearances.items())),
            contact_events=all_events,
            simultaneous_contact_identities=tuple(simultaneous),
        )
