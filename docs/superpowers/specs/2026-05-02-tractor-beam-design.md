# Tractor Beam / Dual Fighter — Design Spec

**Date:** 2026-05-02
**Status:** Approved (pending implementation plan)
**Scope:** Add the Galaga tractor-beam capture mechanic + dual fighter rescue. Faithful to the original arcade.

This feature was explicitly listed as "Future Work" in the original spec ([2026-05-02-galaga-clone-design.md §10](2026-05-02-galaga-clone-design.md)). It moves the project from "Classic Core" toward "Full Clone".

---

## 1. Goals & Scope

Goals:
- Boss enemies can fire a tractor beam during their dive.
- Player ships caught in the beam are captured: lose a life, ship is taken to the formation.
- The captured ship rides above its captor boss in the formation; on subsequent dives it follows the boss down.
- Destroying a boss while it carries a captured ship rescues the ship — it merges with the current player to form a Dual Fighter (twin guns).
- If captured on the last life, a 5-second rescue window suspends game-over.

In scope:
- Boss state machine extension (`TRACTOR_ALIGNING`, `TRACTOR_BEAMING`, `RETURNING_WITH_CAPTURE`).
- Animated striped tractor beam (rendered with `pygame.draw`, no PNG assets).
- Capture state machine (pure module, unit-tested).
- Dual fighter: 2 player sprites side-by-side, double bullets, independent hitboxes per side.
- New scoring: tractor-mode boss kill 400, rescue kill 800, accidentally shooting the captured ship loses it permanently.
- Difficulty multiplier on tractor probability (EASY 0.5, NORMAL 1.0, HARD 1.5).

Out of scope (still):
- "FIGHTER CAPTURED" / "OK" text overlays from the original.
- Triple-fighter cheat.
- Tractor beam in bonus stages (bonus = no enemy fire, no exception here).

---

## 2. Tech Choices

No new dependencies. Tractor beam visuals are drawn with `pygame.draw.polygon` at runtime (no Pillow PNG); captured-ship sprite reuses `player.png` with a darken tint.

---

## 3. Game Design Parameters

| Parameter | Value |
|---|---|
| Tractor beam probability (NORMAL) on boss-dive start | 0.30 |
| Tractor probability difficulty multipliers | EASY 0.5, NORMAL 1.0, HARD 1.5 |
| Beam lifetime | 3.0 s |
| Beam width (top, at boss) | 24 px |
| Beam width (bottom, near player) | 60 px |
| Beam capture grace | 0.3 s of accumulated overlap → capture |
| Beam striped colors | yellow `(240, 220, 60)`, blue `(60, 120, 240)` |
| Stripe band height | 14 px |
| Stripe scroll speed | 240 px/s downward |
| Boss alignment travel speed | 200 px/s |
| Captured ship return speed (with boss) | 220 px/s |
| Rescue ship descent speed (after boss kill) | 220 px/s |
| Concurrent active tractor beams | Max 1 |
| Score: tractor-mode boss kill (before capture) | 400 |
| Score: rescue kill (boss carrying captured ship, in dive) | 800 |
| Score: in-formation boss with captured ship (kill) | 150 (existing), captured ship lost |
| Score: accidentally shooting captured ship | 0, ship permanently lost |
| Last-life rescue window | 5.0 s |
| Dual fighter horizontal offset | ±22 px from center between sprites |
| Dual fighter bullet emission | 2 bullets per Space press (one per ship) |
| Max player bullets on screen (dual) | 4 (vs 2 for single) |

---

## 4. Architecture (Approach B — separate TractorBeam entity + pure capture module)

### File Changes

```
galaga-clone/
├── settings.py                       # MODIFY: tractor beam constants
│
├── entities/
│   ├── enemy.py                      # MODIFY: BossEnemy gets tractor states + captured_ship slot
│   ├── player.py                     # MODIFY: dual_offset / is_left_half / is_right_half flags
│   └── tractor_beam.py               # NEW: TractorBeam sprite (visuals + polygon containment)
│
├── game/
│   ├── capture.py                    # NEW: CaptureMode enum, CaptureState dataclass, CaptureManager
│   └── scoring.py                    # MODIFY: 'tractor' (400) and 'rescue' (800) score kinds
│
├── scenes/
│   └── play.py                       # MODIFY: tractor_beams group, capture orchestration, dual fighter spawn
│
└── tests/
    ├── test_capture.py               # NEW: ~14 unit tests for CaptureManager
    └── test_scoring.py               # MODIFY: +2 tests for tractor/rescue kill scores
```

### Module Boundaries

- `game/capture.py`: pure data + state transitions. Knows nothing about sprites, surfaces, or rendering. Single source of truth for capture-related state.
- `entities/tractor_beam.py`: visuals + collision. Subscribes to a parent `BossEnemy` for position. Polygon-based `contains(point)` for capture detection (rect-based collision is wrong for triangle).
- `entities/enemy.py`: `BossEnemy` extends with new states. Carries `captured_ship: Optional[Surface]` field for rendering only — capture state is in `CaptureManager`.
- `entities/player.py`: minimal — `dual_offset`, `is_left_half`, `is_right_half` flags. The dual fighter is just two `Player` instances side-by-side; no separate `DualFighter` class.
- `scenes/play.py`: orchestrates everything. Holds `tractor_beams: pygame.sprite.Group` and a `CaptureManager` instance. All `mode` transitions go through the manager.

---

## 5. Components

### `game/capture.py`

```python
class CaptureMode(Enum):
    NORMAL           # Default
    BEAMING          # Player overlapping a beam, accumulating grace
    CAPTURED         # Ship taken; captor boss carries it
    AWAITING_RESCUE  # Lives==0 + captured; suspended game-over with timer
    RESCUING         # Boss killed; captured ship descending to player
    DUAL             # Two-ship player active

@dataclass
class CaptureState:
    mode: CaptureMode = CaptureMode.NORMAL
    captor_boss_id: int | None = None
    rescue_timer: float = 0.0      # AWAITING_RESCUE countdown
    beam_grace: float = 0.0        # BEAMING accumulator

class CaptureManager:
    state: CaptureState
    active_tractor_boss_id: int | None  # currently-beaming boss

    def can_start_tractor(self, boss_id: int) -> bool
    def begin_beam(self, boss_id: int) -> None
    def update_beam(self, dt: float, in_beam: bool) -> bool   # True if capture triggered
    def on_beam_ended(self) -> None                            # boss done beaming, no capture
    def on_captured(self, boss_id: int, lives_after: int) -> None
    def on_captor_destroyed(self) -> None                      # boss carrying capture dies
    def on_rescue_eligible_kill(self) -> bool                  # True if RESCUING entered
    def on_dual_lost(self) -> None
    def on_rescue_complete(self) -> None                       # DUAL entered
    def update_awaiting_rescue(self, dt: float) -> bool       # True if timeout (game over)
```

No pygame import. Returns booleans / state for caller to act on.

### `entities/tractor_beam.py`

```python
class TractorBeam(pygame.sprite.Sprite):
    """Striped triangular beam attached to a boss. Self-removes on lifetime expiry."""

    def __init__(self, boss: BossEnemy) -> None: ...
    def update(self, dt: float) -> None:
        # follow boss x; advance stripe phase; decrement lifetime
    def draw(self, surface: pygame.Surface) -> None:
        # render striped triangle with pygame.draw.polygon + clip rects
    def contains(self, point: pygame.Vector2) -> bool:
        # point-in-polygon test for capture detection
    @property
    def expired(self) -> bool: ...
```

`update` and `draw` are separate (not the standard sprite pattern that draws via `image`/`rect`) because the striped animation requires per-frame procedural rendering.

### `entities/enemy.py` — BossEnemy additions

New states (added to `EnemyState` enum):
- `TRACTOR_ALIGNING` — boss moves to align horizontally over the player.
- `TRACTOR_BEAMING` — boss holds position; tractor beam exists in scene.
- `RETURNING_WITH_CAPTURE` — boss returns to its formation slot, captured ship trailing.

New field on `Enemy`:
- `captured_ship: pygame.Surface | None = None` — drawn above the enemy when present.

New methods on `BossEnemy`:
- `enter_tractor_align(player_pos)` — set state, store target x.
- `update_tractor_align(dt, player_pos)` — slide toward target x; transition to `TRACTOR_BEAMING` when within tolerance.
- `update_tractor_beaming(dt)` — hold position. Beam is owned by PlayScene group, not by enemy.
- `attach_captured_ship(surface)` — set `captured_ship` field, transition to `RETURNING_WITH_CAPTURE`.
- `update_returning_with_capture(dt)` — move along straight line back to formation slot; on arrival → `IN_FORMATION`.

In-formation rendering with captured ship:
- `Enemy.update()` already updates rect; PlayScene draws enemy normally. The captured ship is drawn by PlayScene (or an Enemy `extra_draw` hook) at `(enemy.rect.centerx, enemy.rect.top - ship.height/2 - 2)`.

### `entities/player.py` — minor additions

New fields:
```python
class Player(pygame.sprite.Sprite):
    dual_offset: int = 0          # 0 single, -22 left half, +22 right half
    is_left_half: bool = False
    is_right_half: bool = False
```

`Player.update` unchanged for movement; the offset only changes initial spawn position. Bullets are emitted from `(self.pos.x, self.pos.y - height/2)` as before — the calling scene fires once per ship in the players group.

Movement of dual fighter: `PlayScene` updates both Player instances with the same input each frame. They move together because they share input and identical clamping.

Edge case — clamping: when in dual mode, the left ship's x must stay >= half-width of the LEFTMOST sprite, and the right ship's x must stay <= playfield_width - half-width. PlayScene computes a combined clamp envelope and applies it to both ships before per-ship rect update.

### `scenes/play.py` — additions

New fields:
```python
self.tractor_beams: pygame.sprite.Group
self.capture_mgr: CaptureManager
self.captured_ships: pygame.sprite.Group  # only populated during RESCUING (descending ships)
```

Constructor accepts optional `dual: bool = False` for carrying dual state across waves.

`update(dt, inp)` extensions (in order, after existing update steps):
1. Update tractor beams (`for b in tractor_beams: b.update(dt)`); remove expired.
2. Tractor beam vs player collision: for each beam, check `beam.contains(player.center)` for each player sprite. Pass result to `capture_mgr.update_beam(dt, in_beam=True/False)`. If returns True (capture triggered), invoke `_perform_capture(beam, players_in_beam)`.
3. Update capture manager's awaiting-rescue timer if applicable. If returns True (timeout) → `_game_over()`.
4. (Existing) Trigger new dives. Modified to consult `capture_mgr.can_start_tractor(boss.id)` for boss enemies and roll tractor probability.

`_handle_collisions` extensions:
1. (Existing) `player_bullets ⨯ enemies` collision — but when an enemy is killed, check:
   - If enemy is a boss with `captured_ship` AND state == `DIVING` → `_perform_rescue(enemy)`.
   - Else if enemy is a boss in state `TRACTOR_BEAMING` or `TRACTOR_ALIGNING` → `add_kill("tractor")` (400) + `tractor_beams.empty_for(enemy)`.
   - Else → existing scoring.
2. New: `player_bullets ⨯ captured_ships_in_formation` (drawn separately but with their own rect) — kills the captured ship, no score, manager `on_captor_destroyed_for_capture(enemy)`.
3. (Existing) Player vs enemies / enemy bullets — but per-ship in dual mode (loop over both players, kill each independently).

`_perform_capture(beam, captured_players)`:
- For each captured player (only one in single mode, possibly only the left in dual):
  - Add explosion at player position.
  - Remove that Player from the players group.
  - In dual case: `capture_mgr.on_dual_lost()`, then on_captured.
- `scoring.lose_life()`.
- Tint a copy of `assets.sprite("player")` 50% darker → `captured_surface`.
- Attach to the captor boss: `boss.captured_ship = captured_surface`, `boss.attach_captured_ship(...)` (state → RETURNING_WITH_CAPTURE).
- `tractor_beams.empty_for(boss)`.
- `capture_mgr.on_captured(boss.id, lives_after=scoring.lives)`.
- If `scoring.lives == 0`: capture_mgr enters AWAITING_RESCUE (5s timer). Don't start respawn.
- Else: start respawn timer; on respawn, new Player spawns single (mode is CAPTURED but display is normal single ship).

`_perform_rescue(boss)`:
- `scoring.score += 800` (or call `add_kill("rescue")`).
- Add explosion at boss position.
- Spawn `RescuingShip` sprite at `boss.rect.center` traveling toward current player.
- `capture_mgr.on_rescue_eligible_kill()`.
- Boss is killed normally (removed from enemies group).
- `boss.captured_ship = None` (transferred to RescuingShip).

`_complete_rescue(rescue_ship, current_player)`:
- Spawn second Player at `current_player.pos.x + 22` with `is_right_half=True`, `dual_offset=22`.
- Mark current player `is_left_half=True`, `dual_offset=-22`.
- `capture_mgr.on_rescue_complete()`.
- Play SFX.

### `entities/rescuing_ship.py` — small new file (or inline in play.py)

```python
class RescuingShip(pygame.sprite.Sprite):
    """Captured ship descending to attach to current player. Triggers callback on arrival."""

    def __init__(self, start_pos, target_player, on_arrival): ...
    def update(self, dt: float) -> None:
        # move toward target_player.pos at 220 px/s
        # if within 4 px → call on_arrival(self) and self.kill()
```

Lightweight — could live in `entities/player.py` or `scenes/play.py`. Putting it in `entities/` for consistency.

### `game/scoring.py` modification

Add to `_KILL_SCORES`:
```python
_KILL_SCORES = {
    "normal": settings.SCORE_NORMAL_KILL,
    "dive":   settings.SCORE_DIVE_KILL,
    "boss":   settings.SCORE_BOSS_KILL,
    "bonus":  settings.SCORE_BONUS_PER_KILL,
    "tractor": settings.SCORE_TRACTOR_KILL,    # 400
    "rescue":  settings.SCORE_RESCUE_KILL,     # 800
}
```

Add to `settings.py`:
```python
SCORE_TRACTOR_KILL = 400
SCORE_RESCUE_KILL = 800
```

---

## 6. Data Flow

### Tractor Sequence (one full cycle)

```
[Boss-dive start]
  PlayScene.update sees in-formation boss eligible to dive.
  if isinstance(boss, BossEnemy) and capture_mgr.can_start_tractor(boss.id):
      if random() < tractor_probability * difficulty.tractor_mult:
          boss.enter_tractor_align(player.pos); capture_mgr.begin_beam(boss.id)
          continue
  boss.start_dive(...)  # standard dive

[TRACTOR_ALIGNING]
  Per frame: boss slides toward player.x at 200 px/s.
  Within 5 px → state = TRACTOR_BEAMING, spawn TractorBeam(boss).

[TRACTOR_BEAMING]
  TractorBeam updates each frame (stripe phase, lifetime).
  PlayScene checks beam.contains(player.center) per active player.
  capture_mgr.update_beam(dt, in_beam) → True if capture grace reached 0.3s.
  beam.expired → tractor_beams.kill, capture_mgr.on_beam_ended,
                 boss.start_dive() (resume normal dive).

[CAPTURE]
  See _perform_capture above.
  → boss state RETURNING_WITH_CAPTURE; player removed; new player respawns
    in 0.5s (unless lives==0 → AWAITING_RESCUE).

[RETURNING_WITH_CAPTURE → IN_FORMATION (with captured_ship)]
  Boss travels back to formation slot; captured_ship rendered above.

[Captor's next dive]
  Boss enters DIVING; captured_ship moves with it (rendered above).

[Boss kill while DIVING + captured_ship]
  → _perform_rescue: spawn RescuingShip; scoring += 800.

[RESCUING → DUAL]
  RescuingShip descends; on arrival adds second Player; mode = DUAL.
```

### Per-Frame Update Order (PlayScene.update)

```
1. INPUT
2. UPDATE
   ├─ Players (1 or 2 in dual)
   ├─ Bullets (player + enemy)
   ├─ Enemies
   ├─ TractorBeams
   ├─ RescuingShips
   ├─ Explosions
   ├─ Trigger new dives (with tractor probability check)
   └─ CaptureManager.update_awaiting_rescue → may signal game over
3. COLLIDE
   ├─ player_bullets ⨯ enemies
   │    (boss kills branch by state: tractor / rescue / normal)
   ├─ player_bullets ⨯ captured_ships (in formation)
   ├─ enemy_bullets ⨯ players (per-ship in dual)
   ├─ diving enemies ⨯ players (per-ship)
   └─ tractor_beams ⨯ players (polygon contains)
4. DRAW
```

---

## 7. Error Handling

(Carries over the original spec's "boundary-only validation; trust internal calls" principle.)

| Failure / edge | Handling |
|---|---|
| Two bosses try to start tractor same frame | `can_start_tractor` returns True for only the first; second goes to normal dive |
| Beam-active boss killed mid-beam | Beam removed; `capture_mgr.on_beam_ended`; mode unchanged (still NORMAL since no capture happened) |
| Captor boss killed in formation (no dive) | Captured ship lost permanently; mode → NORMAL (or game over if AWAITING_RESCUE) |
| Player accidentally shoots captured ship | Captured ship sprite removed from boss; no score; boss still alive; `capture_mgr.on_captor_destroyed` |
| Last-life capture, then boss exits formation without diving | Timer keeps counting in AWAITING_RESCUE; eventually times out → game over |
| Dual fighter, both halves hit same frame (e.g., diving enemy spans both) | Both die, lives -= 2; if lives ≤ 0 → game over |
| Wave clears with mode == DUAL | New PlayScene constructor receives `dual=True`; both ships re-spawn; mode preserved |
| Wave clears with mode == CAPTURED | Captured ship and captor are in the just-killed enemy set — it's already gone; mode → NORMAL on `on_captor_destroyed`. (If a captor survives via wave-clear edge case, design choice: kill captured_ship and reset mode.) |
| Beam exists at scene transition | `PlayScene.on_exit` empties tractor_beams group |
| Bonus stage entered while AWAITING_RESCUE | Cannot occur (AWAITING_RESCUE means lives==0; game over fires before bonus stage) |
| Difficulty toggle mid-game (not allowed by UI) | Not possible from current UI |

---

## 8. Testing

### Unit tests (`tests/test_capture.py`)

~14 tests for `CaptureManager` covering all transitions and edges:
- Initial state is NORMAL.
- `can_start_tractor` true when idle.
- `can_start_tractor` false when another boss beaming, or mode in (BEAMING/CAPTURED/AWAITING_RESCUE/RESCUING/DUAL).
- `begin_beam` sets active_tractor_boss_id.
- `update_beam(dt, True)` accumulates grace; reaching 0.3 returns True.
- `update_beam(dt, False)` resets grace.
- `on_beam_ended` clears active_tractor_boss_id.
- `on_captured(lives_after=>0)` → mode CAPTURED.
- `on_captured(lives_after=0)` → mode AWAITING_RESCUE, rescue_timer = 5.0.
- `update_awaiting_rescue(6.0)` returns True (timeout).
- `update_awaiting_rescue(1.0)` returns False, decrements timer.
- `on_captor_destroyed` from CAPTURED → mode NORMAL (with lives) or AWAITING_RESCUE → game-over signal.
- `on_rescue_eligible_kill` from CAPTURED → mode RESCUING.
- `on_rescue_complete` → mode DUAL.
- `on_dual_lost` from DUAL → mode NORMAL.

### Unit tests (`tests/test_scoring.py` additions)

- `add_kill("tractor")` → score += 400.
- `add_kill("rescue")` → score += 800.

### Manual playtest checklist

1. Boss tractor probability — visible 1–2× per 5 minutes of NORMAL play.
2. Capture cycle: deliberately enter beam → boss carries ship → kill captor on next dive → dual fighter.
3. Tractor-mode boss kill (before capture lands) → 400 points, no capture.
4. Accidentally shoot captured ship → permanent loss, 0 score.
5. Last-life capture: 5s rescue window — successful rescue restores dual.
6. Last-life capture: timeout → game over.
7. Dual fighter: left-only hit → right ship survives.
8. Dual fighter: both hit same frame by big diving boss → both die.
9. Boss wave (5 bosses): only one tractor at a time.
10. Bonus stage: no tractor beams (since no boss enemies present anyway, also assert by class).
11. Wave cleared while DUAL: next wave starts with both ships intact.
12. Difficulty multipliers: tractor visibly less common on EASY, more frequent on HARD.

### Constraints

- `game/capture.py`: no `import pygame`.
- `entities/tractor_beam.py`: pygame allowed (rendering + collision).
- `entities/player.py`: keep additions minimal; no separate DualFighter class.

---

## 9. Open Items / Future Work

Still deferred:
- "FIGHTER CAPTURED" / "OK" textual flair from the original.
- Triple-fighter cheat (capture twice in a row).
- Stinger gameplay: enemy "stinger" formation patterns.
- Distinct boss types (red boss / green boss).
