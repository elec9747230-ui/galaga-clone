# Galaga 클론 — 설계 명세

**작성일:** 2026-05-02
**상태:** 승인됨 (구현 계획 대기)
**범위:** Python + Pygame 기반 1인용 Galaga 클론, "Classic Core" 기능 + 보너스 스테이지

---

## 1. 목표 및 범위

"Classic Core" 수준의 충실한 Galaga 클론을 만든다. 목표:

- Galaga 특유의 느낌(포메이션 진입, 다이브 공격, 웨이브 진행)이 분명히 살아 있는 1인용 게임.
- 모든 에셋(스프라이트 + 오디오)을 코드로 생성 — 외부 다운로드 불필요.
- 개인 학습용 프로젝트, 공개 배포는 하지 않음.

**범위 내:**
- 플레이어 함선 (이동, 발사, 라이프, 재스폰)
- 적 포메이션 (5×8 = 40마리), 곡선 진입 경로
- 다이브 공격 패턴
- 웨이브 진행: 일반 4 → 보스 1 → 보너스 1, 무한 반복, 난이도 점진 상승
- 보너스 스테이지 (Challenging Stage): 적이 발사하지 않음, 시간 제한, 퍼펙트 시 +10000점 + 라이프 +1
- 사이드 패널 HUD (점수, 라이프, 웨이브, 하이스코어, 명중률, 격파 수)
- 원작 Galaga 멜로디를 코드로 합성한 chiptune 음악 (인트로, 스테이지 시작 등)
- 코드로 합성한 SFX (발사음, 폭발음 등)
- 영구 저장되는 하이스코어
- GitHub repo (공개) + GitHub Actions CI (pytest + ruff)

**범위 밖 (명시적 제외):**
- 트랙터 빔 / 듀얼 파이터 시스템
- Bee/Butterfly/Boss의 시각적 차이 (스프라이트는 placeholder, 색상·크기 변형으로만 구분)
- 온라인 하이스코어 리더보드
- 모바일/터치 컨트롤
- pytest, ruff 외 추가 CI 도구 (mypy, 커버리지 게이트 없음)

---

## 2. 기술 선택

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | 사용자 선호; Pygame 표준 |
| 게임 라이브러리 | Pygame (최신 안정) | 성숙, 단순, 2D 아케이드에 적합 |
| 스프라이트 생성 | Pillow (PIL) | 코드로 PNG 생성, 외부 에셋 불필요 |
| 오디오 생성 | NumPy → WAV | chiptune 멜로디 + SFX 합성 |
| 테스트 프레임워크 | pytest | 표준 |
| 린터/포매터 | ruff | 빠르고 black + flake8 + isort를 한 도구로 대체 |
| CI | GitHub Actions | 공개 repo는 무료, 표준 |
| Repo 공개 범위 | GitHub 공개 | 사용자 선택 |

---

## 3. 게임 디자인 파라미터

| 파라미터 | 값 |
|---|---|
| 창 크기 | 1280 × 720 (16:9) |
| 플레이필드 크기 | 540 × 720 (3:4, 원작 Galaga 비율, 가운데 정렬) |
| 사이드 패널 | 좌측 370 × 720, 우측 370 × 720 |
| 프레임 레이트 | 60 FPS, fixed timestep |
| 조작 | ←/→ 또는 A/D = 이동, Space = 발사, P = 일시정지, Esc = 종료 |
| 시작 라이프 | 3개 |
| 동시 발사 | 화면에 최대 2발 (원작 규칙) |
| 포메이션 | 5행 × 8열 = 40마리 |
| 웨이브 사이클 | 1–4 일반 → 5 보스 → 6 보너스 → 7–10 일반 → 11 보스 → 12 보너스 → ... |
| 난이도 진행 | 웨이브마다: 다이브 빈도 ↑, 적 속도 ↑, 적 총알 속도 ↑ (단조 증가) |
| 점수: 일반 격파 | 50점 |
| 점수: 다이브 중 격파 | 100점 |
| 점수: 보스 격파 | 150점 |
| 보너스 스테이지: 격파당 | 200점 |
| 보너스 스테이지: 퍼펙트 | +10000점 + 라이프 +1 |

### 사이드 패널 레이아웃

| 위치 | 내용 |
|---|---|
| 좌측 상단 | "GALAGA" 로고 |
| 좌측 중간 | SCORE (현재 점수, 큰 글씨) |
| 좌측 하단 | LIVES (함선 아이콘), 조작 키 안내 |
| 우측 상단 | HIGH SCORE |
| 우측 중간 | WAVE / STAGE 번호 |
| 우측 하단 | 명중률 %, 격파 수 |

---

## 4. 아키텍처 (접근 B — 다중 모듈 + 씬 상태머신)

### 프로젝트 구조

```
galaga-clone/
├── main.py                       # 진입점, pygame 초기화, 메인 루프
├── pyproject.toml                # 의존성 (pygame, numpy, pillow), ruff 설정
├── README.md
├── .gitignore                    # assets/, __pycache__ 등 제외
├── .github/
│   └── workflows/
│       └── ci.yml                # push 시 pytest + ruff
├── settings.py                   # 상수: 해상도, FPS, 색상, 점수, 키 매핑
│
├── assets/                       # 코드로 생성, 커밋하지 않음
│   ├── sprites/
│   └── audio/
│
├── tools/                        # 1회성 에셋 생성 스크립트
│   ├── generate_sprites.py
│   └── generate_audio.py
│
├── engine/                       # 게임 로직과 무관한 인프라
│   ├── __init__.py
│   ├── assets.py                 # 에셋 로딩, 캐싱
│   ├── audio.py                  # SFX/BGM 재생, 페이드
│   ├── input.py                  # InputState 추상화
│   └── scene.py                  # Scene 베이스, SceneManager
│
├── entities/                     # 게임 객체 (pygame.sprite.Sprite)
│   ├── __init__.py
│   ├── player.py
│   ├── enemy.py                  # Enemy + Bee/Butterfly/Boss
│   ├── bullet.py                 # PlayerBullet, EnemyBullet
│   └── explosion.py
│
├── game/                         # 순수 게임 규칙 (대부분 pygame 무관)
│   ├── __init__.py
│   ├── formation.py              # 슬롯 좌표 + 진입 베지어 경로
│   ├── wave.py                   # 웨이브 타입 enum, 사이클 진행
│   ├── dive.py                   # 다이브 공격 곡선
│   ├── scoring.py                # 점수, 라이프, 명중률, 하이스코어 영속
│   └── hud.py                    # 사이드 패널 렌더링
│
├── scenes/
│   ├── __init__.py
│   ├── title.py
│   ├── play.py
│   ├── bonus.py
│   ├── gameover.py
│   └── transitions.py
│
├── data/                         # 런타임 생성, gitignore
│   └── highscore.json
│
└── tests/
    ├── test_formation.py
    ├── test_scoring.py
    ├── test_wave.py
    └── test_dive.py
```

**모듈 책임 요약:**
- `engine/`: 재사용 가능한 인프라 (에셋, 입력, 오디오, 씬 관리).
- `entities/`: 화면에 그려지는 객체, 모두 `pygame.sprite.Sprite` 상속.
- `game/`: 순수 게임 로직. `scoring.py`, `wave.py`는 **`import pygame` 금지** (display 없이 단위 테스트 가능해야 함). `formation.py`, `dive.py`는 `pygame.Vector2`만 허용 — surface/sprite 금지.
- `scenes/`: 씬별 로직, entities + game 규칙을 통합. 전환은 `SceneManager`가 관리.
- `tools/`: `assets/`를 생성하는 독립 스크립트. 재실행 가능, idempotent.

파일 크기: 하드 캡 없음. 자연스럽게 비대해지면 분리.

---

## 5. 컴포넌트

### 메인 루프 & 씬 관리
- `main.py`: pygame 초기화, 1280×720 창 생성, `SceneManager`를 `TitleScene`으로 시작, fixed-timestep 60 FPS 루프 실행. 모든 update에 `dt`(델타 타임) 전달.
- `engine/scene.py`: `Scene` 베이스 클래스 (`handle_event(event)`, `update(dt, input)`, `draw(surface)`) + `SceneManager` (현재 씬 + 전환 큐 push/pop/replace).

### 씬 전환

```
TitleScene  --Space-->  PlayScene
                         ├── 웨이브 5 클리어 --> TransitionScene("CHALLENGING STAGE") --> BonusScene --종료--> PlayScene (다음 사이클)
                         └── 라이프==0 --> GameOverScene --Space--> TitleScene
```

### 엔티티

**Player (`entities/player.py`)**
- 좌우 이동, 위치는 플레이필드 안으로 clamp.
- Space 누름 + `len(player_bullets) < 2`일 때만 발사.
- 피격 시: 폭발 애니메이션, 0.5초 후 재스폰, 라이프 -1.

**Enemy (`entities/enemy.py`)**
- 상태머신: `ENTERING` → `IN_FORMATION` → `DIVING` → `RETURNING`.
  - `ENTERING`: 미리 계산된 베지어 진입 경로를 따라 자기 슬롯으로.
  - `IN_FORMATION`: 위치 = 슬롯 + 포메이션 흔들림 오프셋.
  - `DIVING`: 절차적으로 생성된 곡선을 따라 플레이어 영역으로, 그 후 화면 밖으로.
  - `RETURNING`: 화면 위에서 다시 진입.
- 서브타입: `BeeEnemy` (50점, 자주 다이브), `ButterflyEnemy` (100점, 짝지어 다이브), `BossEnemy` (150점, 호위병과 함께 다이브).

**Bullet (`entities/bullet.py`)**
- `PlayerBullet`: 위로 직진, 화면 밖이면 제거.
- `EnemyBullet`: 발사 시점의 (적 → 플레이어) 방향으로 직진.

**Explosion (`entities/explosion.py`)**
- 프레임 기반 애니메이션, 시퀀스 끝나면 자가 제거.

### 게임 로직

**Formation (`game/formation.py`)**
- 5×8 슬롯 그리드, 플레이필드 가운데 정렬, 마진.
- `slot_position(row, col, oscillation_phase)`은 `Vector2` 반환.
- `entry_path(row, col)`는 화면 밖에서 슬롯까지 베지어 샘플링한 waypoint 리스트 반환.
- 순수 함수 모듈, pygame.sprite 사용 안 함.

**Wave Controller (`game/wave.py`)**
- `WaveType` enum: `NORMAL`, `BOSS`, `BONUS`.
- 순수 함수:
  - `wave_type_for(wave_number) -> WaveType`: 1–4 일반, 5 보스, 6 보너스, 6 사이클로 반복.
  - `difficulty_params(wave_number) -> DifficultyParams`: 적 속도, 다이브 확률, 적 총알 속도.
- `WaveController` 클래스: 현재 웨이브 번호를 보유하는 상태 클래스. `current_type()`, `current_params()`, `advance()` 제공. `PlayScene`이 웨이브 종료 전환을 위해 사용.
- pygame import 없음 (controller도 평범한 Python 상태).

**Dive (`game/dive.py`)**
- `dive_path(enemy_pos, player_pos, seed) -> list[Vector2]`: 베지어 + 사인 흔들림 조합. 순수 함수.

**Scoring (`game/scoring.py`)**
- `Scoring` dataclass: `score`, `lives`, `wave`, `shots_fired`, `hits`, `enemies_killed`.
- 메서드: `add_kill(enemy_type)`, `lose_life()`, `gain_life()`, `accuracy() -> float`, `add_shot()`.
- 하이스코어 영속화: `load_highscore()` / `save_highscore(score)` — `data/highscore.json` 사용.
- 단일 진실 소스 — `SceneManager`가 보유, 씬과 HUD에 전달.
- pygame import 없음.

**HUD (`game/hud.py`)**
- `draw_left(surface, scoring)` / `draw_right(surface, scoring)`: 각각 370×720 패널 렌더링.
- 매 프레임 `Scoring` 객체에서 값 읽음.

### 엔진

**Assets (`engine/assets.py`)**
- 시작 시: `assets/sprites/`, `assets/audio/` 검사. 비어 있으면 `tools/generate_*.py` 실행.
- 생성 후 모든 PNG/WAV를 이름 키 dict로 캐시.

**Audio (`engine/audio.py`)**
- `play_sfx(name)`: 1회성 재생.
- `play_music(name, loop=True)` / `stop_music()` / `fade_music(ms)`.
- mixer 채널 8개 관리. `pygame.mixer.init()` 실패 시 silent no-op 모드.

**Input (`engine/input.py`)**
- 매 프레임 `pygame.event.get()`과 `pygame.key.get_pressed()`로 `InputState` 갱신.
- 필드: `left`, `right`, `fire`, `pause`, `quit`.
- 입력 상태의 단일 소스 — 씬/엔티티는 이걸 읽기만 함.

---

## 6. 데이터 흐름 (한 프레임, PlayScene)

```
1. INPUT
   pygame.event.get() → InputState (left/right/fire/pause/quit)

2. UPDATE(dt)
   ├─ Player.update(dt, input)   → PlayerBullet 발사, Scoring.shots 증가
   ├─ Formation.update(dt)        → 흔들림 오프셋 갱신
   ├─ Enemies.update(dt)          → 상태머신, 일정 확률로 DIVING 전환
   ├─ Bullets.update(dt)          → 직선 이동, 화면 밖이면 kill
   └─ WaveController.update(dt)   → 모든 적 죽으면 다음 웨이브 큐잉

3. COLLIDE
   ├─ player_bullets ⨯ enemies → Scoring.add_kill, Explosion, play_sfx("explode")
   ├─ enemy_bullets ⨯ player   → Scoring.lose_life
   └─ enemies ⨯ player          → 상호 격파, Scoring.lose_life
   라이프 == 0이면: SceneManager.replace(GameOverScene)

4. DRAW
   surface.fill(black)
   HUD.draw_left(surface, scoring)
   playfield = pygame.Surface((540, 720))   # 로컬 좌표
       ├─ 별 배경
       ├─ enemies, bullets, player, explosions
       └─ surface (370, 0)에 blit
   HUD.draw_right(surface, scoring)
   pygame.display.flip()
```

### 핵심 결정
- **플레이필드는 로컬 좌표**: 모든 엔티티 위치는 (0..540, 0..720). 마지막 blit이 메인 surface의 (370, 0)으로 오프셋 처리.
- **`Scoring`은 단일 진실 소스**: `SceneManager`가 보유, 씬 전환 사이에도 살아남음, HUD가 매 프레임 읽음.
- **`WaveController`가 씬 전환 트리거**: PlayScene이 "웨이브 끝났는지" 물음 → 끝났으면 다음 웨이브 타입 조회 → BONUS면 BonusScene 푸시, NORMAL/BOSS면 같은 씬에서 새 적 스폰.
- **sprite 그룹은 4개만**: `players`, `player_bullets`, `enemies`, `enemy_bullets`. 폭발은 그리기만 (충돌 검사 없음).
- **입력은 단일 소스**: `engine/input.py`만 pygame 키보드 읽음. 다른 곳은 `InputState`를 읽음.

---

## 7. 에러 처리

경계에서만 검증, 내부 호출은 신뢰.

| 실패 | 처리 |
|---|---|
| `assets/` 비어 있음 | `tools/generate_*.py` 자동 실행. 그래도 실패 시 명확한 에러 출력 후 종료. |
| 개별 에셋 파일 누락 | 로딩 시점에 빠르게 실패, 메시지에 파일명 포함 (게임 중간 아님). |
| `pygame.mixer.init()` 실패 | Audio는 silent no-op 모드 진입. 시작 시 콘솔 경고 1회. 게임은 정상 진행. |
| `data/highscore.json` 누락/손상 | 하이스코어 0 처리, 다음 저장 때 새로 생성. 사용자에게 표시 안 함. |
| 하이스코어 저장 실패 (권한 등) | 콘솔 경고만. 게임 영향 없음. |
| 화면 밖 엔티티 | `kill()`로 제거. 정상 흐름, 메모리 누수 방지. |
| 메인 루프 미처리 예외 | `main.py`가 `try/except`로 감쌈. traceback 출력 후 `pygame.quit()`. |

내부 코드(`entities/`, `game/`)는 다른 내부 호출자의 입력을 검증하지 않음.

---

## 8. 테스팅

순수 로직만 단위 테스트. 렌더링, 오디오, 입력, 씬 전환은 자동 통합 테스트 안 함.

### 테스트 대상

| 모듈 | 테스트 내용 |
|---|---|
| `game/scoring.py` | 점수 증가, 명중률 (shots=0 엣지 케이스), 라이프 경계, 하이스코어 로드/저장 (tmp 파일) |
| `game/wave.py` | 웨이브 사이클 (1→4 일반, 5 보스, 6 보너스, 반복), 난이도 파라미터 단조 증가 |
| `game/formation.py` | 슬롯 좌표가 플레이필드 안에, 가운데 정렬, 진입 경로가 화면 밖에서 시작해 슬롯에서 끝남 |
| `game/dive.py` | 곡선이 적 위치에서 시작, 플레이필드 아래로 빠짐, 매끄러움 (인접 점 거리 제한) |

### 테스트 안 함 (수동 플레이로 검증)
- 렌더링, 사운드, 입력 처리, 씬 전환, 충돌 검출 (Pygame 라이브러리는 신뢰).

### 제약 (도구가 아니라 리뷰로 강제)
- `game/scoring.py`, `game/wave.py`: `import pygame` 금지.
- `game/formation.py`, `game/dive.py`: pygame에서 `pygame.Vector2`만 허용.

### 실행
```
pytest                    # 전체
pytest tests/test_wave.py # 특정 파일
ruff check .              # 린트
ruff format .             # 포맷
```

---

## 9. 리포지토리 & CI

### GitHub Repo
- **이름**: `galaga-clone`
- **공개 범위**: 공개
- **원격 설정**: `gh repo create galaga-clone --public --source=. --push` (실행 단계에서 `gh` 설치/인증 확인 후. 안 되면 사용자가 직접 remote URL 제공).
- **첫 커밋**: 프로젝트 스켈레톤 + 본 spec 문서.

### CI: GitHub Actions (`.github/workflows/ci.yml`)

모든 브랜치의 push와 pull request에서 트리거.

Job:
1. **lint**: `ruff check .` + `ruff format --check .`
2. **test**: `pytest`

둘 다 `ubuntu-latest`, Python 3.11. 매트릭스 없음 — 단일 환경.

`pyproject.toml`이 `pygame`, `numpy`, `pillow`를 런타임 의존성으로, `pytest`, `ruff`를 dev 의존성으로 선언. Ruff 설정(line length, target version)도 `pyproject.toml`의 `[tool.ruff]`에 둠.

### `.gitignore` 핵심 항목
- `assets/` — 재생성 가능
- `__pycache__/`, `*.pyc`
- `.pytest_cache/`, `.ruff_cache/`
- `data/highscore.json` — 로컬 사용자 데이터, 소스 아님
- IDE/에디터: `.vscode/`, `.idea/`

---

## 10. 미해결 / 향후 작업

의도적으로 미룬 항목:
- 트랙터 빔 / 듀얼 파이터 ("Full Clone" 범위로 확장됨)
- 적 종류별 스프라이트 디자인 (placeholder는 색·크기 변형)
- 사운드 옵션 메뉴 (볼륨, 음소거)
- 풀스크린 / letterbox 모드
- 다국어 지원 (게임 내 텍스트는 영문만)
- 커버리지 측정, mypy
