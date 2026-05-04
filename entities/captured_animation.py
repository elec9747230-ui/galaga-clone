"""Animation sprite for the "ship being captured" sequence.

When a boss enemy successfully traps the player inside its tractor beam, the
player ship is replaced with a CapturedAnimation that homes in on the boss
sprite at a constant speed. On arrival at the boss center this sprite invokes
``on_arrival(self, ship_surface)``; the typical play-scene callback attaches
the darkened ship surface to the boss (so the boss visibly carries the captive)
and removes the tractor beam from the scene.
"""

from collections.abc import Callable

import pygame

from engine import assets


class CapturedAnimation(pygame.sprite.Sprite):
    """Darkened player ship sprite that flies up to the capturing boss.

    The sprite simply walks toward the boss center each frame at a fixed speed
    until close enough to "arrive". Arrival fires the supplied callback exactly
    once and removes the sprite from its groups.

    Attributes:
        image (pygame.Surface): A copy of the player sprite tinted toward
            black; the darkening visually distinguishes a captured ship from
            the player's currently-controlled ship.
        pos (pygame.Vector2): Sub-pixel center position of the sprite.
        rect (pygame.Rect): Integer rectangle synchronised to ``pos``.
        boss (pygame.sprite.Sprite): The capturing boss sprite; its current
            ``rect.center`` is read each frame so the animation tracks the
            boss even if the boss is still moving.
        _on_arrival (Callable): One-shot callback invoked when the sprite
            reaches the boss; receives the animation and the ship surface so
            the callback can re-use the darkened surface as the boss's
            attached captive sprite.
        _arrived (bool): Latch preventing the callback from firing twice in
            the unlikely case ``update`` runs again before ``kill`` removes
            the sprite from groups.
    """

    SPEED = 200.0  # Constant homing speed in pixels/second.

    def __init__(
        self,
        start_pos: pygame.Vector2,
        boss: pygame.sprite.Sprite,
        on_arrival: Callable[["CapturedAnimation", pygame.Surface], None],
    ) -> None:
        """Construct the captured-ship animation.

        Args:
            start_pos: Playfield-local position where the captured ship begins
                its journey (typically the player's last position).
            boss: Sprite to home in on. Its current center is sampled each
                frame, so a moving boss still receives the captive correctly.
            on_arrival: Callback invoked once the ship reaches the boss. It
                receives ``(self, self.image)`` so callers can promote the
                darkened surface to the boss's attached-captive sprite.
        """
        super().__init__()
        # Build a darkened copy of the player sprite so the ship visibly looks
        # "subdued" while being pulled in. SRCALPHA + alpha=80 gives a soft
        # tint without fully obscuring the original silhouette.
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
        """Step toward the boss; on arrival fire the callback and self-destroy.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        # Once arrived we may still be pumped one extra frame before kill()
        # propagates through groups; bail out early so the callback only runs
        # once and we don't drift past the target.
        if self._arrived:
            return
        target = pygame.Vector2(self.boss.rect.centerx, self.boss.rect.centery)
        diff = target - self.pos
        # 4 px arrival threshold avoids endless overshoot/jitter at the target
        # caused by floating-point step sizes near zero distance.
        if diff.length() < 4:
            self._arrived = True
            self._on_arrival(self, self.image)
            self.kill()
            return
        self.pos += diff.normalize() * self.SPEED * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
