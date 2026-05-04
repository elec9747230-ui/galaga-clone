# Galaga Clone

Single-player Galaga clone built in Python + Pygame. Personal/learning project.

See [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](docs/superpowers/specs/2026-05-02-galaga-clone-design.md) for the design spec.

## Features

- Authentic 5x8 enemy formation with curved entry paths
- Dive attacks with sine-wave wobble
- Wave cycle: 4 normal -> 1 boss -> 1 bonus, repeating, with rising difficulty
- Bonus (challenging) stages with perfect bonus (+10000 + extra life)
- Programmatically generated pixel sprites + chiptune music + SFX (no external assets)
- Persistent high score
- Side-panel HUD (score, lives, wave, accuracy, kills, controls)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
python main.py
```

Assets (sprites + audio) are auto-generated on first run. To regenerate manually:

```powershell
python -m tools.generate_sprites
python -m tools.generate_audio
```

## Controls

- Arrow keys / A,D -- move
- Space -- fire (max 2 bullets on screen)
- P -- pause
- Esc -- quit

## Develop

```powershell
pytest         # tests
ruff check .   # lint
ruff format .  # format
```

## Architecture

The codebase is organised into four packages with one-way dependencies (`scenes` → `entities`/`game` → `engine`). Pure-logic packages (`game/*`) have no Pygame surface dependencies and are unit-tested directly.

| Package | Role |
|---|---|
| `engine/` | Reusable Pygame plumbing — assets, audio mixer, input edge-detection, scene stack |
| `entities/` | Game objects — Player, Enemy (BeeEnemy/ButterflyEnemy/BossEnemy), bullets, beams, animations |
| `game/` | Pure logic — wave cycle, formation grid math, dive paths, capture FSM, scoring, HUD |
| `scenes/` | High-level screens — title, play, bonus, game over, transitions |

### Class diagrams

Split per concern for readability. Full single-diagram source: [docs/uml/classes_Galaga.mmd](docs/uml/classes_Galaga.mmd) (also [.puml](docs/uml/classes_Galaga.puml), [.svg](docs/uml/classes_Galaga.svg), [.png](docs/uml/classes_Galaga.png)).

#### Scene hierarchy

Five scenes share the abstract `Scene` interface, managed by a stack-based `SceneManager` (`push` / `pop` / `replace`). Title → Play → Bonus/GameOver flow.

```mermaid
classDiagram
  direction TB
  class Scene {
    <<abstract>>
    +manager : SceneManager | None
    +on_enter()*
    +on_exit()*
    +update(dt, inp)*
    +draw(surface)*
    +handle_event(event)*
  }
  class SceneManager {
    +current : Scene | None
    +push(scene)
    +pop()
    +replace(scene)
    +update(dt, inp)
    +draw(surface)
    +handle_event(event)
  }
  class TitleScene {
    +selected_difficulty : Difficulty
  }
  class PlayScene {
    +player
    +enemies
    +capture_mgr
    +wave_controller
    +scoring : Scoring | None
  }
  class BonusScene {
    +player
    +enemies
    +scoring
  }
  class GameOverScene {
    +scoring
    +is_new_high
  }
  class TransitionScene {
    +text : str
  }
  TitleScene --|> Scene
  PlayScene --|> Scene
  BonusScene --|> Scene
  GameOverScene --|> Scene
  TransitionScene --|> Scene
  Scene --o SceneManager : current
```

#### Enemy hierarchy

Three enemy types — Bee, Butterfly, Boss — share state machine and dive logic via `Enemy`. Boss can grow into a tractor-beam captor.

```mermaid
classDiagram
  direction TB
  class Enemy {
    +row : int
    +col : int
    +pos
    +rect
    +state : EnemyState
    +captured_ship : pygame.Surface | None
    +start_dive(player_pos, seed)
    +enter_tractor_align(player_pos)
    +attach_captured_ship(ship_surface)
    +maybe_fire(target, speed_mult) EnemyBullet | None
    +is_in_formation() bool
    +update(dt)
  }
  class BeeEnemy
  class ButterflyEnemy
  class BossEnemy
  class EnemyState {
    <<Enum>>
    ENTERING
    IN_FORMATION
    DIVING
    TRACTOR_ALIGNING
    TRACTOR_BEAMING
    RETURNING_WITH_CAPTURE
  }
  BeeEnemy --|> Enemy
  ButterflyEnemy --|> Enemy
  BossEnemy --|> Enemy
  Enemy --> EnemyState : state
```

#### Capture FSM

Boss tractor-beam capture flow. On dual-fighter loss, the rescue window opens until eligible kill or timeout.

```mermaid
classDiagram
  direction TB
  class CaptureManager {
    +state : CaptureState
    +active_tractor_boss_id : int | None
    +can_start_tractor(boss_id) bool
    +begin_beam(boss_id)
    +on_beam_ended()
    +on_captured(boss_id, lives_after)
    +on_captor_destroyed()
    +on_dual_lost()
    +on_rescue_eligible_kill() bool
    +on_rescue_complete()
    +update_beam(dt, in_beam) bool
    +update_awaiting_rescue(dt) bool
  }
  class CaptureState {
    +mode : CaptureMode
    +captor_boss_id : int | None
    +beam_grace : float
    +rescue_timer : float
  }
  class CaptureMode {
    <<Enum>>
    NORMAL
    BEAMING
    AWAITING_RESCUE
    DUAL_FIGHTER
  }
  CaptureState --* CaptureManager : state
  CaptureMode --> CaptureState : mode
```

#### Difficulty + wave systems

Wave cycle is `4 normal → 1 boss → 1 bonus`, repeating with growing difficulty parameters per wave. Three player-selectable difficulty presets (`Difficulty`) layer on top.

```mermaid
classDiagram
  direction TB
  class WaveController {
    +current_wave : int
    +current_type() WaveType
    +current_params() DifficultyParams
    +advance()
  }
  class WaveType {
    <<Enum>>
    NORMAL
    BOSS
    BONUS
  }
  class DifficultyParams {
    +enemy_speed : float
    +enemy_bullet_speed : float
    +dive_probability : float
  }
  class Difficulty {
    <<Enum>>
    EASY
    NORMAL
    HARD
  }
  class DifficultyConfig {
    +starting_lives : int
    +dive_freq_multiplier : float
    +enemy_bullet_speed_multiplier : float
    +tractor_probability_multiplier : float
  }
  WaveController --> WaveType : current_type
  WaveController --> DifficultyParams : current_params
  Difficulty --> DifficultyConfig
```

#### Engine + entities composition

`PlayScene` aggregates the player, enemy formation, bullet pools, capture manager, wave controller, and scoring.

```mermaid
classDiagram
  direction TB
  class PlayScene {
    +player : Player
    +players : Group
    +enemies : Group
    +player_bullets : Group
    +enemy_bullets : Group
    +tractor_beams : Group
    +captured_animations : Group
    +rescuing_ships : Group
    +explosions : Group
    +capture_mgr : CaptureManager
    +wave_controller : WaveController
    +scoring : Scoring | None
  }
  class Player {
    +pos
    +rect
    +dual_offset : int
    +is_left_half : bool
    +is_right_half : bool
    +update(dt, inp, bullets, on_shot)
  }
  class PlayerBullet
  class EnemyBullet { +velocity }
  class TractorBeam {
    +boss
    +lifetime : float
    +expired : bool
    +contains(point) bool
  }
  class CapturedAnimation { +SPEED : float }
  class RescuingShip
  class Explosion { +frames }
  class Scoring {
    +score : int
    +lives : int
    +wave : int
    +shots_fired : int
    +hits : int
    +enemies_killed : int
    +add_kill(kind)
    +add_shot()
    +accuracy() float
  }
  class InputState {
    +left, right : bool
    +fire, fire_pressed : bool
    +pause_pressed : bool
    +quit_pressed : bool
  }
  class InputReader {
    +state : InputState
    +begin_frame(events)
  }
  Player --* PlayScene : player
  PlayScene --o Scoring : scoring
  InputState --* InputReader : state
```

<details>
<summary>Show full single-diagram class diagram (wide)</summary>

```mermaid
classDiagram
  class BeeEnemy {
    score_kind : str
    sprite_name : str
  }
  class BonusScene {
    difficulty
    enemies
    explosions
    player
    player_bullets
    players
    playfield : NoneType
    scoring
    draw(surface) None
    update(dt, inp) None
  }
  class BossEnemy {
    score_kind : str
    sprite_name : str
  }
  class ButterflyEnemy {
    score_kind : str
    sprite_name : str
  }
  class CaptureManager {
    active_tractor_boss_id : int | None
    state
    begin_beam(boss_id) None
    can_start_tractor(boss_id) bool
    on_beam_ended() None
    on_captor_destroyed() None
    on_captured(boss_id, lives_after) None
    on_dual_lost() None
    on_rescue_complete() None
    on_rescue_eligible_kill() bool
    update_awaiting_rescue(dt) bool
    update_beam(dt, in_beam) bool
  }
  class CaptureMode { name }
  class CaptureState {
    beam_grace : float
    captor_boss_id : int | None
    mode
    rescue_timer : float
  }
  class CapturedAnimation {
    SPEED : float
    boss
    image
    pos
    rect
    update(dt) None
  }
  class Difficulty { name }
  class DifficultyConfig {
    dive_freq_multiplier : float
    enemy_bullet_speed_multiplier : float
    starting_lives : int
    tractor_probability_multiplier : float
  }
  class DifficultyParams {
    dive_probability : float
    enemy_bullet_speed : float
    enemy_speed : float
  }
  class Enemy {
    captured_ship : pygame.Surface | None
    col : int
    image
    pos
    rect
    row : int
    score_kind : str
    sprite_name : str
    state : EnemyState
    attach_captured_ship(ship_surface) None
    enter_tractor_align(player_pos) None
    is_in_formation() bool
    maybe_fire(target, speed_multiplier) EnemyBullet | None
    start_dive(player_pos, seed) None
    update(dt) None
  }
  class EnemyBullet {
    image
    pos
    rect
    velocity
    update(dt) None
  }
  class EnemyState { name }
  class Explosion {
    frames
    image
    rect
    update(dt) None
  }
  class GameOverScene {
    is_new_high
    scoring
    draw(surface) None
    update(dt, inp) None
  }
  class InputReader {
    state
    begin_frame(events) None
  }
  class InputState {
    fire : bool
    fire_pressed : bool
    left : bool
    pause_pressed : bool
    quit_pressed : bool
    right : bool
  }
  class PlayScene {
    capture_mgr
    captured_animations
    difficulty
    enemies
    enemy_bullets
    explosions
    player
    player_bullets
    players
    rescuing_ships
    scoring : Scoring | None
    tractor_beams
    wave_controller
    draw(surface) None
    on_enter() None
    update(dt, inp) None
  }
  class Player {
    dual_offset : int
    image
    is_left_half : bool
    is_right_half : bool
    pos
    rect
    update(dt, inp, bullets, on_shot) None
  }
  class PlayerBullet {
    image
    pos
    rect
    update(dt) None
  }
  class RescuingShip {
    image
    pos
    rect
    update(dt) None
  }
  class Scene {
    manager : SceneManager | None
    draw(surface)* None
    handle_event(event)* None
    on_enter()* None
    on_exit()* None
    update(dt, inp)* None
  }
  class SceneManager {
    current : Scene | None
    draw(surface) None
    handle_event(event) None
    pop() None
    push(scene) None
    replace(scene) None
    update(dt, inp) None
  }
  class Scoring {
    enemies_killed : int
    hits : int
    lives : int
    score : int
    shots_fired : int
    wave : int
    accuracy() float
    add_kill(kind) None
    add_shot() None
    gain_life() None
    lose_life() None
  }
  class TitleScene {
    selected_difficulty : Difficulty
    draw(surface) None
    on_enter() None
    on_exit() None
    update(dt, inp) None
  }
  class TractorBeam {
    boss
    expired : bool
    lifetime : float
    rect
    contains(point) bool
    draw(surface) None
    update(dt) None
  }
  class TransitionScene {
    text : str
    draw(surface) None
    update(dt, inp) None
  }
  class WaveController {
    current_wave : int
    advance() None
    current_params() DifficultyParams
    current_type() WaveType
  }
  class WaveType { name }
  BeeEnemy --|> Enemy
  BossEnemy --|> Enemy
  ButterflyEnemy --|> Enemy
  BonusScene --|> Scene
  GameOverScene --|> Scene
  PlayScene --|> Scene
  TitleScene --|> Scene
  TransitionScene --|> Scene
  InputState --* InputReader : state
  Player --* BonusScene : player
  Player --* PlayScene : player
  CaptureManager --* PlayScene : capture_mgr
  CaptureState --* CaptureManager : state
  WaveController --* PlayScene : wave_controller
  Difficulty --o BonusScene : difficulty
  Difficulty --o PlayScene : difficulty
  Scoring --o BonusScene : scoring
  Scoring --o GameOverScene : scoring
```

</details>

### Module dependency graph

27 modules, 69 imports — no cycles. Source: [docs/uml/packages_Galaga.mmd](docs/uml/packages_Galaga.mmd).

```mermaid
classDiagram
  class engine
  class assets
  class audio
  class input
  class scene
  class bullet
  class captured_animation
  class enemy
  class explosion
  class player
  class rescuing_ship
  class tractor_beam
  class capture
  class difficulty
  class dive
  class formation
  class hud
  class scoring
  class wave
  class bonus
  class gameover
  class play
  class title
  class transitions
  audio --> assets
  bullet --> assets
  captured_animation --> assets
  enemy --> assets
  enemy --> bullet
  explosion --> assets
  player --> assets
  player --> audio
  player --> input
  player --> bullet
  rescuing_ship --> assets
  hud --> assets
  hud --> scoring
  bonus --> audio
  bonus --> input
  bonus --> scene
  bonus --> enemy
  bonus --> explosion
  bonus --> player
  bonus --> difficulty
  bonus --> scoring
  bonus --> play
  bonus --> transitions
  gameover --> audio
  gameover --> input
  gameover --> scene
  gameover --> scoring
  gameover --> title
  play --> audio
  play --> input
  play --> scene
  play --> captured_animation
  play --> enemy
  play --> explosion
  play --> player
  play --> rescuing_ship
  play --> tractor_beam
  play --> capture
  play --> difficulty
  play --> scoring
  play --> wave
  play --> bonus
  play --> gameover
  play --> transitions
  title --> audio
  title --> input
  title --> scene
  title --> difficulty
  title --> scoring
  title --> play
  title --> transitions
  transitions --> input
  transitions --> scene
  scene ..> input
```

### Regenerating diagrams

```powershell
pip install pylint                       # provides pyreverse
# Graphviz only needed for png/svg output:
#   winget install Graphviz.Graphviz
pyreverse -o mmd -p Galaga -d docs/uml engine entities game scenes
pyreverse -o puml -p Galaga -d docs/uml engine entities game scenes
pyreverse -o png  -p Galaga -d docs/uml engine entities game scenes   # needs Graphviz
pyreverse -o svg  -p Galaga -d docs/uml engine entities game scenes   # needs Graphviz
```

## License

Personal project. Original Galaga is (c) Bandai Namco; this is a non-distributed clone for educational purposes only.
