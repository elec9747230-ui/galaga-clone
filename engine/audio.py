"""Sound effect and background-music playback wrapper around ``pygame.mixer``.

Two responsibilities:

* **SFX**: short one-shot clips played on whichever channel is currently
  free. We deliberately reserve channel 0 for music so a flurry of
  explosions can never preempt the BGM.
* **BGM**: a single looping (or one-shot) track on the reserved music
  channel, with optional delayed start via ``play_music_after`` /
  ``tick``. The delayed-start scheduler is a simple single-slot timer:
  scheduling a new track cancels any previous pending track.

If ``pygame.mixer.init`` raises (no audio device, dummy SDL driver, etc.)
the whole module degrades to silent no-ops. This keeps the game playable on
headless CI and on machines with broken audio stacks without forcing every
caller to guard against ``None`` channels.
"""

import pygame

from engine import assets

# Module-level state. We use globals (rather than a class) because there is
# only ever one mixer per process; a singleton object would just be globals
# wearing a hat.
_mixer_ready = False
_music_channel: pygame.mixer.Channel | None = None
_current_music: str | None = None
# Pending delayed-music slot. Tuple shape: (clip_name, loop, remaining_seconds).
# ``None`` means "nothing scheduled". Only one pending track at a time --
# scheduling another overwrites this slot.
_pending: tuple[str, bool, float] | None = None  # (name, loop, remaining_seconds)


def init() -> None:
    """Initialise the mixer and reserve channel 0 for music.

    Call once after ``pygame.init()``. Safe to call when the mixer cannot be
    opened: in that case we log a warning and the rest of the module
    silently no-ops on every subsequent call.

    Why these mixer params:
        * ``frequency=22050`` -- matches what ``tools/generate_audio`` writes,
          so we never resample at load time.
        * ``size=-16`` -- signed 16-bit samples (the SDL_mixer default that
          plays nicely with WAVs on every platform we target).
        * ``channels=1`` -- mono. The clips are mono and we save memory.
        * ``buffer=512`` -- low-latency buffer; small enough that SFX feel
          responsive but large enough to avoid underruns on slow machines.
    """
    global _mixer_ready, _music_channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        # Reserve a generous pool of SFX channels. 8 is plenty for a Galaga
        # clone where simultaneous audio events rarely exceed 3-4.
        pygame.mixer.set_num_channels(8)
        # Channel 0 is dedicated to music; SFX must avoid it (see play_sfx).
        _music_channel = pygame.mixer.Channel(0)
        _mixer_ready = True
    except pygame.error as e:
        # Most common cause: SDL audio driver unavailable in CI/sandbox.
        print(f"Warning: audio disabled ({e})")
        _mixer_ready = False


def play_sfx(name: str) -> None:
    """Play a one-shot sound effect on any free channel.

    Args:
        name: Asset name (file stem) of the clip to play. Missing clips and
            disabled mixer are silently ignored -- audio is best-effort.

    Why the ``find_channel`` dance: pygame's ``Sound.play()`` will happily
    grab any channel including the reserved music channel. We instead pull a
    free channel explicitly and bail out if it happens to be channel 0, so
    background music is never clobbered by a stray laser sound.
    """
    if not _mixer_ready:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    # ``find_channel(True)`` forces a channel even if all are busy by
    # stealing the oldest one -- acceptable for SFX.
    ch = pygame.mixer.find_channel(True)
    if ch is _music_channel:
        # Refuse to play SFX on the music channel; better to drop one
        # gunshot than to cut the BGM mid-bar.
        return
    ch.play(snd)


def play_music(name: str, loop: bool = True) -> None:
    """Start playing ``name`` on the dedicated music channel immediately.

    Args:
        name: Asset name (file stem) of the music clip.
        loop: If True, loop forever (``loops=-1``). If False, play once.

    Any previously playing music is stopped first, so calling this from a
    scene transition produces a clean cut.
    """
    global _current_music
    if not _mixer_ready or _music_channel is None:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    _music_channel.stop()
    # pygame convention: loops=-1 means infinite, loops=0 means play exactly
    # once. There is no "play twice" use case in this game.
    _music_channel.play(snd, loops=-1 if loop else 0)
    _current_music = name


def stop_music() -> None:
    """Stop any current or pending music and clear scheduler state."""
    global _current_music, _pending
    if _music_channel is None:
        return
    _music_channel.stop()
    _current_music = None
    # Also wipe any pending delayed-start so it cannot resurrect music.
    _pending = None


def current_music() -> str | None:
    """Return the asset name of the currently playing track, or ``None``."""
    return _current_music


def play_music_after(name: str, delay: float, loop: bool = True) -> None:
    """Schedule a music track to start after ``delay`` seconds.

    Cancels any prior schedule -- only one delayed track may be queued at a
    time. The actual start happens inside ``tick``, so the active scene
    must call ``tick(dt)`` every frame for the timer to fire.

    Args:
        name: Asset name of the clip to start.
        delay: Seconds from now until playback begins.
        loop: Forwarded to ``play_music`` when the timer fires.
    """
    global _pending
    _pending = (name, loop, delay)


def tick(dt: float) -> None:
    """Advance the delayed-music scheduler by ``dt`` seconds.

    Call once per frame from the active scene's ``update``. If a pending
    track's countdown reaches zero, this triggers ``play_music`` and clears
    the slot. No-op when nothing is pending.

    Args:
        dt: Frame delta in seconds, same value the scene receives.
    """
    global _pending
    if _pending is None:
        return
    name, loop, remaining = _pending
    remaining -= dt
    if remaining <= 0:
        # Clear the slot *before* calling play_music so a re-entrant
        # scheduler call inside play_music would not see a stale entry.
        _pending = None
        play_music(name, loop=loop)
    else:
        _pending = (name, loop, remaining)
