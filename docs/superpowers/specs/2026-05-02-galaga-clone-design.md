# Galaga Clone — Design Spec

**Date:** 2026-05-02
**Status:** Approved (pending implementation plan)
**Scope:** Single-player Galaga clone in Python + Pygame, "Classic Core" feature set with bonus stages.

---

## 1. Goals & Scope

A faithful "Classic Core" Galaga clone. Goals:

- Playable single-player game with the unmistakable Galaga feel: formation entry, dive attacks, wave progression.
- All assets (sprites + audio) generated programmatically — no external downloads required.
- Personal/learning project, not for public distribution.

In scope:
- Player ship (move, fire, lives, respawn).
- Enemy formation (5×8 = 40 enemies) with curved entry paths.
- Dive attack patterns.
- Wave progression: 4 normal → 1 boss → 1 bonus, repeating, with infinite difficulty ramp.
- Bonus stage (challenging stage): no enemy fire, time-limited, perfect bonus = +10000 points + 1 life.
- HUD on side panels (score, lives, wave, hi-score, accuracy, kills).
- Programmatic chiptune music recreating the original Galaga melodies (intro, stage start, etc.).
- Programmatic SFX (fire, explode, etc.).
- Persistent high score.
- GitHub repo (public) with GitHub Actions CI (pytest + ruff).

Out of scope (explicitly):
- Tractor beam / dual fighter mechanic.
- Distinct Bee/Butterfly/Boss visual differentiation beyond color (sprites are placeholders, all enemy types share similar shape with color/size variation).
- Online high-score leaderboards.
- Mobile/touch controls.
- Additional CI tooling beyond pytest + ruff (no mypy, no coverage gates).

---

## 2. Tech Choices

| Decision | Choice | Reason |
|---|---|---|
| Language / runtime | Python 3.11+ | User preference; standard Pygame target. |
| Game library | Pygame (latest stable) | Mature, simple, ideal for 2D arcade games. |
| Sprite generation | Pillow (PIL) | Programmatic PNG generation, no external assets. |
| Audio generation | NumPy → WAV | Programmatic chiptune + SFX synthesis. |
| Test framework | pytest | Standard. |
| Linter/formatter | ruff | Fast, single tool replaces black + flake8 + isort. |
| CI | GitHub Actions | Free for public repos; standard. |
| Repo visibility | Public on GitHub | User preference. |

---

## 3. Game Design Parameters

| Parameter | Value |
|---|---|
| Window size | 1280 × 720 (16:9) |
| Playfield size | 540 × 720 (3:4, original Galaga aspect, centered) |
| Side panels | Left 370 × 720, Right 370 × 720 |
| Frame rate | 60 FPS, fixed timestep |
| Controls | ←/→ or A/D = move, Space = fire, P = pause, Esc = quit |
| Lives | 3 starting |
| Concurrent player bullets | Max 2 on screen (original rule) |
| Formation | 5 rows × 8 columns = 40 enemies |
| Wave cycle | 1–4 normal → 5 boss → 6 bonus → 7–10 normal → 11 boss → 12 bonus → ... |
| Difficulty progression | Each wave: dive frequency ↑, enemy speed ↑, enemy bullet speed ↑ (monotonic) |
| Score: normal kill | 50 points |
| Score: dive-state kill | 100 points |
| Score: boss kill | 150 points |
| Bonus stage: per kill | 200 points |
| Bonus stage: perfect | +10000 points + 1 life |

### Side Panel Layout

| Position | Content |
|---|---|
| Left top | "GALAGA" logo |
| Left mid | SCORE (current, large) |
| Left bottom | LIVES (ship icons), control reference |
| Right top | HIGH SCORE |
| Right mid | WAVE / STAGE number |
| Right bottom | Accuracy %, Enemies destroyed |

---

## 4. Architecture (Approach B — multi-module + scene state machine)

### Project Structure

```
galaga-clone/
├── main.py                       # Entry point, pygame init, main loop
├── pyproject.toml                # Dependencies (pygame, numpy, pillow), ruff config
├── README.md
├── .gitignore                    # excludes assets/, __pycache__, etc.
├── .github/
│   └── workflows/
│       └── ci.yml                # pytest + ruff on push
├── settings.py                   # Constants: resolution, FPS, colors, scoring, key map
│
├── assets/                       # Generated, not committed
│   ├── sprites/
│   └── audio/
│
├── tools/                        # One-shot asset generators
│   ├── generate_sprites.py
│   └── generate_audio.py
│
├── engine/                       # Game-agnostic infrastructure
│   ├── __init__.py
│   ├── assets.py                 # Asset loading, caching
│   ├── audio.py                  # SFX/BGM playback, fades
│   ├── input.py                  # InputState abstraction
│   └── scene.py                  # Scene base class, SceneManager
│
├── entities/                     # In-game objects (pygame.sprite.Sprite)
│   ├── __init__.py
│   ├── player.py
│   ├── enemy.py                  # Enemy + Bee/Butterfly/Boss
│   ├── bullet.py                 # PlayerBullet, EnemyBullet
│   └── explosion.py
│
├── game/                         # Pure game rules (mostly pygame-free)
│   ├── __init__.py
│   ├── formation.py              # Slot positions + entry Bezier paths
│   ├── wave.py                   # Wave type enum, cycle progression
│   ├── dive.py                   # Dive attack curves
│   ├── scoring.py                # Score, lives, accuracy, hi-score persistence
│   └── hud.py                    # Side panel rendering
│
├── scenes/
│   ├── __init__.py
│   ├── title.py
│   ├── play.py
│   ├── bonus.py
│   ├── gameover.py
│   └── transitions.py
│
├── data/                         # Created at runtime, gitignored
│   └── highscore.json
│
└── tests/
    ├── test_formation.py
    ├── test_scoring.py
    ├── test_wave.py
    └── test_dive.py
```

**Module responsibility summary:**
- `engine/`: reusable infrastructure (assets, input, audio, scene management).
- `entities/`: drawable game objects, all `pygame.sprite.Sprite` subclasses.
- `game/`: pure game logic. `scoring.py` and `wave.py` MUST NOT import pygame (so unit tests run without display). `formation.py` and `dive.py` may use `pygame.Vector2` only — no surfaces or sprites.
- `scenes/`: per-scene logic; integrates entities + game rules. Scene transitions managed by `SceneManager`.
- `tools/`: standalone scripts that produce `assets/`. Re-runnable, idempotent.

File size: no hard cap. Split modules when they become unwieldy in practice.

---

## 5. Components

### Main Loop & Scene Management
- `main.py`: pygame init, create 1280×720 window, start `SceneManager` with `TitleScene`, run fixed-timestep 60 FPS loop. Pass `dt` (delta time) to all updates.
- `engine/scene.py`: `Scene` base class with `handle_event(event)`, `update(dt, input)`, `draw(surface)`. `SceneManager` holds current scene + transition queue (push/pop/replace).

### Scene Transitions

```
TitleScene  --Space-->  PlayScene
                         ├── wave 5 cleared --> TransitionScene("CHALLENGING STAGE") --> BonusScene --done--> PlayScene (next cycle)
                         └── lives==0 --> GameOverScene --Space--> TitleScene
```

### Entities

**Player (`entities/player.py`)**
- Horizontal movement with bounded position (clamped to playfield).
- Fire on Space if `len(player_bullets) < 2`.
- On hit: explosion animation, 0.5s respawn delay, lives -= 1.

**Enemy (`entities/enemy.py`)**
- State machine: `ENTERING` → `IN_FORMATION` → `DIVING` → `RETURNING`.
  - `ENTERING`: follow precomputed Bezier entry path to assigned formation slot.
  - `IN_FORMATION`: position = slot + formation oscillation offset.
  - `DIVING`: follow procedurally generated curve toward player area, then offscreen.
  - `RETURNING`: re-enter formation from top.
- Subtypes: `BeeEnemy` (50 pts, frequent dives), `ButterflyEnemy` (100 pts, paired dives), `BossEnemy` (150 pts, dives with escorts).

**Bullet (`entities/bullet.py`)**
- `PlayerBullet`: vertical upward, removed offscreen.
- `EnemyBullet`: launched from enemy toward player position at fire moment, then linear travel.

**Explosion (`entities/explosion.py`)**
- Frame-based animation, removes self when sequence completes.

### Game Logic

**Formation (`game/formation.py`)**
- 5×8 slot grid, centered in playfield, with margins.
- `slot_position(row, col, oscillation_phase)` returns a `Vector2`.
- `entry_path(row, col)` returns a list of waypoints (Bezier-sampled) from offscreen to slot.
- Pure function module; no pygame.sprite.

**Wave Controller (`game/wave.py`)**
- `WaveType` enum: `NORMAL`, `BOSS`, `BONUS`.
- Pure functions:
  - `wave_type_for(wave_number) -> WaveType`: 1–4 normal, 5 boss, 6 bonus, repeats every 6.
  - `difficulty_params(wave_number) -> DifficultyParams`: enemy speed, dive probability, enemy bullet speed.
- `WaveController` class: stateful holder of current wave number. Provides `current_type()`, `current_params()`, `advance()`. Used by `PlayScene` to drive wave-end transitions.
- No pygame import (the controller is plain Python state).

**Dive (`game/dive.py`)**
- `dive_path(enemy_pos, player_pos, seed) -> list[Vector2]`: combination of Bezier + sine oscillation. Pure function.

**Scoring (`game/scoring.py`)**
- `Scoring` dataclass: `score`, `lives`, `wave`, `shots_fired`, `hits`, `enemies_killed`.
- Methods: `add_kill(enemy_type)`, `lose_life()`, `gain_life()`, `accuracy() -> float`, `add_shot()`.
- Hi-score persistence via `load_highscore()` / `save_highscore(score)` reading `data/highscore.json`.
- Single source of truth — held by `SceneManager`, passed to scenes/HUD.
- No pygame import.

**HUD (`game/hud.py`)**
- `draw_left(surface, scoring)` and `draw_right(surface, scoring)`: each renders its 370×720 panel.
- Reads from `Scoring` object every frame.

### Engine

**Assets (`engine/assets.py`)**
- On startup: check `assets/sprites/` and `assets/audio/`. If empty, run `tools/generate_*.py`.
- After generation, load all PNG/WAV files into a cache dict keyed by name.

**Audio (`engine/audio.py`)**
- `play_sfx(name)`: one-shot.
- `play_music(name, loop=True)` / `stop_music()` / `fade_music(ms)`.
- Manages 8 mixer channels. If `pygame.mixer.init()` fails, becomes no-op silently.

**Input (`engine/input.py`)**
- `InputState` updated each frame from `pygame.event.get()` and `pygame.key.get_pressed()`.
- Fields: `left`, `right`, `fire`, `pause`, `quit`.
- Single source of input state — scenes/entities only read from this.

---

## 6. Data Flow (Per Frame, PlayScene)

```
1. INPUT
   pygame.event.get() → InputState (left/right/fire/pause/quit)

2. UPDATE(dt)
   ├─ Player.update(dt, input)   → may emit PlayerBullet, increment Scoring.shots
   ├─ Formation.update(dt)        → updates oscillation offset
   ├─ Enemies.update(dt)          → state machine; may transition to DIVING
   ├─ Bullets.update(dt)          → linear motion, kill if offscreen
   └─ WaveController.update(dt)   → if all enemies dead, queue next wave

3. COLLIDE
   ├─ player_bullets ⨯ enemies → Scoring.add_kill, Explosion, play_sfx("explode")
   ├─ enemy_bullets ⨯ player   → Scoring.lose_life
   └─ enemies ⨯ player          → mutual kill, Scoring.lose_life
   If lives == 0: SceneManager.replace(GameOverScene)

4. DRAW
   surface.fill(black)
   HUD.draw_left(surface, scoring)
   playfield = pygame.Surface((540, 720))   # local coords
       ├─ stars background
       ├─ enemies, bullets, player, explosions
       └─ blit to surface at (370, 0)
   HUD.draw_right(surface, scoring)
   pygame.display.flip()
```

### Key Decisions
- **Playfield in local coords**: all entity positions are (0..540, 0..720). Final blit handles offset to (370, 0) on main surface.
- **`Scoring` is single source of truth**: lives in `SceneManager`, survives scene transitions, read by HUD every frame.
- **`WaveController` triggers scene transitions**: PlayScene asks "wave done?" → if yes, looks up next wave type → BONUS pushes BonusScene; NORMAL/BOSS spawns new enemies in same scene.
- **4 sprite groups only**: `players`, `player_bullets`, `enemies`, `enemy_bullets`. Explosions are draw-only (no collision).
- **Single input source**: only `engine/input.py` reads pygame keyboard. Everyone else reads `InputState`.

---

## 7. Error Handling

Boundary-only validation; internal calls are trusted.

| Failure | Handling |
|---|---|
| `assets/` empty | Auto-run `tools/generate_*.py`. If still fails, print clear error and exit. |
| Individual asset file missing | Fail fast at load with filename in message (not mid-game). |
| `pygame.mixer.init()` fails | Audio becomes no-op silently; print one warning at startup; game proceeds. |
| `data/highscore.json` missing/corrupt | Treat hi-score as 0; rewrite on next save. No user-facing error. |
| Hi-score save fails (e.g., permissions) | Console warning only; game unaffected. |
| Offscreen entities | Removed via `kill()`. Normal flow, prevents memory leaks. |
| Unhandled exception in main loop | `main.py` wraps loop in `try/except`; prints traceback, calls `pygame.quit()`. |

Internal code (`entities/`, `game/`) does not validate inputs from other internal callers.

---

## 8. Testing

Unit tests for pure logic only. No automated integration tests for rendering, audio, input, or scene transitions.

### Tested

| Module | What's tested |
|---|---|
| `game/scoring.py` | Score increments, accuracy with shots=0 edge case, lives bounds, hi-score load/save with tmp file |
| `game/wave.py` | Wave cycle pattern (1→4 normal, 5 boss, 6 bonus, repeats), difficulty params monotonic in wave number |
| `game/formation.py` | Slot coords inside playfield bounds, centered, entry paths start offscreen and end at correct slot |
| `game/dive.py` | Path starts at given enemy pos, terminates below playfield, smooth (bounded segment lengths) |

### Not tested (manual play verification)
- Rendering, sound, input handling, scene transitions, collision detection (Pygame library is trusted).

### Constraints (enforced by review, not tooling)
- `game/scoring.py`, `game/wave.py`: no `import pygame`.
- `game/formation.py`, `game/dive.py`: only `pygame.Vector2` allowed from pygame.

### Running
```
pytest                    # all
pytest tests/test_wave.py # specific file
ruff check .              # lint
ruff format .             # format
```

---

## 9. Repository & CI

### GitHub Repo
- **Name**: `galaga-clone`
- **Visibility**: public
- **Remote setup**: `gh repo create galaga-clone --public --source=. --push` (during execution; verify `gh` is installed and authenticated first; otherwise user will provide remote URL manually).
- **Initial commit**: project skeleton + this spec doc.

### CI: GitHub Actions (`.github/workflows/ci.yml`)

Triggered on push and pull request to any branch.

Jobs:
1. **lint**: `ruff check .` and `ruff format --check .`
2. **test**: `pytest`

Both run on `ubuntu-latest`, Python 3.11. No matrix — single environment.

`pyproject.toml` declares `pygame`, `numpy`, `pillow` as runtime deps and `pytest`, `ruff` as dev deps. Ruff config (line length, target version) lives in `pyproject.toml` under `[tool.ruff]`.

### `.gitignore` (key entries)
- `assets/` — regenerable.
- `__pycache__/`, `*.pyc`
- `.pytest_cache/`, `.ruff_cache/`
- `data/highscore.json` — local user data, not part of source.
- IDE/editor: `.vscode/`, `.idea/`

---

## 10. Open Items / Future Work

Things deliberately deferred:
- Tractor beam / dual fighter (would move scope to "Full Clone").
- Distinct enemy sprite art (placeholders use color/size variation).
- Sound options menu (volume, mute).
- Fullscreen/letterbox mode.
- Localization (game is English-only).
- Coverage measurement, mypy.
