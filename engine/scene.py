"""Scene base class and stack-based ``SceneManager``.

A scene is the unit of game state that owns its own update/draw/event
handling -- e.g. ``TitleScene``, ``PlayScene``, ``BonusScene``,
``GameOverScene``. Only the top scene of the manager's stack is live; it
receives every frame's events, update, and draw call. Scenes underneath are
suspended (their ``on_exit`` was called when they were covered) and can be
re-activated by popping the scene above them.

Stack semantics:

* ``replace(s)`` -- pop the current scene, push ``s``. Used for one-way
  transitions (Title -> Play, Play -> GameOver) where we never want to
  return to the previous scene.
* ``push(s)`` -- suspend the current scene, push ``s`` on top. Used for
  layered/return-to scenes (PlayScene -> BonusScene -> back to PlayScene).
* ``pop()`` -- pop the top scene, resuming whatever sat below.

All transitions are *deferred*: calls to push/replace/pop only enqueue an
intent. The actual stack mutation happens at the start of the next
``update`` via ``_apply_pending``. This avoids the classic
"mutating-list-during-iteration" hazard where a scene calls
``manager.replace(...)`` partway through its own ``update`` or
``handle_event`` -- the current frame finishes cleanly and the swap happens
on the next frame's first call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    # Imported only for type hints to avoid a runtime circular import
    # (engine.input has no scene dependency, but keeping the lazy import
    # documents the layering: scenes consume input, not the other way round).
    from engine.input import InputState


class Scene:
    """Base class for all game scenes. Subclass and override the hooks.

    Default implementations are no-ops, so subclasses only override what they
    need (e.g. a static splash screen needs only ``draw``).

    Attributes:
        manager: The ``SceneManager`` this scene was pushed into. Set by the
            manager itself in ``_apply_pending`` just before ``on_enter`` is
            called, so subclasses may rely on it being non-None inside any
            of the hooks below. ``None`` only on freshly constructed scenes
            that have not yet been added to a manager.
    """

    manager: SceneManager | None = None

    def on_enter(self) -> None:
        """Called once when this scene becomes the active top of the stack."""

    def on_exit(self) -> None:
        """Called once when this scene is replaced, popped, or covered by a push."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Receive a single pygame event for this frame.

        Args:
            event: The event to process. Called once per event in the frame.
        """

    def update(self, dt: float, inp: InputState) -> None:
        """Advance simulation by ``dt`` seconds using the current input snapshot.

        Args:
            dt: Seconds elapsed since the last frame. Variable timestep.
            inp: Per-frame keyboard state from the engine's ``InputReader``.
        """

    def draw(self, surface: pygame.Surface) -> None:
        """Render the scene to the given target surface.

        Args:
            surface: The display surface to draw into.
        """


class SceneManager:
    """Holds a stack of scenes and dispatches events/updates/draws to the top.

    Use ``replace()`` for hard transitions (Title -> Play),
    ``push()`` for layered scenes (PlayScene -> BonusScene then return),
    ``pop()`` to remove the top.

    Attributes:
        _stack: The scene stack. Index ``-1`` is the active scene; lower
            indices are suspended scenes waiting to resume on a pop.
        _pending: Queue of deferred stack operations to apply at the start
            of the next ``update``. Each entry is ``(op, scene_or_None)``
            where op is one of ``"push"``, ``"replace"``, ``"pop"``.
    """

    def __init__(self) -> None:
        self._stack: list[Scene] = []
        self._pending: list[tuple[str, Scene | None]] = []

    @property
    def current(self) -> Scene | None:
        """The currently active (top-of-stack) scene, or ``None`` if empty."""
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        """Queue a push: ``scene`` becomes active after current frame completes."""
        self._pending.append(("push", scene))

    def replace(self, scene: Scene) -> None:
        """Queue a replace: top scene is exited and discarded, ``scene`` takes its place."""
        self._pending.append(("replace", scene))

    def pop(self) -> None:
        """Queue a pop: top scene is exited; the one below (if any) resumes."""
        self._pending.append(("pop", None))

    def _apply_pending(self) -> None:
        """Drain queued transitions in FIFO order.

        Called once at the start of every ``update``. Doing all stack
        mutations here (rather than inline in push/replace/pop) is what
        makes it safe for a scene to request a transition from inside its
        own update or event handler -- the current frame keeps running
        with the old top scene, and the swap happens before the next.

        Why we re-fire ``on_enter`` after a pop: the scene underneath was
        suspended via ``on_exit`` when it was first covered, so its
        ``on_enter`` must run again to mirror that lifecycle (re-acquire
        timers, restart music, etc.).
        """
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
                # If there is now a scene underneath, resume it.
                if self.current:
                    self.current.on_enter()
        self._pending.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward a pygame event to the active scene, if any.

        Args:
            event: The pygame event to dispatch.
        """
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float, inp: InputState) -> None:
        """Apply pending transitions, then update the active scene.

        Args:
            dt: Seconds since last frame.
            inp: Per-frame input snapshot.
        """
        # Drain transitions before update so a scene queued this frame
        # actually runs this frame's update on the new top scene.
        self._apply_pending()
        if self.current:
            self.current.update(dt, inp)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the active scene to ``surface`` (no-op when stack is empty).

        Args:
            surface: Display surface to draw into.
        """
        if self.current:
            self.current.draw(surface)
