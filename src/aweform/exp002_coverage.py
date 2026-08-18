"""Deterministic evaluator-side spatial coverage for EXP-002.

This component deliberately has no connection to controller observations or
random-number generators.  It records the cells touched by the body's actual
straight-line movement path, not a visualizer approximation of that path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Coordinate = tuple[float, float]


@dataclass(slots=True)
class CoverageGrid:
    """A fixed evaluator-only grid over a bounded rectangular world."""

    width: int = 32
    height: int = 32
    world_min: Coordinate = (0.0, 0.0)
    world_max: Coordinate = (1.0, 1.0)
    _visited: bytearray = field(init=False, repr=False)
    _visited_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        _validate_dimension("width", self.width)
        _validate_dimension("height", self.height)
        _validate_bounds(self.world_min, self.world_max)
        self._visited = bytearray(self.width * self.height)

    @property
    def cell_count(self) -> int:
        """Return the total number of coverage cells."""
        return self.width * self.height

    @property
    def visited_cell_count(self) -> int:
        """Return the number of distinct cells visited so far."""
        return self._visited_count

    @property
    def remaining_cell_count(self) -> int:
        """Return the number of cells not yet visited."""
        return self.cell_count - self._visited_count

    @property
    def coverage_fraction(self) -> float:
        """Return visited cells as a fraction of the fixed grid."""
        return self._visited_count / self.cell_count

    @property
    def visited_cells(self) -> tuple[tuple[int, int], ...]:
        """Return visited ``(row, column)`` cells in stable row-major order."""
        return tuple(
            (index // self.width, index % self.width)
            for index, visited in enumerate(self._visited)
            if visited
        )

    def mark_position(self, position: Coordinate) -> None:
        """Mark the cell containing one evaluator-side body position."""
        self._mark_index(self.cell_index(position))

    def mark_movement(self, previous: Coordinate, new: Coordinate) -> None:
        """Mark every grid cell intersected by the straight movement segment."""
        previous_cell = self.cell_index(previous)
        new_cell = self.cell_index(new)
        self._mark_index(previous_cell)
        self._mark_index(new_cell)

        x_min, y_min = self.world_min
        x_max, y_max = self.world_max
        dx = new[0] - previous[0]
        dy = new[1] - previous[1]
        cell_width = (x_max - x_min) / self.width
        cell_height = (y_max - y_min) / self.height
        previous_row, previous_column = divmod(previous_cell, self.width)
        preferred_row = (
            previous_row
            if dy == 0.0
            and _is_grid_boundary(
                previous[1], y_min, cell_height, self.height
            )
            else None
        )
        preferred_column = (
            previous_column
            if dx == 0.0
            and _is_grid_boundary(previous[0], x_min, cell_width, self.width)
            else None
        )
        for row in range(self.height):
            if preferred_row is not None and row != preferred_row:
                continue
            cell_y_min = y_min + row * cell_height
            cell_y_max = y_min + (row + 1) * cell_height
            for column in range(self.width):
                if preferred_column is not None and column != preferred_column:
                    continue
                cell_x_min = x_min + column * cell_width
                cell_x_max = x_min + (column + 1) * cell_width
                if _segment_intersects_rectangle(
                    previous,
                    new,
                    cell_x_min,
                    cell_x_max,
                    cell_y_min,
                    cell_y_max,
                ):
                    self._mark_index(row * self.width + column)

    def cell_index(self, position: Coordinate) -> int:
        """Return the stable row-major index for an in-bounds position."""
        _validate_position(position, self.world_min, self.world_max)
        x_min, y_min = self.world_min
        x_max, y_max = self.world_max
        x_fraction = (position[0] - x_min) / (x_max - x_min)
        y_fraction = (position[1] - y_min) / (y_max - y_min)
        column = min(self.width - 1, int(x_fraction * self.width))
        row = min(self.height - 1, int(y_fraction * self.height))
        return row * self.width + column

    def _mark_index(self, index: int) -> None:
        if not self._visited[index]:
            self._visited[index] = 1
            self._visited_count += 1


def _segment_intersects_rectangle(
    start: Coordinate,
    end: Coordinate,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> bool:
    """Use deterministic Liang–Barsky clipping against a closed rectangle."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    lower = 0.0
    upper = 1.0
    for p, q in (
        (-dx, start[0] - x_min),
        (dx, x_max - start[0]),
        (-dy, start[1] - y_min),
        (dy, y_max - start[1]),
    ):
        if p == 0.0:
            if q < 0.0:
                return False
            continue
        parameter = q / p
        if p < 0.0:
            lower = max(lower, parameter)
        else:
            upper = min(upper, parameter)
        if lower > upper:
            return False
    # Endpoint-only contact is represented by the explicit start/end cell
    # marks. Requiring positive segment length prevents adjacent cells from
    # being counted merely because a path endpoint lies on their boundary.
    return upper > lower


def _is_grid_boundary(
    value: float,
    minimum: float,
    cell_size: float,
    cell_count: int,
) -> bool:
    """Return whether a coordinate lies on an internal grid boundary."""
    scaled = (value - minimum) / cell_size
    return 0 < scaled < cell_count and scaled == math.floor(scaled)


def _validate_dimension(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_bounds(world_min: Coordinate, world_max: Coordinate) -> None:
    _validate_coordinate("world_min", world_min)
    _validate_coordinate("world_max", world_max)
    if not all(lower < upper for lower, upper in zip(world_min, world_max)):
        raise ValueError("world_min must be strictly below world_max")


def _validate_position(
    position: Coordinate,
    world_min: Coordinate,
    world_max: Coordinate,
) -> None:
    _validate_coordinate("position", position)
    if not all(
        lower <= value <= upper
        for value, lower, upper in zip(position, world_min, world_max)
    ):
        raise ValueError("position must be within the world bounds")


def _validate_coordinate(name: str, coordinate: Coordinate) -> None:
    try:
        valid = len(coordinate) == 2 and all(
            math.isfinite(float(value)) for value in coordinate
        )
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"{name} must contain two finite coordinates")
