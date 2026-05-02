import pytest

from game.wave import (
    DifficultyParams,
    WaveController,
    WaveType,
    difficulty_params,
    wave_type_for,
)


@pytest.mark.parametrize(
    "wave,expected",
    [
        (1, WaveType.NORMAL),
        (2, WaveType.NORMAL),
        (3, WaveType.NORMAL),
        (4, WaveType.NORMAL),
        (5, WaveType.BOSS),
        (6, WaveType.BONUS),
        (7, WaveType.NORMAL),
        (10, WaveType.NORMAL),
        (11, WaveType.BOSS),
        (12, WaveType.BONUS),
        (13, WaveType.NORMAL),
        (17, WaveType.BOSS),
        (18, WaveType.BONUS),
    ],
)
def test_wave_type_cycle(wave, expected):
    assert wave_type_for(wave) == expected


def test_difficulty_params_returns_dataclass():
    p = difficulty_params(1)
    assert isinstance(p, DifficultyParams)
    assert p.enemy_speed > 0
    assert 0 <= p.dive_probability <= 1
    assert p.enemy_bullet_speed > 0


def test_difficulty_increases_monotonically():
    params = [difficulty_params(w) for w in range(1, 21)]
    speeds = [p.enemy_speed for p in params]
    dives = [p.dive_probability for p in params]
    bullets = [p.enemy_bullet_speed for p in params]
    # Each metric is non-decreasing
    assert all(speeds[i] <= speeds[i + 1] for i in range(len(speeds) - 1))
    assert all(dives[i] <= dives[i + 1] for i in range(len(dives) - 1))
    assert all(bullets[i] <= bullets[i + 1] for i in range(len(bullets) - 1))


def test_dive_probability_capped():
    p = difficulty_params(1000)
    assert p.dive_probability <= 1.0


def test_wave_controller_starts_at_one():
    c = WaveController()
    assert c.current_wave == 1
    assert c.current_type() == WaveType.NORMAL


def test_wave_controller_advance():
    c = WaveController()
    c.advance()
    assert c.current_wave == 2


def test_wave_controller_reaches_boss_then_bonus():
    c = WaveController()
    for _ in range(4):
        c.advance()
    assert c.current_wave == 5
    assert c.current_type() == WaveType.BOSS
    c.advance()
    assert c.current_type() == WaveType.BONUS
