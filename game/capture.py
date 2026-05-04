"""Capture / rescue state machine for the tractor beam mechanic.

Pure module: no pygame import. Holds the single source of truth for capture
mode and transitions. PlayScene drives it via methods; manager returns
booleans signalling state changes the caller must act on (capture happened,
game-over due to rescue timeout, etc.).

The capture lifecycle is a finite-state machine:
    NORMAL -> BEAMING -> CAPTURED -> RESCUING -> DUAL -> NORMAL
With AWAITING_RESCUE as a special branch when the player has no spare lives
left after being captured (a soft game-over with a final rescue window).
"""

from dataclasses import dataclass
from enum import Enum

import settings


class CaptureMode(Enum):
    """Discrete states for the tractor-beam / rescue mechanic.

    NORMAL: no boss is beaming and no ship is captured.
    BEAMING: a boss has activated its tractor beam and is pulling toward the player.
    CAPTURED: the player ship has been seized; a spare life is on standby.
    AWAITING_RESCUE: capture occurred with zero spare lives; rescue timer is the
        only thing preventing game over.
    RESCUING: the captor boss is being killed while diving with the captured
        ship, triggering the rescue animation.
    DUAL: rescue succeeded; player is in dual-fighter (twin-ship) mode.
    """

    NORMAL = "normal"
    BEAMING = "beaming"
    CAPTURED = "captured"
    AWAITING_RESCUE = "awaiting_rescue"
    RESCUING = "rescuing"
    DUAL = "dual"


@dataclass
class CaptureState:
    """Snapshot of the capture FSM at any given frame.

    Attributes:
        mode: Current CaptureMode the FSM is in.
        captor_boss_id: Identity of the boss currently holding the captured
            ship (None when not captured). Used to detect rescue-eligible kills.
        rescue_timer: Seconds remaining in AWAITING_RESCUE before game-over.
        beam_grace: Seconds the player has been continuously inside the beam
            during BEAMING; resets if the player exits the beam.
    """

    mode: CaptureMode = CaptureMode.NORMAL
    captor_boss_id: int | None = None
    rescue_timer: float = 0.0
    beam_grace: float = 0.0


class CaptureManager:
    """Owns and mutates the CaptureState in response to gameplay events.

    Attributes:
        state: The CaptureState dataclass tracking mode and timers.
        active_tractor_boss_id: Boss currently emitting a tractor beam, or
            None. Acts as a mutex so only one boss can beam at a time.
    """

    def __init__(self) -> None:
        self.state = CaptureState()
        self.active_tractor_boss_id: int | None = None

    def can_start_tractor(self, boss_id: int) -> bool:
        """Return True iff `boss_id` may begin a fresh tractor-beam attack now.

        Args:
            boss_id: Identifier of the boss requesting permission to beam.

        Returns:
            False whenever any beam is already active or any non-NORMAL
            capture state is in progress, ensuring beams never overlap and
            cannot interrupt an ongoing capture/rescue cycle.
        """
        # Mutex: one boss may beam at a time.
        if self.active_tractor_boss_id is not None:
            return False
        # Any non-NORMAL state already involves the player ship in some way;
        # starting a second beam on top would corrupt the FSM.
        if self.state.mode in (
            CaptureMode.BEAMING,
            CaptureMode.CAPTURED,
            CaptureMode.AWAITING_RESCUE,
            CaptureMode.RESCUING,
            CaptureMode.DUAL,
        ):
            return False
        return True

    def begin_beam(self, boss_id: int) -> None:
        """Transition NORMAL -> BEAMING for the given boss.

        Args:
            boss_id: The boss now actively projecting a tractor beam.
        """
        self.active_tractor_boss_id = boss_id
        self.state.mode = CaptureMode.BEAMING
        self.state.beam_grace = 0.0

    def update_beam(self, dt: float, in_beam: bool) -> bool:
        """Advance beam grace timer. Returns True when capture grace is reached.

        Args:
            dt: Seconds elapsed this frame.
            in_beam: Whether the player ship is currently overlapping the beam.

        Returns:
            True exactly on the frame the player has been in the beam long
            enough to be captured; the caller must then drive the actual
            capture transition via on_captured().
        """
        if self.state.mode != CaptureMode.BEAMING:
            return False
        if in_beam:
            # Accumulate dwell time; capture only fires after a sustained dwell
            # so brushing the edge of the beam does not instantly capture.
            self.state.beam_grace += dt
            if self.state.beam_grace >= settings.TRACTOR_BEAM_CAPTURE_GRACE:
                return True
        else:
            # Leaving the beam fully resets the grace counter (no partial credit).
            self.state.beam_grace = 0.0
        return False

    def on_beam_ended(self) -> None:
        """Boss finished beaming without capturing. Reset to NORMAL."""
        self.active_tractor_boss_id = None
        # Only reset mode if we were still BEAMING; an in-flight capture would
        # have already advanced the FSM past BEAMING.
        if self.state.mode == CaptureMode.BEAMING:
            self.state.mode = CaptureMode.NORMAL
            self.state.beam_grace = 0.0

    def on_captured(self, boss_id: int, lives_after: int) -> None:
        """Record a successful capture and pick the appropriate sub-state.

        Args:
            boss_id: The boss that just captured the player ship.
            lives_after: Spare lives remaining after the capture is applied.
                When zero, AWAITING_RESCUE engages a finite rescue window
                rather than ending the run immediately.
        """
        self.active_tractor_boss_id = None
        self.state.captor_boss_id = boss_id
        self.state.beam_grace = 0.0
        # If the player has no spare lives, give them one chance to rescue
        # within TRACTOR_RESCUE_TIMER before declaring game-over.
        if lives_after <= 0:
            self.state.mode = CaptureMode.AWAITING_RESCUE
            self.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
        else:
            self.state.mode = CaptureMode.CAPTURED

    def on_captor_destroyed(self) -> None:
        """Captor boss died (not via rescue dive); captured ship lost permanently."""
        # When a boss is killed while still in formation (not while diving),
        # the captured ship has no path back to the player and is lost.
        self.state.captor_boss_id = None
        self.state.mode = CaptureMode.NORMAL

    def on_rescue_eligible_kill(self) -> bool:
        """Player killed captor while it was diving with captured ship. Returns True."""
        # Rescue can only happen from CAPTURED or AWAITING_RESCUE; ignore other states.
        if self.state.mode not in (CaptureMode.CAPTURED, CaptureMode.AWAITING_RESCUE):
            return False
        self.state.mode = CaptureMode.RESCUING
        return True

    def on_rescue_complete(self) -> None:
        """Rescue animation finished: promote to DUAL fighter mode."""
        if self.state.mode == CaptureMode.RESCUING:
            self.state.mode = CaptureMode.DUAL
            self.state.captor_boss_id = None

    def on_dual_lost(self) -> None:
        """The escort half of the dual fighter was destroyed; revert to NORMAL."""
        if self.state.mode == CaptureMode.DUAL:
            self.state.mode = CaptureMode.NORMAL

    def update_awaiting_rescue(self, dt: float) -> bool:
        """Decrement rescue timer. Returns True on timeout (game-over signal).

        Args:
            dt: Seconds elapsed this frame.

        Returns:
            True only on the frame the timer reaches zero, signalling that
            the caller must end the run.
        """
        if self.state.mode != CaptureMode.AWAITING_RESCUE:
            return False
        self.state.rescue_timer -= dt
        if self.state.rescue_timer <= 0:
            return True
        return False
