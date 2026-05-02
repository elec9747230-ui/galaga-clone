"""Player ship: move + fire. Coordinates are playfield-local."""

from collections.abc import Callable

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
        on_shot: Callable[[], None] | None = None,
    ) -> None:
        dx = 0.0
        if inp.left:
            dx -= 1.0
        if inp.right:
            dx += 1.0
        self.pos.x += dx * settings.PLAYER_SPEED * dt
        half_w = self.rect.width / 2
        self.pos.x = max(half_w, min(settings.PLAYFIELD_WIDTH - half_w, self.pos.x))
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if inp.fire_pressed and len(bullets) < settings.MAX_PLAYER_BULLETS:
            muzzle = pygame.Vector2(self.pos.x, self.pos.y - self.rect.height / 2)
            bullets.add(PlayerBullet(muzzle))
            audio.play_sfx("sfx_shoot")
            if on_shot:
                on_shot()
