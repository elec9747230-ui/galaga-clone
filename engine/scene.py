"""Scene base class + SceneManager. Scenes get update/draw/handle_event."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from engine.input import InputState


class Scene:
    """Subclass and override hooks. The manager passes itself to on_enter."""

    manager: SceneManager | None = None

    def on_enter(self) -> None:
        """Called once when this scene becomes active."""

    def on_exit(self) -> None:
        """Called once when this scene is replaced/popped."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Called for each pygame event in the frame."""

    def update(self, dt: float, inp: InputState) -> None:
        """Called once per frame. dt is seconds since last frame."""

    def draw(self, surface: pygame.Surface) -> None:
        """Called once per frame to render."""


class SceneManager:
    """Holds a stack of scenes. Top scene gets all events/updates/draws.

    Use replace() for hard transitions (Title -> Play),
    push() for layered scenes (PlayScene -> BonusScene then return),
    pop() to remove the top.
    """

    def __init__(self) -> None:
        self._stack: list[Scene] = []
        self._pending: list[tuple[str, Scene | None]] = []

    @property
    def current(self) -> Scene | None:
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        self._pending.append(("push", scene))

    def replace(self, scene: Scene) -> None:
        self._pending.append(("replace", scene))

    def pop(self) -> None:
        self._pending.append(("pop", None))

    def _apply_pending(self) -> None:
        for op, scene in self._pending:
            if op == "push":
                if self.current:
                    self.current.on_exit()
                assert scene is not None
                scene.manager = self
                self._stack.append(scene)
                scene.on_enter()
            elif op == "replace":
                if self.current:
                    self.current.on_exit()
                    self._stack.pop()
                assert scene is not None
                scene.manager = self
                self._stack.append(scene)
                scene.on_enter()
            elif op == "pop":
                if self.current:
                    self.current.on_exit()
                    self._stack.pop()
                if self.current:
                    self.current.on_enter()
        self._pending.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float, inp: InputState) -> None:
        self._apply_pending()
        if self.current:
            self.current.update(dt, inp)

    def draw(self, surface: pygame.Surface) -> None:
        if self.current:
            self.current.draw(surface)
