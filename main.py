"""Galaga clone -- main entry point.

This module wires together the engine subsystems (display, audio, asset
pipeline, input reader, and scene manager) and runs the main game loop.
On first launch the asset loader auto-generates any missing sprite/audio
files into ``assets/`` so the game is playable from a fresh checkout
without external resources.

Boot sequence:
    1. ``pygame.init()`` and audio mixer initialization.
    2. Open the display window at the configured resolution.
    3. Trigger ``assets.load_all()`` which generates and caches all art/SFX.
    4. Create a ``SceneManager`` and push the initial ``TitleScene``.
    5. Enter the fixed-timestep main loop until the user quits.
    6. Cleanly shut down pygame on exit (including the unhandled-exception path).
"""

import sys
import traceback

import pygame

import settings
from engine import assets, audio
from engine.input import InputReader
from engine.scene import SceneManager
from scenes.title import TitleScene


def main() -> int:
    """Run the game until the user quits.

    Performs full boot (pygame, audio, display, asset generation, scene stack),
    then drives the main loop: per-frame timing, event pumping, input snapshot,
    scene update/draw, and buffer flip. ``pygame.quit()`` is called before
    returning so a normal exit leaves no resources dangling.

    Returns:
        int: Process exit code. ``0`` on a clean shutdown.
    """
    pygame.init()
    audio.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Galaga Clone")
    clock = pygame.time.Clock()

    # Load (or auto-generate on first run) every sprite and sound effect.
    assets.load_all()

    # Scene stack starts at the title screen; gameplay scenes are pushed from there.
    manager = SceneManager()
    manager.replace(TitleScene())
    inp = InputReader()

    running = True
    while running:
        # ``clock.tick`` caps the frame rate and returns elapsed ms; convert to
        # seconds so all simulation code can use consistent SI units.
        dt = clock.tick(settings.FPS) / 1000.0
        events = pygame.event.get()
        inp.begin_frame(events)
        for ev in events:
            manager.handle_event(ev)
        if inp.state.quit_pressed:
            running = False

        manager.update(dt, inp.state)
        manager.draw(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    # Top-level guard: if anything escapes ``main`` we still want to print a
    # readable traceback and tear down pygame so the OS window/audio device
    # are released before the interpreter exits with a non-zero status.
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
