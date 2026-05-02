"""Enemy sprite with state machine: ENTERING -> IN_FORMATION -> DIVING -> RETURNING."""

from enum import Enum

import pygame

from engine import assets
from entities.bullet import EnemyBullet
from game import dive, formation


class EnemyState(Enum):
    ENTERING = "entering"
    IN_FORMATION = "in_formation"
    DIVING = "diving"
    RETURNING = "returning"


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
        self.pos = pygame.Vector2(self._entry_path[0])
        self.rect.center = (int(self.pos.x), int(self.pos.y))

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

    def maybe_fire(self, target: pygame.Vector2) -> EnemyBullet | None:
        if self.state != EnemyState.DIVING or not self._dive_fire_armed:
            return None
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
