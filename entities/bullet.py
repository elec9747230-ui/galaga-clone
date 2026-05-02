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
