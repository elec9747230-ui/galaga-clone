"""Per-frame input state. Single place that reads pygame keyboard."""

from dataclasses import dataclass

import pygame


@dataclass
class InputState:
    left: bool = False
    right: bool = False
    fire: bool = False
    fire_pressed: bool = False  # edge-trigger: True only on the frame Space went down
    pause_pressed: bool = False
    quit_pressed: bool = False


_FIRE_KEYS = (pygame.K_SPACE,)
_LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
_RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)


class InputReader:
    def __init__(self) -> None:
        self.state = InputState()
        self._prev_fire = False

    def begin_frame(self, events: list[pygame.event.Event]) -> None:
        keys = pygame.key.get_pressed()
        self.state.left = any(keys[k] for k in _LEFT_KEYS)
        self.state.right = any(keys[k] for k in _RIGHT_KEYS)
        fire_now = any(keys[k] for k in _FIRE_KEYS)
        self.state.fire = fire_now
        self.state.fire_pressed = fire_now and not self._prev_fire
        self._prev_fire = fire_now

        self.state.pause_pressed = False
        self.state.quit_pressed = False
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p:
                    self.state.pause_pressed = True
                elif ev.key == pygame.K_ESCAPE:
                    self.state.quit_pressed = True
            elif ev.type == pygame.QUIT:
                self.state.quit_pressed = True
