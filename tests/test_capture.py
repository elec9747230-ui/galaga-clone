from game.capture import CaptureManager, CaptureMode


def test_initial_mode_is_normal():
    m = CaptureManager()
    assert m.state.mode == CaptureMode.NORMAL
    assert m.active_tractor_boss_id is None


def test_can_start_tractor_when_idle():
    m = CaptureManager()
    assert m.can_start_tractor(boss_id=42) is True


def test_cannot_start_tractor_when_already_active():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    assert m.can_start_tractor(boss_id=99) is False


def test_cannot_start_tractor_when_captured():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    for _ in range(4):
        m.update_beam(0.1, in_beam=True)
    m.on_captured(boss_id=1, lives_after=2)
    assert m.can_start_tractor(boss_id=99) is False


def test_begin_beam_sets_active_id():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    assert m.active_tractor_boss_id == 42


def test_beam_grace_accumulates_when_in_beam():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    assert m.update_beam(0.1, in_beam=True) is False
    assert m.update_beam(0.1, in_beam=True) is False
    captured = m.update_beam(0.15, in_beam=True)
    assert captured is True


def test_beam_grace_resets_when_out_of_beam():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.update_beam(0.2, in_beam=True)
    m.update_beam(0.1, in_beam=False)
    assert m.update_beam(0.2, in_beam=True) is False


def test_on_beam_ended_clears_active():
    m = CaptureManager()
    m.begin_beam(boss_id=42)
    m.on_beam_ended()
    assert m.active_tractor_boss_id is None
    assert m.state.mode == CaptureMode.NORMAL


def test_on_captured_with_remaining_lives_enters_captured():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    assert m.state.mode == CaptureMode.CAPTURED
    assert m.state.captor_boss_id == 1
    assert m.active_tractor_boss_id is None


def test_on_captured_with_zero_lives_enters_awaiting_rescue():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=0)
    assert m.state.mode == CaptureMode.AWAITING_RESCUE
    assert m.state.rescue_timer == 5.0


def test_awaiting_rescue_timeout_signals_game_over():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=0)
    assert m.update_awaiting_rescue(2.0) is False
    assert m.update_awaiting_rescue(2.0) is False
    assert m.update_awaiting_rescue(1.5) is True


def test_awaiting_rescue_no_op_when_not_in_mode():
    m = CaptureManager()
    assert m.update_awaiting_rescue(10.0) is False


def test_on_captor_destroyed_with_lives_resets_to_normal():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_captor_destroyed()
    assert m.state.mode == CaptureMode.NORMAL
    assert m.state.captor_boss_id is None


def test_on_rescue_eligible_kill_enters_rescuing():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    triggered = m.on_rescue_eligible_kill()
    assert triggered is True
    assert m.state.mode == CaptureMode.RESCUING


def test_on_rescue_complete_enters_dual():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_rescue_eligible_kill()
    m.on_rescue_complete()
    assert m.state.mode == CaptureMode.DUAL


def test_on_dual_lost_returns_to_normal():
    m = CaptureManager()
    m.begin_beam(boss_id=1)
    m.on_captured(boss_id=1, lives_after=2)
    m.on_rescue_eligible_kill()
    m.on_rescue_complete()
    m.on_dual_lost()
    assert m.state.mode == CaptureMode.NORMAL
