"""Sprite for the rescue sequence after destroying a capturing boss.

When the player kills a boss that is currently carrying a captured ship, the
ship is freed and descends toward the surviving player ship. On arrival the
play scene typically merges the two into a dual fighter for double firepower.
"""

from collections.abc import Callable

import pygame

import settings
from engine import assets


class RescuingShip(pygame.sprite.Sprite):
    """Darkened captured-ship sprite homing onto the active player.

    Travels at a constant configured speed from ``start_pos`` toward
    ``target_player.pos``. When within 4 px of the target the sprite invokes
    ``on_arrival(self)`` exactly once and removes itself from all groups.

    Attributes:
        image (pygame.Surface): Player sprite tinted toward black so the
            "rescued" ship reads visually distinct from the live player on
            its way down.
        pos (pygame.Vector2): Sub-pixel center position.
        rect (pygame.Rect): Integer rectangle synchronised from ``pos``.
        _target (pygame.sprite.Sprite): The live player sprite to home onto;
            its ``pos`` is sampled each frame so a moving player still
            receives the rescue ship correctly.
        _on_arrival (Callable): One-shot callback fired on arrival.
        _arrived (bool): Latch ensuring the callback runs only once.
    """

    def __init__(
        self,
        start_pos: pygame.Vector2,
        target_player: pygame.sprite.Sprite,
        on_arrival: Callable[["RescuingShip"], None],
    ) -> None:
        """Construct a homing rescue ship.

        Args:
            start_pos: Spawn position (typically the dying boss's location).
            target_player: Player sprite the rescue ship homes onto.
            on_arrival: Called once with this sprite when it reaches the
                target; typical implementation promotes the rescue ship to
                a dual-fighter half attached to the existing player.
        """
        super().__init__()
        # Slightly darker tint than CapturedAnimation (alpha=120 vs 80) so the
        # falling rescue ship is clearly distinguishable from the controlled
        # player ship while in transit.
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
        """Step toward the player; on arrival fire the callback once and self-kill.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        # Arrival latch -- update may be called once more after kill() is
        # scheduled but before group removal completes.
        if self._arrived:
            return
        target = pygame.Vector2(self._target.pos.x, self._target.pos.y)
        diff = target - self.pos
        # 4 px tolerance: same justification as the other homing sprites --
        # avoids overshoot/jitter when the per-frame step size is small.
        if diff.length() < 4:
            self._arrived = True
            self._on_arrival(self)
            self.kill()
            return
        self.pos += diff.normalize() * settings.TRACTOR_RESCUE_DESCENT_SPEED * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
