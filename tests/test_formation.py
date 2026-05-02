from game.formation import entry_path, slot_position
from settings import (
    FORMATION_COLS,
    FORMATION_ROWS,
    PLAYFIELD_HEIGHT,
    PLAYFIELD_WIDTH,
)


def test_slot_positions_inside_playfield():
    for row in range(FORMATION_ROWS):
        for col in range(FORMATION_COLS):
            pos = slot_position(row, col, oscillation_phase=0.0)
            assert 0 < pos.x < PLAYFIELD_WIDTH
            assert 0 < pos.y < PLAYFIELD_HEIGHT / 2  # formation in upper half


def test_slot_positions_centered_horizontally():
    """Leftmost and rightmost columns equidistant from playfield edges."""
    leftmost = slot_position(0, 0, 0.0).x
    rightmost = slot_position(0, FORMATION_COLS - 1, 0.0).x
    left_margin = leftmost
    right_margin = PLAYFIELD_WIDTH - rightmost
    assert abs(left_margin - right_margin) < 1.0


def test_slot_oscillation_changes_x():
    pos1 = slot_position(0, 0, 0.0)
    pos2 = slot_position(0, 0, 1.0)  # different phase
    assert pos1.x != pos2.x


def test_entry_path_starts_offscreen():
    """Entry begins offscreen (above or beside playfield)."""
    path = entry_path(row=0, col=0)
    assert len(path) > 5
    start = path[0]
    assert start.y < 0 or start.x < 0 or start.x > PLAYFIELD_WIDTH


def test_entry_path_ends_at_slot():
    """Last waypoint matches the formation slot."""
    target = slot_position(2, 3, 0.0)
    path = entry_path(row=2, col=3)
    end = path[-1]
    assert (end - target).length() < 1.0


def test_entry_path_smooth():
    """Adjacent waypoints don't jump too far."""
    path = entry_path(row=0, col=0)
    for i in range(len(path) - 1):
        d = (path[i + 1] - path[i]).length()
        assert d < 100  # no huge jumps
