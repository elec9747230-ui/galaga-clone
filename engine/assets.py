"""Asset loading and in-memory caching for sprites and sounds.

This module is the single entry point the rest of the engine uses to obtain
``pygame.Surface`` and ``pygame.mixer.Sound`` objects. It performs three jobs:

1. If the on-disk ``assets/`` directory is missing or empty, it transparently
   invokes the procedural generators under ``tools/`` so the game can run from
   a fresh checkout without any pre-built binary assets.
2. On startup it eagerly loads every ``*.png`` and ``*.wav`` it finds into
   process-local dictionaries keyed by file stem (the filename without
   extension). This keeps the per-frame hot path allocation-free.
3. It exposes small accessor functions (``sprite``, ``sound``, ``has_sound``)
   that the rest of the codebase uses instead of touching pygame loaders
   directly. This indirection lets us swap the loading strategy without
   changing call sites.

Design note: the caches are module-level globals on purpose. The game has a
single asset namespace and a single pygame display, so a singleton-style
module is simpler than threading a registry object through every scene.
"""

from pathlib import Path

import pygame

import settings

# Module-level caches. Keys are file stems (e.g. "player", not "player.png")
# so callers do not need to know the on-disk extension.
_sprites: dict[str, pygame.Surface] = {}
_sounds: dict[str, pygame.mixer.Sound] = {}


def _ensure_assets() -> None:
    """Generate sprite/audio assets on disk if their directories are empty.

    Why: the repo intentionally does not commit binary assets. The first time
    the game runs (or any time the directories are wiped) we re-create them
    procedurally so ``load_all`` always finds something to load.

    The generator imports are deferred to inside the ``if`` branches so that
    the (potentially slow) ``tools.*`` modules are not imported on every
    launch -- only when generation is actually required.
    """
    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    audio_dir = Path(settings.ASSETS_AUDIO_DIR)
    # Treat "directory missing" and "directory present but no PNGs" as
    # equivalent: both mean we need to (re)generate sprites.
    if not sprites_dir.exists() or not any(sprites_dir.glob("*.png")):
        print("Generating sprites...")
        from tools import generate_sprites

        generate_sprites.main()
    if not audio_dir.exists() or not any(audio_dir.glob("*.wav")):
        print("Generating audio...")
        from tools import generate_audio

        generate_audio.main()


def load_all() -> None:
    """Populate the sprite and sound caches from disk.

    Must be called once after ``pygame.init()`` (and ideally after
    ``pygame.display.set_mode``, since ``convert_alpha`` requires a video
    surface to exist). Calling it earlier raises ``pygame.error``.

    Returns:
        None. Results are stored in the module-level ``_sprites`` and
        ``_sounds`` dictionaries.
    """
    _ensure_assets()

    sprites_dir = Path(settings.ASSETS_SPRITES_DIR)
    for png in sprites_dir.glob("*.png"):
        # convert_alpha() pre-multiplies the surface format to match the
        # display, which is the standard pygame perf trick: blits become
        # a memcpy instead of a per-pixel format conversion.
        _sprites[png.stem] = pygame.image.load(str(png)).convert_alpha()

    # The mixer is optional -- on headless CI or systems with no audio
    # device the rest of the game still works, we just skip sound loading.
    if pygame.mixer.get_init():
        audio_dir = Path(settings.ASSETS_AUDIO_DIR)
        for wav in audio_dir.glob("*.wav"):
            _sounds[wav.stem] = pygame.mixer.Sound(str(wav))


def sprite(name: str) -> pygame.Surface:
    """Return the cached surface for ``name``.

    Args:
        name: File stem of the sprite (e.g. ``"player"`` for ``player.png``).

    Returns:
        The loaded ``pygame.Surface``.

    Raises:
        KeyError: If no sprite with that name was loaded. The error lists
            every available key, which makes typos much easier to spot.
    """
    if name not in _sprites:
        raise KeyError(f"Sprite not loaded: {name!r}. Available: {sorted(_sprites)}")
    return _sprites[name]


def sound(name: str) -> pygame.mixer.Sound | None:
    """Return the cached ``Sound`` for ``name``, or ``None`` if absent.

    Why ``None`` instead of raising: audio is best-effort. Callers should be
    able to fire-and-forget without wrapping every ``play_sfx`` in a
    try/except for the headless-CI case.

    Args:
        name: File stem of the audio clip (e.g. ``"explosion"``).

    Returns:
        The loaded ``pygame.mixer.Sound``, or ``None`` if it was never loaded
        (mixer disabled, file missing, etc.).
    """
    return _sounds.get(name)


def has_sound(name: str) -> bool:
    """Return whether a sound clip is currently cached under ``name``.

    Args:
        name: File stem of the audio clip.

    Returns:
        True iff ``sound(name)`` would return a non-None value.
    """
    return name in _sounds
