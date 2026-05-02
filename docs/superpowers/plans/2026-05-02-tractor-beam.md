# Tractor Beam / Dual Fighter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the original Galaga tractor beam capture mechanic — boss fires a beam, captures the player ship, ship rides above boss in formation; killing that boss while it dives with the captured ship rescues it into a Dual Fighter (twin guns).

**Architecture:** Approach B from spec — separate `TractorBeam` sprite + pure `CaptureManager` state machine. `BossEnemy` gains 3 new states; `Player` gets minor flags; `PlayScene` orchestrates the cycle.

**Tech Stack:** Python 3.11+, Pygame (existing). No new dependencies. Tractor beam visuals drawn with `pygame.draw.polygon` at runtime.

**Spec:** [docs/superpowers/specs/2026-05-02-tractor-beam-design.md](../specs/2026-05-02-tractor-beam-design.md)

---

## File Structure

```
galaga-clone/
├── settings.py                       # MODIFY: tractor beam + scoring constants
│
├── entities/
│   ├── enemy.py                      # MODIFY: BossEnemy + 3 new states + captured_ship slot
│   ├── player.py                     # MODIFY: dual_offset, is_left_half, is_right_half
│   ├── tractor_beam.py               # NEW: TractorBeam sprite (visuals + polygon collision)
│   └── rescuing_ship.py              # NEW: RescuingShip sprite (descending captured ship)
│
├── game/
│   ├── capture.py                    # NEW: CaptureMode enum, CaptureState, CaptureManager
│   └── scoring.py                    # MODIFY: tractor (400) + rescue (800) score kinds
│
├── scenes/
│   └── play.py                       # MODIFY: tractor_beams group, capture orchestration, dual mode
│
└── tests/
    ├── test_capture.py               # NEW: ~14 unit tests for CaptureManager
    └── test_scoring.py               # MODIFY: +2 tests for tractor/rescue kills
```

---

## Tasks

### Task 1: Add tractor beam constants to `settings.py`

**Files:**
- Modify: `settings.py`

- [ ] **Step 1: Add constants at the end of the Scoring section**

In `settings.py`, find the `# Scoring` section and add these lines after `LIFE_BONUS_PERFECT = 1`:

```python
SCORE_TRACTOR_KILL = 400
SCORE_RESCUE_KILL = 800
```

Then add a new section after `# Bonus stage`:

```python
# Tractor beam
TRACTOR_BEAM_PROBABILITY = 0.30
TRACTOR_BEAM_LIFETIME = 3.0
TRACTOR_BEAM_TOP_WIDTH = 24
TRACTOR_BEAM_BOTTOM_WIDTH = 60
TRACTOR_BEAM_CAPTURE_GRACE = 0.3
TRACTOR_BEAM_STRIPE_HEIGHT = 14
TRACTOR_BEAM_STRIPE_SPEED = 240.0
TRACTOR_BOSS_ALIGN_SPEED = 200.0
TRACTOR_RETURN_SPEED = 220.0
TRACTOR_RESCUE_DESCENT_SPEED = 220.0
TRACTOR_RESCUE_TIMER = 5.0
DUAL_FIGHTER_OFFSET = 22

# Difficulty multipliers (ALSO add to game/difficulty.py per Task 5)
```

- [ ] **Step 2: Verify import**

```powershell
.venv\Scripts\python.exe -c "import settings; print(settings.SCORE_TRACTOR_KILL, settings.TRACTOR_BEAM_PROBABILITY)"
```

Expected: `400 0.3`

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add settings.py
git commit -m "feat(settings): tractor beam + scoring constants"
```

---

### Task 2: Add `tractor` and `rescue` score kinds to `game/scoring.py` (TDD)

**Files:**
- Modify: `game/scoring.py`
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Add failing tests at the end of `tests/test_scoring.py`**

```python
def test_add_kill_tractor():
    s = Scoring()
    s.add_kill("tractor")
    assert s.score == 400
    assert s.enemies_killed == 1


def test_add_kill_rescue():
    s = Scoring()
    s.add_kill("rescue")
    assert s.score == 800
    assert s.enemies_killed == 1
```

- [ ] **Step 2: Run, expect failures**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_scoring.py::test_add_kill_tractor tests/test_scoring.py::test_add_kill_rescue -v
```

Expected: both fail with `ValueError: Unknown enemy kind: 'tractor'` (or 'rescue').

- [ ] **Step 3: Update `_KILL_SCORES` in `game/scoring.py`**

Find the `_KILL_SCORES` dict and add the two new keys:

```python
_KILL_SCORES = {
    "normal": settings.SCORE_NORMAL_KILL,
    "dive": settings.SCORE_DIVE_KILL,
    "boss": settings.SCORE_BOSS_KILL,
    "bonus": settings.SCORE_BONUS_PER_KILL,
    "tractor": settings.SCORE_TRACTOR_KILL,
    "rescue": settings.SCORE_RESCUE_KILL,
}
```

- [ ] **Step 4: Run tests, expect pass**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_scoring.py -v
```

Expected: all 17 tests pass (15 existing + 2 new).

- [ ] **Step 5: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): add tractor (400) and rescue (800) kill kinds"
```

---

### Task 3: `game/capture.py` — Capture state machine (TDD)

**Files:**
- Create: `game/capture.py`
- Create: `tests/test_capture.py`

- [ ] **Step 1: Write failing tests**

`tests/test_capture.py`:
```python
from game.capture import CaptureManager, CaptureMode


def test_initial_mode_is_normal():
    m = CaptureManager()
    assert m.state.mode == CaptureMode.NORMAL
    assert m.active_tractor_boss_id is None


def test_can_start_tractor_when_idle():
    m = CaptureManager()
    assert m.can_start_tractor(boss_id=42) is True


def test_cannot_start_tractor_when_already_active():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    assert m.can_start_tractor(boss_id=99) is False


def test_cannot_start_tractor_when_captured():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    # Simulate full capture
    for _ in range(4):
        m.update_beam(0.1, in_beam=True)
    m.on_captured(boss_id=1, lives_after=2)
    assert m.can_start_tractor(boss_id=99) is False


def test_begin_beam_sets_active_id():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    assert m.active_tractor_boss_id == 42


def test_beam_grace_accumulates_when_in_beam():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    assert m.update_beam(0.1, in_beam=True) is False
    assert m.update_beam(0.1, in_beam=True) is False
    captured = m.update_beam(0.15, in_beam=True)
    assert captured is True


def test_beam_grace_resets_when_out_of_beam():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.update_beam(0.2, in_beam=True)
    m.update_beam(0.1, in_beam=False)
    # Now grace should be 0; need full 0.3s again
    assert m.update_beam(0.2, in_beam=True) is False


def test_on_beam_ended_clears_active():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    m.on_beam_ended()
    assert m.active_tractor_boss_id is None
    assert m.state.mode == CaptureMode.NORMAL


def test_on_captured_with_remaining_lives_enters_captured():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    assert m.state.mode == CaptureMode.CAPTURED
    assert m.state.captor_boss_id == 1
    assert m.active_tractor_boss_id is None


def test_on_captured_with_zero_lives_enters_awaiting_rescue():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=0)
    assert m.state.mode == CaptureMode.AWAITING_RESCUE
    assert m.state.rescue_timer == 5.0


def test_awaiting_rescue_timeout_signals_game_over():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=0)
    assert m.update_awaiting_rescue(2.0) is False
    assert m.update_awaiting_rescue(2.0) is False
    assert m.update_awaiting_rescue(1.5) is True


def test_awaiting_rescue_no_op_when_not_in_mode():
    m = CaptureManager()
    assert m.update_awaiting_rescue(10.0) is False


def test_on_captor_destroyed_with_lives_resets_to_normal():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_captor_destroyed()
    assert m.state.mode == CaptureMode.NORMAL
    assert m.state.captor_boss_id is None


def test_on_rescue_eligible_kill_enters_rescuing():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    triggered = m.on_rescue_eligible_kill()
    assert triggered is True
    assert m.state.mode == CaptureMode.RESCUING


def test_on_rescue_complete_enters_dual():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_rescue_eligible_kill()
    m.on_rescue_complete()
    assert m.state.mode == CaptureMode.DUAL


def test_on_dual_lost_returns_to_normal():
    m = CaptureManager()
    # Force into DUAL
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_rescue_eligible_kill()
    m.on_rescue_complete()
    m.on_dual_lost()
    assert m.state.mode == CaptureMode.NORMAL
```

- [ ] **Step 2: Run, expect ImportError**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_capture.py -v
```

- [ ] **Step 3: Write `game/capture.py`**

```python
"""Capture / rescue state machine for the tractor beam mechanic.

Pure module: no pygame import. Holds the single source of truth for capture
mode and transitions. PlayScene drives it via methods; manager returns
booleans signalling state changes the caller must act on (capture happened,
game-over due to rescue timeout, etc.).
"""

from dataclasses import dataclass
from enum import Enum

import settings


class CaptureMode(Enum):
    NORMAL = "normal"
    BEAMING = "beaming"
    CAPTURED = "captured"
    AWAITING_RESCUE = "awaiting_rescue"
    RESCUING = "rescuing"
    DUAL = "dual"


@dataclass
class CaptureState:
    mode: CaptureMode = CaptureMode.NORMAL
    captor_boss_id: int | None = None
    rescue_timer: float = 0.0
    beam_grace: float = 0.0


class CaptureManager:
    def __init__(self) -> None:
        self.state = CaptureState()
        self.active_tractor_boss_id: int | None = None

    def can_start_tractor(self, boss_id: int) -> bool:
        if self.active_tractor_boss_id is not None:
            return False
        if self.state.mode in (
            CaptureMode.BEAMING,
            CaptureMode.CAPTURED,
            CaptureMode.AWAITING_RESCUE,
            CaptureMode.RESCUING,
            CaptureMode.DUAL,
        ):
            return False
        return True

    def begin_beam(self, boss_id: int) -> None:
        self.active_tractor_boss_id = boss_id
        self.state.mode = CaptureMode.BEAMING
        self.state.beam_grace = 0.0

    def update_beam(self, dt: float, in_beam: bool) -> bool:
        """Advance beam grace timer. Returns True when capture grace is reached."""
        if self.state.mode != CaptureMode.BEAMING:
            return False
        if in_beam:
            self.state.beam_grace += dt
            if self.state.beam_grace >= settings.TRACTOR_BEAM_CAPTURE_GRACE:
                return True
        else:
            self.state.beam_grace = 0.0
        return False

    def on_beam_ended(self) -> None:
        """Boss finished beaming without capturing. Reset to NORMAL."""
        self.active_tractor_boss_id = None
        if self.state.mode == CaptureMode.BEAMING:
            self.state.mode = CaptureMode.NORMAL
            self.state.beam_grace = 0.0

    def on_captured(self, boss_id: int, lives_after: int) -> None:
        self.active_tractor_boss_id = None
        self.state.captor_boss_id = boss_id
        self.state.beam_grace = 0.0
        if lives_after <= 0:
            self.state.mode = CaptureMode.AWAITING_RESCUE
            self.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
        else:
            self.state.mode = CaptureMode.CAPTURED

    def on_captor_destroyed(self) -> None:
        """Captor boss died (not via rescue dive); captured ship lost permanently."""
        self.state.captor_boss_id = None
        self.state.mode = CaptureMode.NORMAL

    def on_rescue_eligible_kill(self) -> bool:
        """Player killed captor while it was diving with captured ship. Returns True."""
        if self.state.mode not in (CaptureMode.CAPTURED, CaptureMode.AWAITING_RESCUE):
            return False
        self.state.mode = CaptureMode.RESCUING
        return True

    def on_rescue_complete(self) -> None:
        if self.state.mode == CaptureMode.RESCUING:
            self.state.mode = CaptureMode.DUAL
            self.state.captor_boss_id = None

    def on_dual_lost(self) -> None:
        if self.state.mode == CaptureMode.DUAL:
            self.state.mode = CaptureMode.NORMAL

    def update_awaiting_rescue(self, dt: float) -> bool:
        """Decrement rescue timer. Returns True on timeout (game-over signal)."""
        if self.state.mode != CaptureMode.AWAITING_RESCUE:
            return False
        self.state.rescue_timer -= dt
        if self.state.rescue_timer <= 0:
            return True
        return False
```

- [ ] **Step 4: Run tests, expect pass**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_capture.py -v
```

Expected: 16 tests pass.

- [ ] **Step 5: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/capture.py tests/test_capture.py
git commit -m "feat(capture): pure CaptureManager state machine with tests"
```

---

### Task 4: `entities/tractor_beam.py` — TractorBeam sprite

**Files:**
- Create: `entities/tractor_beam.py`

- [ ] **Step 1: Write the module**

`entities/tractor_beam.py`:
```python
"""Tractor beam: striped triangular cone attached to a boss.

Renders procedurally with pygame.draw — no PNG asset needed. Performs
point-in-polygon collision testing for capture detection.
"""

import pygame

import settings


class TractorBeam(pygame.sprite.Sprite):
    """Animated yellow/blue striped triangular beam below a parent boss."""

    def __init__(self, boss: pygame.sprite.Sprite) -> None:
        super().__init__()
        self.boss = boss
        self.lifetime = settings.TRACTOR_BEAM_LIFETIME
        self._stripe_phase = 0.0  # px offset for stripe scroll
        # Empty surface for sprite group compat (we render in draw())
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self._update_rect()

    @property
    def expired(self) -> bool:
        return self.lifetime <= 0

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        self._stripe_phase = (
            self._stripe_phase + settings.TRACTOR_BEAM_STRIPE_SPEED * dt
        ) % (settings.TRACTOR_BEAM_STRIPE_HEIGHT * 2)
        self._update_rect()
        if self.expired:
            self.kill()

    def _update_rect(self) -> None:
        # Bounding rect for the beam triangle (boss bottom → playfield bottom)
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        self.rect = pygame.Rect(
            int(bx - half_bot),
            int(top),
            int(half_bot * 2),
            int(bottom - top),
        )

    def _polygon(self) -> list[tuple[int, int]]:
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_top = settings.TRACTOR_BEAM_TOP_WIDTH / 2
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        return [
            (int(bx - half_top), int(top)),
            (int(bx + half_top), int(top)),
            (int(bx + half_bot), int(bottom)),
            (int(bx - half_bot), int(bottom)),
        ]

    def contains(self, point: pygame.Vector2) -> bool:
        """Point-in-polygon test using ray casting."""
        poly = self._polygon()
        x, y = point.x, point.y
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
                inside = not inside
            j = i
        return inside

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the striped beam onto a playfield-local surface."""
        poly = self._polygon()
        # Build a clip surface to mask stripes to the polygon shape
        beam_rect = pygame.Rect(
            min(p[0] for p in poly),
            min(p[1] for p in poly),
            max(p[0] for p in poly) - min(p[0] for p in poly),
            max(p[1] for p in poly) - min(p[1] for p in poly),
        )
        if beam_rect.width <= 0 or beam_rect.height <= 0:
            return
        mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        # Draw stripes onto the mask
        stripe_h = settings.TRACTOR_BEAM_STRIPE_HEIGHT
        phase = int(self._stripe_phase)
        y = -phase
        toggle = 0
        while y < beam_rect.height:
            color = (
                settings.COLOR_YELLOW + (140,)
                if toggle == 0
                else settings.COLOR_BLUE + (140,)
            )
            pygame.draw.rect(
                mask,
                color,
                pygame.Rect(0, max(0, y), beam_rect.width, stripe_h),
            )
            y += stripe_h
            toggle = 1 - toggle

        # Now clip to the polygon by drawing polygon onto a alpha mask, then blit only inside
        poly_local = [(p[0] - beam_rect.x, p[1] - beam_rect.y) for p in poly]
        clip_mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(clip_mask, (255, 255, 255, 255), poly_local)
        # Multiply: keep stripes only where polygon mask is opaque
        mask.blit(clip_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(mask, beam_rect.topleft)
```

- [ ] **Step 2: Smoke import**

```powershell
.venv\Scripts\python.exe -c "from entities.tractor_beam import TractorBeam; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add entities/tractor_beam.py
git commit -m "feat(entities): TractorBeam sprite with striped polygon rendering"
```

---

### Task 5: Add tractor probability multiplier to `game/difficulty.py`

**Files:**
- Modify: `game/difficulty.py`
- Modify: `tests/test_difficulty.py`

- [ ] **Step 1: Add field to `DifficultyConfig` and update configs**

In `game/difficulty.py`, modify the dataclass:

```python
@dataclass(frozen=True)
class DifficultyConfig:
    starting_lives: int
    dive_freq_multiplier: float
    enemy_bullet_speed_multiplier: float
    tractor_probability_multiplier: float
```

Update `_CONFIGS`:

```python
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
```

- [ ] **Step 2: Add tests in `tests/test_difficulty.py`**

Append:

```python
def test_tractor_probability_multipliers():
    assert config_for(Difficulty.EASY).tractor_probability_multiplier == 0.5
    assert config_for(Difficulty.NORMAL).tractor_probability_multiplier == 1.0
    assert config_for(Difficulty.HARD).tractor_probability_multiplier == 1.5
```

- [ ] **Step 3: Run all tests**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: all pass (existing 7 difficulty tests + 1 new + 16 capture + 17 scoring + 19 wave + 6 formation + 5 dive = 71).

- [ ] **Step 4: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/difficulty.py tests/test_difficulty.py
git commit -m "feat(difficulty): add tractor_probability_multiplier"
```

---

### Task 6: `entities/enemy.py` — BossEnemy tractor states

**Files:**
- Modify: `entities/enemy.py`

- [ ] **Step 1: Add new states + captured_ship field + tractor methods**

In `entities/enemy.py`:

Add to `EnemyState` enum (after RETURNING):
```python
class EnemyState(Enum):
    ENTERING = "entering"
    IN_FORMATION = "in_formation"
    DIVING = "diving"
    RETURNING = "returning"
    TRACTOR_ALIGNING = "tractor_aligning"
    TRACTOR_BEAMING = "tractor_beaming"
    RETURNING_WITH_CAPTURE = "returning_with_capture"
```

Add to `Enemy.__init__` (after `self._dive_fire_armed = True`):
```python
        self.captured_ship: pygame.Surface | None = None
        self._tractor_target_x: float = 0.0
```

Add new methods to `Enemy`:
```python
    def enter_tractor_align(self, player_pos: pygame.Vector2) -> None:
        if self.state != EnemyState.IN_FORMATION:
            return
        self._tractor_target_x = player_pos.x
        self.state = EnemyState.TRACTOR_ALIGNING

    def attach_captured_ship(self, ship_surface: pygame.Surface) -> None:
        self.captured_ship = ship_surface
        self._return_target = pygame.Vector2(
            self.pos.x, self.pos.y
        )  # captured at current pos
        # Compute target = formation slot
        from game import formation as _formation

        slot = _formation.slot_position(self.row, self.col, self._phase_ref[0])
        self._return_target = pygame.Vector2(slot)
        self.state = EnemyState.RETURNING_WITH_CAPTURE
```

Modify `Enemy.update` to dispatch new states:
```python
    def update(self, dt: float) -> None:
        if self.state == EnemyState.ENTERING:
            self._update_entering(dt)
        elif self.state == EnemyState.IN_FORMATION:
            self._update_in_formation()
        elif self.state == EnemyState.DIVING:
            self._update_diving(dt)
        elif self.state == EnemyState.RETURNING:
            self._update_returning(dt)
        elif self.state == EnemyState.TRACTOR_ALIGNING:
            self._update_tractor_aligning(dt)
        elif self.state == EnemyState.TRACTOR_BEAMING:
            pass  # hold position
        elif self.state == EnemyState.RETURNING_WITH_CAPTURE:
            self._update_returning_with_capture(dt)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
```

Add the two new update methods:
```python
    def _update_tractor_aligning(self, dt: float) -> None:
        speed = settings.TRACTOR_BOSS_ALIGN_SPEED
        diff = self._tractor_target_x - self.pos.x
        if abs(diff) < 5:
            self.state = EnemyState.TRACTOR_BEAMING
            return
        step = speed * dt
        if abs(diff) <= step:
            self.pos.x = self._tractor_target_x
        else:
            self.pos.x += step if diff > 0 else -step

    def _update_returning_with_capture(self, dt: float) -> None:
        target = self._return_target
        diff = target - self.pos
        if diff.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        self.pos += diff.normalize() * settings.TRACTOR_RETURN_SPEED * dt
```

You also need to import `settings` at the top if not already. Check the existing import block.

- [ ] **Step 2: Smoke import**

```powershell
.venv\Scripts\python.exe -c "from entities.enemy import BossEnemy, EnemyState; print(EnemyState.TRACTOR_ALIGNING, EnemyState.TRACTOR_BEAMING)"
```

Expected: `EnemyState.TRACTOR_ALIGNING EnemyState.TRACTOR_BEAMING`.

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add entities/enemy.py
git commit -m "feat(enemy): tractor states (aligning/beaming/returning_with_capture) + captured_ship slot"
```

---

### Task 7: `entities/player.py` — Dual fighter flags

**Files:**
- Modify: `entities/player.py`

- [ ] **Step 1: Add fields to `Player.__init__`**

In `entities/player.py`, after `self.rect.center = ...` line at end of `__init__`, add:

```python
        self.dual_offset: int = 0
        self.is_left_half: bool = False
        self.is_right_half: bool = False
```

Add a constructor argument so you can spawn a dual half directly:

Replace `def __init__(self) -> None:` with:

```python
    def __init__(self, dual_offset: int = 0, is_right_half: bool = False) -> None:
```

And update the body so the spawn position respects offset:

```python
    def __init__(self, dual_offset: int = 0, is_right_half: bool = False) -> None:
        super().__init__()
        self.image = assets.sprite("player")
        self.rect = self.image.get_rect()
        self.pos = pygame.Vector2(
            settings.PLAYFIELD_WIDTH / 2 + dual_offset,
            settings.PLAYFIELD_HEIGHT - 40,
        )
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.dual_offset = dual_offset
        self.is_left_half = dual_offset < 0
        self.is_right_half = is_right_half or dual_offset > 0
```

- [ ] **Step 2: Smoke import + instantiate**

```powershell
.venv\Scripts\python.exe -c "import pygame; pygame.init(); pygame.display.set_mode((1,1)); from entities.player import Player; from engine import assets; assets.load_all(); p = Player(dual_offset=22); print(p.dual_offset, p.is_right_half)"
```

Expected: `22 True`.

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add entities/player.py
git commit -m "feat(player): dual fighter offset/half flags"
```

---

### Task 8: `entities/rescuing_ship.py` — Descending captured ship

**Files:**
- Create: `entities/rescuing_ship.py`

- [ ] **Step 1: Write module**

`entities/rescuing_ship.py`:
```python
"""Captured ship descending from a destroyed boss to merge with the current player."""

from collections.abc import Callable

import pygame

import settings
from engine import assets


class RescuingShip(pygame.sprite.Sprite):
    """Travels at constant speed from start_pos toward target_player.pos.
    Calls on_arrival(self) and self.kill() when within 4 px of target."""

    def __init__(
        self,
        start_pos: pygame.Vector2,
        target_player: pygame.sprite.Sprite,
        on_arrival: Callable[["RescuingShip"], None],
    ) -> None:
        super().__init__()
        # Use a darker player sprite as visual indicator
        base = assets.sprite("player")
        self.image = base.copy()
        # apply 50% darken
        dark = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        self.image.blit(dark, (0, 0))
        self.pos = pygame.Vector2(start_pos)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self._target = target_player
        self._on_arrival = on_arrival
        self._arrived = False

    def update(self, dt: float) -> None:
        if self._arrived:
            return
        target = pygame.Vector2(self._target.pos.x, self._target.pos.y)
        diff = target - self.pos
        if diff.length() < 4:
            self._arrived = True
            self._on_arrival(self)
            self.kill()
            return
        self.pos += diff.normalize() * settings.TRACTOR_RESCUE_DESCENT_SPEED * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
```

- [ ] **Step 2: Smoke import**

```powershell
.venv\Scripts\python.exe -c "from entities.rescuing_ship import RescuingShip; print('ok')"
```

- [ ] **Step 3: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add entities/rescuing_ship.py
git commit -m "feat(entities): RescuingShip sprite for dual-fighter merge animation"
```

---

### Task 9: `scenes/play.py` — Wire tractor beam orchestration

**Files:**
- Modify: `scenes/play.py`

This is the largest task. Apply the changes step by step.

- [ ] **Step 1: Add imports at top of `scenes/play.py`**

Add the new imports near the existing imports:

```python
from entities.tractor_beam import TractorBeam
from entities.rescuing_ship import RescuingShip
from game.capture import CaptureManager, CaptureMode
```

- [ ] **Step 2: Modify `__init__` — add capture manager, tractor groups, dual support**

Change `__init__` signature:

```python
    def __init__(
        self,
        scoring: Scoring | None = None,
        difficulty: Difficulty = Difficulty.NORMAL,
        dual: bool = False,
    ) -> None:
```

After the existing `self.players = pygame.sprite.GroupSingle(self.player)` line, replace with a regular Group so we can hold 2 ships:

```python
        self.player = Player()
        self.players: pygame.sprite.Group = pygame.sprite.Group(self.player)
        if dual:
            second = Player(dual_offset=settings.DUAL_FIGHTER_OFFSET, is_right_half=True)
            self.player.dual_offset = -settings.DUAL_FIGHTER_OFFSET
            self.player.is_left_half = True
            self.player.pos.x += self.player.dual_offset
            self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))
            self.players.add(second)
```

After `self.explosions = ...`, add:

```python
        self.tractor_beams: pygame.sprite.Group = pygame.sprite.Group()
        self.rescuing_ships: pygame.sprite.Group = pygame.sprite.Group()
        self.capture_mgr = CaptureManager()
        if dual:
            # Force CaptureManager directly into DUAL (we just spawned both halves)
            self.capture_mgr.state.mode = CaptureMode.DUAL
```

- [ ] **Step 3: Replace dive trigger to roll for tractor**

Find this block in `update`:

```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt:
            attacker = random.choice(in_formation)
            self._dive_seed_counter += 1
            attacker.start_dive(self.player.pos, self._dive_seed_counter)
            audio.play_sfx("sfx_dive")
```

Replace with:

```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt:
            attacker = random.choice(in_formation)
            self._dive_seed_counter += 1
            # Roll for tractor beam (boss only, capture manager allows)
            from entities.enemy import BossEnemy

            tractor_chance = (
                settings.TRACTOR_BEAM_PROBABILITY
                * self._diff_cfg.tractor_probability_multiplier
            )
            if (
                isinstance(attacker, BossEnemy)
                and self.capture_mgr.can_start_tractor(id(attacker))
                and random.random() < tractor_chance
                and self._player_alive
            ):
                attacker.enter_tractor_align(pygame.Vector2(self.player.pos))
                self.capture_mgr.begin_beam(id(attacker))
            else:
                attacker.start_dive(self.player.pos, self._dive_seed_counter)
                audio.play_sfx("sfx_dive")
```

- [ ] **Step 4: After dive trigger, add beam spawn check**

Right after the dive-trigger block, add:

```python
        # Spawn tractor beams for bosses that have reached TRACTOR_BEAMING this frame
        from entities.enemy import EnemyState

        for e in self.enemies:
            if (
                e.state == EnemyState.TRACTOR_BEAMING
                and not any(b.boss is e for b in self.tractor_beams)
            ):
                self.tractor_beams.add(TractorBeam(e))
                audio.play_sfx("sfx_dive")
```

- [ ] **Step 5: Update tractor beams + rescuing ships in update loop**

After existing entity updates (after `for x in self.explosions: x.update(dt)`), add:

```python
        for b in self.tractor_beams:
            b.update(dt)
        for r in self.rescuing_ships:
            r.update(dt)

        # Beam-vs-player collision and capture grace
        any_player_in_beam = False
        captured_player = None
        captured_beam = None
        if self._player_alive and self.tractor_beams:
            for beam in self.tractor_beams:
                # Only the left half is eligible to be captured (per spec)
                left_player = next(
                    (p for p in self.players if not p.is_right_half),
                    None,
                )
                if left_player is not None and beam.contains(
                    pygame.Vector2(left_player.pos)
                ):
                    any_player_in_beam = True
                    captured_player = left_player
                    captured_beam = beam
                    break
        if self.tractor_beams:
            triggered = self.capture_mgr.update_beam(dt, any_player_in_beam)
            if triggered and captured_player is not None and captured_beam is not None:
                self._perform_capture(captured_beam, captured_player)

        # Beams that expired naturally
        for beam in list(self.tractor_beams):
            if beam.expired:
                # Beam ended without capture — boss resumes normal dive
                if (
                    beam.boss in self.enemies
                    and beam.boss.state == EnemyState.TRACTOR_BEAMING
                ):
                    self._dive_seed_counter += 1
                    beam.boss.start_dive(self.player.pos, self._dive_seed_counter)
                self.capture_mgr.on_beam_ended()

        # Awaiting-rescue timeout
        if self.capture_mgr.update_awaiting_rescue(dt):
            self._game_over()
            return
```

- [ ] **Step 6: Add `_perform_capture`, `_perform_rescue`, `_complete_rescue`, `_game_over` methods**

After `_kill_player` method, add:

```python
    def _perform_capture(self, beam: TractorBeam, captured_player: Player) -> None:
        boss = beam.boss
        # Remove captured player half
        self.explosions.add(Explosion(pygame.Vector2(captured_player.pos)))
        was_dual = self.capture_mgr.state.mode == CaptureMode.DUAL
        captured_player.kill()
        if was_dual:
            self.capture_mgr.on_dual_lost()
            # Promote remaining player back to single (re-center handled by user input clamping)
            for p in self.players:
                p.dual_offset = 0
                p.is_left_half = False
                p.is_right_half = False
        else:
            self._player_alive = False
            self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        self.scoring.lose_life()

        # Tint captured ship sprite
        from engine import assets as _assets

        base = _assets.sprite("player").copy()
        dark = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        base.blit(dark, (0, 0))

        # Attach to boss; remove beam
        boss.attach_captured_ship(base)
        beam.kill()
        audio.play_sfx("sfx_player_hit")
        self.capture_mgr.on_captured(id(boss), lives_after=self.scoring.lives)

    def _perform_rescue(self, boss) -> None:
        self.scoring.add_kill("rescue")
        self.explosions.add(Explosion(pygame.Vector2(boss.rect.center)))
        # Find current player to merge with (first ship in players group)
        target = next(iter(self.players), None)
        if target is not None and boss.captured_ship is not None:
            self.rescuing_ships.add(
                RescuingShip(
                    pygame.Vector2(boss.rect.center),
                    target,
                    self._complete_rescue,
                )
            )
        boss.captured_ship = None
        self.capture_mgr.on_rescue_eligible_kill()
        boss.kill()
        audio.play_sfx("sfx_explode")

    def _complete_rescue(self, _ship: RescuingShip) -> None:
        # Find the surviving player; promote to left half + spawn right half
        existing = next(iter(self.players), None)
        if existing is None:
            return
        existing.dual_offset = -settings.DUAL_FIGHTER_OFFSET
        existing.is_left_half = True
        existing.is_right_half = False
        existing.pos.x = max(
            settings.DUAL_FIGHTER_OFFSET + existing.rect.width / 2,
            existing.pos.x - settings.DUAL_FIGHTER_OFFSET / 2,
        )
        right = Player(dual_offset=settings.DUAL_FIGHTER_OFFSET, is_right_half=True)
        right.pos.x = existing.pos.x + 2 * settings.DUAL_FIGHTER_OFFSET
        right.rect.center = (int(right.pos.x), int(right.pos.y))
        self.players.add(right)
        self.capture_mgr.on_rescue_complete()
        audio.play_sfx("sfx_extra_life")

    def _game_over(self) -> None:
        from scenes.gameover import GameOverScene

        assert self.manager
        self.manager.replace(GameOverScene(self.scoring))
```

- [ ] **Step 7: Update existing player handling to support dual mode**

Replace the existing player update logic (in `update`):

```python
        # Player update / respawn
        if self._player_alive:
            self.player.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        else:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0 and self.scoring.lives > 0:
                self.player = Player()
                self.players = pygame.sprite.GroupSingle(self.player)
                self._player_alive = True
```

With the per-ship version:

```python
        # Player update / respawn
        alive_players = list(self.players)
        if alive_players:
            self._player_alive = True
            self.player = alive_players[0]
            for p in alive_players:
                p.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        else:
            self._player_alive = False
            self._respawn_timer -= dt
            if (
                self._respawn_timer <= 0
                and self.scoring.lives > 0
                and self.capture_mgr.state.mode != CaptureMode.AWAITING_RESCUE
            ):
                self.player = Player()
                self.players.add(self.player)
                self._player_alive = True
```

- [ ] **Step 8: Update collision handling for boss kills + captured ship + per-ship**

Replace `_handle_collisions` with:

```python
    def _handle_collisions(self) -> None:
        from entities.enemy import BossEnemy, EnemyState

        # Player bullets vs enemies — branch on boss + capture state
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                if isinstance(e, BossEnemy) and e.captured_ship is not None and e.state == EnemyState.DIVING:
                    self._perform_rescue(e)
                    continue
                if isinstance(e, BossEnemy) and e.state in (
                    EnemyState.TRACTOR_ALIGNING,
                    EnemyState.TRACTOR_BEAMING,
                ):
                    self.scoring.add_kill("tractor")
                    # Remove any active beam owned by this boss
                    for beam in list(self.tractor_beams):
                        if beam.boss is e:
                            beam.kill()
                    self.capture_mgr.on_beam_ended()
                else:
                    kind = "dive" if e.state == EnemyState.DIVING else e.score_kind
                    self.scoring.add_kill(kind)
                # Lose any captured ship attached to a non-dive kill
                if isinstance(e, BossEnemy) and e.captured_ship is not None:
                    self.capture_mgr.on_captor_destroyed()
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")

        if not self._player_alive:
            return

        # Enemy bullets vs each player half independently
        for p in list(self.players):
            if pygame.sprite.spritecollide(p, self.enemy_bullets, True):
                self._kill_player_half(p)

        # Diving enemies vs each player half
        for p in list(self.players):
            diving = [
                e
                for e in self.enemies
                if e.state == EnemyState.DIVING and p.rect.colliderect(e.rect)
            ]
            if diving:
                for e in diving:
                    self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                    e.kill()
                self._kill_player_half(p)
```

Add a new helper `_kill_player_half`:

```python
    def _kill_player_half(self, p: Player) -> None:
        self.explosions.add(Explosion(pygame.Vector2(p.pos)))
        audio.play_sfx("sfx_player_hit")
        was_dual = len(self.players) >= 2
        p.kill()
        self.scoring.lose_life()
        if was_dual:
            self.capture_mgr.on_dual_lost()
            # Promote remaining player to single
            for other in self.players:
                other.dual_offset = 0
                other.is_left_half = False
                other.is_right_half = False
        else:
            self._player_alive = False
            self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
            if self.scoring.lives <= 0:
                if self.capture_mgr.state.mode in (CaptureMode.CAPTURED,):
                    # Suspend game over — captured ship may still be rescued
                    self.capture_mgr.state.mode = CaptureMode.AWAITING_RESCUE
                    self.capture_mgr.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
                else:
                    self._game_over()
```

(Note: `_kill_player` still exists for `_perform_capture` flow. We keep it for that path; the new `_kill_player_half` covers per-ship death.)

Actually — since `_kill_player_half` covers everything `_kill_player` did, remove the old `_kill_player` if it's no longer referenced. Search for callers; if none remain, delete it. Otherwise leave it.

- [ ] **Step 9: Pass `dual` flag through wave-clear transitions**

Find the wave-clear block at the bottom of `update`. Replace the PlayScene factory line:

```python
                self.manager.replace(
                    TransitionScene(
                        text,
                        lambda: type(self)(scoring=self.scoring, difficulty=self.difficulty),
                        duration=1.5,
                    )
                )
```

With:

```python
                is_dual = self.capture_mgr.state.mode == CaptureMode.DUAL
                self.manager.replace(
                    TransitionScene(
                        text,
                        lambda: type(self)(
                            scoring=self.scoring,
                            difficulty=self.difficulty,
                            dual=is_dual,
                        ),
                        duration=1.5,
                    )
                )
```

The BonusScene factory remains unchanged (bonus has no boss, so DUAL state stays in capture_mgr but no tractor anyway; on return from bonus, PlayScene resumes — but bonus.py creates a new PlayScene without dual flag, so dual is lost on bonus stage entry; this is a known limitation, acceptable for now).

- [ ] **Step 10: Update `draw` to render tractor beams + captured ships + rescuing ships**

Replace the existing `draw` body (between the explosions draw and pause overlay) — find:

```python
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
```

Replace with:

```python
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        # Draw captured ships above their captors
        for e in self.enemies:
            if e.captured_ship is not None:
                cs = e.captured_ship
                self.playfield.blit(
                    cs,
                    cs.get_rect(center=(e.rect.centerx, e.rect.top - cs.get_height() // 2 - 2)),
                )
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        self.rescuing_ships.draw(self.playfield)
        for beam in self.tractor_beams:
            beam.draw(self.playfield)
```

- [ ] **Step 11: Smoke test**

```powershell
.venv\Scripts\python.exe -c "from scenes.play import PlayScene; print('imports ok')"
.venv\Scripts\python.exe -m pytest -q
```

Expected: imports clean, all existing tests still pass.

- [ ] **Step 12: Format + commit**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/play.py
git commit -m "feat(play): tractor beam + capture/rescue + dual fighter orchestration"
```

---

### Task 10: Final verification + push

**Files:** none

- [ ] **Step 1: Full test suite + lint**

```powershell
.venv\Scripts\python.exe -m pytest -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
```

Expected: 70+ tests pass (52 existing + 16 capture + 2 scoring + 1 difficulty = 71), ruff clean.

- [ ] **Step 2: Smoke import end-to-end**

```powershell
.venv\Scripts\python.exe -c "import main; print('main.py imports cleanly')"
```

- [ ] **Step 3: Manual playtest checklist (user-facing)**

Run `python main.py` and verify with deliberate actions:
- [ ] Boss tractor fires occasionally on NORMAL (1-2× per 5 minutes).
- [ ] Walking into beam after ~0.3s = capture; player ship taken.
- [ ] Captured ship visible above captor boss in formation.
- [ ] Killing captor while it's diving with captured ship = rescue → dual fighter.
- [ ] Dual fires 2 bullets per Space press.
- [ ] One half hit = single fighter survives.
- [ ] Last-life capture: 5s window to kill captor; success → dual; timeout → game over.
- [ ] HARD: tractor noticeably more frequent.
- [ ] EASY: tractor noticeably less frequent.

- [ ] **Step 4: Push branch**

```powershell
git push -u origin feat/tractor-beam
```

---

## Self-Review Notes

**Spec coverage:**
- §3 game design parameters → Task 1, 5
- §4 architecture / file structure → matches Task ordering
- §5 components → all listed components have a task (capture: 3, tractor_beam: 4, enemy: 6, player: 7, rescuing_ship: 8, scoring: 2, play: 9)
- §6 data flow → Task 9 implements the per-frame integration
- §7 error handling → Task 9 covers tractor-during-formation, dual-half-loss, awaiting-rescue timeout, captured-ship-shot
- §8 testing → Task 3 (capture) + Task 2 (scoring) + Task 5 (difficulty); manual list in Task 10
- §9 future work → out of scope, not implemented

**Placeholder scan:** No TBD/TODO. Each step contains exact code to apply.

**Type consistency:**
- `CaptureMode` enum used consistently across Tasks 3, 9.
- `CaptureManager` method names consistent (`begin_beam`, `update_beam`, `on_beam_ended`, `on_captured`, `on_captor_destroyed`, `on_rescue_eligible_kill`, `on_rescue_complete`, `on_dual_lost`, `update_awaiting_rescue`, `can_start_tractor`).
- `EnemyState` new values referenced in Task 6, 9 match.
- `TractorBeam.boss` / `TractorBeam.contains` / `TractorBeam.expired` consistent in Task 4 + 9.
- `Player.dual_offset`, `is_left_half`, `is_right_half` consistent in Task 7 + 9.

**Risk:** Task 9 is large (~200 lines added/modified to one file). If implementation diverges, fall back to TDD-style smoke checks: after each step in Task 9, run `python -c "from scenes.play import PlayScene"` to catch syntax errors early.
