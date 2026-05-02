"""Tractor beam: striped triangular cone attached to a boss.

Renders procedurally with pygame.draw -- no PNG asset needed. Performs
point-in-polygon collision testing for capture detection.
"""

import pygame

import settings


class TractorBeam(pygame.sprite.Sprite):
    """Animated yellow/blue striped triangular beam below a parent boss."""

    def __init__(self, boss: pygame.sprite.Sprite) -> None:
        super().__init__()
        self.boss = boss
        self.lifetime = settings.TRACTOR_BEAM_LIFETIME
        self._stripe_phase = 0.0
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self._update_rect()

    @property
    def expired(self) -> bool:
        return self.lifetime <= 0

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        self._stripe_phase = (self._stripe_phase + settings.TRACTOR_BEAM_STRIPE_SPEED * dt) % (
            settings.TRACTOR_BEAM_STRIPE_HEIGHT * 2
        )
        self._update_rect()
        # Do NOT self-kill on expiry; PlayScene drives end-of-beam transitions
        # so it can decide whether to start a dive vs leave the beam visible
        # (e.g., during a capture pull-up animation).

    def _update_rect(self) -> None:
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        self.rect = pygame.Rect(
            int(bx - half_bot),
            int(top),
            int(half_bot * 2),
            max(1, int(bottom - top)),
        )

    def _polygon(self) -> list[tuple[int, int]]:
        bx = self.boss.rect.centerx
        top = self.boss.rect.bottom
        bottom = settings.PLAYFIELD_HEIGHT
        half_top = settings.TRACTOR_BEAM_TOP_WIDTH / 2
        half_bot = settings.TRACTOR_BEAM_BOTTOM_WIDTH / 2
        return [
            (int(bx - half_top), int(top)),
            (int(bx + half_top), int(top)),
            (int(bx + half_bot), int(bottom)),
            (int(bx - half_bot), int(bottom)),
        ]

    def contains(self, point: pygame.Vector2) -> bool:
        """Point-in-polygon test using ray casting."""
        poly = self._polygon()
        x, y = point.x, point.y
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
                inside = not inside
            j = i
        return inside

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the striped beam onto a playfield-local surface."""
        poly = self._polygon()
        beam_rect = pygame.Rect(
            min(p[0] for p in poly),
            min(p[1] for p in poly),
            max(p[0] for p in poly) - min(p[0] for p in poly),
            max(p[1] for p in poly) - min(p[1] for p in poly),
        )
        if beam_rect.width <= 0 or beam_rect.height <= 0:
            return
        mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        stripe_h = settings.TRACTOR_BEAM_STRIPE_HEIGHT
        phase = int(self._stripe_phase)
        y = -phase
        toggle = 0
        while y < beam_rect.height:
            color = (*settings.COLOR_YELLOW, 140) if toggle == 0 else (*settings.COLOR_BLUE, 140)
            pygame.draw.rect(
                mask,
                color,
                pygame.Rect(0, max(0, y), beam_rect.width, stripe_h),
            )
            y += stripe_h
            toggle = 1 - toggle
        poly_local = [(p[0] - beam_rect.x, p[1] - beam_rect.y) for p in poly]
        clip_mask = pygame.Surface((beam_rect.width, beam_rect.height), pygame.SRCALPHA)
        pygame.draw.polygon(clip_mask, (255, 255, 255, 255), poly_local)
        mask.blit(clip_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(mask, beam_rect.topleft)
