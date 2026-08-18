from __future__ import annotations

import copy

import numpy as np
import pytest

from aweform.exp002_coverage import CoverageGrid


def test_default_grid_has_exactly_1024_cells() -> None:
    grid = CoverageGrid()

    assert grid.cell_count == 32 * 32 == 1024
    assert grid.visited_cell_count == 0
    assert grid.remaining_cell_count == 1024
    assert grid.coverage_fraction == 0.0


def test_start_cell_counts_once() -> None:
    grid = CoverageGrid()

    grid.mark_position((0.5, 0.5))

    assert grid.visited_cell_count == 1
    assert grid.remaining_cell_count == 1023
    assert grid.coverage_fraction == pytest.approx(1 / 1024)
    assert grid.visited_cells == ((16, 16),)


def test_movement_crossing_multiple_cells_marks_the_whole_path() -> None:
    grid = CoverageGrid()

    grid.mark_movement((0.01, 0.5), (0.30, 0.5))

    assert grid.visited_cell_count == 10
    assert {row for row, _ in grid.visited_cells} == {16}
    assert {column for _, column in grid.visited_cells} == set(range(0, 10))


def test_revisits_do_not_increase_coverage() -> None:
    grid = CoverageGrid()
    grid.mark_position((0.5, 0.5))
    grid.mark_movement((0.5, 0.5), (0.5, 0.5))
    grid.mark_position((0.5, 0.5))

    assert grid.visited_cell_count == 1


def test_same_segments_produce_identical_coverage() -> None:
    movements = (
        ((0.01, 0.01), (0.51, 0.31)),
        ((0.51, 0.31), (0.90, 0.90)),
        ((0.90, 0.90), (0.10, 0.90)),
    )
    first = CoverageGrid()
    second = CoverageGrid()
    for previous, new in movements:
        first.mark_movement(previous, new)
        second.mark_movement(previous, new)

    assert first.visited_cells == second.visited_cells
    assert first.visited_cell_count == second.visited_cell_count
    assert first.coverage_fraction == second.coverage_fraction


def test_coverage_does_not_consume_a_rng() -> None:
    rng = np.random.default_rng(12002)
    state_before = copy.deepcopy(rng.bit_generator.state)
    grid = CoverageGrid()
    grid.mark_position((0.2, 0.2))
    grid.mark_movement((0.2, 0.2), (0.8, 0.8))
    state_after = copy.deepcopy(rng.bit_generator.state)

    assert state_after == state_before


@pytest.mark.parametrize(
    ("position", "message"),
    [((-0.01, 0.5), "within the world bounds"), ((0.5, 1.01), "within")],
)
def test_positions_must_be_in_bounds(
    position: tuple[float, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        CoverageGrid().mark_position(position)
