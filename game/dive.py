"""Dive attack path generation. Uses pygame.Vector2 only."""

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
    """
    rng = random.Random(seed)
    swing_dir = rng.choice([-1, 1])
    swing_x = swing_dir * rng.uniform(80, 160)
    wobble_amp = rng.uniform(8, 22)
    wobble_freq = rng.uniform(2.0, 3.5)

    midpoint_y = (enemy_pos.y + player_pos.y) / 2
    ctrl1 = Vector2(enemy_pos.x + swing_x, midpoint_y - 40)
    ctrl2 = Vector2(player_pos.x - swing_x * 0.5, player_pos.y - 40)
    end = Vector2(player_pos.x + swing_x, settings.PLAYFIELD_HEIGHT + 30)

    path = []
    for i in range(samples + 1):
        t = i / samples
        p = _cubic_bezier(enemy_pos, ctrl1, ctrl2, end, t)
        # Apply tangent-perpendicular wobble (just along x for simplicity)
        wobble = wobble_amp * math.sin(wobble_freq * math.pi * t)
        path.append(Vector2(p.x + wobble, p.y))
    return path


def _cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
    u = 1 - t
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
