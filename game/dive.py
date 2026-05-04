"""Dive attack path generation. Uses pygame.Vector2 only.

Generates the polyline an enemy follows when it leaves formation to dive at
the player. Each path is a cubic Bezier curve with a small sinusoidal wobble
applied so two simultaneous dives never look identical, even from the same
slot. Only `pygame.Vector2` is imported from pygame, keeping this testable
without a display surface.
"""

import math
import random

from pygame import Vector2

import settings


def dive_path(
    enemy_pos: Vector2,
    player_pos: Vector2,
    seed: int,
    samples: int = 80,
) -> list[Vector2]:
    """Curve from enemy_pos sweeping toward player area then offscreen below.

    Combines cubic Bezier with a sine wobble for organic feel. `seed` chooses
    swing direction and amplitude.

    Args:
        enemy_pos: Starting position of the diving enemy (typically its
            formation slot).
        player_pos: Current player position used as the curve target.
        seed: Integer seed for a local RNG so the same enemy/frame produces
            the same swing direction and wobble; isolated from global RNG.
        samples: Number of polyline points; higher = smoother curve at the
            cost of memory.

    Returns:
        A list of Vector2 sample points along the dive curve, in order from
        `enemy_pos` to a target just below the playfield bottom.
    """
    # Local RNG keyed by `seed` so paths are reproducible and don't perturb
    # the rest of the game's randomness (bullets, formation entries, etc.).
    rng = random.Random(seed)
    # Swing direction (-1 left, +1 right) and magnitude shape the curve's bulge:
    # the enemy first arcs sideways before plunging toward the player.
    swing_dir = rng.choice([-1, 1])
    swing_x = swing_dir * rng.uniform(80, 160)
    # Wobble parameters add a small lateral oscillation to break up perfect
    # Bezier symmetry; tuned to feel "alive" without making the path unfair.
    wobble_amp = rng.uniform(8, 22)
    wobble_freq = rng.uniform(2.0, 3.5)

    # Two control points define the cubic Bezier:
    #   ctrl1 pulls the early curve sideways (the swing).
    #   ctrl2 pulls the late curve back toward the player vicinity.
    midpoint_y = (enemy_pos.y + player_pos.y) / 2
    ctrl1 = Vector2(enemy_pos.x + swing_x, midpoint_y - 40)
    ctrl2 = Vector2(player_pos.x - swing_x * 0.5, player_pos.y - 40)
    # End below the playfield so the enemy exits cleanly even if it misses.
    end = Vector2(player_pos.x + swing_x, settings.PLAYFIELD_HEIGHT + 30)

    path = []
    for i in range(samples + 1):
        t = i / samples
        p = _cubic_bezier(enemy_pos, ctrl1, ctrl2, end, t)
        # Apply tangent-perpendicular wobble (just along x for simplicity)
        # A true perpendicular would track the curve's tangent, but x-only
        # wobble is visually indistinguishable for these small amplitudes
        # and avoids per-sample tangent calculations.
        wobble = wobble_amp * math.sin(wobble_freq * math.pi * t)
        path.append(Vector2(p.x + wobble, p.y))
    return path


def _cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
    """Standard cubic Bezier interpolation at parameter `t` in [0, 1].

    Args:
        p0: Curve start point.
        p1: First control point (tangent at p0).
        p2: Second control point (tangent at p3).
        p3: Curve end point.
        t: Parameter in [0, 1].

    Returns:
        The Vector2 point on the curve at `t`.
    """
    u = 1 - t
    # Bernstein form: B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
