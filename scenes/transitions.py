"""Transition (interstitial) overlay scene.

Shows a brief, full-screen banner such as ``STAGE 5`` or ``CHALLENGING STAGE``
between gameplay phases. Sits between the previous scene and the next one in
the scene flow (title -> play -> bonus/gameover); it owns no gameplay state
and simply waits a fixed duration before swapping itself out for the real
next scene via the scene manager.

The next scene is supplied as a factory callable rather than a constructed
instance so its (potentially expensive) construction is deferred until the
banner has finished — this keeps the visible transition snappy and avoids
side-effects (audio, sprite spawn) firing while the banner is still on
screen.
"""

from collections.abc import Callable

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene


class TransitionScene(Scene):
    """Full-screen text banner shown for a fixed duration, then auto-replaces.

    Attributes:
        text: The banner text rendered centered on screen (e.g. ``"STAGE 2"``).
        _next_factory: Zero-argument callable that produces the scene to switch
            to when the banner expires. Deferred construction avoids running
            the next scene's ``__init__`` side-effects during the banner.
        _duration: Total seconds to display the banner before transitioning.
        _t: Elapsed time in seconds since the banner first appeared.
        _font: Cached pygame font used to render the banner text.
    """

    def __init__(
        self,
        text: str,
        next_scene_factory: Callable[[], Scene],
        duration: float = 2.0,
    ) -> None:
        """Initialize the banner with text, a deferred next-scene factory, and duration.

        Args:
            text: Banner string (already localized / formatted by the caller).
            next_scene_factory: Callable returning the Scene to install when
                the banner expires. Construction is deferred until expiry.
            duration: How long to display the banner, in seconds.
        """
        self.text = text
        self._next_factory = next_scene_factory
        self._duration = duration
        self._t = 0.0
        self._font = pygame.font.SysFont("consolas", 56, bold=True)

    def update(self, dt: float, inp: InputState) -> None:
        """Advance the banner timer; replace this scene when the duration expires.

        Args:
            dt: Frame delta time in seconds.
            inp: Current input snapshot (unused — banner ignores all input).
        """
        self._t += dt
        if self._t >= self._duration:
            # Scene-stack swap: the manager pops this transition and pushes the
            # newly constructed next scene in its place (no nested stack growth).
            assert self.manager
            self.manager.replace(self._next_factory())

    def draw(self, surface: pygame.Surface) -> None:
        """Render the centered banner text on a black background.

        Args:
            surface: The window surface to blit into.
        """
        # Pure draw step — no game-state mutation here (kept separate from update).
        surface.fill(settings.COLOR_BLACK)
        text = self._font.render(self.text, True, settings.COLOR_YELLOW)
        rect = text.get_rect(center=(settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2))
        surface.blit(text, rect)
