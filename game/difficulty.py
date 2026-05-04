"""Difficulty levels and per-level config. Pure module; no pygame import.

Provides three preset difficulty bands. Each preset is expressed as a set of
multipliers applied on top of the base wave-progression curve in `wave.py`,
so wave-by-wave growth still happens; difficulty only re-scales the curve.
"""

from dataclasses import dataclass
from enum import Enum


class Difficulty(Enum):
    """Selectable difficulty presets exposed in the menu."""

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


@dataclass(frozen=True)
class DifficultyConfig:
    """Immutable bundle of multipliers and starting values for one difficulty.

    Attributes:
        starting_lives: Number of lives the player begins the run with.
        dive_freq_multiplier: Scales the per-frame dive probability emitted
            by `wave.difficulty_params`. Lower = fewer dive attacks.
        enemy_bullet_speed_multiplier: Scales enemy projectile velocity.
            Lower values give the player more reaction time.
        tractor_probability_multiplier: Scales the chance a boss attempts
            a tractor beam capture each eligible frame.
    """

    starting_lives: int
    dive_freq_multiplier: float
    enemy_bullet_speed_multiplier: float
    tractor_probability_multiplier: float


# Tuning notes for the curve below:
#   - EASY: more lives, ~60% dive frequency, slower bullets, halved capture odds.
#     Keeps the player relaxed; mistakes are forgiven.
#   - NORMAL: identity multipliers (1.0) so the base curve in `wave.py` is the truth.
#   - HARD: fewer lives, 50% more dives, 30% faster bullets, 50% more capture attempts.
#     Designed to reward veterans without changing wave structure.
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
    """Return the immutable DifficultyConfig matching `level`.

    Args:
        level: A Difficulty enum member.

    Returns:
        The corresponding DifficultyConfig instance from the preset table.

    Raises:
        KeyError: If `level` is not a registered preset (should not occur
            given the closed enum).
    """
    return _CONFIGS[level]
