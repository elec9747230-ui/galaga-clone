# Galaga 클론 구현 계획

> **에이전트 작업자용:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (권장) 또는 superpowers:executing-plans를 사용해 task 단위로 구현. 진행 추적은 체크박스(`- [ ]`) 표기.

**목표:** Python + Pygame으로 1인용 Galaga 클론 구현. "Classic Core" 범위 (포메이션 진입, 다이브 공격, 일반/보스/보너스 웨이브 사이클), 모든 에셋은 코드로 생성.

**아키텍처:** 다중 모듈 구조 — `engine/` (assets, audio, input, scene 관리), `entities/` (Sprite 서브클래스), `game/` (순수 로직: scoring, wave, formation, dive, hud), `scenes/` (title, play, bonus, gameover, transitions), `tools/` (1회성 에셋 생성기). Pygame이 렌더링, Pillow가 스프라이트 생성, NumPy가 chiptune+SFX 합성. `game/scoring.py`와 `game/wave.py`는 단위 테스트 가능하도록 pygame import 없음.

**기술 스택:** Python 3.11+, Pygame, Pillow, NumPy, pytest, ruff. GitHub Actions CI는 `ubuntu-latest`.

**스펙:** [docs/superpowers/specs/2026-05-02-galaga-clone-design.ko.md](../specs/2026-05-02-galaga-clone-design.ko.md)

---

## 파일 구조 (Task 진입 전 확정)

```
galaga-clone/
├── main.py                       # 진입점, pygame 초기화, 메인 루프
├── settings.py                   # 상수 (해상도, FPS, 색, 점수, 키 매핑)
├── pyproject.toml                # 의존성 + ruff 설정
├── README.md
├── .gitignore                    # (이미 존재)
├── .github/workflows/ci.yml      # pytest + ruff
│
├── tools/
│   ├── __init__.py
│   ├── generate_sprites.py       # Pillow → PNG
│   └── generate_audio.py         # NumPy → WAV (SFX + chiptune 음악)
│
├── engine/
│   ├── __init__.py
│   ├── assets.py                 # assets/의 PNG/WAV 지연 로드 + 캐시
│   ├── audio.py                  # SFX + BGM 재생 (mixer 실패 시 silent no-op)
│   ├── input.py                  # InputState dataclass
│   └── scene.py                  # Scene 베이스 + SceneManager
│
├── entities/
│   ├── __init__.py
│   ├── player.py                 # 플레이어 함선 sprite
│   ├── bullet.py                 # PlayerBullet, EnemyBullet
│   ├── enemy.py                  # Enemy + Bee/Butterfly/Boss + 상태머신
│   └── explosion.py              # 애니메이션 폭발 sprite
│
├── game/
│   ├── __init__.py
│   ├── scoring.py                # 순수: Scoring dataclass + 하이스코어 I/O
│   ├── wave.py                   # 순수: WaveType, wave_type_for, difficulty_params, WaveController
│   ├── formation.py              # Vector2만 사용: slot_position, entry_path
│   ├── dive.py                   # Vector2만 사용: dive_path
│   └── hud.py                    # 좌/우 사이드 패널 렌더링
│
├── scenes/
│   ├── __init__.py
│   ├── title.py
│   ├── play.py                   # 메인 게임플레이
│   ├── bonus.py                  # Challenging 스테이지 (적 발사 없음)
│   ├── gameover.py
│   └── transitions.py            # "STAGE N START" / "CHALLENGING STAGE" 오버레이
│
├── data/                         # 런타임 생성, gitignore
│   └── highscore.json
│
├── assets/                       # tools/가 생성, gitignore
│   ├── sprites/
│   └── audio/
│
└── tests/
    ├── __init__.py
    ├── test_scoring.py
    ├── test_wave.py
    ├── test_formation.py
    └── test_dive.py
```

---

## 단계 (Phases)

- **Phase 1:** 프로젝트 스켈레톤 (deps, settings, CI) — Task 1–3
- **Phase 2:** TDD 순수 로직 모듈 (game/scoring, wave, formation, dive) — Task 4–7
- **Phase 3:** 에셋 생성 도구 (스프라이트 + 오디오) — Task 8–9
- **Phase 4:** 엔진 레이어 (scene, input, assets, audio) — Task 10–13
- **Phase 5:** 최소 플레이 가능 루프 (player + bullets + main + play scene shell) — Task 14–16
- **Phase 6:** 적 (포메이션 진입, 형태 흔들림, 다이브 공격) — Task 17–19
- **Phase 7:** 웨이브 진행 + HUD + scoring 통합 — Task 20–22
- **Phase 8:** 보너스 스테이지 + 보스 웨이브 + 씬 (title, transitions, gameover) — Task 23–26
- **Phase 9:** 오디오 통합 + 최종 다듬기 — Task 27–28

총 28개 task. 각 task는 커밋으로 끝남.

---

## Phase 1: 프로젝트 스켈레톤

### Task 1: 의존성 + ruff 설정이 담긴 `pyproject.toml` 생성

**파일:**
- 신규: `pyproject.toml`

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[project]
name = "galaga-clone"
version = "0.1.0"
description = "Galaga clone in Python + Pygame (Classic Core)"
requires-python = ">=3.11"
dependencies = [
    "pygame>=2.5.0",
    "numpy>=1.26.0",
    "pillow>=10.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
ignore = ["E501"]  # line length warnings handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: venv 생성 + 의존성 설치**

```powershell
cd c:\Users\elec9\galaga-clone
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

기대: `Successfully installed pygame-... numpy-... pillow-... pytest-... ruff-...`

- [ ] **Step 3: ruff와 pytest 실행 확인**

```powershell
ruff --version
pytest --version
```

기대: 버전 번호 출력, 에러 없음.

- [ ] **Step 4: 커밋**

```powershell
git add pyproject.toml
git commit -m "chore: add pyproject.toml with deps and ruff config"
```

---

### Task 2: 모든 상수가 담긴 `settings.py` 생성

**파일:**
- 신규: `settings.py`

- [ ] **Step 1: `settings.py` 작성**

```python
"""Game-wide constants. No pygame import to keep importable from anywhere."""

# Window
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

# Playfield (centered in window)
PLAYFIELD_WIDTH = 540
PLAYFIELD_HEIGHT = 720
PLAYFIELD_OFFSET_X = (WINDOW_WIDTH - PLAYFIELD_WIDTH) // 2  # 370
PLAYFIELD_OFFSET_Y = 0

# Side panels
SIDE_PANEL_WIDTH = PLAYFIELD_OFFSET_X  # 370

# Colors (RGB)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 40, 40)
COLOR_YELLOW = (240, 220, 60)
COLOR_BLUE = (60, 120, 240)
COLOR_CYAN = (80, 220, 220)
COLOR_GREEN = (80, 220, 80)
COLOR_HUD_DIM = (120, 120, 140)
COLOR_STAR = (180, 180, 200)

# Player
PLAYER_SPEED = 280  # pixels per second
PLAYER_BULLET_SPEED = 600
MAX_PLAYER_BULLETS = 2
PLAYER_RESPAWN_DELAY = 0.5  # seconds
PLAYER_START_LIVES = 3

# Enemy
ENEMY_BASE_SPEED = 80
ENEMY_BULLET_SPEED = 220
FORMATION_ROWS = 5
FORMATION_COLS = 8
FORMATION_SLOT_WIDTH = 50
FORMATION_SLOT_HEIGHT = 45
FORMATION_TOP_MARGIN = 80

# Scoring
SCORE_NORMAL_KILL = 50
SCORE_DIVE_KILL = 100
SCORE_BOSS_KILL = 150
SCORE_BONUS_PER_KILL = 200
SCORE_BONUS_PERFECT = 10000
LIFE_BONUS_PERFECT = 1

# Wave cycle (1-4 normal, 5 boss, 6 bonus)
WAVE_CYCLE_LENGTH = 6

# Bonus stage
BONUS_STAGE_DURATION = 30.0  # seconds

# Files
HIGHSCORE_PATH = "data/highscore.json"
ASSETS_SPRITES_DIR = "assets/sprites"
ASSETS_AUDIO_DIR = "assets/audio"

# Key bindings (pygame key constants resolved at use-site to keep this file pygame-free)
KEY_LEFT = ("LEFT", "a")
KEY_RIGHT = ("RIGHT", "d")
KEY_FIRE = ("SPACE",)
KEY_PAUSE = ("p",)
KEY_QUIT = ("ESCAPE",)
```

- [ ] **Step 2: import 동작 확인**

```powershell
python -c "import settings; print(settings.WINDOW_WIDTH, settings.PLAYFIELD_OFFSET_X)"
```

기대: `1280 370`

- [ ] **Step 3: 커밋**

```powershell
git add settings.py
git commit -m "feat: add settings.py with all game constants"
```

---

### Task 3: GitHub Actions CI 워크플로우 추가

**파일:**
- 신규: `.github/workflows/ci.yml`

- [ ] **Step 1: CI 워크플로우 작성**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -v
```

- [ ] **Step 2: 커밋 후 push로 CI 트리거**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for ruff + pytest"
git push
```

- [ ] **Step 3: CI 실행 확인**

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --limit 3
```

기대: 최근 실행이 표시됨 (`in_progress` 또는 `completed`). 이 시점에는 테스트나 Python 코드가 없어서 `lint`와 `test` 잡 모두 실패함 — 정상. 다음 task에서 채워짐. Task 4가 들어가면 재실행 시 성공.

---

## Phase 2: 순수 로직 모듈 (TDD)

### Task 4: `game/scoring.py` — 점수, 라이프, 명중률, 하이스코어 I/O

**파일:**
- 신규: `game/__init__.py` (빈 파일)
- 신규: `game/scoring.py`
- 신규: `tests/__init__.py` (빈 파일)
- 신규: `tests/test_scoring.py`

- [ ] **Step 1: 빈 패키지 파일 생성**

```powershell
New-Item game/__init__.py -ItemType File -Force
New-Item tests/__init__.py -ItemType File -Force
```

- [ ] **Step 2: 실패하는 테스트 먼저 작성**

`tests/test_scoring.py`:
```python
import json
from pathlib import Path

import pytest

from game.scoring import Scoring, load_highscore, save_highscore


def test_scoring_initial_state():
    s = Scoring()
    assert s.score == 0
    assert s.lives == 3
    assert s.wave == 1
    assert s.shots_fired == 0
    assert s.hits == 0
    assert s.enemies_killed == 0


def test_add_kill_normal():
    s = Scoring()
    s.add_kill("normal")
    assert s.score == 50
    assert s.enemies_killed == 1


def test_add_kill_dive():
    s = Scoring()
    s.add_kill("dive")
    assert s.score == 100


def test_add_kill_boss():
    s = Scoring()
    s.add_kill("boss")
    assert s.score == 150


def test_add_kill_bonus():
    s = Scoring()
    s.add_kill("bonus")
    assert s.score == 200


def test_add_kill_unknown_type_raises():
    s = Scoring()
    with pytest.raises(ValueError):
        s.add_kill("alien_overlord")


def test_lose_life_decrements():
    s = Scoring(lives=3)
    s.lose_life()
    assert s.lives == 2


def test_lose_life_clamps_at_zero():
    s = Scoring(lives=0)
    s.lose_life()
    assert s.lives == 0


def test_gain_life_increments():
    s = Scoring(lives=3)
    s.gain_life()
    assert s.lives == 4


def test_add_shot_increments():
    s = Scoring()
    s.add_shot()
    s.add_shot()
    assert s.shots_fired == 2


def test_accuracy_with_zero_shots():
    s = Scoring()
    assert s.accuracy() == 0.0


def test_accuracy_normal():
    s = Scoring(shots_fired=10, hits=3)
    assert s.accuracy() == pytest.approx(0.30)


def test_save_and_load_highscore(tmp_path):
    path = tmp_path / "hs.json"
    save_highscore(12345, path)
    assert load_highscore(path) == 12345


def test_load_highscore_missing_file_returns_zero(tmp_path):
    assert load_highscore(tmp_path / "nope.json") == 0


def test_load_highscore_corrupt_file_returns_zero(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json")
    assert load_highscore(path) == 0
```

- [ ] **Step 3: 테스트 실행, 실패 확인**

```powershell
pytest tests/test_scoring.py -v
```

기대: 모든 테스트가 `ModuleNotFoundError: No module named 'game.scoring'`로 실패.

- [ ] **Step 4: 구현 작성**

`game/scoring.py`:
```python
"""Pure scoring/lives logic. No pygame import."""

import json
from dataclasses import dataclass, field
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
```

- [ ] **Step 5: 테스트 실행, 통과 확인**

```powershell
pytest tests/test_scoring.py -v
```

기대: ~14개 테스트 모두 통과.

- [ ] **Step 6: ruff format + check 실행**

```powershell
ruff format .
ruff check . --fix
```

기대: clean.

- [ ] **Step 7: 커밋**

```powershell
git add game/ tests/
git commit -m "feat(scoring): pure scoring/lives/highscore module with tests"
```

---

### Task 5: `game/wave.py` — 웨이브 타입, 사이클, 난이도, 컨트롤러

**파일:**
- 신규: `game/wave.py`
- 신규: `tests/test_wave.py`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

`tests/test_wave.py`:
```python
import pytest

from game.wave import (
    DifficultyParams,
    WaveController,
    WaveType,
    difficulty_params,
    wave_type_for,
)


@pytest.mark.parametrize(
    "wave,expected",
    [
        (1, WaveType.NORMAL),
        (2, WaveType.NORMAL),
        (3, WaveType.NORMAL),
        (4, WaveType.NORMAL),
        (5, WaveType.BOSS),
        (6, WaveType.BONUS),
        (7, WaveType.NORMAL),
        (10, WaveType.NORMAL),
        (11, WaveType.BOSS),
        (12, WaveType.BONUS),
        (13, WaveType.NORMAL),
        (17, WaveType.BOSS),
        (18, WaveType.BONUS),
    ],
)
def test_wave_type_cycle(wave, expected):
    assert wave_type_for(wave) == expected


def test_difficulty_params_returns_dataclass():
    p = difficulty_params(1)
    assert isinstance(p, DifficultyParams)
    assert p.enemy_speed > 0
    assert 0 <= p.dive_probability <= 1
    assert p.enemy_bullet_speed > 0


def test_difficulty_increases_monotonically():
    params = [difficulty_params(w) for w in range(1, 21)]
    speeds = [p.enemy_speed for p in params]
    dives = [p.dive_probability for p in params]
    bullets = [p.enemy_bullet_speed for p in params]
    # Each metric is non-decreasing
    assert all(speeds[i] <= speeds[i + 1] for i in range(len(speeds) - 1))
    assert all(dives[i] <= dives[i + 1] for i in range(len(dives) - 1))
    assert all(bullets[i] <= bullets[i + 1] for i in range(len(bullets) - 1))


def test_dive_probability_capped():
    p = difficulty_params(1000)
    assert p.dive_probability <= 1.0


def test_wave_controller_starts_at_one():
    c = WaveController()
    assert c.current_wave == 1
    assert c.current_type() == WaveType.NORMAL


def test_wave_controller_advance():
    c = WaveController()
    c.advance()
    assert c.current_wave == 2


def test_wave_controller_reaches_boss_then_bonus():
    c = WaveController()
    for _ in range(4):
        c.advance()
    assert c.current_wave == 5
    assert c.current_type() == WaveType.BOSS
    c.advance()
    assert c.current_type() == WaveType.BONUS
```

- [ ] **Step 2: 테스트 실행, 실패 확인**

```powershell
pytest tests/test_wave.py -v
```

기대: `game.wave` ImportError.

- [ ] **Step 3: 구현 작성**

`game/wave.py`:
```python
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
```

- [ ] **Step 4: 테스트 실행, 통과 확인**

```powershell
pytest tests/test_wave.py -v
```

기대: 모두 통과.

- [ ] **Step 5: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add game/wave.py tests/test_wave.py
git commit -m "feat(wave): wave type cycle, difficulty params, WaveController"
```

---

### Task 6: `game/formation.py` — 슬롯 좌표 + 진입 경로

**파일:**
- 신규: `game/formation.py`
- 신규: `tests/test_formation.py`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

`tests/test_formation.py`:
```python
import pygame

from game.formation import entry_path, slot_position
from settings import (
    FORMATION_COLS,
    FORMATION_ROWS,
    PLAYFIELD_HEIGHT,
    PLAYFIELD_WIDTH,
)


def test_slot_positions_inside_playfield():
    for row in range(FORMATION_ROWS):
        for col in range(FORMATION_COLS):
            pos = slot_position(row, col, oscillation_phase=0.0)
            assert 0 < pos.x < PLAYFIELD_WIDTH
            assert 0 < pos.y < PLAYFIELD_HEIGHT / 2  # formation in upper half


def test_slot_positions_centered_horizontally():
    """Leftmost and rightmost columns equidistant from playfield edges."""
    leftmost = slot_position(0, 0, 0.0).x
    rightmost = slot_position(0, FORMATION_COLS - 1, 0.0).x
    left_margin = leftmost
    right_margin = PLAYFIELD_WIDTH - rightmost
    assert abs(left_margin - right_margin) < 1.0


def test_slot_oscillation_changes_x():
    pos1 = slot_position(0, 0, 0.0)
    pos2 = slot_position(0, 0, 1.0)  # different phase
    assert pos1.x != pos2.x


def test_entry_path_starts_offscreen():
    """Entry begins offscreen (above or beside playfield)."""
    path = entry_path(row=0, col=0)
    assert len(path) > 5
    start = path[0]
    assert start.y < 0 or start.x < 0 or start.x > PLAYFIELD_WIDTH


def test_entry_path_ends_at_slot():
    """Last waypoint matches the formation slot."""
    target = slot_position(2, 3, 0.0)
    path = entry_path(row=2, col=3)
    end = path[-1]
    assert (end - target).length() < 1.0


def test_entry_path_smooth():
    """Adjacent waypoints don't jump too far."""
    path = entry_path(row=0, col=0)
    for i in range(len(path) - 1):
        d = (path[i + 1] - path[i]).length()
        assert d < 100  # no huge jumps
```

- [ ] **Step 2: pygame init용 conftest 추가**

`tests/conftest.py`:
```python
import pygame


def pytest_configure(config):
    pygame.init()
```

- [ ] **Step 3: 테스트 실행, 실패 확인**

```powershell
pytest tests/test_formation.py -v
```

기대: ImportError.

- [ ] **Step 4: 구현 작성**

`game/formation.py`:
```python
"""Formation slot positions and entry paths. Uses pygame.Vector2 only."""

import math

from pygame import Vector2

import settings

_FORMATION_TOP = settings.FORMATION_TOP_MARGIN
_TOTAL_W = settings.FORMATION_COLS * settings.FORMATION_SLOT_WIDTH
_LEFT_MARGIN = (settings.PLAYFIELD_WIDTH - _TOTAL_W) / 2 + settings.FORMATION_SLOT_WIDTH / 2
_OSCILLATION_AMPLITUDE = 14.0  # pixels
_OSCILLATION_PERIOD = 4.0  # seconds (caller passes elapsed-time-derived phase)


def slot_position(row: int, col: int, oscillation_phase: float) -> Vector2:
    """Return formation slot position in playfield-local coords.

    oscillation_phase: typically `time * 2*pi / OSCILLATION_PERIOD` from caller.
    """
    base_x = _LEFT_MARGIN + col * settings.FORMATION_SLOT_WIDTH
    base_y = _FORMATION_TOP + row * settings.FORMATION_SLOT_HEIGHT
    offset_x = _OSCILLATION_AMPLITUDE * math.sin(oscillation_phase)
    return Vector2(base_x + offset_x, base_y)


def entry_path(row: int, col: int, samples: int = 60) -> list[Vector2]:
    """Bezier path from offscreen to slot. Different sides per column."""
    target = slot_position(row, col, 0.0)
    # Alternate entry side based on column for visual variety
    if col < settings.FORMATION_COLS / 2:
        start = Vector2(-30, -30)
        ctrl1 = Vector2(60, settings.PLAYFIELD_HEIGHT * 0.4)
        ctrl2 = Vector2(target.x - 80, target.y + 100)
    else:
        start = Vector2(settings.PLAYFIELD_WIDTH + 30, -30)
        ctrl1 = Vector2(settings.PLAYFIELD_WIDTH - 60, settings.PLAYFIELD_HEIGHT * 0.4)
        ctrl2 = Vector2(target.x + 80, target.y + 100)
    return [_cubic_bezier(start, ctrl1, ctrl2, target, t / samples) for t in range(samples + 1)]


def _cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
    u = 1 - t
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
```

- [ ] **Step 5: 테스트 실행, 통과 확인**

```powershell
pytest tests/test_formation.py -v
```

- [ ] **Step 6: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add game/formation.py tests/test_formation.py tests/conftest.py
git commit -m "feat(formation): slot positions + Bezier entry paths"
```

---

### Task 7: `game/dive.py` — 다이브 공격 곡선

**파일:**
- 신규: `game/dive.py`
- 신규: `tests/test_dive.py`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

`tests/test_dive.py`:
```python
from pygame import Vector2

from game.dive import dive_path
from settings import PLAYFIELD_HEIGHT, PLAYFIELD_WIDTH


def test_path_starts_at_enemy():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    assert (path[0] - enemy).length() < 1.0


def test_path_exits_below_playfield():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    assert path[-1].y >= PLAYFIELD_HEIGHT


def test_path_smooth():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    for i in range(len(path) - 1):
        d = (path[i + 1] - path[i]).length()
        assert d < 60.0  # no big jumps


def test_path_seed_changes_path():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    p1 = dive_path(enemy, player, seed=1)
    p2 = dive_path(enemy, player, seed=2)
    # at least one waypoint differs
    differs = any((p1[i] - p2[i]).length() > 1.0 for i in range(min(len(p1), len(p2))))
    assert differs


def test_path_stays_within_horizontal_bounds_mostly():
    enemy = Vector2(100, 100)
    player = Vector2(270, 700)
    path = dive_path(enemy, player, seed=1)
    # allow small overshoot at edges due to sine wobble
    for p in path:
        assert -50 < p.x < PLAYFIELD_WIDTH + 50
```

- [ ] **Step 2: 테스트 실행, 실패 확인**

```powershell
pytest tests/test_dive.py -v
```

- [ ] **Step 3: 구현 작성**

`game/dive.py`:
```python
"""Dive attack path generation. Uses pygame.Vector2 only."""

import math
import random

from pygame import Vector2

import settings


def dive_path(
    enemy_pos: Vector2,
    player_pos: Vector2,
    seed: int,
    samples: int = 80,
) -> list[Vector2]:
    """Curve from enemy_pos sweeping toward player area then offscreen below.

    Combines cubic Bezier with a sine wobble for organic feel. `seed` chooses
    swing direction and amplitude.
    """
    rng = random.Random(seed)
    swing_dir = rng.choice([-1, 1])
    swing_x = swing_dir * rng.uniform(80, 160)
    wobble_amp = rng.uniform(8, 22)
    wobble_freq = rng.uniform(2.0, 3.5)

    midpoint_y = (enemy_pos.y + player_pos.y) / 2
    ctrl1 = Vector2(enemy_pos.x + swing_x, midpoint_y - 40)
    ctrl2 = Vector2(player_pos.x - swing_x * 0.5, player_pos.y - 40)
    end = Vector2(player_pos.x + swing_x, settings.PLAYFIELD_HEIGHT + 30)

    path = []
    for i in range(samples + 1):
        t = i / samples
        p = _cubic_bezier(enemy_pos, ctrl1, ctrl2, end, t)
        # Apply tangent-perpendicular wobble (just along x for simplicity)
        wobble = wobble_amp * math.sin(wobble_freq * math.pi * t)
        path.append(Vector2(p.x + wobble, p.y))
    return path


def _cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
    u = 1 - t
    return (u * u * u) * p0 + (3 * u * u * t) * p1 + (3 * u * t * t) * p2 + (t * t * t) * p3
```

- [ ] **Step 4: 테스트 실행, 통과 확인**

- [ ] **Step 5: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add game/dive.py tests/test_dive.py
git commit -m "feat(dive): dive attack curve generation with wobble"
```

---

## Phase 3: 에셋 생성 도구

### Task 8: `tools/generate_sprites.py` — 코드로 픽셀 스프라이트 생성

**파일:**
- 신규: `tools/__init__.py` (빈 파일)
- 신규: `tools/generate_sprites.py`

- [ ] **Step 1: 빈 패키지 init 생성**

```powershell
New-Item tools/__init__.py -ItemType File -Force
```

- [ ] **Step 2: 생성기 작성**

`tools/generate_sprites.py`:
```python
"""Generate placeholder pixel-art PNG sprites with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

import settings

OUT_DIR = Path(settings.ASSETS_SPRITES_DIR)


def _make_image(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img: Image.Image, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / f"{name}.png")


def generate_player() -> None:
    img, d = _make_image((32, 24))
    white = (255, 255, 255, 255)
    red = (220, 40, 40, 255)
    blue = (60, 120, 240, 255)
    # ship body (triangle-ish)
    d.rectangle((14, 4, 17, 20), fill=white)
    d.rectangle((10, 8, 21, 20), fill=white)
    d.rectangle((6, 12, 25, 20), fill=white)
    d.rectangle((2, 18, 29, 22), fill=white)
    # red trim
    d.rectangle((13, 16, 18, 19), fill=red)
    # blue cockpit
    d.rectangle((15, 6, 16, 8), fill=blue)
    _save(img, "player")


def generate_bee() -> None:
    img, d = _make_image((28, 22))
    yellow = (240, 220, 60, 255)
    blue = (60, 120, 240, 255)
    d.rectangle((10, 4, 17, 18), fill=yellow)  # body
    d.rectangle((4, 6, 9, 14), fill=blue)  # left wing
    d.rectangle((18, 6, 23, 14), fill=blue)  # right wing
    d.rectangle((12, 0, 15, 3), fill=yellow)  # antenna stub
    _save(img, "enemy_bee")


def generate_butterfly() -> None:
    img, d = _make_image((28, 22))
    red = (220, 40, 40, 255)
    blue = (60, 120, 240, 255)
    yellow = (240, 220, 60, 255)
    d.rectangle((10, 4, 17, 18), fill=red)
    d.rectangle((2, 4, 9, 16), fill=blue)
    d.rectangle((18, 4, 25, 16), fill=blue)
    d.rectangle((4, 6, 7, 9), fill=yellow)
    d.rectangle((20, 6, 23, 9), fill=yellow)
    _save(img, "enemy_butterfly")


def generate_boss() -> None:
    img, d = _make_image((32, 26))
    green = (80, 220, 80, 255)
    cyan = (80, 220, 220, 255)
    d.rectangle((10, 4, 21, 20), fill=green)
    d.rectangle((4, 8, 9, 18), fill=cyan)
    d.rectangle((22, 8, 27, 18), fill=cyan)
    d.rectangle((12, 0, 19, 3), fill=green)
    d.rectangle((14, 8, 17, 11), fill=(0, 0, 0, 255))  # eye
    _save(img, "enemy_boss")


def generate_player_bullet() -> None:
    img, d = _make_image((4, 12))
    d.rectangle((1, 0, 2, 11), fill=(255, 255, 255, 255))
    _save(img, "player_bullet")


def generate_enemy_bullet() -> None:
    img, d = _make_image((4, 12))
    d.rectangle((1, 0, 2, 11), fill=(220, 80, 220, 255))
    _save(img, "enemy_bullet")


def generate_explosion_frames() -> None:
    """4-frame expanding explosion."""
    palette = [
        (255, 240, 80, 255),
        (255, 160, 40, 255),
        (220, 60, 40, 255),
        (120, 30, 30, 255),
    ]
    for i in range(4):
        img, d = _make_image((24, 24))
        radius = 4 + i * 4
        c = palette[i]
        # crude pixel circle
        cx, cy = 12, 12
        for y in range(24):
            for x in range(24):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius * radius:
                    img.putpixel((x, y), c)
        _save(img, f"explosion_{i}")


def generate_logo() -> None:
    """Simple text-style 'GALAGA' logo placeholder."""
    img, d = _make_image((220, 60))
    yellow = (240, 220, 60, 255)
    # 6 letter blocks; very rough "GALAGA" without true font shapes
    d.rectangle((4, 12, 200, 48), outline=yellow, width=3)
    d.text((48, 22), "GALAGA", fill=yellow)
    _save(img, "logo")


def main() -> None:
    generate_player()
    generate_bee()
    generate_butterfly()
    generate_boss()
    generate_player_bullet()
    generate_enemy_bullet()
    generate_explosion_frames()
    generate_logo()
    print(f"Sprites written to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 생성기 실행**

```powershell
python -m tools.generate_sprites
```

기대: `Sprites written to .../assets/sprites`. `assets/sprites/`에 11개 PNG 확인 (player, bee, butterfly, boss, 총알 2개, 폭발 4프레임, logo).

- [ ] **Step 4: 시각 확인 (선택)**

PNG 중 하나를 이미지 뷰어로 열어 의도한 모양인지 가볍게 검토.

- [ ] **Step 5: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add tools/
git commit -m "feat(tools): sprite generator (player, enemies, bullets, explosion, logo)"
```

(주: `assets/`는 gitignore — 생성기 스크립트만 커밋.)

---

### Task 9: `tools/generate_audio.py` — SFX + chiptune 음악

**파일:**
- 신규: `tools/generate_audio.py`

- [ ] **Step 1: 생성기 작성**

`tools/generate_audio.py`:
```python
"""Generate WAV files: SFX + chiptune recreations of original Galaga melodies.

Personal/learning use only — original Galaga BGM melodies are Bandai Namco IP.
"""

import wave
from pathlib import Path

import numpy as np

import settings

OUT_DIR = Path(settings.ASSETS_AUDIO_DIR)
SAMPLE_RATE = 22050  # 22kHz, plenty for 8-bit style


# ---------- WAV writing ----------

def _write_wav(name: str, samples: np.ndarray) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(str(OUT_DIR / f"{name}.wav"), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm.tobytes())


# ---------- Waveform helpers ----------

def _square(freq: float, duration: float, duty: float = 0.5, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return np.where(phase < duty, volume, -volume)


def _triangle(freq: float, duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return (4 * np.abs(phase - 0.5) - 1) * volume


def _noise(duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    return (np.random.uniform(-1, 1, n) * volume).astype(np.float32)


def _sweep(f_start: float, f_end: float, duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    freqs = np.linspace(f_start, f_end, n)
    phases = np.cumsum(2 * np.pi * freqs / SAMPLE_RATE)
    return np.sign(np.sin(phases)) * volume


def _envelope(samples: np.ndarray, attack: float = 0.01, release: float = 0.05) -> np.ndarray:
    n = len(samples)
    a = int(SAMPLE_RATE * attack)
    r = int(SAMPLE_RATE * release)
    env = np.ones(n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return samples * env


def _silence(duration: float) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * duration))


# ---------- Note → frequency ----------

# Equal temperament; A4 = 440Hz
def _freq(note: str) -> float:
    """e.g. 'A4', 'C#5', 'Bb3'."""
    name = note[:-1]
    octave = int(note[-1])
    semitones = {"C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6,
                 "E": -5, "F": -4, "F#": -3, "Gb": -3, "G": -2, "G#": -1, "Ab": -1,
                 "A": 0, "A#": 1, "Bb": 1, "B": 2}
    n = semitones[name] + (octave - 4) * 12
    return 440.0 * (2 ** (n / 12))


def _melody(notes: list[tuple[str, float]], volume: float = 0.4) -> np.ndarray:
    """notes: list of (note_or_'rest', duration_seconds)."""
    parts = []
    for note, dur in notes:
        if note == "rest":
            parts.append(_silence(dur))
        else:
            wave_data = _square(_freq(note), dur, duty=0.5, volume=volume)
            parts.append(_envelope(wave_data, attack=0.005, release=0.03))
    return np.concatenate(parts)


# ---------- SFX ----------

def sfx_shoot() -> None:
    s = _sweep(880, 220, 0.08, volume=0.4)
    _write_wav("sfx_shoot", _envelope(s, attack=0.001, release=0.04))


def sfx_explode() -> None:
    n = _noise(0.25, volume=0.6)
    fade = np.linspace(1.0, 0.0, len(n)) ** 2
    _write_wav("sfx_explode", n * fade)


def sfx_player_hit() -> None:
    s = _sweep(440, 80, 0.4, volume=0.5)
    _write_wav("sfx_player_hit", _envelope(s, attack=0.005, release=0.1))


def sfx_extra_life() -> None:
    parts = [
        _envelope(_square(_freq("C5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("E5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("G5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("C6"), 0.18, volume=0.4)),
    ]
    _write_wav("sfx_extra_life", np.concatenate(parts))


def sfx_dive() -> None:
    s = _sweep(660, 220, 0.18, volume=0.35)
    _write_wav("sfx_dive", _envelope(s, attack=0.005, release=0.06))


# ---------- Music (chiptune recreations) ----------

def music_intro() -> None:
    """Galaga intro fanfare — short heroic phrase."""
    notes = [
        ("G4", 0.15), ("C5", 0.15), ("E5", 0.15), ("G5", 0.30),
        ("E5", 0.15), ("G5", 0.45),
        ("rest", 0.10),
        ("F5", 0.15), ("D5", 0.15), ("B4", 0.30),
        ("C5", 0.45),
    ]
    _write_wav("music_intro", _melody(notes))


def music_stage_start() -> None:
    """Short stage-start jingle."""
    notes = [
        ("E5", 0.12), ("G5", 0.12), ("C6", 0.24),
        ("rest", 0.06),
        ("E5", 0.12), ("G5", 0.12), ("C6", 0.36),
    ]
    _write_wav("music_stage_start", _melody(notes))


def music_challenging_stage() -> None:
    """Bonus stage music — playful bouncy loop (~4s)."""
    notes = [
        ("C5", 0.12), ("E5", 0.12), ("G5", 0.12), ("C6", 0.12),
        ("G5", 0.12), ("E5", 0.12), ("C5", 0.24),
        ("D5", 0.12), ("F5", 0.12), ("A5", 0.12), ("D6", 0.12),
        ("A5", 0.12), ("F5", 0.12), ("D5", 0.24),
        ("E5", 0.12), ("G5", 0.12), ("B5", 0.12), ("E6", 0.12),
        ("D6", 0.12), ("C6", 0.12), ("B5", 0.12), ("A5", 0.12),
        ("G5", 0.36),
    ]
    _write_wav("music_bonus", _melody(notes))


def music_game_over() -> None:
    notes = [
        ("C5", 0.20), ("B4", 0.20), ("A4", 0.20),
        ("G4", 0.20), ("F4", 0.20), ("E4", 0.20),
        ("D4", 0.20), ("C4", 0.60),
    ]
    _write_wav("music_game_over", _melody(notes))


def main() -> None:
    sfx_shoot()
    sfx_explode()
    sfx_player_hit()
    sfx_extra_life()
    sfx_dive()
    music_intro()
    music_stage_start()
    music_challenging_stage()
    music_game_over()
    print(f"Audio written to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 생성기 실행**

```powershell
python -m tools.generate_audio
```

기대: `assets/audio/`에 9개 WAV 생성 (5 SFX + 4 음악).

- [ ] **Step 3: 빠른 청취 (선택)**

`sfx_shoot.wav`와 `music_intro.wav`를 재생해서 무음/왜곡 없는지 확인.

- [ ] **Step 4: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add tools/generate_audio.py
git commit -m "feat(tools): SFX + chiptune music generator (NumPy)"
```

---

## Phase 4: 엔진 레이어

### Task 10: `engine/scene.py` — Scene 베이스 + SceneManager

**파일:**
- 신규: `engine/__init__.py` (빈 파일)
- 신규: `engine/scene.py`

- [ ] **Step 1: init 생성 + 모듈 작성**

```powershell
New-Item engine/__init__.py -ItemType File -Force
```

`engine/scene.py`:
```python
"""Scene base class + SceneManager. Scenes get update/draw/handle_event."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from engine.input import InputState


class Scene:
    """Subclass and override hooks. The manager passes itself to on_enter."""

    manager: "SceneManager | None" = None

    def on_enter(self) -> None:
        """Called once when this scene becomes active."""

    def on_exit(self) -> None:
        """Called once when this scene is replaced/popped."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Called for each pygame event in the frame."""

    def update(self, dt: float, inp: "InputState") -> None:
        """Called once per frame. dt is seconds since last frame."""

    def draw(self, surface: pygame.Surface) -> None:
        """Called once per frame to render."""


class SceneManager:
    """Holds a stack of scenes. Top scene gets all events/updates/draws.

    Use replace() for hard transitions (Title -> Play),
    push() for layered scenes (PlayScene -> BonusScene then return),
    pop() to remove the top.
    """

    def __init__(self) -> None:
        self._stack: list[Scene] = []
        self._pending: list[tuple[str, Scene | None]] = []

    @property
    def current(self) -> Scene | None:
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        self._pending.append(("push", scene))

    def replace(self, scene: Scene) -> None:
        self._pending.append(("replace", scene))

    def pop(self) -> None:
        self._pending.append(("pop", None))

    def _apply_pending(self) -> None:
        for op, scene in self._pending:
            if op == "push":
                if self.current:
                    self.current.on_exit()
                assert scene is not None
                scene.manager = self
                self._stack.append(scene)
                scene.on_enter()
            elif op == "replace":
                if self.current:
                    self.current.on_exit()
                    self._stack.pop()
                assert scene is not None
                scene.manager = self
                self._stack.append(scene)
                scene.on_enter()
            elif op == "pop":
                if self.current:
                    self.current.on_exit()
                    self._stack.pop()
                if self.current:
                    self.current.on_enter()
        self._pending.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float, inp: "InputState") -> None:
        self._apply_pending()
        if self.current:
            self.current.update(dt, inp)

    def draw(self, surface: pygame.Surface) -> None:
        if self.current:
            self.current.draw(surface)
```

- [ ] **Step 2: 빠른 smoke import**

```powershell
python -c "from engine.scene import Scene, SceneManager; print('ok')"
```

기대: `ok`.

- [ ] **Step 3: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add engine/
git commit -m "feat(engine): Scene base class and SceneManager"
```

---

### Task 11: `engine/input.py` — InputState 추상화

**파일:**
- 신규: `engine/input.py`

- [ ] **Step 1: 모듈 작성**

```python
"""Per-frame input state. Single place that reads pygame keyboard."""

from dataclasses import dataclass

import pygame


@dataclass
class InputState:
    left: bool = False
    right: bool = False
    fire: bool = False
    fire_pressed: bool = False  # edge-trigger: True only on the frame Space went down
    pause_pressed: bool = False
    quit_pressed: bool = False


_FIRE_KEYS = (pygame.K_SPACE,)
_LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
_RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)


class InputReader:
    def __init__(self) -> None:
        self.state = InputState()
        self._prev_fire = False

    def begin_frame(self, events: list[pygame.event.Event]) -> None:
        keys = pygame.key.get_pressed()
        self.state.left = any(keys[k] for k in _LEFT_KEYS)
        self.state.right = any(keys[k] for k in _RIGHT_KEYS)
        fire_now = any(keys[k] for k in _FIRE_KEYS)
        self.state.fire = fire_now
        self.state.fire_pressed = fire_now and not self._prev_fire
        self._prev_fire = fire_now

        self.state.pause_pressed = False
        self.state.quit_pressed = False
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p:
                    self.state.pause_pressed = True
                elif ev.key == pygame.K_ESCAPE:
                    self.state.quit_pressed = True
            elif ev.type == pygame.QUIT:
                self.state.quit_pressed = True
```

- [ ] **Step 2: smoke import**

```powershell
python -c "from engine.input import InputReader; print('ok')"
```

- [ ] **Step 3: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add engine/input.py
git commit -m "feat(engine): InputReader and InputState"
```

---

### Task 12: `engine/assets.py` — 에셋 자동 생성 + 캐시

**파일:**
- 신규: `engine/assets.py`

- [ ] **Step 1: 모듈 작성**

```python
"""Asset loading + caching. Auto-runs generators if assets/ is empty."""

from pathlib import Path

import pygame

import settings

_sprites: dict[str, pygame.Surface] = {}
_sounds: dict[str, pygame.mixer.Sound] = {}


def _ensure_assets() -> None:
    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    audio_dir = Path(settings.ASSETS_AUDIO_DIR)
    if not sprites_dir.exists() or not any(sprites_dir.glob("*.png")):
        print("Generating sprites...")
        from tools import generate_sprites
        generate_sprites.main()
    if not audio_dir.exists() or not any(audio_dir.glob("*.wav")):
        print("Generating audio...")
        from tools import generate_audio
        generate_audio.main()


def load_all() -> None:
    """Call once after pygame.init(). Loads every PNG/WAV into caches."""
    _ensure_assets()

    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    for png in sprites_dir.glob("*.png"):
        _sprites[png.stem] = pygame.image.load(str(png)).convert_alpha()

    if pygame.mixer.get_init():
        audio_dir = Path(settings.ASSETS_AUDIO_DIR)
        for wav in audio_dir.glob("*.wav"):
            _sounds[wav.stem] = pygame.mixer.Sound(str(wav))


def sprite(name: str) -> pygame.Surface:
    if name not in _sprites:
        raise KeyError(f"Sprite not loaded: {name!r}. Available: {sorted(_sprites)}")
    return _sprites[name]


def sound(name: str) -> pygame.mixer.Sound | None:
    return _sounds.get(name)


def has_sound(name: str) -> bool:
    return name in _sounds
```

- [ ] **Step 2: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add engine/assets.py
git commit -m "feat(engine): asset loader with auto-generation fallback"
```

---

### Task 13: `engine/audio.py` — 재생 wrapper + no-op 폴백

**파일:**
- 신규: `engine/audio.py`

- [ ] **Step 1: 모듈 작성**

```python
"""SFX + BGM playback. Silent no-op if pygame.mixer fails to init."""

import pygame

from engine import assets

_mixer_ready = False
_music_channel: pygame.mixer.Channel | None = None
_current_music: str | None = None


def init() -> None:
    """Call after pygame.init(). Safe to call when mixer is unavailable."""
    global _mixer_ready, _music_channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(8)
        _music_channel = pygame.mixer.Channel(0)  # reserve channel 0 for music
        _mixer_ready = True
    except pygame.error as e:
        print(f"Warning: audio disabled ({e})")
        _mixer_ready = False


def play_sfx(name: str) -> None:
    if not _mixer_ready:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    # pygame.mixer.find_channel(True) finds first available, force-replacing oldest if all busy
    ch = pygame.mixer.find_channel(True)
    if ch is _music_channel:
        # don't steal music channel
        return
    ch.play(snd)


def play_music(name: str, loop: bool = True) -> None:
    global _current_music
    if not _mixer_ready or _music_channel is None:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    _music_channel.stop()
    _music_channel.play(snd, loops=-1 if loop else 0)
    _current_music = name


def stop_music() -> None:
    global _current_music
    if _music_channel is None:
        return
    _music_channel.stop()
    _current_music = None


def current_music() -> str | None:
    return _current_music
```

- [ ] **Step 2: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add engine/audio.py
git commit -m "feat(engine): audio playback with safe no-op fallback"
```

---

## Phase 5: 최소 플레이 가능 루프

### Task 14: `entities/player.py` + `entities/bullet.py` — Player와 bullets

**파일:**
- 신규: `entities/__init__.py` (빈 파일)
- 신규: `entities/player.py`
- 신규: `entities/bullet.py`

- [ ] **Step 1: init 생성**

```powershell
New-Item entities/__init__.py -ItemType File -Force
```

- [ ] **Step 2: `entities/bullet.py` 작성**

```python
"""PlayerBullet (upward) and EnemyBullet (toward player)."""

import pygame

import settings
from engine import assets


class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, pos: pygame.Vector2) -> None:
        super().__init__()
        self.image = assets.sprite("player_bullet")
        self.rect = self.image.get_rect(midbottom=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)

    def update(self, dt: float) -> None:
        self.pos.y -= settings.PLAYER_BULLET_SPEED * dt
        self.rect.midbottom = (int(self.pos.x), int(self.pos.y))
        if self.rect.bottom < 0:
            self.kill()


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, pos: pygame.Vector2, target: pygame.Vector2) -> None:
        super().__init__()
        self.image = assets.sprite("enemy_bullet")
        self.rect = self.image.get_rect(midtop=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)
        direction = target - pos
        if direction.length() == 0:
            direction = pygame.Vector2(0, 1)
        self.velocity = direction.normalize() * settings.ENEMY_BULLET_SPEED

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt
        self.rect.midtop = (int(self.pos.x), int(self.pos.y))
        if (
            self.rect.top > settings.PLAYFIELD_HEIGHT
            or self.rect.right < 0
            or self.rect.left > settings.PLAYFIELD_WIDTH
        ):
            self.kill()
```

- [ ] **Step 3: `entities/player.py` 작성**

```python
"""Player ship: move + fire. Coordinates are playfield-local."""

import pygame

import settings
from engine import assets, audio
from engine.input import InputState
from entities.bullet import PlayerBullet


class Player(pygame.sprite.Sprite):
    def __init__(self) -> None:
        super().__init__()
        self.image = assets.sprite("player")
        self.rect = self.image.get_rect()
        self.pos = pygame.Vector2(
            settings.PLAYFIELD_WIDTH / 2,
            settings.PLAYFIELD_HEIGHT - 40,
        )
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def update(
        self,
        dt: float,
        inp: InputState,
        bullets: pygame.sprite.Group,
        on_shot: callable | None = None,
    ) -> None:
        # Movement
        dx = 0.0
        if inp.left:
            dx -= 1.0
        if inp.right:
            dx += 1.0
        self.pos.x += dx * settings.PLAYER_SPEED * dt
        # Clamp inside playfield
        half_w = self.rect.width / 2
        self.pos.x = max(half_w, min(settings.PLAYFIELD_WIDTH - half_w, self.pos.x))
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Fire (edge-triggered, max 2 on screen)
        if inp.fire_pressed and len(bullets) < settings.MAX_PLAYER_BULLETS:
            muzzle = pygame.Vector2(self.pos.x, self.pos.y - self.rect.height / 2)
            bullets.add(PlayerBullet(muzzle))
            audio.play_sfx("sfx_shoot")
            if on_shot:
                on_shot()
```

- [ ] **Step 4: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add entities/
git commit -m "feat(entities): Player and bullet sprites with movement and firing"
```

---

### Task 15: `scenes/play.py` (shell) — Player + bullets만

**파일:**
- 신규: `scenes/__init__.py` (빈 파일)
- 신규: `scenes/play.py`

- [ ] **Step 1: init 생성**

```powershell
New-Item scenes/__init__.py -ItemType File -Force
```

- [ ] **Step 2: 최소 `scenes/play.py` 작성**

```python
"""Main gameplay scene. Builds up over later tasks."""

import random

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene
from entities.player import Player


class PlayScene(Scene):
    def __init__(self) -> None:
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface(
            (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT)
        )
        # starfield
        rng = random.Random(7)
        self._stars = [
            (rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
             rng.randint(0, settings.PLAYFIELD_HEIGHT - 1))
            for _ in range(60)
        ]

    def update(self, dt: float, inp: InputState) -> None:
        self.player.update(dt, inp, self.player_bullets)
        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Window background
        surface.fill(settings.COLOR_BLACK)
        # Playfield
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        surface.blit(
            self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y)
        )
```

- [ ] **Step 3: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add scenes/
git commit -m "feat(scenes): minimal PlayScene shell with player + starfield"
```

---

### Task 16: `main.py` — 모두 연결해서 첫 플레이 가능

**파일:**
- 신규: `main.py`

- [ ] **Step 1: 진입점 작성**

```python
"""Galaga clone — main entry point."""

import sys
import traceback

import pygame

import settings
from engine import assets, audio
from engine.input import InputReader
from engine.scene import SceneManager
from scenes.play import PlayScene


def main() -> int:
    pygame.init()
    audio.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Galaga Clone")
    clock = pygame.time.Clock()

    assets.load_all()

    manager = SceneManager()
    manager.replace(PlayScene())  # for now, jump straight to play
    inp = InputReader()

    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000.0
        events = pygame.event.get()
        inp.begin_frame(events)
        for ev in events:
            manager.handle_event(ev)
        if inp.state.quit_pressed:
            running = False

        manager.update(dt, inp.state)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
```

- [ ] **Step 2: 게임 실행!**

```powershell
python main.py
```

기대: 1280×720 창이 열림. 검은 배경, 540 폭의 세로 스트립 아래쪽 가운데에 플레이어 함선, 별 배경. 화살표로 좌우 이동 (플레이필드 안에서). Space로 발사 (화면에 최대 2발, 엣지 트리거이므로 매번 누를 때마다 1발). Esc로 창 닫음. **사운드: 발사할 때마다 짧은 blip음.**

문제 있으면 다음 진행 전에 디버그.

- [ ] **Step 3: README에 실행 방법 추가**

`README.md`:
```markdown
# Galaga Clone

Single-player Galaga clone built in Python + Pygame. Personal/learning project.

See [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](docs/superpowers/specs/2026-05-02-galaga-clone-design.md) for the design spec.

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

- Arrow keys / A,D — move
- Space — fire
- P — pause
- Esc — quit

## Develop

```powershell
pytest         # tests
ruff check .   # lint
ruff format .  # format
```
```

- [ ] **Step 4: 커밋**

```powershell
git add main.py README.md
git commit -m "feat: wire up main loop, first playable (player + bullets)"
git push
```

https://github.com/elec9747230-ui/galaga-clone 에서 CI 실행 + (lint + test) 잡 통과 확인.

---

## Phase 6: 적

### Task 17: `entities/enemy.py` — 상태머신 가진 Enemy

**파일:**
- 신규: `entities/enemy.py`

- [ ] **Step 1: 모듈 작성**

```python
"""Enemy sprite with state machine: ENTERING -> IN_FORMATION -> DIVING -> RETURNING."""

import math
from enum import Enum

import pygame

import settings
from engine import assets
from entities.bullet import EnemyBullet
from game import dive, formation


class EnemyState(Enum):
    ENTERING = "entering"
    IN_FORMATION = "in_formation"
    DIVING = "diving"
    RETURNING = "returning"


class Enemy(pygame.sprite.Sprite):
    sprite_name = "enemy_bee"  # subclasses override
    score_kind = "normal"  # "normal" or "boss"

    def __init__(
        self,
        row: int,
        col: int,
        formation_phase_ref: list[float],
        entry_delay: float = 0.0,
    ) -> None:
        super().__init__()
        self.image = assets.sprite(self.sprite_name)
        self.rect = self.image.get_rect()
        self.row = row
        self.col = col
        self._phase_ref = formation_phase_ref  # mutable list-of-1; live read each frame
        self.state = EnemyState.ENTERING
        self._entry_path = formation.entry_path(row, col)
        self._entry_index = 0
        self._entry_delay = entry_delay
        self._dive_path: list[pygame.Vector2] = []
        self._dive_index = 0
        self._dive_seed = 0
        self._dive_fire_armed = True
        self.pos = pygame.Vector2(self._entry_path[0])
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    # ----- public hooks -----

    def is_in_formation(self) -> bool:
        return self.state == EnemyState.IN_FORMATION

    def start_dive(self, player_pos: pygame.Vector2, seed: int) -> None:
        if self.state != EnemyState.IN_FORMATION:
            return
        self._dive_path = dive.dive_path(self.pos, player_pos, seed)
        self._dive_index = 0
        self._dive_seed = seed
        self._dive_fire_armed = True
        self.state = EnemyState.DIVING

    # ----- per-frame -----

    def update(self, dt: float) -> None:
        if self.state == EnemyState.ENTERING:
            self._update_entering(dt)
        elif self.state == EnemyState.IN_FORMATION:
            self._update_in_formation()
        elif self.state == EnemyState.DIVING:
            self._update_diving(dt)
        elif self.state == EnemyState.RETURNING:
            self._update_returning(dt)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _update_entering(self, dt: float) -> None:
        if self._entry_delay > 0:
            self._entry_delay -= dt
            return
        speed = 220
        # advance along path by speed*dt
        remain = speed * dt
        while remain > 0 and self._entry_index < len(self._entry_path) - 1:
            target = self._entry_path[self._entry_index + 1]
            d = (target - self.pos).length()
            if d <= remain:
                self.pos = pygame.Vector2(target)
                self._entry_index += 1
                remain -= d
            else:
                self.pos += (target - self.pos).normalize() * remain
                remain = 0
        if self._entry_index >= len(self._entry_path) - 1:
            self.state = EnemyState.IN_FORMATION

    def _update_in_formation(self) -> None:
        self.pos = formation.slot_position(self.row, self.col, self._phase_ref[0])

    def _update_diving(self, dt: float) -> None:
        speed = 260
        remain = speed * dt
        while remain > 0 and self._dive_index < len(self._dive_path) - 1:
            target = self._dive_path[self._dive_index + 1]
            d = (target - self.pos).length()
            if d <= remain:
                self.pos = pygame.Vector2(target)
                self._dive_index += 1
                remain -= d
            else:
                self.pos += (target - self.pos).normalize() * remain
                remain = 0
        if self._dive_index >= len(self._dive_path) - 1:
            # Re-enter from top: respawn ENTERING from a top entry
            self.state = EnemyState.RETURNING
            self.pos = pygame.Vector2(self.pos.x, -30)

    def _update_returning(self, dt: float) -> None:
        # Drift down to slot, then resume IN_FORMATION
        target = formation.slot_position(self.row, self.col, self._phase_ref[0])
        direction = target - self.pos
        if direction.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        self.pos += direction.normalize() * 220 * dt

    def maybe_fire(self, target: pygame.Vector2) -> EnemyBullet | None:
        """Called by PlayScene during DIVING to optionally emit a bullet."""
        if self.state != EnemyState.DIVING or not self._dive_fire_armed:
            return None
        # Fire once near the start of the dive
        if self._dive_index < 8 or self._dive_index > 16:
            return None
        self._dive_fire_armed = False
        return EnemyBullet(self.pos, target)


class BeeEnemy(Enemy):
    sprite_name = "enemy_bee"
    score_kind = "normal"


class ButterflyEnemy(Enemy):
    sprite_name = "enemy_butterfly"
    score_kind = "normal"


class BossEnemy(Enemy):
    sprite_name = "enemy_boss"
    score_kind = "boss"
```

- [ ] **Step 2: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add entities/enemy.py
git commit -m "feat(entities): Enemy state machine (entering/formation/diving/returning)"
```

---

### Task 18: PlayScene에 적 포메이션 연결

**파일:**
- 수정: `scenes/play.py`

- [ ] **Step 1: `scenes/play.py`를 포메이션 인지 버전으로 교체**

```python
"""Main gameplay scene with player + enemy formation."""

import math
import random

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy, BossEnemy, ButterflyEnemy
from entities.player import Player


class PlayScene(Scene):
    def __init__(self) -> None:
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface(
            (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT)
        )
        rng = random.Random(7)
        self._stars = [
            (rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
             rng.randint(0, settings.PLAYFIELD_HEIGHT - 1))
            for _ in range(60)
        ]
        self._formation_phase = [0.0]  # mutable for enemies to read
        self._time = 0.0
        self._spawn_formation()

    def _spawn_formation(self) -> None:
        """Spawn one row of bees + one row of butterflies + one row of bosses + 2 more rows of bees."""
        delays = []
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = (row * 0.25) + (col * 0.05)
                delays.append((row, col, delay))
                if row == 0:
                    cls = BossEnemy
                elif row == 1:
                    cls = ButterflyEnemy
                else:
                    cls = BeeEnemy
                self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        self._time += dt
        # Drive formation oscillation phase: 2*pi per ~4s
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        self.player.update(dt, inp, self.player_bullets)
        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        surface.blit(
            self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y)
        )
```

- [ ] **Step 2: 플레이테스트**

```powershell
python main.py
```

기대: 40 마리 적이 시간차로 곡선 경로 따라 모서리에서 진입, 5×8 그리드에 자리 잡고, 좌우로 천천히 흔들림. 플레이어는 여전히 이동/발사 가능하지만 총알이 적을 죽이지는 않음.

- [ ] **Step 3: 커밋**

```powershell
git add scenes/play.py
git commit -m "feat(scenes): spawn enemy formation with staggered Bezier entry"
```

---

### Task 19: 다이브 공격 + 충돌 + 폭발 추가

**파일:**
- 신규: `entities/explosion.py`
- 수정: `scenes/play.py`

- [ ] **Step 1: `entities/explosion.py` 작성**

```python
"""4-frame animated explosion. Auto-removes when sequence completes."""

import pygame

from engine import assets

FRAME_DURATION = 0.07  # seconds per frame


class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos: pygame.Vector2) -> None:
        super().__init__()
        self.frames = [assets.sprite(f"explosion_{i}") for i in range(4)]
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self._frame_index = 0
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        idx = int(self._t / FRAME_DURATION)
        if idx >= len(self.frames):
            self.kill()
            return
        if idx != self._frame_index:
            self._frame_index = idx
            center = self.rect.center
            self.image = self.frames[idx]
            self.rect = self.image.get_rect(center=center)
```

- [ ] **Step 2: `scenes/play.py` 업데이트** — 다이브 트리거, 충돌, 폭발, 플레이어 재스폰 추가

`scenes/play.py`를 다음 확장 버전으로 교체:

```python
"""Main gameplay scene: formation + dives + collisions + explosions + lives."""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy, BossEnemy, ButterflyEnemy
from entities.explosion import Explosion
from entities.player import Player
from game.scoring import Scoring


class PlayScene(Scene):
    def __init__(self, scoring: Scoring | None = None) -> None:
        self.scoring = scoring or Scoring()
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface(
            (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT)
        )
        rng = random.Random(7)
        self._stars = [
            (rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
             rng.randint(0, settings.PLAYFIELD_HEIGHT - 1))
            for _ in range(60)
        ]
        self._formation_phase = [0.0]
        self._time = 0.0
        self._dive_seed_counter = 1
        self._dive_probability_per_sec = 0.25  # tweaked later via difficulty
        self._respawn_timer = 0.0
        self._player_alive = True
        self._spawn_formation()

    def _spawn_formation(self) -> None:
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = (row * 0.25) + (col * 0.05)
                if row == 0:
                    cls = BossEnemy
                elif row == 1:
                    cls = ButterflyEnemy
                else:
                    cls = BeeEnemy
                self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        self._time += dt
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        # Player update / respawn
        if self._player_alive:
            self.player.update(
                dt, inp, self.player_bullets, on_shot=self.scoring.add_shot
            )
        else:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0 and self.scoring.lives > 0:
                self.player = Player()
                self.players = pygame.sprite.GroupSingle(self.player)
                self._player_alive = True

        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

        # Trigger dives
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt * 60:
            attacker = random.choice(in_formation)
            self._dive_seed_counter += 1
            attacker.start_dive(self.player.pos, self._dive_seed_counter)
            audio.play_sfx("sfx_dive")

        # Diving enemies may fire
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(self.player.pos)
                if bullet:
                    self.enemy_bullets.add(bullet)

        # Collisions
        self._handle_collisions()

    def _handle_collisions(self) -> None:
        # player bullets vs enemies
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                kind = "dive" if e.state.value == "diving" else e.score_kind
                self.scoring.add_kill(kind)
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")

        if not self._player_alive:
            return

        # enemy bullets vs player
        if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
            self._kill_player()
            return

        # diving enemies vs player
        diving_collisions = [
            e for e in self.enemies if e.state.value == "diving" and self.player.rect.colliderect(e.rect)
        ]
        if diving_collisions:
            for e in diving_collisions:
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                e.kill()
            self._kill_player()

    def _kill_player(self) -> None:
        self.explosions.add(Explosion(pygame.Vector2(self.player.pos)))
        audio.play_sfx("sfx_player_hit")
        self.scoring.lose_life()
        self.players.empty()
        self._player_alive = False
        self._respawn_timer = settings.PLAYER_RESPAWN_DELAY

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        surface.blit(
            self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y)
        )
```

- [ ] **Step 3: 플레이테스트**

```powershell
python main.py
```

기대: 적이 다이브, 가끔 플레이어 향해 발사. 플레이어 총알이 적을 죽임 (폭발 + 사운드). 적 총알과 다이브 중인 적이 플레이어를 죽임 (라이프 감소, 짧은 딜레이 후 재스폰). 라이프 카운트는 줄지만 UI는 아직 없음.

- [ ] **Step 4: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add entities/explosion.py scenes/play.py
git commit -m "feat: dive attacks, collisions, explosions, player respawn"
```

---

## Phase 7: 웨이브 진행 + HUD

### Task 20: `game/hud.py` — 사이드 패널 렌더링

**파일:**
- 신규: `game/hud.py`

- [ ] **Step 1: 모듈 작성**

```python
"""HUD rendering for left and right side panels.

Reads from a Scoring instance every frame.
"""

import pygame

import settings
from engine import assets
from game.scoring import Scoring

_font_cache: dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("consolas", size, bold=True)
    return _font_cache[size]


def draw_left(surface: pygame.Surface, scoring: Scoring, highscore: int) -> None:
    panel = pygame.Surface((settings.SIDE_PANEL_WIDTH, settings.WINDOW_HEIGHT))
    panel.fill(settings.COLOR_BLACK)

    # Logo
    logo = assets.sprite("logo")
    panel.blit(logo, (40, 30))

    # Score label + value
    label = _font(18).render("SCORE", True, settings.COLOR_HUD_DIM)
    panel.blit(label, (40, 130))
    val = _font(36).render(f"{scoring.score:>8}", True, settings.COLOR_WHITE)
    panel.blit(val, (40, 154))

    # Lives
    lives_label = _font(18).render("LIVES", True, settings.COLOR_HUD_DIM)
    panel.blit(lives_label, (40, 360))
    ship = assets.sprite("player")
    for i in range(scoring.lives):
        panel.blit(ship, (40 + i * (ship.get_width() + 6), 388))

    # Controls
    controls = [
        "MOVE  : Arrow / A,D",
        "FIRE  : Space",
        "PAUSE : P",
        "QUIT  : Esc",
    ]
    f = _font(14)
    for i, line in enumerate(controls):
        panel.blit(f.render(line, True, settings.COLOR_HUD_DIM), (40, 540 + i * 22))

    surface.blit(panel, (0, 0))


def draw_right(surface: pygame.Surface, scoring: Scoring, highscore: int) -> None:
    panel = pygame.Surface((settings.SIDE_PANEL_WIDTH, settings.WINDOW_HEIGHT))
    panel.fill(settings.COLOR_BLACK)

    # High score
    hs_label = _font(18).render("HIGH SCORE", True, settings.COLOR_HUD_DIM)
    panel.blit(hs_label, (40, 30))
    hs_val = _font(28).render(f"{highscore:>8}", True, settings.COLOR_YELLOW)
    panel.blit(hs_val, (40, 56))

    # Wave
    w_label = _font(18).render("WAVE", True, settings.COLOR_HUD_DIM)
    panel.blit(w_label, (40, 200))
    w_val = _font(36).render(f"{scoring.wave:>3}", True, settings.COLOR_CYAN)
    panel.blit(w_val, (40, 226))

    # Accuracy
    acc_label = _font(18).render("ACCURACY", True, settings.COLOR_HUD_DIM)
    panel.blit(acc_label, (40, 400))
    pct = scoring.accuracy() * 100
    acc_val = _font(28).render(f"{pct:5.1f}%", True, settings.COLOR_GREEN)
    panel.blit(acc_val, (40, 426))

    # Kills
    k_label = _font(18).render("KILLS", True, settings.COLOR_HUD_DIM)
    panel.blit(k_label, (40, 540))
    k_val = _font(28).render(f"{scoring.enemies_killed:>5}", True, settings.COLOR_WHITE)
    panel.blit(k_val, (40, 566))

    surface.blit(panel, (settings.PLAYFIELD_OFFSET_X + settings.PLAYFIELD_WIDTH, 0))
```

- [ ] **Step 2: PlayScene draw에 연결**

`scenes/play.py`의 `draw` 메서드 수정:
```python
def draw(self, surface: pygame.Surface) -> None:
    from game import hud
    surface.fill(settings.COLOR_BLACK)
    self.playfield.fill(settings.COLOR_BLACK)
    for sx, sy in self._stars:
        self.playfield.set_at((sx, sy), settings.COLOR_STAR)
    self.players.draw(self.playfield)
    self.player_bullets.draw(self.playfield)
    self.enemies.draw(self.playfield)
    self.enemy_bullets.draw(self.playfield)
    self.explosions.draw(self.playfield)
    surface.blit(self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y))
    hs = self._highscore if hasattr(self, "_highscore") else 0
    hud.draw_left(surface, self.scoring, hs)
    hud.draw_right(surface, self.scoring, hs)
```

`scenes/play.py` `__init__`에도 추가:
```python
from game.scoring import load_highscore
self._highscore = load_highscore()
```

- [ ] **Step 3: 플레이테스트**

```powershell
python main.py
```

기대: 양 사이드 패널에 HUD 표시: 좌측 logo + SCORE + LIVES + 조작; 우측 HIGH SCORE + WAVE + ACCURACY + KILLS. 발사/처치 시 숫자가 실시간 갱신.

- [ ] **Step 4: 포맷 + 커밋**

```powershell
ruff format .
ruff check . --fix
git add game/hud.py scenes/play.py
git commit -m "feat(hud): side panel rendering wired into PlayScene"
```

---

### Task 21: 웨이브 클리어 + 다음 웨이브 스폰 + 난이도

**파일:**
- 수정: `scenes/play.py`

- [ ] **Step 1: PlayScene에 wave controller와 클리어/다음 웨이브 로직 추가**

`scenes/play.py` __init__에 추가:
```python
from game.wave import WaveController
# ...
self.wave_controller = WaveController(start_wave=self.scoring.wave)
self._apply_wave_difficulty()
```

PlayScene에 헬퍼 메서드 추가:
```python
def _apply_wave_difficulty(self) -> None:
    p = self.wave_controller.current_params()
    self._dive_probability_per_sec = 0.20 + 0.5 * p.dive_probability  # use as a scalar
    # Speed-up enemy & bullet behavior could be wired by passing into enemies/bullets;
    # for simplicity, keep base speeds constant for now and only ramp dive frequency.
```

`update`의 충돌 처리 후에 추가:
```python
if not self.enemies:
    # Wave cleared
    self.wave_controller.advance()
    self.scoring.wave = self.wave_controller.current_wave
    self._apply_wave_difficulty()
    # For now, just respawn the formation (Task 23 will branch on wave type)
    self._spawn_formation()
```

- [ ] **Step 2: 플레이테스트**

```powershell
python main.py
```

기대: 40 마리 적 모두 처치 시 새로운 포메이션 진입. HUD WAVE 카운터 증가. 난이도 (다이브 빈도) 점진 상승.

- [ ] **Step 3: 커밋**

```powershell
git add scenes/play.py
git commit -m "feat(scenes): wave clearing, advance, and formation respawn"
```

---

### Task 22: Game over → GameOverScene + scoring 인계

**파일:**
- 신규: `scenes/gameover.py`
- 수정: `scenes/play.py`

- [ ] **Step 1: `scenes/gameover.py` 작성**

```python
"""Game over screen — show final score, save high score, return to title."""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.scoring import Scoring, load_highscore, save_highscore


class GameOverScene(Scene):
    def __init__(self, scoring: Scoring) -> None:
        self.scoring = scoring
        self._font_big = pygame.font.SysFont("consolas", 64, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 20)
        self._t = 0.0
        prev = load_highscore()
        self.is_new_high = scoring.score > prev
        if self.is_new_high:
            save_highscore(scoring.score)
        audio.play_music("music_game_over", loop=False)

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if self._t > 1.0 and inp.fire_pressed:
            from scenes.title import TitleScene
            assert self.manager
            self.manager.replace(TitleScene())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        title = self._font_big.render("GAME OVER", True, settings.COLOR_RED)
        score = self._font_med.render(
            f"Score: {self.scoring.score}", True, settings.COLOR_WHITE
        )
        kills = self._font_sm.render(
            f"Kills: {self.scoring.enemies_killed}    Accuracy: {self.scoring.accuracy() * 100:.1f}%",
            True, settings.COLOR_HUD_DIM,
        )
        new_hs = (
            self._font_med.render("NEW HIGH SCORE!", True, settings.COLOR_YELLOW)
            if self.is_new_high else None
        )
        prompt = self._font_sm.render("Press SPACE to continue", True, settings.COLOR_HUD_DIM)

        cx = settings.WINDOW_WIDTH // 2
        surface.blit(title, title.get_rect(center=(cx, 200)))
        surface.blit(score, score.get_rect(center=(cx, 290)))
        surface.blit(kills, kills.get_rect(center=(cx, 340)))
        if new_hs:
            surface.blit(new_hs, new_hs.get_rect(center=(cx, 400)))
        if self._t > 1.0:
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
```

- [ ] **Step 2: `scenes/play.py` `_kill_player`에서 `lose_life` 후 라이프 0이면 GameOver로 전환**

```python
def _kill_player(self) -> None:
    self.explosions.add(Explosion(pygame.Vector2(self.player.pos)))
    audio.play_sfx("sfx_player_hit")
    self.scoring.lose_life()
    self.players.empty()
    self._player_alive = False
    self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
    if self.scoring.lives <= 0:
        from scenes.gameover import GameOverScene
        assert self.manager
        self.manager.replace(GameOverScene(self.scoring))
```

- [ ] **Step 3: 플레이테스트**

라이프 3개 모두 잃기. GameOverScene에 점수, kills, accuracy 표시 기대. 해당하면 new high score 메시지. Space 누르면 → 타이틀로 (아직 없으니 NoneType crash 가능 — stub 추가 안 했다면).

지금 단계에서는 "Press SPACE" 시 TitleScene이 아직 없으면 그 줄을 주석 처리 OR 빨리 다음 task로 진행.

- [ ] **Step 4: 커밋**

```powershell
git add scenes/gameover.py scenes/play.py
git commit -m "feat(scenes): GameOverScene with high-score persistence"
```

---

## Phase 8: 보너스 스테이지 + 보스 웨이브 + 남은 씬

### Task 23: 웨이브 클리어를 BonusScene으로 분기

**파일:**
- 신규: `scenes/bonus.py`
- 신규: `scenes/transitions.py`
- 수정: `scenes/play.py`

- [ ] **Step 1: `scenes/transitions.py` 작성**

```python
"""Brief overlay screens between phases (e.g., 'STAGE 5', 'CHALLENGING STAGE')."""

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene


class TransitionScene(Scene):
    def __init__(self, text: str, next_scene_factory, duration: float = 2.0) -> None:
        self.text = text
        self._next_factory = next_scene_factory
        self._duration = duration
        self._t = 0.0
        self._font = pygame.font.SysFont("consolas", 56, bold=True)

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if self._t >= self._duration:
            assert self.manager
            self.manager.replace(self._next_factory())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        text = self._font.render(self.text, True, settings.COLOR_YELLOW)
        rect = text.get_rect(center=(settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2))
        surface.blit(text, rect)
```

- [ ] **Step 2: `scenes/bonus.py` 작성**

```python
"""Bonus (challenging) stage. Enemies enter, don't fire, perfect = +10000 + 1 life."""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy
from entities.explosion import Explosion
from entities.player import Player
from game.scoring import Scoring


class BonusScene(Scene):
    """Reuses player + bullets but no enemy fire and time-limited."""

    def __init__(self, scoring: Scoring) -> None:
        self.scoring = scoring
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface(
            (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT)
        )
        rng = random.Random(101)
        self._stars = [
            (rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
             rng.randint(0, settings.PLAYFIELD_HEIGHT - 1))
            for _ in range(60)
        ]
        self._formation_phase = [0.0]
        self._time = 0.0
        self._initial_count = settings.FORMATION_ROWS * settings.FORMATION_COLS
        self._kills = 0
        self._spawn()
        audio.play_music("music_bonus", loop=False)

    def _spawn(self) -> None:
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = 0.5 + (row * 0.4) + (col * 0.08)
                self.enemies.add(BeeEnemy(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        self._time += dt
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        self.player.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        for b in self.player_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

        # Collision: player bullets vs enemies (no enemy fire here, no diving)
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _, enemies_hit in hits.items():
            for e in enemies_hit:
                self.scoring.add_kill("bonus")
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")
                self._kills += 1

        # End condition
        if self._time > settings.BONUS_STAGE_DURATION or not self.enemies:
            self._finish()

    def _finish(self) -> None:
        if self._kills == self._initial_count:
            self.scoring.score += settings.SCORE_BONUS_PERFECT
            for _ in range(settings.LIFE_BONUS_PERFECT):
                self.scoring.gain_life()
            audio.play_sfx("sfx_extra_life")
        # Advance wave and return to PlayScene
        self.scoring.wave += 1
        from scenes.play import PlayScene
        from scenes.transitions import TransitionScene
        assert self.manager
        self.manager.replace(
            TransitionScene(
                f"STAGE {self.scoring.wave}",
                lambda: PlayScene(scoring=self.scoring),
                duration=1.5,
            )
        )

    def draw(self, surface: pygame.Surface) -> None:
        from game import hud
        from game.scoring import load_highscore
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.explosions.draw(self.playfield)
        surface.blit(self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y))
        hs = load_highscore()
        hud.draw_left(surface, self.scoring, hs)
        hud.draw_right(surface, self.scoring, hs)
```

- [ ] **Step 3: `scenes/play.py`에서 웨이브 클리어를 웨이브 타입에 따라 분기**

`update`의 웨이브 클리어 블록 교체:
```python
if not self.enemies:
    self.wave_controller.advance()
    self.scoring.wave = self.wave_controller.current_wave
    next_type = self.wave_controller.current_type()
    from game.wave import WaveType
    from scenes.transitions import TransitionScene
    if next_type == WaveType.BONUS:
        from scenes.bonus import BonusScene
        assert self.manager
        self.manager.replace(
            TransitionScene("CHALLENGING STAGE",
                lambda: BonusScene(self.scoring), duration=1.8)
        )
    else:
        text = f"STAGE {self.scoring.wave}" if next_type == WaveType.NORMAL else "BOSS STAGE"
        assert self.manager
        self.manager.replace(
            TransitionScene(text,
                lambda: PlayScene(scoring=self.scoring), duration=1.5)
        )
```

`from scenes.play import PlayScene`은 PlayScene 안이라 묵시적; 직접 클래스 참조 사용.

실제로는 `PlayScene.update` 안에서 `PlayScene` 클래스를 직접 참조 가능. `type(self)` 사용:

```python
        self.manager.replace(
            TransitionScene(text, lambda: type(self)(scoring=self.scoring), duration=1.5)
        )
```

- [ ] **Step 4: 플레이테스트**

웨이브 5(보스)까지 클리어 → 웨이브 6은 "CHALLENGING STAGE"로 전환 → 보너스 스테이지 진행 (적 발사 없음), 적 진입 후 격파 → 30초 후 또는 모두 격파 시 종료 → "STAGE 7" 오버레이 후 PlayScene으로 복귀.

- [ ] **Step 5: 커밋**

```powershell
git add scenes/bonus.py scenes/transitions.py scenes/play.py
git commit -m "feat(scenes): bonus stage + transitions + wave-type branching"
```

---

### Task 24: 보스 웨이브 변형 (보스 더 많이 + 다이브 강함)

"Classic Core" 단순화를 위해 보스 웨이브는 같은 포메이션이지만 모든 행이 BossEnemy. `_spawn_formation`이 boss-only 플래그를 받도록 수정.

**파일:**
- 수정: `scenes/play.py`

- [ ] **Step 1: 웨이브 타입에 따라 `_spawn_formation` 일반화**

`_spawn_formation` 교체:
```python
def _spawn_formation(self) -> None:
    from game.wave import WaveType
    wave_type = self.wave_controller.current_type()
    is_boss = wave_type == WaveType.BOSS
    for row in range(settings.FORMATION_ROWS):
        for col in range(settings.FORMATION_COLS):
            delay = (row * 0.25) + (col * 0.05)
            if is_boss:
                cls = BossEnemy if row < 2 else ButterflyEnemy
            else:
                if row == 0:
                    cls = BossEnemy
                elif row == 1:
                    cls = ButterflyEnemy
                else:
                    cls = BeeEnemy
            self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))
```

- [ ] **Step 2: 보스 웨이브 플레이테스트**

웨이브 5에 도달. 상위 2행이 보스, 하위 3행이 butterfly. 격파당 점수 = 150 (보스) 또는 100 (다이브 중인 butterfly).

- [ ] **Step 3: 커밋**

```powershell
git add scenes/play.py
git commit -m "feat(scenes): boss wave variant (top rows are bosses)"
```

---

### Task 25: `scenes/title.py` — 타이틀 화면

**파일:**
- 신규: `scenes/title.py`

- [ ] **Step 1: title scene 작성**

```python
"""Title screen — Press SPACE to start."""

import pygame

import settings
from engine import assets, audio
from engine.input import InputState
from engine.scene import Scene
from game.scoring import load_highscore


class TitleScene(Scene):
    def __init__(self) -> None:
        self._font_big = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 22)
        self._t = 0.0
        self._highscore = load_highscore()

    def on_enter(self) -> None:
        audio.play_music("music_intro", loop=True)

    def on_exit(self) -> None:
        audio.stop_music()

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if inp.fire_pressed:
            from game.scoring import Scoring
            from scenes.play import PlayScene
            from scenes.transitions import TransitionScene
            assert self.manager
            self.manager.replace(
                TransitionScene(
                    "STAGE 1",
                    lambda: PlayScene(scoring=Scoring()),
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
        surface.blit(title, title.get_rect(center=(cx, 200)))
        surface.blit(sub, sub.get_rect(center=(cx, 280)))
        surface.blit(hs, hs.get_rect(center=(cx, 380)))
        # Blink prompt
        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 520)))
        controls = self._font_sm.render(
            "Arrow / A,D move  |  Space fire  |  P pause  |  Esc quit",
            True, settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
```

- [ ] **Step 2: `main.py`를 TitleScene으로 시작하도록 수정**

`main.py`에서 변경:
```python
from scenes.title import TitleScene
# ...
manager.replace(TitleScene())
```

(`from scenes.play import PlayScene`과 PlayScene 시작 코드 제거.)

- [ ] **Step 3: 플레이테스트**

게임 실행. "PRESS SPACE TO START" 깜빡이는 타이틀, 하이스코어, 조작 안내 표시 기대. Space 누르면 → "STAGE 1" 오버레이 → 게임 시작.

- [ ] **Step 4: 커밋**

```powershell
git add scenes/title.py main.py
git commit -m "feat(scenes): TitleScene with high-score display and intro music"
```

---

### Task 26: 일시정지 기능

**파일:**
- 수정: `scenes/play.py`, `scenes/bonus.py`

- [ ] **Step 1: PlayScene에 pause 추가**

`PlayScene.__init__`:
```python
self._paused = False
```

`PlayScene.update` 최상단:
```python
if inp.pause_pressed:
    self._paused = not self._paused
if self._paused:
    return
```

`PlayScene.draw` 끝부분의 surface.blit 호출 직전:
```python
if self._paused:
    overlay = pygame.Surface(
        (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT), pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 160))
    self.playfield.blit(overlay, (0, 0))
    f = pygame.font.SysFont("consolas", 48, bold=True)
    text = f.render("PAUSED", True, settings.COLOR_WHITE)
    rect = text.get_rect(
        center=(settings.PLAYFIELD_WIDTH // 2, settings.PLAYFIELD_HEIGHT // 2)
    )
    self.playfield.blit(text, rect)
```

(`surface.blit(self.playfield, ...)` BEFORE에 둬서 오버레이가 최종 blit 전에 playfield 위에 얹히도록.)

`BonusScene`도 같은 패턴 적용.

- [ ] **Step 2: 플레이테스트**

게임 중 P 누르면 일시정지. 동작 정지, "PAUSED" 텍스트가 playfield 위에 표시. P 다시 누르면 재개.

- [ ] **Step 3: 커밋**

```powershell
git add scenes/play.py scenes/bonus.py
git commit -m "feat(scenes): pause toggle (P) for play and bonus scenes"
```

---

## Phase 9: 오디오 통합 + 최종 다듬기

### Task 27: Play scene 음악 + extra-life 트리거 수정

**파일:**
- 수정: `scenes/play.py`

- [ ] **Step 1: PlayScene.on_enter에 음악 재생 추가**

`PlayScene` 클래스에 추가:
```python
def on_enter(self) -> None:
    from engine import audio
    audio.play_music("music_stage_start", loop=False)
```

- [ ] **Step 2: BonusScene + GameOverScene의 오디오 경로 이미 동작 확인**

(이전 task에서 이미 연결됨.)

- [ ] **Step 3: 플레이테스트**

타이틀 화면에 타이틀 음악. PlayScene 진입 시 stage start 징글. BonusScene에 보너스 음악. GameOverScene에 game over 멜로디. SFX: shoot/explode/dive/player_hit/extra_life.

- [ ] **Step 4: 커밋**

```powershell
git add scenes/play.py
git commit -m "feat(audio): per-scene music wiring"
```

---

### Task 28: README 다듬기 + 최종 테스트 + push

**파일:**
- 수정: `README.md`

- [ ] **Step 1: 최종 수동 플레이테스트 체크리스트**

`python main.py` 실행 후 확인:
- [ ] 타이틀 화면에 logo, 하이스코어, 깜빡이는 prompt, 인트로 음악 표시
- [ ] Space → "STAGE 1" 오버레이 → stage start 징글로 게임 시작
- [ ] 플레이어가 playfield 안에서 좌우 이동
- [ ] Space로 발사 (화면에 최대 2발, 엣지 트리거)
- [ ] 40 마리 적이 곡선 경로로 진입해 5×8 그리드 형성
- [ ] 포메이션이 좌우로 흔들림
- [ ] 적이 주기적으로 플레이어 영역으로 다이브
- [ ] 다이브 중인 적이 플레이어 향해 총알 발사
- [ ] 플레이어 총알이 적 격파 (폭발 + 사운드)
- [ ] 적 총알 / 다이브 충돌이 플레이어 사살 (라이프 감소, 짧은 딜레이, 재스폰)
- [ ] HUD 업데이트: score, lives, wave, accuracy, kills
- [ ] 웨이브 클리어 → 다음 웨이브 진입; "STAGE N" 오버레이 표시
- [ ] 웨이브 5 = 보스 웨이브 (상위 2행이 보스)
- [ ] 웨이브 6 = "CHALLENGING STAGE" 오버레이 → 적 발사 없는 보너스 스테이지 → 30초 후 또는 모두 격파 시 종료
- [ ] 퍼펙트 보너스 = +10000점 + 라이프 +1 + extra-life 사운드
- [ ] P로 일시정지 / 재개
- [ ] Esc로 깔끔하게 종료
- [ ] 라이프 0 → Game Over 화면에 score, kills, accuracy, "NEW HIGH SCORE!" (해당 시)
- [ ] 하이스코어가 다음 실행에서도 유지 (`data/highscore.json`)

문제 있으면 수정 후 진행.

- [ ] **Step 2: 전체 테스트 + ruff**

```powershell
pytest -v
ruff check .
ruff format --check .
```

기대: 모두 green.

- [ ] **Step 3: README에 feature 목록 추가**

`README.md`:
```markdown
# Galaga Clone

Single-player Galaga clone built in Python + Pygame. Personal/learning project.

See [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](docs/superpowers/specs/2026-05-02-galaga-clone-design.md) for the design spec.

## Features

- Authentic 5×8 enemy formation with curved entry paths
- Dive attacks with sine-wave wobble
- Wave cycle: 4 normal → 1 boss → 1 bonus, repeating, with rising difficulty
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

- Arrow keys / A,D — move
- Space — fire (max 2 bullets on screen)
- P — pause
- Esc — quit

## Develop

```powershell
pytest         # tests
ruff check .   # lint
ruff format .  # format
```

## License

Personal project. Original Galaga is © Bandai Namco; this is a non-distributed clone for educational purposes only.
```

- [ ] **Step 4: 커밋 + push**

```powershell
git add README.md
git commit -m "docs: final README polish with feature list"
git push
```

https://github.com/elec9747230-ui/galaga-clone 에 최신 커밋 + CI green 확인.

---

## 자체 리뷰 메모

**스펙 커버리지:**
- §1 Goals → 모두 범위 내 (player, formation, dives, waves, bonus, HUD, audio, hi-score, CI) — Task 14, 17–19, 20–24, 9+13+27, 4+22, 3 으로 커버
- §2 Tech choices → Task 1 (pyproject)
- §3 Game design parameters → Task 2 (settings)
- §4 Architecture → Task 순서와 일치
- §5 Components → 각 컴포넌트마다 전용 task
- §6 Data flow → Task 19, 20이 프레임당 흐름 구현
- §7 Error handling → Task 12 (asset auto-gen), Task 13 (audio no-op), Task 4 (highscore corrupt → 0), `main.py` try/except는 Task 16
- §8 Testing → Task 4–7 (순수 로직 TDD)
- §9 Repo + CI → Task 3
- §10 Open items → 모두 명시적으로 범위 밖

**Placeholder 스캔:** "TBD"/"TODO" placeholder 없음. 모든 코드 step에 실제 코드 포함.

**타입 일관성:** 검증됨. `Scoring` 필드와 메서드는 Task 4, 19, 20, 22, 23 전반에 일관. `WaveType` enum 값은 Task 5, 23 전반에 일관. `Enemy.state` 값은 `EnemyState` enum 문자열 — `.state.value == "diving"`으로 일관 사용. `entry_delay` 파라미터는 적 스폰 코드 전반에 일관.
