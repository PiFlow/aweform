"""Direct Pymunk rigid-body fixture; no production Aweform imports."""

from __future__ import annotations

import math
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


def wall_penetration(position: tuple[float, float], angle: float) -> float:
    pts = corners(position, angle)
    return max(
        0.0,
        max(-x for x, _ in pts),
        max(x - ROOM for x, _ in pts),
        max(-y for _, y in pts),
        max(y - ROOM for _, y in pts),
    )


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


class ContactWorld:
    """One deterministic room/post fixture advanced by Pymunk's Space.step."""

    def __init__(
        self,
        *,
        microsteps: int = 10,
        posts: tuple[tuple[float, float], ...] = (),
        collision_bias: float = 0.001797010299914434,
        suppress_velocity_refresh_after_contact: bool = False,
    ) -> None:
        if microsteps not in (10, 20):
            raise ValueError("microsteps must be 10 or 20")
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
        self._walls: list[pymunk.Segment] = []
        static = self.space.static_body
        walls = (
            ((0.0, 0.0), (ROOM, 0.0)),
            ((ROOM, 0.0), (ROOM, ROOM)),
            ((ROOM, ROOM), (0.0, ROOM)),
            ((0.0, ROOM), (0.0, 0.0)),
        )
        for a, b in walls:
            wall = pymunk.Segment(static, a, b, WALL_THICKNESS / 2)
            wall.friction = wall.elasticity = 0.0
            self._walls.append(wall)
        shapes: list[pymunk.Shape] = list(self._walls)
        for center in posts:
            post = pymunk.Circle(static, POST_RADIUS, center)
            post.friction = post.elasticity = 0.0
            shapes.append(post)
        self.space.add(*shapes)
        self.elapsed = 0.0
        self.logical_steps = 0
        self.engine_steps = 0
        self._contacts: list[tuple[int, float]] = []
        self.space.on_collision(None, None, post_solve=self._post_solve)

    def _post_solve(
        self, arbiter: pymunk.Arbiter, _space: pymunk.Space, _data: object
    ) -> None:
        impulse = arbiter.total_impulse.length
        self._contact_seen_this_command = True
        self._contacts.append((len(arbiter.contact_point_set.points), float(impulse)))

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
        self._contact_seen_this_command = False
        for _ in range(self.microsteps):
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
            self.space.step(h)
            self.engine_steps += 1
            p = (float(self.body.position.x), float(self.body.position.y))
            a = float(self.body.angle)
            wall_pen = wall_penetration(p, a)
            max_pen = max(max_pen, wall_pen)
            crossed |= wall_pen > 0.001
            for center in self.posts:
                post_pen = circle_penetration(p, a, center, POST_RADIUS)
                if post_pen > 0.001:
                    crossed = True
                max_pen = max(max_pen, post_pen)
        self.elapsed += DT
        self.logical_steps += 1
        end = (float(self.body.position.x), float(self.body.position.y))
        angle = float(self.body.angle)
        expected_distance = abs(distance)
        mismatch = abs(math.dist(start, end) - expected_distance)
        contacts = tuple(self._contacts)
        self._contacts = []
        return StepRecord(
            request,
            shaft,
            start,
            start_angle,
            end,
            angle,
            (float(self.body.velocity.x), float(self.body.velocity.y)),
            float(self.body.angular_velocity),
            self.elapsed,
            self.engine_steps,
            max_pen,
            sum(n for n, _ in contacts),
            len(contacts),
            sum(i for _, i in contacts),
            crossed,
            mismatch,
            wall_penetration(end, angle),
            self._contact_seen_this_command or bool(contacts),
        )
