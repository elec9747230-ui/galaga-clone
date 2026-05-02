# 난이도 선택 + 다이브 빈도 버그 수정 구현 계획

> **에이전트 작업자용:** 진행 추적은 체크박스(`- [ ]`) 표기로.

**목표:** ~12회/초 다이브가 발생하던 버그(원래 의도는 ~0.2/초)를 수정하고, 타이틀 화면에 3단계 난이도 선택(EASY/NORMAL/HARD)을 추가한다.

**아키텍처:**
- 신규 `game/difficulty.py`(순수 모듈, pygame import 없음) — `Difficulty` enum + 단계별 배율 표.
- `TitleScene`에 좌/우 화살표(또는 A/D) 토글로 EASY/NORMAL/HARD 전환, Space로 시작.
- `PlayScene` / `BonusScene`이 `Difficulty` 파라미터를 받아: 시작 라이프, 다이브 빈도 배율, 적 총알 속도 배율에 적용.
- 버그 수정: 매 프레임 다이브 검사 식의 `* dt * 60` → `* dt`. 변수 이름(`_dive_probability_per_sec`)대로 진짜 초당 비율이 되게.

**기술 스택:** Python 3.11+, Pygame (기존).

**스펙 참조:** [docs/superpowers/specs/2026-05-02-galaga-clone-design.ko.md](../specs/2026-05-02-galaga-clone-design.ko.md). 원래 스펙 §10 "미해결 / 향후 작업"의 추가 항목.

---

## 파일 구조

```
galaga-clone/
├── game/
│   └── difficulty.py            # NEW: Difficulty enum + 배율 표
├── scenes/
│   ├── title.py                 # MODIFY: 난이도 선택 UI
│   ├── play.py                  # MODIFY: difficulty 받기, 다이브 버그 수정, 배율 적용
│   └── bonus.py                 # MODIFY: difficulty 받기 (전달용)
└── tests/
    └── test_difficulty.py       # NEW: 배율 일관성 테스트
```

---

## Task 목록

### Task 1: `game/difficulty.py` + 테스트 작성

**파일:**
- 신규: `game/difficulty.py`
- 신규: `tests/test_difficulty.py`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

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
    """NORMAL 배율은 1.0이어서 기존 동작이 그대로 유지되어야 함."""
    n = config_for(Difficulty.NORMAL)
    assert n.dive_freq_multiplier == 1.0
    assert n.enemy_bullet_speed_multiplier == 1.0
```

- [ ] **Step 2: 테스트 실행, 실패 확인**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -v
```

기대: ImportError.

- [ ] **Step 3: 구현 작성**

`game/difficulty.py`:
```python
"""난이도 단계와 단계별 설정. 순수 모듈, pygame import 없음."""

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

- [ ] **Step 4: 테스트 통과 확인**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_difficulty.py -v
```

- [ ] **Step 5: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/difficulty.py tests/test_difficulty.py
git commit -m "feat(difficulty): Difficulty enum + per-level config with tests"
```

---

### Task 2: `scenes/play.py` 다이브 빈도 버그 수정

**파일:**
- 수정: `scenes/play.py`

현재 식은 `random.random() < self._dive_probability_per_sec * dt * 60`. `dt ≈ 1/60`이므로 사실상 `random() < 0.2` per frame이 되어 **초당 약 12회** 다이브 발생. 변수 이름이 "per second"이니 식은 `random() < self._dive_probability_per_sec * dt`로 바꿔서 진짜 초당 비율이 되게 한다.

- [ ] **Step 1: 식 수정**

`scenes/play.py`에서 다음을 찾아:
```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt * 60:
```

다음으로 교체:
```python
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt:
```

또한 진짜 초당 비율이 되었으니 기준값 자체도 재조정 필요. 현재 `_dive_probability_per_sec = 0.20 + 0.5 * p.dive_probability` → 약 0.2025 (per-frame 가정 하에). 합리적인 per-second 기준값으로 조정.

`_apply_wave_difficulty`를 다음으로 변경:
```python
    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        # 진짜 초당 비율 기준 (웨이브 1에서 0.5/초, 캡 근처에서 ~2.0/초)
        self._dive_probability_per_sec = 0.5 + 30.0 * p.dive_probability
```

- [ ] **Step 2: smoke import**

```powershell
.venv\Scripts\python.exe -c "from scenes.play import PlayScene; print('ok')"
```

- [ ] **Step 3: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/play.py
git commit -m "fix(play): correct dive-frequency unit (was ~12/s, now ~0.5/s base)"
```

---

### Task 3: PlayScene과 BonusScene에 difficulty 연결

**파일:**
- 수정: `scenes/play.py`
- 수정: `scenes/bonus.py`
- 수정: `entities/bullet.py`
- 수정: `entities/enemy.py`

- [ ] **Step 1: PlayScene.__init__에 difficulty 파라미터 추가**

`scenes/play.py` 상단에 import 추가:
```python
from game.difficulty import Difficulty, config_for
```

`__init__` 시그니처와 본문 변경:
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

(나머지 `__init__`는 그대로.)

- [ ] **Step 2: `_apply_wave_difficulty`에 배율 곱하기**

```python
    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        base_rate = 0.5 + 30.0 * p.dive_probability
        self._dive_probability_per_sec = base_rate * self._diff_cfg.dive_freq_multiplier
```

- [ ] **Step 3: 적 총알 속도 배율 적용**

가장 깔끔한 방법은 `EnemyBullet` 생성 시점에 배율 적용. `entities/bullet.py`의 `EnemyBullet.__init__`이 `speed_multiplier` 옵션을 받게 수정:

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

`entities/enemy.py`의 `Enemy.maybe_fire`에 옵션 추가:

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

`scenes/play.py` `update`의 다음 부분:
```python
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(self.player.pos)
                if bullet:
                    self.enemy_bullets.add(bullet)
```

다음으로 변경:
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

- [ ] **Step 4: 씬 전환 시 difficulty 전달**

`scenes/play.py`의 `if not self.enemies:` 블록에서 PlayScene factory:
```python
                self.manager.replace(
                    TransitionScene(
                        text,
                        lambda: type(self)(scoring=self.scoring, difficulty=self.difficulty),
                        duration=1.5,
                    )
                )
```

BonusScene factory:
```python
                self.manager.replace(
                    TransitionScene(
                        "CHALLENGING STAGE",
                        lambda: BonusScene(self.scoring, self.difficulty),
                        duration=1.8,
                    )
                )
```

- [ ] **Step 5: BonusScene이 difficulty 받고 다시 전달**

`scenes/bonus.py` import 추가:
```python
from game.difficulty import Difficulty
```

`__init__` 변경:
```python
    def __init__(self, scoring: Scoring, difficulty: Difficulty = Difficulty.NORMAL) -> None:
        self.difficulty = difficulty
        ...
```

`_finish` 메서드의 전환:
```python
        self.manager.replace(
            TransitionScene(
                f"STAGE {self.scoring.wave}",
                lambda: PlayScene(scoring=self.scoring, difficulty=self.difficulty),
                duration=1.5,
            )
        )
```

- [ ] **Step 6: 기존 테스트 + smoke import**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -c "from scenes.play import PlayScene; from scenes.bonus import BonusScene; from entities.bullet import EnemyBullet; print('ok')"
```

- [ ] **Step 7: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/play.py scenes/bonus.py entities/bullet.py entities/enemy.py
git commit -m "feat(difficulty): wire Difficulty through PlayScene, BonusScene, EnemyBullet"
```

---

### Task 4: TitleScene에 난이도 선택 UI 추가

**파일:**
- 수정: `scenes/title.py`

- [ ] **Step 1: 선택 상태 + 로직 추가**

`scenes/title.py` 내용 교체:

```python
"""타이틀 화면 -- Space로 시작. Arrow/A,D로 난이도 선택."""

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
        self._diff_index = 1  # NORMAL을 기본으로
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
        # 난이도 선택은 left/right 엣지 트리거
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

        # 난이도 행: < EASY  NORMAL  HARD >
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
        # 화살표
        arrow = self._font_med.render("<", True, settings.COLOR_CYAN)
        surface.blit(arrow, arrow.get_rect(center=(cx - 280, diff_y)))
        arrow_r = self._font_med.render(">", True, settings.COLOR_CYAN)
        surface.blit(arrow_r, arrow_r.get_rect(center=(cx + 280, diff_y)))

        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
        controls = self._font_sm.render(
            "Arrow / A,D 난이도 선택  |  Space 시작  |  Esc 종료",
            True,
            settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
```

- [ ] **Step 2: smoke import**

```powershell
.venv\Scripts\python.exe -c "import main; from scenes.title import TitleScene; print('ok')"
```

- [ ] **Step 3: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add scenes/title.py
git commit -m "feat(title): difficulty selector (EASY / NORMAL / HARD)"
```

---

### Task 5: 최종 검증 + 수동 플레이테스트

**파일:** 없음

- [ ] **Step 1: 전체 테스트 + 린트**

```powershell
.venv\Scripts\python.exe -m pytest -v
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
```

기대: 50개 이상 테스트 통과 (기존 45 + 신규 5), ruff clean.

- [ ] **Step 2: 수동 플레이테스트 체크리스트**

`python main.py` 실행 후 확인:
- [ ] 타이틀에 세 난이도 옵션 표시, NORMAL이 강조됨
- [ ] 좌/우 (또는 A/D)로 EASY/NORMAL/HARD 순환, 선택된 항목 강조
- [ ] EASY에서 SPACE: 라이프 4, 다이브 빈도 눈에 띄게 적음, 적 총알 느림
- [ ] NORMAL에서 SPACE: 라이프 3, 일반 페이스
- [ ] HARD에서 SPACE: 라이프 2, 다이브 빈도 높음, 적 총알 빠름
- [ ] 다이브 빈도가 합리적 (이전의 "총알 비"가 아니라) — 웨이브 1 NORMAL에서 1-2초당 1회 정도
- [ ] 보너스/웨이브 진행 후에도 난이도 유지 (전달됨)

- [ ] **Step 3: 브랜치 push**

```powershell
git push -u origin feat/difficulty-selection
```

---

## 자체 리뷰 메모

**스펙 커버리지:**
- 원래 스펙 §10 "향후 작업"에 난이도 선택은 없었음. 이번 feature는 *추가*.
- 모든 배율은 NORMAL에서 1.0이므로, (다이브 버그 수정을 빼면) 기존 동작이 그대로 유지됨.

**Placeholder 스캔:** TBD/TODO 없음. 모든 step이 정확한 코드 변경 포함.

**타입 일관성:** `Difficulty` enum, `DifficultyConfig` dataclass, `config_for()`가 Task 1-4 전반에 일관되게 참조됨.

**리스크:** Task 2의 버그 수정으로 NORMAL 게임플레이 특성이 "회피 불가능한 폭격"에서 "실제 플레이 가능한 수준"으로 바뀜. 이게 의도된 결과.
