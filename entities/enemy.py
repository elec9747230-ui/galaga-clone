"""Enemy sprite with state machine: ENTERING -> IN_FORMATION -> DIVING -> RETURNING.

Boss enemies additionally support tractor beam states for the capture mechanic.
"""

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
    TRACTOR_ALIGNING = "tractor_aligning"
    TRACTOR_BEAMING = "tractor_beaming"
    RETURNING_WITH_CAPTURE = "returning_with_capture"


class Enemy(pygame.sprite.Sprite):
    sprite_name = "enemy_bee"
    score_kind = "normal"

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
        self._phase_ref = formation_phase_ref
        self.state = EnemyState.ENTERING
        self._entry_path = formation.entry_path(row, col)
        self._entry_index = 0
        self._entry_delay = entry_delay
        self._dive_path: list[pygame.Vector2] = []
        self._dive_index = 0
        self._dive_seed = 0
        self._dive_fire_armed = True
        self.captured_ship: pygame.Surface | None = None
        self._tractor_target_x: float = 0.0
        self._return_target: pygame.Vector2 = pygame.Vector2(0, 0)
        self.pos = pygame.Vector2(self._entry_path[0])
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def is_in_formation(self) -> bool:
        return self.state == EnemyState.IN_FORMATION

    def start_dive(self, player_pos: pygame.Vector2, seed: int) -> None:
        # Allow dive from formation OR after a failed tractor attempt.
        if self.state not in (
            EnemyState.IN_FORMATION,
            EnemyState.TRACTOR_ALIGNING,
            EnemyState.TRACTOR_BEAMING,
        ):
            return
        self._dive_path = dive.dive_path(self.pos, player_pos, seed)
        self._dive_index = 0
        self._dive_seed = seed
        self._dive_fire_armed = True
        self.state = EnemyState.DIVING

    def enter_tractor_align(self, player_pos: pygame.Vector2) -> None:
        if self.state != EnemyState.IN_FORMATION:
            return
        self._tractor_target_x = player_pos.x
        self.state = EnemyState.TRACTOR_ALIGNING

    def attach_captured_ship(self, ship_surface: pygame.Surface) -> None:
        self.captured_ship = ship_surface
        slot = formation.slot_position(self.row, self.col, self._phase_ref[0])
        self._return_target = pygame.Vector2(slot)
        self.state = EnemyState.RETURNING_WITH_CAPTURE

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

    def _update_entering(self, dt: float) -> None:
        if self._entry_delay > 0:
            self._entry_delay -= dt
            return
        speed = 220
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
            self.state = EnemyState.RETURNING
            self.pos = pygame.Vector2(self.pos.x, -30)

    def _update_returning(self, dt: float) -> None:
        target = formation.slot_position(self.row, self.col, self._phase_ref[0])
        direction = target - self.pos
        if direction.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        self.pos += direction.normalize() * 220 * dt

    def _update_tractor_aligning(self, dt: float) -> None:
        speed = settings.TRACTOR_BOSS_ALIGN_SPEED
        target = pygame.Vector2(self._tractor_target_x, settings.TRACTOR_BOSS_ALIGN_TARGET_Y)
        diff = target - self.pos
        if diff.length() < 5:
            self.pos = target
            self.state = EnemyState.TRACTOR_BEAMING
            return
        step = speed * dt
        if diff.length() <= step:
            self.pos = target
        else:
            self.pos += diff.normalize() * step

    def _update_returning_with_capture(self, dt: float) -> None:
        target = self._return_target
        diff = target - self.pos
        if diff.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        self.pos += diff.normalize() * settings.TRACTOR_RETURN_SPEED * dt

    def maybe_fire(
        self, target: pygame.Vector2, speed_multiplier: float = 1.0
    ) -> EnemyBullet | None:
        if self.state != EnemyState.DIVING or not self._dive_fire_armed:
            return None
        if self._dive_index < 8 or self._dive_index > 16:
            return None
        self._dive_fire_armed = False
        return EnemyBullet(self.pos, target, speed_multiplier=speed_multiplier)


class BeeEnemy(Enemy):
    sprite_name = "enemy_bee"
    score_kind = "normal"


class ButterflyEnemy(Enemy):
    sprite_name = "enemy_butterfly"
    score_kind = "normal"


class BossEnemy(Enemy):
    sprite_name = "enemy_boss"
    score_kind = "boss"
