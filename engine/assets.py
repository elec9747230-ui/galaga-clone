"""Asset loading + caching. Auto-runs generators if assets/ is empty."""

from pathlib import Path

import pygame

import settings

_sprites: dict[str, pygame.Surface] = {}
_sounds: dict[str, pygame.mixer.Sound] = {}


def _ensure_assets() -> None:
    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    audio_dir = Path(settings.ASSETS_AUDIO_DIR)
    if not sprites_dir.exists() or not any(sprites_dir.glob("*.png")):
        print("Generating sprites...")
        from tools import generate_sprites

        generate_sprites.main()
    if not audio_dir.exists() or not any(audio_dir.glob("*.wav")):
        print("Generating audio...")
        from tools import generate_audio

        generate_audio.main()


def load_all() -> None:
    """Call once after pygame.init(). Loads every PNG/WAV into caches."""
    _ensure_assets()

    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    for png in sprites_dir.glob("*.png"):
        _sprites[png.stem] = pygame.image.load(str(png)).convert_alpha()

    if pygame.mixer.get_init():
        audio_dir = Path(settings.ASSETS_AUDIO_DIR)
        for wav in audio_dir.glob("*.wav"):
            _sounds[wav.stem] = pygame.mixer.Sound(str(wav))


def sprite(name: str) -> pygame.Surface:
    if name not in _sprites:
        raise KeyError(f"Sprite not loaded: {name!r}. Available: {sorted(_sprites)}")
    return _sprites[name]


def sound(name: str) -> pygame.mixer.Sound | None:
    return _sounds.get(name)


def has_sound(name: str) -> bool:
    return name in _sounds
