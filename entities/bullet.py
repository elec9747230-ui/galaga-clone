"""Projectile sprites used during gameplay.

Defines two sprite classes:
- PlayerBullet: a straight-up projectile fired by the player ship.
- EnemyBullet: a directed projectile fired by an enemy toward a target point
  (typically the player's current position at the moment of firing).

Both sprites maintain their own floating-point ``pos`` vector to support
sub-pixel movement; the integer ``rect`` is synchronised each frame for
collision tests and rendering. Bullets self-destruct (``self.kill()``) when
they leave the playfield, so the owning sprite group automatically prunes
them.
"""

import pygame

import settings
from engine import assets


class PlayerBullet(pygame.sprite.Sprite):
    """Straight upward bullet fired from the player ship.

    Attributes:
        image (pygame.Surface): Cached sprite surface for the player bullet.
        rect (pygame.Rect): Integer-aligned rectangle used for rendering and
            collision; its ``midbottom`` is anchored at the muzzle point so
            the bullet "grows" upward from the firing position.
        pos (pygame.Vector2): Sub-pixel position of the bullet's bottom-center
            point, advanced each frame using ``dt`` for frame-rate-independent
            motion.
    """

    def __init__(self, pos: pygame.Vector2) -> None:
        """Spawn a player bullet anchored at the given muzzle position.

        Args:
            pos: Playfield-local position of the muzzle (bullet's midbottom).
        """
        super().__init__()
        self.image = assets.sprite("player_bullet")
        # Anchor by midbottom so the bullet appears to emerge from the muzzle.
        self.rect = self.image.get_rect(midbottom=(int(pos.x), int(pos.y)))
        # Maintain a separate float position so motion is not quantised to int rect.
        self.pos = pygame.Vector2(pos)

    def update(self, dt: float) -> None:
        """Advance the bullet upward and remove it once off-screen.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        # Move upward (decreasing y) at a fixed configured speed.
        self.pos.y -= settings.PLAYER_BULLET_SPEED * dt
        self.rect.midbottom = (int(self.pos.x), int(self.pos.y))
        # Once fully past the top of the playfield the bullet is irrelevant.
        if self.rect.bottom < 0:
            self.kill()


class EnemyBullet(pygame.sprite.Sprite):
    """Directed projectile fired by an enemy toward a fixed target point.

    The bullet's velocity is computed once at spawn time from the source-to-target
    vector, then held constant; the bullet does NOT home in on a moving target.

    Attributes:
        image (pygame.Surface): Cached sprite surface for the enemy bullet.
        rect (pygame.Rect): Integer-aligned rectangle anchored by ``midtop``
            so the projectile sits below its origin point at spawn.
        pos (pygame.Vector2): Sub-pixel position of the bullet's top-center.
        velocity (pygame.Vector2): Constant per-second velocity vector pointing
            from the spawn point toward the target, scaled by the configured
            base speed and an optional difficulty multiplier.
    """

    def __init__(
        self,
        pos: pygame.Vector2,
        target: pygame.Vector2,
        speed_multiplier: float = 1.0,
    ) -> None:
        """Spawn an enemy bullet aimed at ``target`` from ``pos``.

        Args:
            pos: Origin of the bullet (typically the enemy's current position).
            target: Point the bullet is aimed at (typically the player's
                position at firing time). The bullet flies in a straight line
                through this point; it does not track a moving player.
            speed_multiplier: Optional scalar applied to the configured base
                speed; used by the difficulty system to make late waves faster.
        """
        super().__init__()
        self.image = assets.sprite("enemy_bullet")
        self.rect = self.image.get_rect(midtop=(int(pos.x), int(pos.y)))
        self.pos = pygame.Vector2(pos)
        direction = target - pos
        # Guard against a zero-length direction (enemy fired exactly at itself);
        # default to firing straight down so the bullet still leaves the screen.
        if direction.length() == 0:
            direction = pygame.Vector2(0, 1)
        self.velocity = direction.normalize() * settings.ENEMY_BULLET_SPEED * speed_multiplier

    def update(self, dt: float) -> None:
        """Advance the bullet along its fixed velocity and cull when off-field.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        self.pos += self.velocity * dt
        self.rect.midtop = (int(self.pos.x), int(self.pos.y))
        # Cull on any off-field exit. The top edge is intentionally NOT checked
        # because enemy bullets travel downward; angled shots can still leave
        # via the left/right sides as well as the bottom.
        if (
            self.rect.top > settings.PLAYFIELD_HEIGHT
            or self.rect.right < 0
            or self.rect.left > settings.PLAYFIELD_WIDTH
        ):
            self.kill()
