"""Pure wave-progression logic. No pygame import.

Maps a 1-based wave number to (a) its kind (normal / boss / bonus) and (b) a
difficulty-parameter bundle. The wave cycle is deliberately Galaga-flavoured:
four normal waves, one boss wave, one bonus wave, then repeat. Difficulty
parameters grow monotonically with the wave number so later cycles are
harder than earlier ones even though the structural pattern repeats.
"""

from dataclasses import dataclass
from enum import Enum

import settings


class WaveType(Enum):
    """Kind of wave the player is about to face."""

    NORMAL = "normal"
    BOSS = "boss"
    BONUS = "bonus"


@dataclass
class DifficultyParams:
    """Per-wave tuning knobs consumed by the spawner and enemy AI.

    Attributes:
        enemy_speed: Base translational speed of formation enemies.
        dive_probability: Probability per frame that an idle enemy
            initiates a dive attack. Clamped at 0.05 in `difficulty_params`.
        enemy_bullet_speed: Velocity of enemy projectiles.
    """

    enemy_speed: float
    dive_probability: float
    enemy_bullet_speed: float


def wave_type_for(wave_number: int) -> WaveType:
    """Cycle: 1-4 normal, 5 boss, 6 bonus, repeats every 6.

    Args:
        wave_number: 1-based wave index.

    Returns:
        WaveType.NORMAL for the first four positions in each cycle, BOSS for
        the fifth, BONUS for the sixth. The cycle length is settings-driven
        so designers can extend it without code changes.
    """
    # Convert to 0-based position inside the current cycle.
    pos_in_cycle = (wave_number - 1) % settings.WAVE_CYCLE_LENGTH
    # Cycle layout (positions 0..5): N N N N B Bonus
    if pos_in_cycle < 4:
        return WaveType.NORMAL
    if pos_in_cycle == 4:
        return WaveType.BOSS
    return WaveType.BONUS


def difficulty_params(wave_number: int) -> DifficultyParams:
    """Each metric grows monotonically with wave number.

    Args:
        wave_number: 1-based wave index.

    Returns:
        DifficultyParams scaled so that every wave is at least as hard as
        the one before it.
    """
    # `growth` is wave-1 so wave 1 returns the bare base values from settings.
    growth = wave_number - 1
    return DifficultyParams(
        # Enemy speed: linear growth at +4 px/s per wave.
        enemy_speed=settings.ENEMY_BASE_SPEED + growth * 4.0,
        # Dive probability: linear growth, capped at 0.05/frame to keep
        # late-game waves chaotic but not unplayable.
        dive_probability=min(0.005 + growth * 0.0015, 0.05),
        # Bullet speed: linear growth at +6 px/s per wave.
        enemy_bullet_speed=settings.ENEMY_BULLET_SPEED + growth * 6.0,
    )


class WaveController:
    """Stateful holder of current wave number; not pygame-dependent.

    Attributes:
        current_wave: 1-based wave index that this controller currently
            represents. Mutated only via `advance()`.
    """

    def __init__(self, start_wave: int = 1) -> None:
        """Construct a controller starting at the given wave (default 1).

        Args:
            start_wave: Initial wave number. Useful for tests or debug menus
                that want to jump directly to a later wave.
        """
        self.current_wave = start_wave

    def current_type(self) -> WaveType:
        """Return the WaveType of the wave currently being played."""
        return wave_type_for(self.current_wave)

    def current_params(self) -> DifficultyParams:
        """Return DifficultyParams for the wave currently being played."""
        return difficulty_params(self.current_wave)

    def advance(self) -> None:
        """Move to the next wave in sequence (no upper bound)."""
        self.current_wave += 1
