"""Capture / rescue state machine for the tractor beam mechanic.

Pure module: no pygame import. Holds the single source of truth for capture
mode and transitions. PlayScene drives it via methods; manager returns
booleans signalling state changes the caller must act on (capture happened,
game-over due to rescue timeout, etc.).
"""

from dataclasses import dataclass
from enum import Enum

import settings


class CaptureMode(Enum):
    NORMAL = "normal"
    BEAMING = "beaming"
    CAPTURED = "captured"
    AWAITING_RESCUE = "awaiting_rescue"
    RESCUING = "rescuing"
    DUAL = "dual"


@dataclass
class CaptureState:
    mode: CaptureMode = CaptureMode.NORMAL
    captor_boss_id: int | None = None
    rescue_timer: float = 0.0
    beam_grace: float = 0.0


class CaptureManager:
    def __init__(self) -> None:
        self.state = CaptureState()
        self.active_tractor_boss_id: int | None = None

    def can_start_tractor(self, boss_id: int) -> bool:
        if self.active_tractor_boss_id is not None:
            return False
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
        self.active_tractor_boss_id = boss_id
        self.state.mode = CaptureMode.BEAMING
        self.state.beam_grace = 0.0

    def update_beam(self, dt: float, in_beam: bool) -> bool:
        """Advance beam grace timer. Returns True when capture grace is reached."""
        if self.state.mode != CaptureMode.BEAMING:
            return False
        if in_beam:
            self.state.beam_grace += dt
            if self.state.beam_grace >= settings.TRACTOR_BEAM_CAPTURE_GRACE:
                return True
        else:
            self.state.beam_grace = 0.0
        return False

    def on_beam_ended(self) -> None:
        """Boss finished beaming without capturing. Reset to NORMAL."""
        self.active_tractor_boss_id = None
        if self.state.mode == CaptureMode.BEAMING:
            self.state.mode = CaptureMode.NORMAL
            self.state.beam_grace = 0.0

    def on_captured(self, boss_id: int, lives_after: int) -> None:
        self.active_tractor_boss_id = None
        self.state.captor_boss_id = boss_id
        self.state.beam_grace = 0.0
        if lives_after <= 0:
            self.state.mode = CaptureMode.AWAITING_RESCUE
            self.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
        else:
            self.state.mode = CaptureMode.CAPTURED

    def on_captor_destroyed(self) -> None:
        """Captor boss died (not via rescue dive); captured ship lost permanently."""
        self.state.captor_boss_id = None
        self.state.mode = CaptureMode.NORMAL

    def on_rescue_eligible_kill(self) -> bool:
        """Player killed captor while it was diving with captured ship. Returns True."""
        if self.state.mode not in (CaptureMode.CAPTURED, CaptureMode.AWAITING_RESCUE):
            return False
        self.state.mode = CaptureMode.RESCUING
        return True

    def on_rescue_complete(self) -> None:
        if self.state.mode == CaptureMode.RESCUING:
            self.state.mode = CaptureMode.DUAL
            self.state.captor_boss_id = None

    def on_dual_lost(self) -> None:
        if self.state.mode == CaptureMode.DUAL:
            self.state.mode = CaptureMode.NORMAL

    def update_awaiting_rescue(self, dt: float) -> bool:
        """Decrement rescue timer. Returns True on timeout (game-over signal)."""
        if self.state.mode != CaptureMode.AWAITING_RESCUE:
            return False
        self.state.rescue_timer -= dt
        if self.state.rescue_timer <= 0:
            return True
        return False
