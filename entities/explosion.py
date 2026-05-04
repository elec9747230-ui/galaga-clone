"""Four-frame animated explosion sprite.

The explosion plays its frames sequentially at a fixed cadence and removes
itself from all sprite groups once the final frame elapses, so callers do not
need to track or clean up the effect. Frames are pulled from the asset cache
under the keys ``explosion_0`` through ``explosion_3``.
"""

import pygame

from engine import assets

# Per-frame display duration, in seconds. With 4 frames this yields a total
# explosion length of ~0.28 s -- short enough to feel snappy, long enough to
# be readable at 60 FPS.
FRAME_DURATION = 0.07


class Explosion(pygame.sprite.Sprite):
    """Short-lived sprite that plays through a 4-frame explosion animation.

    Attributes:
        frames (list[pygame.Surface]): The 4 pre-loaded explosion frames in
            playback order.
        image (pygame.Surface): The currently displayed frame.
        rect (pygame.Rect): Rectangle re-derived from each new frame so that
            different frame sizes remain centered on the original spawn point.
        _frame_index (int): Last frame index actually applied to ``image``;
            used to avoid redundant rect recomputation when the elapsed-time
            quantisation hasn't advanced to the next frame yet.
        _t (float): Total elapsed time since spawn, in seconds.
    """

    def __init__(self, pos: pygame.Vector2) -> None:
        """Spawn an explosion centered at ``pos``.

        Args:
            pos: Playfield-local position where the explosion originates
                (typically a destroyed enemy or player).
        """
        super().__init__()
        self.frames = [assets.sprite(f"explosion_{i}") for i in range(4)]
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(int(pos.x), int(pos.y)))
        self._frame_index = 0
        self._t = 0.0

    def update(self, dt: float) -> None:
        """Advance the animation timer and switch to the next frame as needed.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        self._t += dt
        # Integer division of elapsed time by FRAME_DURATION yields the
        # current frame index without per-frame state machinery.
        idx = int(self._t / FRAME_DURATION)
        if idx >= len(self.frames):
            # Sequence finished: self-destruct so groups release the sprite.
            self.kill()
            return
        # Only swap surfaces when the index actually advances; this avoids
        # re-deriving the rect every frame at high refresh rates.
        if idx != self._frame_index:
            self._frame_index = idx
            # Preserve the on-screen center because successive explosion
            # frames may have slightly different sizes.
            center = self.rect.center
            self.image = self.frames[idx]
            self.rect = self.image.get_rect(center=center)
