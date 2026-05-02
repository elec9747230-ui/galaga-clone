"""SFX + BGM playback. Silent no-op if pygame.mixer fails to init."""

import pygame

from engine import assets

_mixer_ready = False
_music_channel: pygame.mixer.Channel | None = None
_current_music: str | None = None


def init() -> None:
    """Call after pygame.init(). Safe to call when mixer is unavailable."""
    global _mixer_ready, _music_channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(8)
        _music_channel = pygame.mixer.Channel(0)
        _mixer_ready = True
    except pygame.error as e:
        print(f"Warning: audio disabled ({e})")
        _mixer_ready = False


def play_sfx(name: str) -> None:
    if not _mixer_ready:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    ch = pygame.mixer.find_channel(True)
    if ch is _music_channel:
        return
    ch.play(snd)


def play_music(name: str, loop: bool = True) -> None:
    global _current_music
    if not _mixer_ready or _music_channel is None:
        return
    snd = assets.sound(name)
    if snd is None:
        return
    _music_channel.stop()
    _music_channel.play(snd, loops=-1 if loop else 0)
    _current_music = name


def stop_music() -> None:
    global _current_music
    if _music_channel is None:
        return
    _music_channel.stop()
    _current_music = None


def current_music() -> str | None:
    return _current_music
