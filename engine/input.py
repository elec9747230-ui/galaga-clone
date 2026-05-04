"""Per-frame keyboard input snapshot.

The rest of the game never touches ``pygame.key`` directly; instead, the main
loop builds a single ``InputState`` per frame via ``InputReader.begin_frame``
and passes it down to scenes. That gives us:

* one consistent place to remap controls,
* a clean separation between continuous "is held" state (left/right/fire) and
  discrete "was just pressed this frame" edges (fire_pressed, pause_pressed,
  quit_pressed), so gameplay code never has to track previous-frame keys.

Edge detection for ``fire_pressed`` is done internally; the other "*_pressed"
fields are derived from the per-frame event queue rather than key state, which
is the correct way to detect taps in pygame (key state can miss a sub-frame
keypress on a low FPS frame).
"""

from dataclasses import dataclass

import pygame


@dataclass
class InputState:
    """A single frame's keyboard snapshot consumed by scenes.

    Attributes:
        left: True while a Left-arrow / 'A' key is held down.
        right: True while a Right-arrow / 'D' key is held down.
        fire: True while Space is held (continuous; for autofire if desired).
        fire_pressed: True only on the single frame Space transitions from
            up to down. Used for tap-to-shoot semantics.
        pause_pressed: True only on the frame the 'P' key was pressed.
        quit_pressed: True if Escape was pressed or a window-close event
            (``pygame.QUIT``) arrived this frame.
    """

    left: bool = False
    right: bool = False
    fire: bool = False
    fire_pressed: bool = False  # edge-trigger: True only on the frame Space went down
    pause_pressed: bool = False
    quit_pressed: bool = False


# Key bindings live as module-level tuples so we can extend them (e.g. add
# WASD or gamepad equivalents) in one place without touching the reader.
_FIRE_KEYS = (pygame.K_SPACE,)
_LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
_RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)


class InputReader:
    """Collects keyboard state into an ``InputState`` once per frame.

    Attributes:
        state: The most recently produced ``InputState``. Reused across
            frames -- callers should not retain references between frames
            or copy the dataclass if they need a snapshot.
        _prev_fire: Internal flag tracking whether the fire key was held on
            the previous frame, used to compute the ``fire_pressed`` edge.
    """

    def __init__(self) -> None:
        self.state = InputState()
        self._prev_fire = False

    def begin_frame(self, events: list[pygame.event.Event]) -> None:
        """Refresh ``self.state`` from current key state and the frame's events.

        Args:
            events: The list returned by ``pygame.event.get()`` for this
                frame. We need the event list (not just key state) so we
                can detect discrete tap events (pause, quit) reliably even
                on slow frames.

        Why we mix two pygame APIs:
            * ``pygame.key.get_pressed()`` gives instantaneous "is held"
              state -- ideal for movement and continuous fire.
            * The event queue gives us the actual KEYDOWN edge, which is
              the only reliable source for one-shot actions like "pause"
              that must not double-fire if a key is held across frames.
        """
        keys = pygame.key.get_pressed()
        self.state.left = any(keys[k] for k in _LEFT_KEYS)
        self.state.right = any(keys[k] for k in _RIGHT_KEYS)
        fire_now = any(keys[k] for k in _FIRE_KEYS)
        self.state.fire = fire_now
        # Edge: True only on the transition from up to down.
        self.state.fire_pressed = fire_now and not self._prev_fire
        self._prev_fire = fire_now

        # Discrete edges are reset every frame; they are only ever True on
        # the frame the key was pressed.
        self.state.pause_pressed = False
        self.state.quit_pressed = False
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p:
                    self.state.pause_pressed = True
                elif ev.key == pygame.K_ESCAPE:
                    self.state.quit_pressed = True
            elif ev.type == pygame.QUIT:
                # Window close button -- treat as quit so the main loop
                # exits cleanly instead of relying on the OS to kill us.
                self.state.quit_pressed = True
