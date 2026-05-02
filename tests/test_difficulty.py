import pytest

from game.difficulty import (
    Difficulty,
    DifficultyConfig,
    config_for,
)


def test_difficulty_levels_exist():
    assert Difficulty.EASY.name == "EASY"
    assert Difficulty.NORMAL.name == "NORMAL"
    assert Difficulty.HARD.name == "HARD"


@pytest.mark.parametrize("level", list(Difficulty))
def test_config_for_returns_dataclass(level):
    cfg = config_for(level)
    assert isinstance(cfg, DifficultyConfig)
    assert cfg.starting_lives >= 1
    assert cfg.dive_freq_multiplier > 0
    assert cfg.enemy_bullet_speed_multiplier > 0


def test_easy_easier_than_normal():
    e = config_for(Difficulty.EASY)
    n = config_for(Difficulty.NORMAL)
    assert e.starting_lives >= n.starting_lives
    assert e.dive_freq_multiplier <= n.dive_freq_multiplier
    assert e.enemy_bullet_speed_multiplier <= n.enemy_bullet_speed_multiplier


def test_hard_harder_than_normal():
    n = config_for(Difficulty.NORMAL)
    h = config_for(Difficulty.HARD)
    assert h.starting_lives <= n.starting_lives
    assert h.dive_freq_multiplier >= n.dive_freq_multiplier
    assert h.enemy_bullet_speed_multiplier >= n.enemy_bullet_speed_multiplier


def test_normal_is_baseline():
    """Normal multipliers should equal 1.0 so the baseline is preserved."""
    n = config_for(Difficulty.NORMAL)
    assert n.dive_freq_multiplier == 1.0
    assert n.enemy_bullet_speed_multiplier == 1.0


def test_tractor_probability_multipliers():
    assert config_for(Difficulty.EASY).tractor_probability_multiplier == 0.5
    assert config_for(Difficulty.NORMAL).tractor_probability_multiplier == 1.0
    assert config_for(Difficulty.HARD).tractor_probability_multiplier == 1.5
