"""Captured ship descending from a destroyed boss to merge with the current player."""

from collections.abc import Callable

import pygame

import settings
from engine import assets


class RescuingShip(pygame.sprite.Sprite):
    """Travels at constant speed from start_pos toward target_player.pos.
    Calls on_arrival(self) and self.kill() when within 4 px of target."""

    def __init__(
        self,
        start_pos: pygame.Vector2,
        target_player: pygame.sprite.Sprite,
        on_arrival: Callable[["RescuingShip"], None],
    ) -> None:
        super().__init__()
        base = assets.sprite("player").copy()
        dark = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        base.blit(dark, (0, 0))
        self.image = base
        self.pos = pygame.Vector2(start_pos)
        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self._target = target_player
        self._on_arrival = on_arrival
        self._arrived = False

    def update(self, dt: float) -> None:
        if self._arrived:
            return
        target = pygame.Vector2(self._target.pos.x, self._target.pos.y)
        diff = target - self.pos
        if diff.length() < 4:
            self._arrived = True
            self._on_arrival(self)
            self.kill()
            return
        self.pos += diff.normalize() * settings.TRACTOR_RESCUE_DESCENT_SPEED * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
