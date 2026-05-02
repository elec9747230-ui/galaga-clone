"""Galaga clone -- main entry point."""

import sys
import traceback

import pygame

import settings
from engine import assets, audio
from engine.input import InputReader
from engine.scene import SceneManager
from scenes.play import PlayScene


def main() -> int:
    pygame.init()
    audio.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Galaga Clone")
    clock = pygame.time.Clock()

    assets.load_all()

    manager = SceneManager()
    manager.replace(PlayScene())
    inp = InputReader()

    running = True
    while running:
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
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
