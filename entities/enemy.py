"""Enemy sprite driven by a finite-state machine.

The base flow models the classic Galaga enemy lifecycle:

    ENTERING --> IN_FORMATION --> DIVING --> RETURNING --> IN_FORMATION

Boss enemies extend the same machine with three additional states that
implement the tractor-beam capture mechanic:

    IN_FORMATION --> TRACTOR_ALIGNING --> TRACTOR_BEAMING
                                      `--> (DIVING, on failure)
    TRACTOR_BEAMING --> RETURNING_WITH_CAPTURE --> IN_FORMATION

Path generation lives in ``game.formation`` (entry curves, formation slots)
and ``game.dive`` (dive trajectories); this module only consumes those paths
and walks them at the appropriate speed each frame.
"""

from enum import Enum

import pygame

import settings
from engine import assets
from entities.bullet import EnemyBullet
from game import dive, formation


class EnemyState(Enum):
    """All states an enemy may be in at any given moment.

    Standard combat states:
        ENTERING: Walking the scripted entry path from off-screen into formation.
        IN_FORMATION: Tracking the formation slot for this row/column.
        DIVING: Following a generated attack curve toward (or past) the player.
        RETURNING: Re-entering from off-top to the assigned formation slot.

    Tractor-beam states (boss only):
        TRACTOR_ALIGNING: Boss steers above the player to deploy the beam.
        TRACTOR_BEAMING: Boss is stationary while the beam plays out.
        RETURNING_WITH_CAPTURE: Boss carries the captured ship back to its slot.
    """

    ENTERING = "entering"
    IN_FORMATION = "in_formation"
    DIVING = "diving"
    RETURNING = "returning"
    TRACTOR_ALIGNING = "tractor_aligning"
    TRACTOR_BEAMING = "tractor_beaming"
    RETURNING_WITH_CAPTURE = "returning_with_capture"


class Enemy(pygame.sprite.Sprite):
    """Base enemy sprite implementing the entry/formation/dive state machine.

    Subclasses customise behavior by overriding the ``sprite_name`` (asset key)
    and ``score_kind`` (scoring category) class attributes; all motion logic is
    shared.

    Class Attributes:
        sprite_name (str): Asset key resolved through ``engine.assets.sprite``.
        score_kind (str): Identifier consumed by the score system to pick
            the correct point value (``"normal"`` vs ``"boss"`` etc.).

    Instance Attributes:
        image (pygame.Surface): The current sprite image for this enemy.
        rect (pygame.Rect): Integer rectangle synchronised from ``pos`` each
            frame; used for both rendering and collision.
        row (int): 0-based row index inside the formation grid.
        col (int): 0-based column index inside the formation grid.
        _phase_ref (list[float]): Single-element list shared across all
            enemies, holding the current global formation sway phase. Using
            a list creates a mutable reference so every enemy reads the
            latest value without rebinding an attribute.
        state (EnemyState): Current FSM state.
        _entry_path (list[pygame.Vector2]): Pre-computed waypoint list for
            the entrance fly-in.
        _entry_index (int): Index of the current segment within ``_entry_path``.
        _entry_delay (float): Seconds remaining before this enemy starts
            walking its entry path; staggers wave entrance.
        _dive_path (list[pygame.Vector2]): Waypoints for the active dive.
        _dive_index (int): Index of the current segment within ``_dive_path``.
        _dive_seed (int): RNG seed used to generate the dive; retained for
            potential debugging/replay use.
        _dive_fire_armed (bool): Latch ensuring an enemy fires at most one
            shot per dive (see ``maybe_fire``).
        captured_ship (pygame.Surface | None): Darkened player surface to
            render attached below a boss after a successful capture.
        _tractor_target_x (float): X-coordinate the boss aligns to when
            preparing to deploy a tractor beam (typically the player's x).
        _return_target (pygame.Vector2): Cached target slot used while in
            ``RETURNING_WITH_CAPTURE``.
        pos (pygame.Vector2): Sub-pixel center position.
    """

    sprite_name = "enemy_bee"
    score_kind = "normal"

    def __init__(
        self,
        row: int,
        col: int,
        formation_phase_ref: list[float],
        entry_delay: float = 0.0,
    ) -> None:
        """Construct an enemy at its entry-path origin.

        Args:
            row: Formation row this enemy belongs to.
            col: Formation column this enemy belongs to.
            formation_phase_ref: One-element mutable list holding the shared
                formation sway phase. Mutating index 0 from the wave manager
                animates every enemy in lock-step without per-enemy updates.
            entry_delay: Seconds to wait before beginning the entry path;
                used to stagger enemies arriving in the same wave.
        """
        super().__init__()
        self.image = assets.sprite(self.sprite_name)
        self.rect = self.image.get_rect()
        self.row = row
        self.col = col
        self._phase_ref = formation_phase_ref
        self.state = EnemyState.ENTERING
        self._entry_path = formation.entry_path(row, col)
        self._entry_index = 0
        self._entry_delay = entry_delay
        self._dive_path: list[pygame.Vector2] = []
        self._dive_index = 0
        self._dive_seed = 0
        self._dive_fire_armed = True
        self.captured_ship: pygame.Surface | None = None
        self._tractor_target_x: float = 0.0
        self._return_target: pygame.Vector2 = pygame.Vector2(0, 0)
        # Start positioned at the first entry waypoint so the first frame draws
        # the enemy at a coherent location even before any update runs.
        self.pos = pygame.Vector2(self._entry_path[0])
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def is_in_formation(self) -> bool:
        """Return True iff this enemy is currently anchored to its formation slot.

        Returns:
            bool: True when the FSM is in ``IN_FORMATION``.
        """
        return self.state == EnemyState.IN_FORMATION

    def start_dive(self, player_pos: pygame.Vector2, seed: int) -> None:
        """Generate a dive path toward the player and switch to DIVING.

        Args:
            player_pos: Current player position used as the dive's aim point.
            seed: RNG seed forwarded to the dive generator for reproducibility.

        Why this is gated:
            A dive may be initiated from formation, or as a graceful fall-back
            when a tractor-beam attempt is interrupted (so the boss does
            something useful instead of freezing). All other states are
            already executing motion and would be corrupted by a re-target.
        """
        # Allow dive from formation OR after a failed tractor attempt.
        if self.state not in (
            EnemyState.IN_FORMATION,
            EnemyState.TRACTOR_ALIGNING,
            EnemyState.TRACTOR_BEAMING,
        ):
            return
        self._dive_path = dive.dive_path(self.pos, player_pos, seed)
        self._dive_index = 0
        self._dive_seed = seed
        # Re-arm the one-shot fire latch each new dive so the enemy can shoot
        # exactly once during the dive's mid-portion.
        self._dive_fire_armed = True
        self.state = EnemyState.DIVING

    def enter_tractor_align(self, player_pos: pygame.Vector2) -> None:
        """Begin the boss tractor-beam sequence by aligning above the player.

        Args:
            player_pos: Current player position; only the x-coordinate is
                latched (the boss descends to a fixed configured Y).

        Why gated to IN_FORMATION:
            Aligning from any other state would conflict with active path
            interpolation and visibly snap the boss.
        """
        if self.state != EnemyState.IN_FORMATION:
            return
        self._tractor_target_x = player_pos.x
        self.state = EnemyState.TRACTOR_ALIGNING

    def attach_captured_ship(self, ship_surface: pygame.Surface) -> None:
        """Mark this boss as carrying a captive and head back to formation.

        Args:
            ship_surface: Darkened player sprite surface that should be drawn
                below the boss to indicate the captured ship.
        """
        self.captured_ship = ship_surface
        # Capture the slot at the moment of attachment using the live phase
        # value; subsequent slot updates resume normal formation tracking.
        slot = formation.slot_position(self.row, self.col, self._phase_ref[0])
        self._return_target = pygame.Vector2(slot)
        self.state = EnemyState.RETURNING_WITH_CAPTURE

    def update(self, dt: float) -> None:
        """Dispatch to the per-state update and resync ``rect`` from ``pos``.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        # Explicit per-state dispatch keeps each handler small, named, and
        # individually testable.
        if self.state == EnemyState.ENTERING:
            self._update_entering(dt)
        elif self.state == EnemyState.IN_FORMATION:
            self._update_in_formation()
        elif self.state == EnemyState.DIVING:
            self._update_diving(dt)
        elif self.state == EnemyState.RETURNING:
            self._update_returning(dt)
        elif self.state == EnemyState.TRACTOR_ALIGNING:
            self._update_tractor_aligning(dt)
        elif self.state == EnemyState.TRACTOR_BEAMING:
            # Intentional no-op: while the beam is active the boss is anchored
            # in place; PlayScene drives the rest of the capture choreography.
            pass  # hold position
        elif self.state == EnemyState.RETURNING_WITH_CAPTURE:
            self._update_returning_with_capture(dt)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _update_entering(self, dt: float) -> None:
        """Walk the entry path at a fixed speed; transition to IN_FORMATION at end.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        # Honour stagger delays first so simultaneous spawns don't clump.
        if self._entry_delay > 0:
            self._entry_delay -= dt
            return
        speed = 220
        remain = speed * dt
        # Distance-based loop: consume frame budget across multiple short
        # segments instead of advancing only one segment per frame. Without
        # this, very dense path waypoints would underflow at high frame rates.
        while remain > 0 and self._entry_index < len(self._entry_path) - 1:
            target = self._entry_path[self._entry_index + 1]
            d = (target - self.pos).length()
            if d <= remain:
                # Snap exactly onto the waypoint to avoid floating-point drift.
                self.pos = pygame.Vector2(target)
                self._entry_index += 1
                remain -= d
            else:
                self.pos += (target - self.pos).normalize() * remain
                remain = 0
        if self._entry_index >= len(self._entry_path) - 1:
            self.state = EnemyState.IN_FORMATION

    def _update_in_formation(self) -> None:
        """Snap to the current swaying formation slot.

        ``_phase_ref[0]`` is the live shared phase, so all enemies sway in sync
        without redundant phase animation per sprite.
        """
        self.pos = formation.slot_position(self.row, self.col, self._phase_ref[0])

    def _update_diving(self, dt: float) -> None:
        """Walk the dive path; transition to RETURNING when the path ends.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        speed = 260
        remain = speed * dt
        # Same multi-segment consumption pattern as _update_entering.
        while remain > 0 and self._dive_index < len(self._dive_path) - 1:
            target = self._dive_path[self._dive_index + 1]
            d = (target - self.pos).length()
            if d <= remain:
                self.pos = pygame.Vector2(target)
                self._dive_index += 1
                remain -= d
            else:
                self.pos += (target - self.pos).normalize() * remain
                remain = 0
        if self._dive_index >= len(self._dive_path) - 1:
            # End of dive: respawn just above the top edge so RETURNING
            # animates a clean fly-in from off-screen instead of teleporting
            # from the bottom of the playfield back to the formation slot.
            self.state = EnemyState.RETURNING
            self.pos = pygame.Vector2(self.pos.x, -30)

    def _update_returning(self, dt: float) -> None:
        """Steer back to the current formation slot at fixed speed.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        target = formation.slot_position(self.row, self.col, self._phase_ref[0])
        direction = target - self.pos
        # 4 px arrival threshold; same justification as the homing animations.
        if direction.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        self.pos += direction.normalize() * 220 * dt

    def _update_tractor_aligning(self, dt: float) -> None:
        """Steer the boss to the latched x and the tractor-beam Y altitude.

        Args:
            dt: Elapsed time since the previous frame, in seconds.

        Why two thresholds (5 px AND step-clamp):
            The 5 px threshold finalises the alignment to avoid hovering jitter,
            and the per-frame ``step`` clamp prevents overshooting the target
            on slow hardware where ``step`` could exceed the remaining distance.
        """
        speed = settings.TRACTOR_BOSS_ALIGN_SPEED
        target = pygame.Vector2(self._tractor_target_x, settings.TRACTOR_BOSS_ALIGN_TARGET_Y)
        diff = target - self.pos
        if diff.length() < 5:
            self.pos = target
            self.state = EnemyState.TRACTOR_BEAMING
            return
        step = speed * dt
        if diff.length() <= step:
            self.pos = target
        else:
            self.pos += diff.normalize() * step

    def _update_returning_with_capture(self, dt: float) -> None:
        """Carry the captured ship back to the formation slot.

        Args:
            dt: Elapsed time since the previous frame, in seconds.
        """
        target = self._return_target
        diff = target - self.pos
        if diff.length() < 4:
            self.state = EnemyState.IN_FORMATION
            return
        # Distinct (typically slower) speed than RETURNING so the carry-back
        # reads as deliberate and gives the player time to react.
        self.pos += diff.normalize() * settings.TRACTOR_RETURN_SPEED * dt

    def maybe_fire(
        self, target: pygame.Vector2, speed_multiplier: float = 1.0
    ) -> EnemyBullet | None:
        """Possibly emit a single bullet during the mid-portion of a dive.

        Args:
            target: Aim point for the bullet's velocity.
            speed_multiplier: Difficulty scalar passed through to EnemyBullet.

        Returns:
            EnemyBullet | None: A new bullet to add to the scene, or ``None``
                if this enemy is not currently eligible to fire.

        Why the index window [8, 16]:
            Firing at the very start of a dive looks unfair (no reaction time)
            and firing at the very end looks weak (the enemy is leaving the
            screen). The window samples the visually-aggressive middle arc
            of the dive curve.
        """
        if self.state != EnemyState.DIVING or not self._dive_fire_armed:
            return None
        if self._dive_index < 8 or self._dive_index > 16:
            return None
        # One-shot latch: an enemy fires at most a single bullet per dive.
        self._dive_fire_armed = False
        return EnemyBullet(self.pos, target, speed_multiplier=speed_multiplier)


class BeeEnemy(Enemy):
    """Standard bee enemy: same behavior as base Enemy, alternate sprite/score."""

    sprite_name = "enemy_bee"
    score_kind = "normal"


class ButterflyEnemy(Enemy):
    """Butterfly enemy: same FSM as the base Enemy, alternate sprite."""

    sprite_name = "enemy_butterfly"
    score_kind = "normal"


class BossEnemy(Enemy):
    """Boss enemy: identical FSM, but eligible to enter the tractor-beam states.

    The capture-related transitions are defined on the base class so any
    subclass could in principle perform a capture; in practice the play scene
    only invokes them on BossEnemy instances.
    """

    sprite_name = "enemy_boss"
    score_kind = "boss"
