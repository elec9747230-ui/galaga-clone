"""Formation slot positions and entry paths. Uses pygame.Vector2 only."""

import math

from pygame import Vector2

import settings

_FORMATION_TOP = settings.FORMATION_TOP_MARGIN
_TOTAL_W = settings.FORMATION_COLS * settings.FORMATION_SLOT_WIDTH
_LEFT_MARGIN = (settings.PLAYFIELD_WIDTH - _TOTAL_W) / 2 + settings.FORMATION_SLOT_WIDTH / 2
_OSCILLATION_AMPLITUDE = 14.0  # pixels
_OSCILLATION_PERIOD = 4.0  # seconds (caller passes elapsed-time-derived phase)


def slot_position(row: int, col: int, oscillation_phase: float) -> Vector2:
    """Return formation slot position in playfield-local coords.

    oscillation_phase: typically `time * 2*pi / OSCILLATION_PERIOD` from caller.
    """
    base_x = _LEFT_MARGIN + col * settings.FORMATION_SLOT_WIDTH
    base_y = _FORMATION_TOP + row * settings.FORMATION_SLOT_HEIGHT
    offset_x = _OSCILLATION_AMPLITUDE * math.sin(oscillation_phase)
    return Vector2(base_x + offset_x, base_y)


def entry_path(row: int, col: int, samples: int = 60) -> list[Vector2]:
    """Bezier path from offscreen to slot. Different sides per column."""
    target = slot_position(row, col, 0.0)
    # Alternate entry side based on column for visual variety
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
    u = 1 - t
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
