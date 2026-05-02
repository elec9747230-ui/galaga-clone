"""Difficulty levels and per-level config. Pure module; no pygame import."""

from dataclasses import dataclass
from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


@dataclass(frozen=True)
class DifficultyConfig:
    starting_lives: int
    dive_freq_multiplier: float
    enemy_bullet_speed_multiplier: float
    tractor_probability_multiplier: float


_CONFIGS: dict[Difficulty, DifficultyConfig] = {
    Difficulty.EASY: DifficultyConfig(
        starting_lives=4,
        dive_freq_multiplier=0.6,
        enemy_bullet_speed_multiplier=0.7,
        tractor_probability_multiplier=0.5,
    ),
    Difficulty.NORMAL: DifficultyConfig(
        starting_lives=3,
        dive_freq_multiplier=1.0,
        enemy_bullet_speed_multiplier=1.0,
        tractor_probability_multiplier=1.0,
    ),
    Difficulty.HARD: DifficultyConfig(
        starting_lives=2,
        dive_freq_multiplier=1.5,
        enemy_bullet_speed_multiplier=1.3,
        tractor_probability_multiplier=1.5,
    ),
}


def config_for(level: Difficulty) -> DifficultyConfig:
    return _CONFIGS[level]
