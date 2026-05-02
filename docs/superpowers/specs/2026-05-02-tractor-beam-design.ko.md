# 트랙터 빔 / 듀얼 파이터 — 설계 명세

**작성일:** 2026-05-02
**상태:** 승인됨 (구현 계획 대기)
**범위:** Galaga의 트랙터 빔 포획 메커닉 + 듀얼 파이터 구출. 원작에 충실.

이 기능은 원래 spec ([2026-05-02-galaga-clone-design.ko.md §10](2026-05-02-galaga-clone-design.ko.md))에 "향후 작업"으로 명시됨. 프로젝트를 "Classic Core"에서 "Full Clone" 쪽으로 확장.

---

## 1. 목표 및 범위

목표:
- 보스 적이 다이브 중 트랙터 빔 발사 가능.
- 빔에 잡힌 플레이어 함선 포획: 라이프 -1, 함선이 포메이션으로 끌려감.
- 포획된 함선은 포획 보스 위에 떠서 포메이션에 함께 있음. 보스가 다음 다이브할 때 같이 따라 내려옴.
- 포획된 함선과 함께 다이브 중인 보스를 격파 = 구출 → 함선이 현재 플레이어와 합체해 듀얼 파이터 (총알 2발 동시).
- 마지막 라이프에 포획되면 5초 구출 대기 — 즉시 game over 안 함.

**범위 내:**
- 보스 상태머신 확장 (`TRACTOR_ALIGNING`, `TRACTOR_BEAMING`, `RETURNING_WITH_CAPTURE`).
- 줄무늬 애니메이션 트랙터 빔 (`pygame.draw` 런타임 그리기, PNG 에셋 없음).
- Capture 상태머신 (순수 모듈, 단위 테스트 가능).
- 듀얼 파이터: 함선 2개 나란히, 총알 2발 동시, 좌/우 hitbox 독립.
- 새 점수: 트랙터 모드 보스 격파 400, 구출 격파 800, 포획된 함선 실수 발사 시 영구 손실.
- 난이도 배율 (EASY 0.5 / NORMAL 1.0 / HARD 1.5).

**범위 밖 (여전히 안 함):**
- 원작의 "FIGHTER CAPTURED" / "OK" 텍스트 오버레이.
- 트리플 파이터 치트.
- 보너스 스테이지 트랙터 빔 (보너스 = 적이 안 쏨 규칙 유지).

---

## 2. 기술 선택

신규 의존성 없음. 트랙터 빔은 `pygame.draw.polygon` 런타임 그리기 (Pillow PNG 불필요). 포획된 함선 sprite는 기존 `player.png` 어둡게 tint해서 재사용.

---

## 3. 게임 디자인 파라미터

| 파라미터 | 값 |
|---|---|
| 트랙터 빔 확률 (NORMAL, 보스 다이브 시작 시) | 0.30 |
| 트랙터 확률 난이도 배율 | EASY 0.5, NORMAL 1.0, HARD 1.5 |
| 빔 지속시간 | 3.0초 |
| 빔 폭 (위, 보스 부근) | 24 px |
| 빔 폭 (아래, 플레이어 부근) | 60 px |
| 빔 capture grace | 0.3초 누적 overlap → 포획 |
| 빔 줄무늬 색 | 노란색 `(240, 220, 60)`, 파란색 `(60, 120, 240)` |
| 줄무늬 띠 높이 | 14 px |
| 줄무늬 스크롤 속도 | 240 px/s 아래로 |
| 보스 정렬 이동 속도 | 200 px/s |
| 포획된 함선 복귀 속도 (보스 동반) | 220 px/s |
| 구출 함선 하강 속도 (보스 격파 후) | 220 px/s |
| 동시 활성 트랙터 빔 | 최대 1 |
| 점수: 트랙터 모드 보스 격파 (포획 전) | 400 |
| 점수: 구출 격파 (포획 함선 데리고 다이브 중인 보스) | 800 |
| 점수: 포획 함선 들고 포메이션에 있는 보스 격파 | 150 (기존), 포획된 함선 같이 손실 |
| 점수: 포획된 함선 실수 발사 | 0, 함선 영구 손실 |
| 마지막 라이프 구출 윈도우 | 5.0초 |
| 듀얼 파이터 가로 오프셋 | 함선 사이 중심에서 ±22 px |
| 듀얼 파이터 발사 | Space 1회당 2발 (함선당 1발) |
| 화면 최대 플레이어 총알 (듀얼) | 4 (단일은 2) |

---

## 4. 아키텍처 (접근 B — 별도 TractorBeam 엔티티 + 순수 capture 모듈)

### 파일 변경

```
galaga-clone/
├── settings.py                       # MODIFY: 트랙터 빔 상수
│
├── entities/
│   ├── enemy.py                      # MODIFY: BossEnemy에 트랙터 상태 + captured_ship 슬롯
│   ├── player.py                     # MODIFY: dual_offset / is_left_half / is_right_half 플래그
│   └── tractor_beam.py               # NEW: TractorBeam sprite (시각 + 다각형 contains)
│
├── game/
│   ├── capture.py                    # NEW: CaptureMode enum, CaptureState dataclass, CaptureManager
│   └── scoring.py                    # MODIFY: 'tractor' (400), 'rescue' (800) kind 추가
│
├── scenes/
│   └── play.py                       # MODIFY: tractor_beams 그룹, capture 오케스트레이션, 듀얼 spawn
│
└── tests/
    ├── test_capture.py               # NEW: CaptureManager ~14 단위 테스트
    └── test_scoring.py               # MODIFY: tractor/rescue 점수 테스트 +2
```

### 모듈 경계

- `game/capture.py`: 순수 데이터 + 상태 전이. sprite/surface/렌더링 무관. capture 관련 단일 진실 소스.
- `entities/tractor_beam.py`: 시각 + 충돌. 부모 `BossEnemy` 위치 추적. 다각형 `contains(point)` 검사 (rect 충돌은 삼각형이라 부정확).
- `entities/enemy.py`: `BossEnemy`에 새 상태 추가. `captured_ship: Optional[Surface]` 필드는 렌더링용 — capture 상태는 `CaptureManager`에 있음.
- `entities/player.py`: 최소 변경 — `dual_offset`, `is_left_half`, `is_right_half` 플래그만. 듀얼 파이터는 `Player` 인스턴스 2개 나란히; 별도 `DualFighter` 클래스 없음.
- `scenes/play.py`: 모든 걸 조율. `tractor_beams: pygame.sprite.Group`과 `CaptureManager` 인스턴스 보유. 모든 mode 전이는 manager 통해서.

---

## 5. 컴포넌트

### `game/capture.py`

```python
class CaptureMode(Enum):
    NORMAL           # 평소
    BEAMING          # 빔에 들어가는 중, grace 누적
    CAPTURED         # 포획됨; 보스가 데려가는 중
    AWAITING_RESCUE  # 라이프 0 + 포획됨; game-over 보류 + 타이머
    RESCUING         # 보스 격파됨; 포획된 함선이 플레이어로 내려옴
    DUAL             # 듀얼 파이터 활성

@dataclass
class CaptureState:
    mode: CaptureMode = CaptureMode.NORMAL
    captor_boss_id: int | None = None
    rescue_timer: float = 0.0      # AWAITING_RESCUE 카운트다운
    beam_grace: float = 0.0        # BEAMING 누적

class CaptureManager:
    state: CaptureState
    active_tractor_boss_id: int | None  # 현재 빔 발사 중인 보스

    def can_start_tractor(self, boss_id: int) -> bool
    def begin_beam(self, boss_id: int) -> None
    def update_beam(self, dt: float, in_beam: bool) -> bool   # True면 capture 트리거
    def on_beam_ended(self) -> None                            # 보스 빔 종료, capture 안 됨
    def on_captured(self, boss_id: int, lives_after: int) -> None
    def on_captor_destroyed(self) -> None                      # 포획한 보스 격파됨
    def on_rescue_eligible_kill(self) -> bool                  # True면 RESCUING 진입
    def on_dual_lost(self) -> None
    def on_rescue_complete(self) -> None                       # DUAL 진입
    def update_awaiting_rescue(self, dt: float) -> bool       # True면 timeout (game over)
```

pygame import 없음. 호출자가 작용할 수 있는 boolean / state 반환.

### `entities/tractor_beam.py`

```python
class TractorBeam(pygame.sprite.Sprite):
    """보스에 부착된 줄무늬 삼각 빔. lifetime 만료 시 자가 제거."""

    def __init__(self, boss: BossEnemy) -> None: ...
    def update(self, dt: float) -> None:
        # 보스 x 따라가기; 줄무늬 phase 진행; lifetime 감소
    def draw(self, surface: pygame.Surface) -> None:
        # pygame.draw.polygon + clip rect로 줄무늬 삼각형 렌더링
    def contains(self, point: pygame.Vector2) -> bool:
        # capture 검사용 점-다각형 테스트
    @property
    def expired(self) -> bool: ...
```

`update`와 `draw`가 분리됨 (image/rect 통한 표준 sprite 패턴 아님) — 줄무늬 애니메이션이 매 프레임 절차적 렌더링 필요해서.

### `entities/enemy.py` — BossEnemy 추가

새 상태 (`EnemyState` enum에 추가):
- `TRACTOR_ALIGNING` — 보스가 플레이어 위로 가로 정렬.
- `TRACTOR_BEAMING` — 보스 정지; 트랙터 빔이 씬에 존재.
- `RETURNING_WITH_CAPTURE` — 보스가 포획 함선과 함께 자기 슬롯으로 복귀.

`Enemy`에 새 필드:
- `captured_ship: pygame.Surface | None = None` — 존재 시 적 위에 그려짐.

`BossEnemy`에 새 메서드:
- `enter_tractor_align(player_pos)` — 상태 설정, 타겟 x 저장.
- `update_tractor_align(dt, player_pos)` — 타겟 x 쪽으로 이동; 허용 오차 내면 `TRACTOR_BEAMING` 전환.
- `update_tractor_beaming(dt)` — 위치 유지. 빔은 PlayScene의 그룹이 보유 (적이 보유 X).
- `attach_captured_ship(surface)` — `captured_ship` 필드 설정, `RETURNING_WITH_CAPTURE` 전환.
- `update_returning_with_capture(dt)` — 포메이션 슬롯으로 직선 이동; 도착 시 `IN_FORMATION`.

포메이션에서 captured_ship 렌더링:
- `Enemy.update()`은 rect 갱신 (기존). PlayScene이 적을 평소처럼 그림. captured ship은 PlayScene이 (또는 Enemy의 `extra_draw` 훅) `(enemy.rect.centerx, enemy.rect.top - ship.height/2 - 2)` 위치에 그림.

### `entities/player.py` — 작은 추가

새 필드:
```python
class Player(pygame.sprite.Sprite):
    dual_offset: int = 0          # 0: 단일, -22: 좌측, +22: 우측
    is_left_half: bool = False
    is_right_half: bool = False
```

`Player.update`은 이동 로직 그대로. 오프셋은 초기 spawn 위치만 바꿈. 총알은 기존대로 `(self.pos.x, self.pos.y - height/2)`에서 발사 — 호출 씬이 players 그룹의 함선마다 발사함.

듀얼 파이터 이동: `PlayScene`이 매 프레임 두 Player 인스턴스에 같은 input을 줌. 같은 input + 같은 clamping이라 같이 움직임.

엣지 케이스 — clamping: 듀얼 모드에서 좌측 함선의 x는 가장 좌측 sprite 폭의 절반 이상이어야 하고, 우측 함선의 x는 playfield_width - 폭/2 이하. PlayScene이 결합 clamp 영역 계산해서 두 함선에 적용.

### `scenes/play.py` — 추가

새 필드:
```python
self.tractor_beams: pygame.sprite.Group
self.capture_mgr: CaptureManager
self.captured_ships: pygame.sprite.Group  # RESCUING 중에만 (하강 함선)
```

생성자에 옵션 `dual: bool = False` — 웨이브 사이 듀얼 상태 인계.

`update(dt, inp)` 확장 (기존 단계 후 순서대로):
1. 트랙터 빔 갱신 (`for b in tractor_beams: b.update(dt)`); 만료 제거.
2. 트랙터 빔 vs 플레이어 충돌: 각 빔에 대해 `beam.contains(player.center)`을 각 player sprite에 대해 검사. 결과를 `capture_mgr.update_beam(dt, in_beam=True/False)`에 전달. True 반환 시 (capture 트리거) `_perform_capture(beam, players_in_beam)` 호출.
3. capture manager의 awaiting-rescue 타이머 갱신. True 반환 시 (timeout) → `_game_over()`.
4. (기존) 새 다이브 트리거. 보스 적의 경우 `capture_mgr.can_start_tractor(boss.id)` 검사 + 트랙터 확률 굴림으로 수정.

`_handle_collisions` 확장:
1. (기존) `player_bullets ⨯ enemies` 충돌 — 적 격파 시 검사:
   - 적이 보스 + `captured_ship` 있음 + 상태 == `DIVING` → `_perform_rescue(enemy)`.
   - 그렇지 않으면, 적이 보스 + 상태 `TRACTOR_BEAMING` 또는 `TRACTOR_ALIGNING` → `add_kill("tractor")` (400) + `tractor_beams.empty_for(enemy)`.
   - 그 외 → 기존 점수.
2. 신규: `player_bullets ⨯ captured_ships_in_formation` (별도로 그려지지만 자체 rect 있음) — 포획 함선 격파, 점수 0, manager `on_captor_destroyed_for_capture(enemy)`.
3. (기존) Player vs 적 / 적 총알 — 듀얼 모드는 함선별 (둘에 대해 루프, 각자 독립 격파).

`_perform_capture(beam, captured_players)`:
- 각 포획된 player에 대해 (단일이면 1, 듀얼이면 좌측만 가능):
  - 플레이어 위치에 폭발 추가.
  - 그 Player를 players 그룹에서 제거.
  - 듀얼 케이스: `capture_mgr.on_dual_lost()` 후 on_captured.
- `scoring.lose_life()`.
- `assets.sprite("player")` 복사본을 50% 어둡게 tint → `captured_surface`.
- 포획 보스에 부착: `boss.captured_ship = captured_surface`, `boss.attach_captured_ship(...)` (상태 → RETURNING_WITH_CAPTURE).
- `tractor_beams.empty_for(boss)`.
- `capture_mgr.on_captured(boss.id, lives_after=scoring.lives)`.
- `scoring.lives == 0`이면: capture_mgr가 AWAITING_RESCUE (5초 타이머) 진입. 재스폰 시작 안 함.
- 그렇지 않으면: 재스폰 타이머 시작; 재스폰 시 새 Player 단일로 spawn (mode는 CAPTURED지만 표시는 일반 단일).

`_perform_rescue(boss)`:
- `scoring.score += 800` (또는 `add_kill("rescue")`).
- 보스 위치에 폭발 추가.
- `RescuingShip` sprite를 `boss.rect.center`에 spawn, 현재 player 향해 이동.
- `capture_mgr.on_rescue_eligible_kill()`.
- 보스는 평소처럼 격파 (enemies 그룹에서 제거).
- `boss.captured_ship = None` (RescuingShip으로 이전).

`_complete_rescue(rescue_ship, current_player)`:
- 두 번째 Player를 `current_player.pos.x + 22`에 `is_right_half=True`, `dual_offset=22`로 spawn.
- 현재 player를 `is_left_half=True`, `dual_offset=-22`로 표시.
- `capture_mgr.on_rescue_complete()`.
- SFX 재생.

### `entities/rescuing_ship.py` — 작은 신규 파일 (또는 play.py 안)

```python
class RescuingShip(pygame.sprite.Sprite):
    """현재 player에 합체하러 내려오는 포획 함선. 도착 시 콜백 트리거."""

    def __init__(self, start_pos, target_player, on_arrival): ...
    def update(self, dt: float) -> None:
        # target_player.pos 향해 220 px/s 이동
        # 4 px 이내 → on_arrival(self) 호출 + self.kill()
```

가벼움 — `entities/player.py`나 `scenes/play.py`에 둘 수도. 일관성을 위해 `entities/`에 둠.

### `game/scoring.py` 수정

`_KILL_SCORES`에 추가:
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

`settings.py`에 추가:
```python
SCORE_TRACTOR_KILL = 400
SCORE_RESCUE_KILL = 800
```

---

## 6. 데이터 흐름

### 트랙터 시퀀스 (한 사이클)

```
[보스 다이브 시작]
  PlayScene.update가 다이브 가능한 in-formation 보스 찾음.
  if isinstance(boss, BossEnemy) and capture_mgr.can_start_tractor(boss.id):
      if random() < tractor_probability * difficulty.tractor_mult:
          boss.enter_tractor_align(player.pos); capture_mgr.begin_beam(boss.id)
          continue
  boss.start_dive(...)  # 표준 다이브

[TRACTOR_ALIGNING]
  매 프레임: 보스가 player.x 향해 200 px/s로 슬라이드.
  5 px 이내 → 상태 TRACTOR_BEAMING, TractorBeam(boss) spawn.

[TRACTOR_BEAMING]
  TractorBeam이 매 프레임 갱신 (줄무늬 phase, lifetime).
  PlayScene이 활성 player마다 beam.contains(player.center) 검사.
  capture_mgr.update_beam(dt, in_beam) → grace 0.3초 도달 시 True.
  beam.expired → tractor_beams.kill, capture_mgr.on_beam_ended,
                 boss.start_dive() (일반 다이브 재개).

[CAPTURE]
  위 _perform_capture 참조.
  → 보스 상태 RETURNING_WITH_CAPTURE; player 제거; 0.5초 후 새 player 재스폰
    (라이프 0이면 AWAITING_RESCUE).

[RETURNING_WITH_CAPTURE → IN_FORMATION (with captured_ship)]
  보스가 포메이션 슬롯으로 복귀; captured_ship 위에 표시.

[포획 보스의 다음 다이브]
  보스 DIVING 진입; captured_ship이 같이 움직임 (위에 표시).

[다이브 중 captured_ship 보유 보스 격파]
  → _perform_rescue: RescuingShip spawn; 점수 += 800.

[RESCUING → DUAL]
  RescuingShip 하강; 도착 시 두 번째 Player 추가; mode = DUAL.
```

### 매 프레임 갱신 순서 (PlayScene.update)

```
1. INPUT
2. UPDATE
   ├─ Players (단일 또는 듀얼 시 2개)
   ├─ Bullets (player + enemy)
   ├─ Enemies
   ├─ TractorBeams
   ├─ RescuingShips
   ├─ Explosions
   ├─ 새 다이브 트리거 (트랙터 확률 검사 포함)
   └─ CaptureManager.update_awaiting_rescue → game over 신호 가능
3. COLLIDE
   ├─ player_bullets ⨯ enemies
   │    (보스 격파는 상태별로 분기: tractor / rescue / normal)
   ├─ player_bullets ⨯ captured_ships (포메이션)
   ├─ enemy_bullets ⨯ players (듀얼은 함선별)
   ├─ diving enemies ⨯ players (함선별)
   └─ tractor_beams ⨯ players (다각형 contains)
4. DRAW
```

---

## 7. 에러 처리

(원래 spec의 "경계만 검증; 내부 호출은 신뢰" 원칙 유지.)

| 실패 / 엣지 | 처리 |
|---|---|
| 같은 프레임에 보스 둘이 트랙터 시도 | `can_start_tractor`가 첫 번째에만 True; 두 번째는 일반 다이브 |
| 빔 활성 보스가 빔 도중 격파 | 빔 제거; `capture_mgr.on_beam_ended`; mode 그대로 (capture 안 일어났으니 NORMAL) |
| 포획 보스가 포메이션에서 격파 (다이브 X) | 포획 함선 영구 손실; mode → NORMAL (또는 AWAITING_RESCUE이면 game over) |
| 플레이어가 실수로 captured_ship 발사 | 포획 함선 sprite를 보스에서 제거; 점수 없음; 보스는 살아있음; `capture_mgr.on_captor_destroyed` |
| 마지막 라이프 capture 후 보스가 다이브 안 하고 포메이션에 있음 | AWAITING_RESCUE 타이머 계속 카운트다운; 결국 timeout → game over |
| 듀얼 파이터, 같은 프레임에 양쪽 hit (예: 큰 다이브 적이 양쪽 걸침) | 둘 다 죽음, 라이프 -2; lives ≤ 0면 game over |
| mode == DUAL인 채 웨이브 클리어 | 새 PlayScene 생성자에 `dual=True` 전달; 두 함선 다시 spawn; mode 유지 |
| mode == CAPTURED인 채 웨이브 클리어 | 포획 함선과 보스가 방금 죽은 적 집합에 있음 — 이미 사라짐; `on_captor_destroyed`로 mode → NORMAL. (보스가 웨이브 클리어 엣지로 살아남으면 captured_ship 폐기 + mode reset) |
| 씬 전환 시 빔 존재 | `PlayScene.on_exit`이 tractor_beams 그룹 비움 |
| AWAITING_RESCUE 중 보너스 스테이지 진입 | 발생 불가 (AWAITING_RESCUE = lives==0; 보너스 전에 game over 발생) |
| 게임 중 난이도 토글 (UI 미허용) | 현재 UI에서 불가능 |

---

## 8. 테스팅

### 단위 테스트 (`tests/test_capture.py`)

`CaptureManager`의 모든 전이/엣지 ~14 테스트:
- 초기 상태가 NORMAL.
- `can_start_tractor` idle 시 true.
- `can_start_tractor` 다른 보스 빔 중이거나 mode가 (BEAMING/CAPTURED/AWAITING_RESCUE/RESCUING/DUAL)이면 false.
- `begin_beam`이 active_tractor_boss_id 설정.
- `update_beam(dt, True)` grace 누적; 0.3 도달 시 True.
- `update_beam(dt, False)` grace reset.
- `on_beam_ended` active_tractor_boss_id 클리어.
- `on_captured(lives_after>0)` → mode CAPTURED.
- `on_captured(lives_after=0)` → mode AWAITING_RESCUE, rescue_timer = 5.0.
- `update_awaiting_rescue(6.0)` True (timeout).
- `update_awaiting_rescue(1.0)` False, 타이머 감소.
- `on_captor_destroyed` from CAPTURED → mode NORMAL (lives 있음) 또는 AWAITING_RESCUE → game-over 신호.
- `on_rescue_eligible_kill` from CAPTURED → mode RESCUING.
- `on_rescue_complete` → mode DUAL.
- `on_dual_lost` from DUAL → mode NORMAL.

### 단위 테스트 (`tests/test_scoring.py` 추가)

- `add_kill("tractor")` → score += 400.
- `add_kill("rescue")` → score += 800.

### 수동 플레이테스트 체크리스트

1. 보스 트랙터 확률 — NORMAL 5분 플레이 시 1~2회 관찰.
2. 포획 사이클: 일부러 빔 들어가기 → 보스가 함선 데려감 → 다음 다이브 때 격파 → 듀얼 파이터.
3. 트랙터 모드 보스 격파 (포획 전) → 400점, 포획 안 됨.
4. 포획된 함선 실수 발사 → 영구 손실, 점수 0.
5. 마지막 라이프 capture: 5초 윈도우 — 구출 성공 시 듀얼 부활.
6. 마지막 라이프 capture: timeout → game over.
7. 듀얼 파이터: 좌측만 hit → 우측 함선 살아남음.
8. 듀얼 파이터: 큰 다이브 보스에 같은 프레임 양쪽 hit → 둘 다 죽음.
9. 보스 웨이브 (보스 5+): 동시 트랙터 1개만.
10. 보너스 스테이지: 트랙터 빔 없음 (보스 적 자체가 없으니 자연스럽게도, 클래스로도 검증).
11. DUAL 상태로 웨이브 클리어: 다음 웨이브에 두 함선 그대로.
12. 난이도 배율: EASY는 트랙터 눈에 띄게 적고, HARD는 더 자주.

### 제약

- `game/capture.py`: `import pygame` 금지.
- `entities/tractor_beam.py`: pygame 허용 (렌더링 + 충돌).
- `entities/player.py`: 추가 최소화; 별도 DualFighter 클래스 만들지 말 것.

---

## 9. 미해결 / 향후 작업

여전히 미룬 항목:
- 원작의 "FIGHTER CAPTURED" / "OK" 텍스트 연출.
- 트리플 파이터 치트 (연속 두 번 capture).
- Stinger 게임플레이: 적의 "stinger" 포메이션 패턴.
- 보스 종류 구분 (빨간 보스 / 초록 보스).
