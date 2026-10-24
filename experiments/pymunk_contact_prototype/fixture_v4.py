"""Versioned S2 motor adapter with explicit #226 fixture provenance.

`fixture.py` is not byte-identical to #226's main version: main has SHA-256
`63127723dae68ebf9a2113cd1d9827925871e8d595557522f5cc9b4ee47f72f0`, while
the executed/current version has SHA-256
`99765d1d8f1a4d7894035d8dc075f635709f5f351651b5cd98175d1726fc8a53`.
Relative to main, the executed file adds `Callable`, an optional
`execution_guard` field and its call immediately before `Space.step`; adds the
no-op `_begin_motor_command` hook and `_apply_motor_substep` containing the
original legacy schedule; and replaces the inline `advance` schedule with
those hook calls. It also has two formatting-only changes.
By source inspection, the legacy branch retains the original contact-flag
condition and wheel-derived velocity formula. That semantic equivalence was not
independently reproduced with a physical #226 run. The V4 subclass overrides
the hooks and does not use the legacy motor law.
"""

from __future__ import annotations

from experiments.pymunk_contact_prototype.fixture import ContactWorld
from experiments.pymunk_contact_prototype.motor import (
    apply_persistent_curvature_force,
    begin_wheel_command,
)


class ContactWorldV4(ContactWorld):
    """Use the shared callback-independent motor law for successor probes.

    This adapter inherits the extended `fixture.py`; see the module provenance
    above for its exact main/executed hashes and documented hook/guard changes.
    Its legacy compatibility option is explicitly fixed to False. Successor
    velocity targets are set only at command boundaries; the curvature force
    is submitted each substep without contact-dependent gating.
    """

    def __init__(self, *, microsteps: int = 400) -> None:
        super().__init__(
            microsteps=microsteps,
            suppress_velocity_refresh_after_contact=False,
        )

    def _begin_motor_command(
        self, speed: float, omega: float, start_angle: float
    ) -> None:
        begin_wheel_command(self.body, speed, omega, start_angle)

    def _apply_motor_substep(self, speed: float, omega: float, h: float) -> None:
        apply_persistent_curvature_force(self.body, omega)

    def reset(self, position: tuple[float, float], angle: float) -> None:
        super().reset(position, angle)
        # The base reset reconstructs a temporary ContactWorld. Rebind its
        # callback to this live successor so event collection remains owned by
        # the reset instance, exactly as the obstacle adapter does.
        self.space.on_collision(None, None, post_solve=self._post_solve)
