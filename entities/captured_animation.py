"""Animation of a player ship being pulled up the tractor beam to the boss.

On arrival at the boss center, calls on_arrival(self, ship_surface) which
typically attaches the captured ship sprite to the boss and kills the beam.
"""

from collections.abc import Callable

import pygame

from engine import assets


class CapturedAnimation(pygame.sprite.Sprite):
    SPEED = 200.0  # px/s

    def __init__(
        self,
        start_pos: pygame.Vector2,
        boss: pygame.sprite.Sprite,
        on_arrival: Callable[["CapturedAnimation", pygame.Surface], None],
    ) -> None:
        super().__init__()
        base = assets.sprite("player").copy()
        dark = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 80))
        base.blit(dark, (0, 0))
        self.image = base
        self.pos = pygame.Vector2(start_pos)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self.boss = boss
        self._on_arrival = on_arrival
        self._arrived = False

    def update(self, dt: float) -> None:
        if self._arrived:
            return
        target = pygame.Vector2(self.boss.rect.centerx, self.boss.rect.centery)
        diff = target - self.pos
        if diff.length() < 4:
            self._arrived = True
            self._on_arrival(self, self.image)
            self.kill()
            return
        self.pos += diff.normalize() * self.SPEED * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
