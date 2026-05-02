# Difficulty Selection + Dive Frequency Fix Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the dive-frequency bug that causes ~12 dives/sec (intended ~0.2/sec), and add a 3-level difficulty selector (EASY/NORMAL/HARD) to the title screen.

**Architecture:**
- New `game/difficulty.py` (pure module, pygame-free) — `Difficulty` enum + per-level multiplier tables.
- `TitleScene` adds horizontal arrow-key selector that cycles EASY/NORMAL/HARD before pressing SPACE.
- `PlayScene` and `BonusScene` accept a `Difficulty` parameter and apply it to: starting lives, dive frequency multiplier, enemy bullet speed multiplier.
- Bug fix: replace the `* dt * 60` factor in the per-frame dive check with `* dt`, so the unit matches the variable name (`_dive_probability_per_sec`).

**Tech Stack:** Python 3.11+, Pygame (existing).

**Spec reference:** [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](../specs/2026-05-02-galaga-clone-design.md). This feature is an addition to "Open Items / Future Work" §10.

---

## File Structure

```
galaga-clone/
├── game/
│   └── difficulty.py            # NEW: Difficulty enum + multiplier tables
├── scenes/
│   ├── title.py                 # MODIFY: difficulty selector UI
│   ├── play.py                  # MODIFY: accept difficulty, fix dive bug, apply mults
│   └── bonus.py                 # MODIFY: accept difficulty (passed through)
└── tests/
    └── test_difficulty.py       # NEW: ensure multiplier consistency
```

---

## Tasks

### Task 1: Create `game/difficulty.py` with Difficulty enum + tests

**Files:**
- Create: `game/difficulty.py`
- Create: `tests/test_difficulty.py`

- [ ] **Step 1: Write failing tests**

`tests/test_difficulty.py`:
```python
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
```

- [ ] **Step 2: Run tests, expect failure**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write implementation**

`game/difficulty.py`:
```python
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


_CONFIGS: dict[Difficulty, DifficultyConfig] = {
    Difficulty.EASY: DifficultyConfig(
        starting_lives=4,
        dive_freq_multiplier=0.6,
        enemy_bullet_speed_multiplier=0.7,
    ),
    Difficulty.NORMAL: DifficultyConfig(
        starting_lives=3,
        dive_freq_multiplier=1.0,
        enemy_bullet_speed_multiplier=1.0,
    ),
    Difficulty.HARD: DifficultyConfig(
        starting_lives=2,
        dive_freq_multiplier=1.5,
        enemy_bullet_speed_multiplier=1.3,
    ),
}


def config_for(level: Difficulty) -> DifficultyConfig:
    return _CONFIGS[level]
```

- [ ] **Step 4: Run tests, expect pass**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -v
```

- [ ] **Step 5: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/difficulty.py tests/test_difficulty.py
git commit -m "feat(difficulty): Difficulty enum + per-level config with tests"
```

---

### Task 2: Fix dive frequency bug in `scenes/play.py`

**Files:**
- Modify: `scenes/play.py`

The current check is `random.random() < self._dive_probability_per_sec * dt * 60`. With `dt ≈ 1/60`, this evaluates as `random() < 0.2` per frame — about 12 successful dives per second. The variable name says "per second", so the math should be `random() < self._dive_probability_per_sec * dt` for a true per-second rate.

- [ ] **Step 1: Make the fix**

In `scenes/play.py`, find:
```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt * 60:
```

Replace with:
```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt:
```

Also, since the per-second rate is now actual seconds, the base value needs scaling. Currently `_dive_probability_per_sec = 0.20 + 0.5 * p.dive_probability` produces ~0.2025 (which was always wrong as per-second; it was treated as per-frame). Adjust the scale to a sensible per-second base.

In `_apply_wave_difficulty`, change:
```python
    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        self._dive_probability_per_sec = 0.20 + 0.5 * p.dive_probability
```

To:
```python
    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        # Scaled to genuine per-second rate (0.5 dives/sec base, +grows with wave)
        self._dive_probability_per_sec = 0.5 + 30.0 * p.dive_probability
```

That gives ~0.5 dives/sec at wave 1, ~2.0 dives/sec near the cap.

- [ ] **Step 2: Smoke import**

```powershell
.venv\Scripts\python.exe -c "from scenes.play import PlayScene; print('ok')"
```

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/play.py
git commit -m "fix(play): correct dive-frequency unit (was ~12/s, now ~0.5/s base)"
```

---

### Task 3: Wire difficulty into PlayScene and BonusScene

**Files:**
- Modify: `scenes/play.py`
- Modify: `scenes/bonus.py`

- [ ] **Step 1: Add `difficulty` param to PlayScene.__init__**

In `scenes/play.py`:

Add import at top:
```python
from game.difficulty import Difficulty, config_for
```

Change the `__init__` signature and body:
```python
    def __init__(
        self,
        scoring: Scoring | None = None,
        difficulty: Difficulty = Difficulty.NORMAL,
    ) -> None:
        self.difficulty = difficulty
        self._diff_cfg = config_for(difficulty)
        if scoring is None:
            scoring = Scoring(lives=self._diff_cfg.starting_lives)
        self.scoring = scoring
```

(The rest of `__init__` stays the same.)

- [ ] **Step 2: Apply difficulty multipliers in `_apply_wave_difficulty`**

```python
    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        base_rate = 0.5 + 30.0 * p.dive_probability
        self._dive_probability_per_sec = base_rate * self._diff_cfg.dive_freq_multiplier
```

- [ ] **Step 3: Apply enemy_bullet_speed multiplier**

The cleanest path is to scale `EnemyBullet` on creation. Modify `entities/bullet.py`'s `EnemyBullet.__init__` to accept an optional `speed_multiplier`:

```python
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(
        self,
        pos: pygame.Vector2,
        target: pygame.Vector2,
        speed_multiplier: float = 1.0,
    ) -> None:
        super().__init__()
        self.image = assets.sprite("enemy_bullet")
        self.rect = self.image.get_rect(midtop=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)
        direction = target - pos
        if direction.length() == 0:
            direction = pygame.Vector2(0, 1)
        self.velocity = direction.normalize() * settings.ENEMY_BULLET_SPEED * speed_multiplier
```

Then in `entities/enemy.py`, modify `Enemy.maybe_fire` to take an optional speed mult:

```python
    def maybe_fire(
        self, target: pygame.Vector2, speed_multiplier: float = 1.0
    ) -> EnemyBullet | None:
        if self.state != EnemyState.DIVING or not self._dive_fire_armed:
            return None
        if self._dive_index < 8 or self._dive_index > 16:
            return None
        self._dive_fire_armed = False
        return EnemyBullet(self.pos, target, speed_multiplier=speed_multiplier)
```

In `scenes/play.py`'s `update`, change:
```python
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(self.player.pos)
                if bullet:
                    self.enemy_bullets.add(bullet)
```

To:
```python
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(
                    self.player.pos,
                    speed_multiplier=self._diff_cfg.enemy_bullet_speed_multiplier,
                )
                if bullet:
                    self.enemy_bullets.add(bullet)
```

- [ ] **Step 4: Pass difficulty through transitions**

In `scenes/play.py`, when transitioning to next PlayScene/BonusScene, include difficulty.

In the `if not self.enemies:` block, change the `PlayScene` factory:
```python
                self.manager.replace(
                    TransitionScene(
                        text,
                        lambda: type(self)(scoring=self.scoring, difficulty=self.difficulty),
                        duration=1.5,
                    )
                )
```

And the BonusScene factory:
```python
                self.manager.replace(
                    TransitionScene(
                        "CHALLENGING STAGE",
                        lambda: BonusScene(self.scoring, self.difficulty),
                        duration=1.8,
                    )
                )
```

- [ ] **Step 5: Update BonusScene to accept difficulty and pass back**

In `scenes/bonus.py`, change `__init__`:
```python
    def __init__(self, scoring: Scoring, difficulty: Difficulty = Difficulty.NORMAL) -> None:
        self.difficulty = difficulty
        ...
```

Add import:
```python
from game.difficulty import Difficulty
```

Update the `_finish` method's transition:
```python
        self.manager.replace(
            TransitionScene(
                f"STAGE {self.scoring.wave}",
                lambda: PlayScene(scoring=self.scoring, difficulty=self.difficulty),
                duration=1.5,
            )
        )
```

- [ ] **Step 6: Run existing tests + smoke import**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -c "from scenes.play import PlayScene; from scenes.bonus import BonusScene; from entities.bullet import EnemyBullet; print('ok')"
```

- [ ] **Step 7: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/play.py scenes/bonus.py entities/bullet.py entities/enemy.py
git commit -m "feat(difficulty): wire Difficulty through PlayScene, BonusScene, EnemyBullet"
```

---

### Task 4: Add difficulty selector to TitleScene

**Files:**
- Modify: `scenes/title.py`

- [ ] **Step 1: Add selector state and logic**

Replace `scenes/title.py`'s contents:

```python
"""Title screen -- Press SPACE to start. Arrow/A,D to choose difficulty."""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.difficulty import Difficulty
from game.scoring import load_highscore

_DIFFICULTIES: list[Difficulty] = [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]


class TitleScene(Scene):
    def __init__(self) -> None:
        self._font_big = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 22)
        self._t = 0.0
        self._highscore = load_highscore()
        self._diff_index = 1  # NORMAL by default
        self._prev_left = False
        self._prev_right = False

    @property
    def selected_difficulty(self) -> Difficulty:
        return _DIFFICULTIES[self._diff_index]

    def on_enter(self) -> None:
        audio.play_music("music_intro", loop=True)

    def on_exit(self) -> None:
        audio.stop_music()

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        # Edge-trigger left/right for difficulty selection
        if inp.left and not self._prev_left:
            self._diff_index = (self._diff_index - 1) % len(_DIFFICULTIES)
        if inp.right and not self._prev_right:
            self._diff_index = (self._diff_index + 1) % len(_DIFFICULTIES)
        self._prev_left = inp.left
        self._prev_right = inp.right

        if inp.fire_pressed:
            from game.difficulty import config_for
            from game.scoring import Scoring
            from scenes.play import PlayScene
            from scenes.transitions import TransitionScene

            cfg = config_for(self.selected_difficulty)
            scoring = Scoring(lives=cfg.starting_lives)
            assert self.manager
            self.manager.replace(
                TransitionScene(
                    "STAGE 1",
                    lambda: PlayScene(
                        scoring=scoring, difficulty=self.selected_difficulty
                    ),
                    duration=1.5,
                )
            )

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        title = self._font_big.render("GALAGA", True, settings.COLOR_YELLOW)
        sub = self._font_med.render("CLONE", True, settings.COLOR_HUD_DIM)
        hs = self._font_sm.render(
            f"HIGH SCORE   {self._highscore}", True, settings.COLOR_CYAN
        )
        cx = settings.WINDOW_WIDTH // 2
        surface.blit(title, title.get_rect(center=(cx, 180)))
        surface.blit(sub, sub.get_rect(center=(cx, 250)))
        surface.blit(hs, hs.get_rect(center=(cx, 330)))

        # Difficulty row: < EASY  NORMAL  HARD >
        diff_y = 430
        diff_label = self._font_sm.render("DIFFICULTY", True, settings.COLOR_HUD_DIM)
        surface.blit(diff_label, diff_label.get_rect(center=(cx, diff_y - 30)))
        labels = ["EASY", "NORMAL", "HARD"]
        spacing = 160
        start_x = cx - spacing
        for i, name in enumerate(labels):
            color = settings.COLOR_WHITE if i == self._diff_index else settings.COLOR_HUD_DIM
            font = self._font_med if i == self._diff_index else self._font_sm
            surface.blit(
                font.render(name, True, color),
                font.render(name, True, color).get_rect(center=(start_x + i * spacing, diff_y)),
            )
        # arrows
        arrow = self._font_med.render("<", True, settings.COLOR_CYAN)
        surface.blit(arrow, arrow.get_rect(center=(cx - 280, diff_y)))
        arrow_r = self._font_med.render(">", True, settings.COLOR_CYAN)
        surface.blit(arrow_r, arrow_r.get_rect(center=(cx + 280, diff_y)))

        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
        controls = self._font_sm.render(
            "Arrow / A,D choose difficulty  |  Space start  |  Esc quit",
            True,
            settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
```

- [ ] **Step 2: Smoke import**

```powershell
.venv\Scripts\python.exe -c "import main; from scenes.title import TitleScene; print('ok')"
```

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/title.py
git commit -m "feat(title): difficulty selector (EASY / NORMAL / HARD)"
```

---

### Task 5: Final verification + manual playtest

**Files:** none

- [ ] **Step 1: Full test suite + lint**

```powershell
.venv\Scripts\python.exe -m pytest -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
```

Expected: 50+ tests pass (45 original + 5 new difficulty tests), ruff clean.

- [ ] **Step 2: Manual playtest checklist**

Run `python main.py` and verify:
- [ ] Title shows three difficulty options with NORMAL highlighted
- [ ] Left/Right (or A/D) cycles through EASY/NORMAL/HARD; selected one is highlighted
- [ ] Pressing SPACE on EASY starts game with 4 lives, dives noticeably less frequent, slower enemy bullets
- [ ] Pressing SPACE on NORMAL starts with 3 lives, normal pacing
- [ ] Pressing SPACE on HARD starts with 2 lives, more frequent dives, faster bullets
- [ ] Dive frequency is now reasonable (not the previous "constant rain") — about one dive every 1-2 seconds at wave 1 NORMAL
- [ ] After bonus stage / wave clear, difficulty stays the same (passed through)

- [ ] **Step 3: Push branch**

```powershell
git push -u origin feat/difficulty-selection
```

---

## Self-Review Notes

**Spec coverage:**
- Original spec §10 lists "Future Work" items but doesn't mandate difficulty selection. This feature is an *addition* and OK to add.
- All multipliers default to 1.0 for NORMAL, preserving the original baseline behavior (modulo the dive bug fix).

**Placeholder scan:** No TBD/TODO. Each step contains the exact code change.

**Type consistency:** `Difficulty` enum, `DifficultyConfig` dataclass, and `config_for()` are referenced consistently across Tasks 1-4.

**Risk:** Task 2's bug fix changes the gameplay characteristic of NORMAL — it goes from "unplayable barrage" to "actually playable." This is the intent.
