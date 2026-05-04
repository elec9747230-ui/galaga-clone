"""Pure scoring/lives logic. No pygame import.

Tracks the run's score, lives, current wave, and shot/hit counters used to
derive accuracy. All point values are sourced from `settings` so designers
can rebalance without touching this module. Highscore persistence is a
small JSON file; load/save degrade gracefully if the file is missing or
corrupt rather than crashing the game.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import settings

# Scoring rules (see settings.py for the actual point values):
#   normal  - kill of an in-formation grunt
#   dive    - kill while the enemy is performing a dive attack (worth more)
#   boss    - boss kill (highest base value)
#   bonus   - per-kill points awarded during BONUS waves
#   tractor - kill of a boss specifically while it is firing its tractor beam
#   rescue  - kill of the boss during a rescue dive (rewards the rescue play)
_KILL_SCORES = {
    "normal": settings.SCORE_NORMAL_KILL,
    "dive": settings.SCORE_DIVE_KILL,
    "boss": settings.SCORE_BOSS_KILL,
    "bonus": settings.SCORE_BONUS_PER_KILL,
    "tractor": settings.SCORE_TRACTOR_KILL,
    "rescue": settings.SCORE_RESCUE_KILL,
}


@dataclass
class Scoring:
    """Mutable run-state for points, lives, and accuracy.

    Attributes:
        score: Current accumulated point total.
        lives: Spare lives remaining (does not include the active ship).
        wave: 1-based current wave number.
        shots_fired: Total bullets the player has launched. Used as the
            denominator for accuracy; only the player's own shots count.
        hits: Total successful enemy kills (the numerator for accuracy).
            Note: each kill increments hits regardless of how many bullets
            were needed, matching the arcade convention of "hits per shot".
        enemies_killed: Lifetime kill counter shown on the HUD.
    """

    score: int = 0
    lives: int = settings.PLAYER_START_LIVES
    wave: int = 1
    shots_fired: int = 0
    hits: int = 0
    enemies_killed: int = 0

    def add_kill(self, kind: str) -> None:
        """Record a kill of the given category, awarding the matching points.

        Args:
            kind: One of the keys in _KILL_SCORES (e.g. "normal", "boss").

        Raises:
            ValueError: If `kind` is not a known scoring category. Failing
                loudly here surfaces typos at the call site instead of
                silently awarding zero points.
        """
        if kind not in _KILL_SCORES:
            raise ValueError(f"Unknown enemy kind: {kind!r}")
        self.score += _KILL_SCORES[kind]
        self.enemies_killed += 1
        # Every kill is also a hit for accuracy purposes; this is intentional
        # even when multiple bullets contributed, matching the original game.
        self.hits += 1

    def add_shot(self) -> None:
        """Increment the shots-fired counter (call once per player bullet)."""
        self.shots_fired += 1

    def lose_life(self) -> None:
        """Decrement lives, never going below zero."""
        if self.lives > 0:
            self.lives -= 1

    def gain_life(self) -> None:
        """Award an extra life (e.g. score-threshold bonus)."""
        self.lives += 1

    def accuracy(self) -> float:
        """Return current shot accuracy in [0, 1].

        Returns:
            hits / shots_fired, or 0.0 when no shots have been fired (avoids
            a divide-by-zero on the first frame of a run).
        """
        if self.shots_fired == 0:
            return 0.0
        return self.hits / self.shots_fired


def load_highscore(path: Path | str = settings.HIGHSCORE_PATH) -> int:
    """Read the persisted highscore from disk.

    Args:
        path: Filesystem path to the JSON highscore file.

    Returns:
        The stored highscore as an int, or 0 if the file is missing,
        malformed, or unreadable. The function never raises so a corrupted
        file cannot prevent the game from launching.
    """
    p = Path(path)
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text())
        return int(data.get("highscore", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        # Swallow all expected failure modes: corrupt JSON, non-int value,
        # or I/O errors. A fresh 0 is always safe to return.
        return 0


def save_highscore(score: int, path: Path | str = settings.HIGHSCORE_PATH) -> None:
    """Persist the highscore to disk, creating parent dirs as needed.

    Args:
        score: New highscore to store.
        path: Destination JSON path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(json.dumps({"highscore": int(score)}))
    except OSError as e:
        # I/O errors (read-only FS, permission denied) should not crash the
        # game on exit; log a warning and continue.
        print(f"Warning: could not save highscore: {e}")
