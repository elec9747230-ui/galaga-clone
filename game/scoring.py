"""Pure scoring/lives logic. No pygame import."""

import json
from dataclasses import dataclass
from pathlib import Path

import settings

_KILL_SCORES = {
    "normal": settings.SCORE_NORMAL_KILL,
    "dive": settings.SCORE_DIVE_KILL,
    "boss": settings.SCORE_BOSS_KILL,
    "bonus": settings.SCORE_BONUS_PER_KILL,
}


@dataclass
class Scoring:
    score: int = 0
    lives: int = settings.PLAYER_START_LIVES
    wave: int = 1
    shots_fired: int = 0
    hits: int = 0
    enemies_killed: int = 0

    def add_kill(self, kind: str) -> None:
        if kind not in _KILL_SCORES:
            raise ValueError(f"Unknown enemy kind: {kind!r}")
        self.score += _KILL_SCORES[kind]
        self.enemies_killed += 1
        self.hits += 1

    def add_shot(self) -> None:
        self.shots_fired += 1

    def lose_life(self) -> None:
        if self.lives > 0:
            self.lives -= 1

    def gain_life(self) -> None:
        self.lives += 1

    def accuracy(self) -> float:
        if self.shots_fired == 0:
            return 0.0
        return self.hits / self.shots_fired


def load_highscore(path: Path | str = settings.HIGHSCORE_PATH) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text())
        return int(data.get("highscore", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0


def save_highscore(score: int, path: Path | str = settings.HIGHSCORE_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(json.dumps({"highscore": int(score)}))
    except OSError as e:
        print(f"Warning: could not save highscore: {e}")
