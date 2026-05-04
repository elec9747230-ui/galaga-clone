"""Tractor beam sprite: a striped triangular cone attached to a boss.

The beam is rendered procedurally with ``pygame.draw`` (no PNG asset is
needed) and is shaped like a downward-widening trapezoid: narrow at the
boss's belly, wider at the bottom of the playfield. Two phases of behaviour
are managed here:

1. Visual animation -- yellow/blue horizontal stripes scroll downward by
   continuously incrementing a phase value.
2. Capture collision -- a point-in-polygon ray-casting test exposes
   ``contains`` so the play scene can detect when the player ship's
   center lies inside the beam and trigger the capture sequence.

The beam intentionally does NOT self-destruct on lifetime expiry; the play
scene owns the end-of-beam transition (start a dive on failure, or keep the
beam visible during the capture pull-up animation).
"""

import pygame

import settings


class TractorBeam(pygame.sprite.Sprite):
    """Animated yellow/blue striped trapezoidal beam below a parent boss.

    Attributes:
        boss (pygame.sprite.Sprite): The boss this beam is anchored to. The
            beam's top edge tracks the boss's bottom each frame so the beam
            follows the boss laterally during alignment.
        lifetime (float): Seconds remaining before the beam is considered
            expired. Decremented in ``update`` but never used to self-kill.
        _stripe_phase (float): Scrolling offset of the stripe pattern, kept
            in [0, 2 * stripe_height) so the modulo wraps cleanly each cycle.
        image (pygame.Surface): Placeholder 1x1 surface required by Sprite;
            actual rendering is performed via the explicit ``draw`` method.
        rect (pygame.Rect): Bounding rectangle of the beam, used for
            broad-phase collision; refined to the exact polygon by ``contains``.
    """

    def __init__(self, boss: pygame.sprite.Sprite) -> None:
        """Attach a freshly deployed beam under ``boss``.

        Args:
            boss: The capturing boss sprite. Its ``rect`` is sampled on every
                frame so the beam stays glued to the boss as it moves.
        """
        super().__init__()
        self.boss = boss
        self.lifetime = settings.TRACTOR_BEAM_LIFETIME
        self._stripe_phase = 0.0
        # 1x1 placeholder surface: Sprite needs `image`, but our `draw` method
        # bypasses group.draw() and renders the polygon directly. The real
        # bounds are tracked via ``rect`` in ``_update_rect``.
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self._update_rect()

    @property
    def expired(self) -> bool:
        """Whether the beam's timed phase has elapsed.

        Returns:
            bool: True once ``lifetime`` has reached zero. The play scene
                polls this to decide when to advance the boss out of the
                ``TRACTOR_BEAMING`` state.
        """
        return self.lifetime <= 0

    def update(self, dt: float) -> None:
        """Tick the lifetime timer, scroll the stripe phase, and refresh ``rect``.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        self.lifetime -= dt
        # Advance the stripe scroll. Modulo (2 * stripe_height) keeps the
        # phase bounded; one full cycle = one yellow + one blue stripe, so
        # this is the smallest period after which the drawn pattern repeats.
        self._stripe_phase = (self._stripe_phase + settings.TRACTOR_BEAM_STRIPE_SPEED * dt) % (
            settings.TRACTOR_BEAM_STRIPE_HEIGHT * 2
        )
        self._update_rect()
        # Do NOT self-kill on expiry; PlayScene drives end-of-beam transitions
        # so it can decide whether to start a dive vs leave the beam visible
        # (e.g., during a capture pull-up animation).

    def _update_rect(self) -> None:
        """Refresh ``rect`` to cover the beam's current trapezoidal extent.

        The bounding rect is sized to the bottom (wider) edge so it fully
        encloses the trapezoid for broad-phase culling and group-level
        collision optimisation.
        """
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        # Use bottom width for both x extents so the rect always encloses the
        # beam, even though the top edge is narrower than ``half_bot``.
        # max(1, ...) avoids a degenerate zero-height rect when the boss is
        # already at the bottom of the playfield (which would crash some
        # pygame collision routines).
        self.rect = pygame.Rect(
            int(bx - half_bot),
            int(top),
            int(half_bot * 2),
            max(1, int(bottom - top)),
        )

    def _polygon(self) -> list[tuple[int, int]]:
        """Build the trapezoid vertices for the current beam in clockwise order.

        Returns:
            list[tuple[int, int]]: Four (x, y) integer vertices ordered
                top-left, top-right, bottom-right, bottom-left. Suitable for
                both ``pygame.draw.polygon`` and the ray-cast test.
        """
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_top = settings.TRACTOR_BEAM_TOP_WIDTH / 2
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        # Trapezoid: narrow at top (boss belly), wide at bottom (playfield floor).
        return [
            (int(bx - half_top), int(top)),
            (int(bx + half_top), int(top)),
            (int(bx + half_bot), int(bottom)),
            (int(bx - half_bot), int(bottom)),
        ]

    def contains(self, point: pygame.Vector2) -> bool:
        """Test whether a point lies inside the beam's trapezoid.

        Uses the standard "crossing-number" ray-casting algorithm: a horizontal
        ray is shot from the test point to +infinity and edge crossings are
        counted; an odd count means the point is inside.

        Args:
            point: Playfield-local point to test (typically the player's center).

        Returns:
            bool: True if ``point`` is inside the beam polygon.
        """
        poly = self._polygon()
        x, y = point.x, point.y
        inside = False
        n = len(poly)
        # j tracks the previous vertex index so each iteration represents the
        # edge from poly[j] -> poly[i].
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            # `(yi > y) != (yj > y)` checks whether the edge straddles the
            # horizontal ray. The second clause computes the x of the edge at
            # height y and tests whether the point is to its left. The
            # +1e-9 epsilon avoids ZeroDivisionError on horizontal edges.
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
                inside = not inside
            j = i
        return inside

    def draw(self, surface: pygame.Surface) -> None:
        """Render the striped beam clipped to its trapezoid onto ``surface``.

        The implementation uses a two-pass alpha-mask trick:
            1. Paint horizontal yellow/blue stripes onto a rectangular mask.
            2. Blit a white-filled polygon over the mask using BLEND_RGBA_MIN
               to clip the stripe rectangle down to the trapezoid shape.

        Args:
            surface: Target surface (typically the playfield surface).
        """
        poly = self._polygon()
        # Compute the smallest axis-aligned rectangle enclosing the polygon;
        # we'll generate the stripe pattern at this size for efficiency.
        beam_rect = pygame.Rect(
            min(p[0] for p in poly),
            min(p[1] for p in poly),
            max(p[0] for p in poly) - min(p[0] for p in poly),
            max(p[1] for p in poly) - min(p[1] for p in poly),
        )
        # Defensive bail-out: a degenerate beam (e.g., boss already past the
        # bottom of the playfield) would otherwise raise a pygame error.
        if beam_rect.width <= 0 or beam_rect.height <= 0:
            return
        mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        stripe_h = settings.TRACTOR_BEAM_STRIPE_HEIGHT
        phase = int(self._stripe_phase)
        # Start one phase above the top so partial stripes appear at the top
        # edge as the pattern scrolls -- this is what makes the beam look
        # like it's sucking content upward.
        y = -phase
        toggle = 0
        while y < beam_rect.height:
            # Alpha 140: translucent enough that the boss/playfield show
            # through, opaque enough to read as a beam at small sizes.
            color = (*settings.COLOR_YELLOW, 140) if toggle == 0 else (*settings.COLOR_BLUE, 140)
            pygame.draw.rect(
                mask,
                color,
                pygame.Rect(0, max(0, y), beam_rect.width, stripe_h),
            )
            y += stripe_h
            toggle = 1 - toggle
        # Translate polygon vertices into mask-local coordinates so the clip
        # polygon lands in the correct place on the stripe rectangle.
        poly_local = [(p[0] - beam_rect.x, p[1] - beam_rect.y) for p in poly]
        clip_mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(clip_mask, (255, 255, 255, 255), poly_local)
        # BLEND_RGBA_MIN keeps the per-pixel minimum across channels: pixels
        # outside the polygon (alpha=0 in clip_mask) become 0 in the stripe
        # mask, effectively cropping the stripes to the trapezoid shape.
        mask.blit(clip_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(mask, beam_rect.topleft)
