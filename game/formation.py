"""Formation slot positions and entry paths. Uses pygame.Vector2 only.

Computes:
  * The grid coordinates of every slot in the enemy formation, including a
    shared horizontal oscillation that makes the whole grid sway in unison.
  * A cubic Bezier path that brings an enemy from offscreen into its slot,
    alternating entry side per column for visual variety.

The grid math centres the formation horizontally inside the playfield:
    total_width  = COLS * SLOT_WIDTH
    left_margin  = (PLAYFIELD_WIDTH - total_width) / 2 + SLOT_WIDTH / 2
The `+ SLOT_WIDTH/2` bias places the *centre* of column 0 (not its left edge)
at the computed margin so sprites are correctly centred in their cells.
"""

import math

from pygame import Vector2

import settings

# Pre-compute layout constants once at import. They depend only on settings,
# so caching avoids recomputing on every slot_position() call.
_FORMATION_TOP = settings.FORMATION_TOP_MARGIN
_TOTAL_W = settings.FORMATION_COLS * settings.FORMATION_SLOT_WIDTH
# Centre column 0's slot midline; see module docstring for derivation.
_LEFT_MARGIN = (settings.PLAYFIELD_WIDTH - _TOTAL_W) / 2 + settings.FORMATION_SLOT_WIDTH / 2
_OSCILLATION_AMPLITUDE = 14.0  # pixels
_OSCILLATION_PERIOD = 4.0  # seconds (caller passes elapsed-time-derived phase)


def slot_position(row: int, col: int, oscillation_phase: float) -> Vector2:
    """Return formation slot position in playfield-local coords.

    oscillation_phase: typically `time * 2*pi / OSCILLATION_PERIOD` from caller.

    Args:
        row: 0-based row index inside the formation grid.
        col: 0-based column index inside the formation grid.
        oscillation_phase: Phase in radians of the global sway. The caller
            supplies the same phase for every slot in a frame so the entire
            grid moves together.

    Returns:
        Vector2 of the slot's centre in playfield-local coordinates.
    """
    # Linear grid mapping: each row/col steps by a fixed slot size.
    base_x = _LEFT_MARGIN + col * settings.FORMATION_SLOT_WIDTH
    base_y = _FORMATION_TOP + row * settings.FORMATION_SLOT_HEIGHT
    # Single global x-offset shared by every slot this frame: that uniformity
    # is what makes the formation visually translate as one rigid body.
    offset_x = _OSCILLATION_AMPLITUDE * math.sin(oscillation_phase)
    return Vector2(base_x + offset_x, base_y)


def entry_path(row: int, col: int, samples: int = 60) -> list[Vector2]:
    """Bezier path from offscreen to slot. Different sides per column.

    Args:
        row: Target row in the formation.
        col: Target column in the formation; determines entry side.
        samples: Polyline resolution.

    Returns:
        List of Vector2 points from an offscreen origin to the slot centre.
    """
    # Use phase 0 so entries always converge on the formation's neutral
    # position regardless of the current oscillation; the formation will
    # sway after the enemy has settled in.
    target = slot_position(row, col, 0.0)
    # Alternate entry side based on column for visual variety
    # Left half of the grid enters from the upper-left, right half from
    # the upper-right; control points mirror accordingly.
    if col < settings.FORMATION_COLS / 2:
        start = Vector2(-30, -30)
        ctrl1 = Vector2(60, settings.PLAYFIELD_HEIGHT * 0.4)
        ctrl2 = Vector2(target.x - 80, target.y + 100)
    else:
        start = Vector2(settings.PLAYFIELD_WIDTH + 30, -30)
        ctrl1 = Vector2(settings.PLAYFIELD_WIDTH - 60, settings.PLAYFIELD_HEIGHT * 0.4)
        ctrl2 = Vector2(target.x + 80, target.y + 100)
    return [_cubic_bezier(start, ctrl1, ctrl2, target, t / samples) for t in range(samples + 1)]


def _cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
    """Standard cubic Bezier interpolation at parameter `t` in [0, 1].

    Args:
        p0: Curve start point.
        p1: First control point.
        p2: Second control point.
        p3: Curve end point.
        t: Parameter in [0, 1].

    Returns:
        Vector2 point on the curve at `t`.
    """
    u = 1 - t
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
