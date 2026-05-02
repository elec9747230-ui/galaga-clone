"""4-frame animated explosion. Auto-removes when sequence completes."""

import pygame

from engine import assets

FRAME_DURATION = 0.07


class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos: pygame.Vector2) -> None:
        super().__init__()
        self.frames = [assets.sprite(f"explosion_{i}") for i in range(4)]
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self._frame_index = 0
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        idx = int(self._t / FRAME_DURATION)
        if idx >= len(self.frames):
            self.kill()
            return
        if idx != self._frame_index:
            self._frame_index = idx
            center = self.rect.center
            self.image = self.frames[idx]
            self.rect = self.image.get_rect(center=center)
