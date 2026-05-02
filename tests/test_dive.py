from pygame import Vector2

from game.dive import dive_path
from settings import PLAYFIELD_HEIGHT, PLAYFIELD_WIDTH


def test_path_starts_at_enemy():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    assert (path[0] - enemy).length() < 1.0


def test_path_exits_below_playfield():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    assert path[-1].y >= PLAYFIELD_HEIGHT


def test_path_smooth():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    for i in range(len(path) - 1):
        d = (path[i + 1] - path[i]).length()
        assert d < 60.0  # no big jumps


def test_path_seed_changes_path():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    p1 = dive_path(enemy, player, seed=1)
    p2 = dive_path(enemy, player, seed=2)
    # at least one waypoint differs
    differs = any((p1[i] - p2[i]).length() > 1.0 for i in range(min(len(p1), len(p2))))
    assert differs


def test_path_stays_within_horizontal_bounds_mostly():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    # allow small overshoot at edges due to sine wobble
    for p in path:
        assert -50 < p.x < PLAYFIELD_WIDTH + 50
