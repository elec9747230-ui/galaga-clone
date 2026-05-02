# 트랙터 빔 / 듀얼 파이터 구현 계획

> **에이전트 작업자용:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (권장) 또는 superpowers:executing-plans 사용. 진행 추적은 체크박스(`- [ ]`).

**목표:** 원작 Galaga 트랙터 빔 포획 메커닉 구현 — 보스가 빔 발사, 플레이어 함선 포획, 함선이 보스 위에 떠서 포메이션에 함께; 그 보스가 포획 함선 데리고 다이브 중일 때 격파 = 구출 → 듀얼 파이터 (총알 2발).

**아키텍처:** spec의 접근 B — 별도 `TractorBeam` sprite + 순수 `CaptureManager` 상태머신. `BossEnemy`에 새 상태 3개; `Player`에 작은 플래그 추가; `PlayScene`이 사이클 조율.

**기술 스택:** Python 3.11+, Pygame (기존). 신규 의존성 없음. 빔 시각은 `pygame.draw.polygon` 런타임 그리기.

**스펙:** [docs/superpowers/specs/2026-05-02-tractor-beam-design.ko.md](../specs/2026-05-02-tractor-beam-design.ko.md)

---

## 파일 구조

```
galaga-clone/
├── settings.py                       # MODIFY: 트랙터 빔 + 점수 상수
│
├── entities/
│   ├── enemy.py                      # MODIFY: BossEnemy + 새 상태 3개 + captured_ship 슬롯
│   ├── player.py                     # MODIFY: dual_offset, is_left_half, is_right_half
│   ├── tractor_beam.py               # NEW: TractorBeam sprite (시각 + 다각형 충돌)
│   └── rescuing_ship.py              # NEW: RescuingShip sprite (하강하는 포획 함선)
│
├── game/
│   ├── capture.py                    # NEW: CaptureMode enum, CaptureState, CaptureManager
│   └── scoring.py                    # MODIFY: tractor (400) + rescue (800) 점수 종류
│
├── scenes/
│   └── play.py                       # MODIFY: tractor_beams 그룹, capture 오케스트레이션, 듀얼 모드
│
└── tests/
    ├── test_capture.py               # NEW: CaptureManager 단위 테스트 ~14개
    └── test_scoring.py               # MODIFY: tractor/rescue 격파 테스트 +2
```

---

## Task 목록

(전체 코드 블록은 영문판과 동일하게 유지 — Python 식별자/문자열은 영어 그대로. 산문/단계 제목만 한국어. 영문판: [2026-05-02-tractor-beam.md](2026-05-02-tractor-beam.md))

### Task 1: `settings.py`에 트랙터 빔 상수 추가

**파일:**
- 수정: `settings.py`

- [ ] **Step 1: Scoring 섹션 끝에 상수 추가**

`settings.py`에서 `# Scoring` 섹션 찾아 `LIFE_BONUS_PERFECT = 1` 다음에 추가:

```python
SCORE_TRACTOR_KILL = 400
SCORE_RESCUE_KILL = 800
```

`# Bonus stage` 뒤에 새 섹션 추가:

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

# Difficulty multipliers (Task 5에서 game/difficulty.py에도 추가)
```

- [ ] **Step 2: import 확인**

```powershell
.venv\Scripts\python.exe -c "import settings; print(settings.SCORE_TRACTOR_KILL, settings.TRACTOR_BEAM_PROBABILITY)"
```

기대: `400 0.3`

- [ ] **Step 3: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add settings.py
git commit -m "feat(settings): tractor beam + scoring constants"
```

---

### Task 2: `game/scoring.py`에 `tractor`/`rescue` 종류 추가 (TDD)

**파일:**
- 수정: `game/scoring.py`
- 수정: `tests/test_scoring.py`

- [ ] **Step 1: `tests/test_scoring.py` 끝에 실패 테스트 추가**

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

- [ ] **Step 2: 실행, 실패 확인**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_scoring.py::test_add_kill_tractor tests/test_scoring.py::test_add_kill_rescue -v
```

기대: 둘 다 `ValueError: Unknown enemy kind: 'tractor'` (또는 'rescue')로 실패.

- [ ] **Step 3: `game/scoring.py`의 `_KILL_SCORES` 갱신**

`_KILL_SCORES` dict 찾아서 두 키 추가:

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

- [ ] **Step 4: 테스트 통과 확인**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_scoring.py -v
```

기대: 17개 모두 통과 (기존 15 + 신규 2).

- [ ] **Step 5: 포맷 + 커밋**

```powershell
.venv\Scripts\ruff.exe check . --fix
.venv\Scripts\ruff.exe format .
.venv\Scripts\ruff.exe format --check .
git add game/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): add tractor (400) and rescue (800) kill kinds"
```

---

### Task 3: `game/capture.py` — Capture 상태머신 (TDD)

**파일:**
- 신규: `game/capture.py`
- 신규: `tests/test_capture.py`

상세한 코드는 영문 plan의 Task 3 참조. 같은 16개 단위 테스트 + `CaptureManager` 구현.

- [ ] **Step 1**: 영문 Task 3 Step 1의 16개 테스트 그대로 `tests/test_capture.py` 작성
- [ ] **Step 2**: 실행, ImportError 확인
- [ ] **Step 3**: 영문 Task 3 Step 3의 `game/capture.py` 그대로 작성
- [ ] **Step 4**: 16개 테스트 통과 확인
- [ ] **Step 5**: 포맷 + 커밋

```powershell
git add game/capture.py tests/test_capture.py
git commit -m "feat(capture): pure CaptureManager state machine with tests"
```

---

### Task 4: `entities/tractor_beam.py` — TractorBeam sprite

**파일:**
- 신규: `entities/tractor_beam.py`

영문 Task 4 Step 1의 모듈 그대로 작성. 핵심:
- `pygame.sprite.Sprite` 상속, 보스 참조 보유
- `update(dt)`: lifetime 감소, 줄무늬 phase 진행
- `contains(point)`: 점-다각형 충돌 (capture 검사용)
- `draw(surface)`: 노란색/파란색 줄무늬 삼각형 렌더링 (`pygame.draw.polygon` + `BLEND_RGBA_MIN` 클립)

- [ ] **Step 1**: 영문 Task 4 Step 1의 코드로 모듈 작성
- [ ] **Step 2**: smoke import
- [ ] **Step 3**: 포맷 + 커밋

```powershell
git add entities/tractor_beam.py
git commit -m "feat(entities): TractorBeam sprite with striped polygon rendering"
```

---

### Task 5: `game/difficulty.py`에 트랙터 확률 배율 추가

**파일:**
- 수정: `game/difficulty.py`
- 수정: `tests/test_difficulty.py`

- [ ] **Step 1: `DifficultyConfig`에 필드 추가, `_CONFIGS` 갱신**

`game/difficulty.py`에서 dataclass 수정:

```python
@dataclass(frozen=True)
class DifficultyConfig:
    starting_lives: int
    dive_freq_multiplier: float
    enemy_bullet_speed_multiplier: float
    tractor_probability_multiplier: float
```

`_CONFIGS` 갱신 (영문 Task 5 Step 1 참조).

- [ ] **Step 2: `tests/test_difficulty.py`에 테스트 추가**

```python
def test_tractor_probability_multipliers():
    assert config_for(Difficulty.EASY).tractor_probability_multiplier == 0.5
    assert config_for(Difficulty.NORMAL).tractor_probability_multiplier == 1.0
    assert config_for(Difficulty.HARD).tractor_probability_multiplier == 1.5
```

- [ ] **Step 3: 전체 테스트 실행**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 4: 포맷 + 커밋**

```powershell
git add game/difficulty.py tests/test_difficulty.py
git commit -m "feat(difficulty): add tractor_probability_multiplier"
```

---

### Task 6: `entities/enemy.py` — BossEnemy 트랙터 상태

**파일:**
- 수정: `entities/enemy.py`

`EnemyState` enum에 3개 추가, `Enemy.__init__`에 `captured_ship` 필드, `enter_tractor_align()` / `attach_captured_ship()` / `_update_tractor_aligning()` / `_update_returning_with_capture()` 메서드 추가, `update()` 디스패치 확장.

- [ ] **Step 1**: 영문 Task 6 Step 1의 모든 코드 변경 적용
- [ ] **Step 2**: smoke import (`EnemyState.TRACTOR_ALIGNING` 출력 확인)
- [ ] **Step 3**: 포맷 + 커밋

```powershell
git add entities/enemy.py
git commit -m "feat(enemy): tractor states (aligning/beaming/returning_with_capture) + captured_ship slot"
```

---

### Task 7: `entities/player.py` — 듀얼 파이터 플래그

**파일:**
- 수정: `entities/player.py`

`Player.__init__`에 `dual_offset: int = 0`, `is_right_half: bool = False` 인자 추가, 본문에서 spawn 위치에 offset 반영, 플래그 설정.

- [ ] **Step 1**: 영문 Task 7 Step 1의 변경 적용
- [ ] **Step 2**: smoke 인스턴스화 (`p.dual_offset, p.is_right_half` 출력)
- [ ] **Step 3**: 포맷 + 커밋

```powershell
git add entities/player.py
git commit -m "feat(player): dual fighter offset/half flags"
```

---

### Task 8: `entities/rescuing_ship.py` — 하강하는 포획 함선

**파일:**
- 신규: `entities/rescuing_ship.py`

영문 Task 8 Step 1의 모듈 그대로 작성. `RescuingShip(start_pos, target_player, on_arrival)` — target에 도달 시 `on_arrival` 콜백 + `self.kill()`.

- [ ] **Step 1**: 영문 Task 8 Step 1의 코드로 모듈 작성
- [ ] **Step 2**: smoke import
- [ ] **Step 3**: 포맷 + 커밋

```powershell
git add entities/rescuing_ship.py
git commit -m "feat(entities): RescuingShip sprite for dual-fighter merge animation"
```

---

### Task 9: `scenes/play.py` — 트랙터 빔 오케스트레이션 연결

**파일:**
- 수정: `scenes/play.py`

가장 큰 task. 영문 Task 9의 12개 step을 순서대로 적용:

- [ ] **Step 1**: 새 import 추가 (`TractorBeam`, `RescuingShip`, `CaptureManager`, `CaptureMode`)
- [ ] **Step 2**: `__init__` 수정 — `dual: bool = False` 인자, `players` Group 사용 (단일 → 듀얼 인스턴스화 지원), `tractor_beams` / `rescuing_ships` / `capture_mgr` 추가
- [ ] **Step 3**: 다이브 트리거에 트랙터 굴림 추가 (보스 + capture_mgr.can_start + 확률 + difficulty 배율)
- [ ] **Step 4**: 다이브 트리거 직후 빔 spawn 검사 추가
- [ ] **Step 5**: update 루프에 트랙터 빔 / 구출 함선 갱신 + 빔 충돌 + 만료 처리 + AWAITING_RESCUE 타이머 추가
- [ ] **Step 6**: `_perform_capture` / `_perform_rescue` / `_complete_rescue` / `_game_over` 메서드 추가
- [ ] **Step 7**: 기존 player 갱신 로직을 함선별로 변경 (듀얼 모드 지원)
- [ ] **Step 8**: 충돌 처리 변경 — 보스 격파 분기 (트랙터 모드 / 구출 / 일반), 함선별 충돌, `_kill_player_half` 추가
- [ ] **Step 9**: 웨이브 클리어 시 PlayScene 재생성에 `dual` 플래그 전달
- [ ] **Step 10**: `draw`에 captured_ship 위에 그리기, rescuing_ships, tractor_beams 그리기 추가
- [ ] **Step 11**: smoke 테스트 + 전체 테스트
- [ ] **Step 12**: 포맷 + 커밋

```powershell
git add scenes/play.py
git commit -m "feat(play): tractor beam + capture/rescue + dual fighter orchestration"
```

---

### Task 10: 최종 검증 + push

**파일:** 없음

- [ ] **Step 1**: 전체 테스트 + 린트 (70+ 테스트 통과 기대)
- [ ] **Step 2**: end-to-end smoke import (`import main`)
- [ ] **Step 3**: 수동 플레이테스트 체크리스트 (영문 Task 10 Step 3 참조)
- [ ] **Step 4**: push

```powershell
git push -u origin feat/tractor-beam
```

---

## 자체 리뷰 메모

영문판과 동일 (영문판: [2026-05-02-tractor-beam.md §Self-Review Notes](2026-05-02-tractor-beam.md)).

- 스펙 §3, §4, §5, §6, §7, §8 모두 task로 커버.
- Placeholder 없음.
- 타입 일관성: `CaptureMode`/`CaptureManager` 메서드명, `EnemyState` 새 값, `TractorBeam.boss/contains/expired`, `Player.dual_offset/is_left_half/is_right_half` 모두 task 간 일관.
- 리스크: Task 9가 큼 (~200 줄). step 단위로 smoke import 자주 돌려서 syntax 오류 조기 발견.
