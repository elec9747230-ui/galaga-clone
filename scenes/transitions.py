"""Brief overlay screens between phases (e.g., 'STAGE 5', 'CHALLENGING STAGE')."""

from collections.abc import Callable

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene


class TransitionScene(Scene):
    def __init__(
        self,
        text: str,
        next_scene_factory: Callable[[], Scene],
        duration: float = 2.0,
    ) -> None:
        self.text = text
        self._next_factory = next_scene_factory
        self._duration = duration
        self._t = 0.0
        self._font = pygame.font.SysFont("consolas", 56, bold=True)

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if self._t >= self._duration:
            assert self.manager
            self.manager.replace(self._next_factory())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        text = self._font.render(self.text, True, settings.COLOR_YELLOW)
        rect = text.get_rect(center=(settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2))
        surface.blit(text, rect)
