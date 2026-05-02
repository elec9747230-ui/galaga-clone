"""Pure wave-progression logic. No pygame import."""

from dataclasses import dataclass
from enum import Enum

import settings


class WaveType(Enum):
    NORMAL = "normal"
    BOSS = "boss"
    BONUS = "bonus"


@dataclass
class DifficultyParams:
    enemy_speed: float
    dive_probability: float
    enemy_bullet_speed: float


def wave_type_for(wave_number: int) -> WaveType:
    """Cycle: 1-4 normal, 5 boss, 6 bonus, repeats every 6."""
    pos_in_cycle = (wave_number - 1) % settings.WAVE_CYCLE_LENGTH
    if pos_in_cycle < 4:
        return WaveType.NORMAL
    if pos_in_cycle == 4:
        return WaveType.BOSS
    return WaveType.BONUS


def difficulty_params(wave_number: int) -> DifficultyParams:
    """Each metric grows monotonically with wave number."""
    growth = wave_number - 1
    return DifficultyParams(
        enemy_speed=settings.ENEMY_BASE_SPEED + growth * 4.0,
        dive_probability=min(0.005 + growth * 0.0015, 0.05),
        enemy_bullet_speed=settings.ENEMY_BULLET_SPEED + growth * 6.0,
    )


class WaveController:
    """Stateful holder of current wave number; not pygame-dependent."""

    def __init__(self, start_wave: int = 1) -> None:
        self.current_wave = start_wave

    def current_type(self) -> WaveType:
        return wave_type_for(self.current_wave)

    def current_params(self) -> DifficultyParams:
        return difficulty_params(self.current_wave)

    def advance(self) -> None:
        self.current_wave += 1
