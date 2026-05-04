"""Player ship sprite: handles movement and firing.

All positions in this module are expressed in playfield-local coordinates;
the play scene composes the playfield surface onto the window each frame.
Two ships can co-exist (dual-fighter mode after a successful rescue): the
``dual_offset`` and ``is_right_half`` flags describe each ship's role so the
firing cap can be doubled when both halves are alive.
"""

from collections.abc import Callable

import pygame

import settings
from engine import assets, audio
from engine.input import InputState
from entities.bullet import PlayerBullet


class Player(pygame.sprite.Sprite):
    """Player-controlled ship.

    Attributes:
        image (pygame.Surface): Player sprite surface from the asset cache.
        rect (pygame.Rect): Integer rectangle synchronised from ``pos`` each
            frame; used for collision and rendering.
        pos (pygame.Vector2): Sub-pixel center position. Stored separately
            from ``rect`` so smooth motion is not quantised to integers.
        dual_offset (int): Pixel offset from the playfield center used when
            spawning. Zero for a normal solo ship; non-zero for the two
            halves of a dual-fighter formation.
        is_left_half (bool): True if this is the left half of a dual fighter.
            Derived from a negative ``dual_offset`` (left of center).
        is_right_half (bool): True if this is the right half of a dual fighter.
            Set explicitly via the ``is_right_half`` constructor flag, OR
            inferred from a positive ``dual_offset`` so callers may pass
            either signal.
    """

    def __init__(self, dual_offset: int = 0, is_right_half: bool = False) -> None:
        """Spawn the player ship near the bottom-center of the playfield.

        Args:
            dual_offset: Horizontal pixel offset from the playfield center.
                Negative values place the ship to the left of center (left
                half of a dual fighter), positive values to the right.
            is_right_half: Explicit flag for "this ship is the right half of a
                dual fighter". Useful when callers want to force the role
                regardless of offset sign.
        """
        super().__init__()
        self.image = assets.sprite("player")
        self.rect = self.image.get_rect()
        # Spawn ~40 px above the bottom edge so the ship is fully visible and
        # has a small buffer for incoming bullets to be telegraphed.
        self.pos = pygame.Vector2(
            settings.PLAYFIELD_WIDTH / 2 + dual_offset,
            settings.PLAYFIELD_HEIGHT - 40,
        )
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.dual_offset = dual_offset
        self.is_left_half = dual_offset < 0
        # Accept either the explicit flag or a positive offset as evidence
        # that this is the right half. This lets the play scene construct
        # halves with whichever signal is most convenient at the call site.
        self.is_right_half = is_right_half or dual_offset > 0

    def update(
        self,
        dt: float,
        inp: InputState,
        bullets: pygame.sprite.Group,
        on_shot: Callable[[], None] | None = None,
    ) -> None:
        """Apply input to move/shoot, clamp to playfield, and emit a bullet on press.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
            inp: Current input snapshot (left/right held, fire just pressed).
            bullets: Sprite group new player bullets are added to. The current
                size of this group is also used to enforce the on-screen cap.
            on_shot: Optional callback invoked exactly once per emitted bullet,
                e.g. to update HUD/statistics. Called after the bullet is
                added and the SFX is played.
        """
        # Discrete left/right axis: allow simultaneous press to cancel out.
        dx = 0.0
        if inp.left:
            dx -= 1.0
        if inp.right:
            dx += 1.0
        self.pos.x += dx * settings.PLAYER_SPEED * dt
        # Clamp by half-width so the sprite's edges never leave the playfield;
        # this is the ship's effective hit box for screen-edge purposes.
        half_w = self.rect.width / 2
        self.pos.x = max(half_w, min(settings.PLAYFIELD_WIDTH - half_w, self.pos.x))
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # In dual mode each ship fires once; allow up to 4 bullets on screen.
        # Using a doubled cap (instead of one cap per half) keeps the policy
        # centralised in the bullet group rather than tracked per-ship.
        is_dual = self.is_left_half or self.is_right_half
        cap = settings.MAX_PLAYER_BULLETS * (2 if is_dual else 1)
        if inp.fire_pressed and len(bullets) < cap:
            # Muzzle is at the top-center of the sprite; subtract half the
            # height so the bullet visually emerges from the ship's nose.
            muzzle = pygame.Vector2(self.pos.x, self.pos.y - self.rect.height / 2)
            bullets.add(PlayerBullet(muzzle))
            audio.play_sfx("sfx_shoot")
            if on_shot:
                on_shot()
