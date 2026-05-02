"""Title screen -- Press SPACE to start."""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.scoring import load_highscore


class TitleScene(Scene):
    def __init__(self) -> None:
        self._font_big = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 22)
        self._t = 0.0
        self._highscore = load_highscore()

    def on_enter(self) -> None:
        audio.play_music("music_intro", loop=True)

    def on_exit(self) -> None:
        audio.stop_music()

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if inp.fire_pressed:
            from game.scoring import Scoring
            from scenes.play import PlayScene
            from scenes.transitions import TransitionScene

            assert self.manager
            self.manager.replace(
                TransitionScene(
                    "STAGE 1",
                    lambda: PlayScene(scoring=Scoring()),
                    duration=1.5,
                )
            )

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        title = self._font_big.render("GALAGA", True, settings.COLOR_YELLOW)
        sub = self._font_med.render("CLONE", True, settings.COLOR_HUD_DIM)
        hs = self._font_sm.render(f"HIGH SCORE   {self._highscore}", True, settings.COLOR_CYAN)
        cx = settings.WINDOW_WIDTH // 2
        surface.blit(title, title.get_rect(center=(cx, 200)))
        surface.blit(sub, sub.get_rect(center=(cx, 280)))
        surface.blit(hs, hs.get_rect(center=(cx, 380)))
        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 520)))
        controls = self._font_sm.render(
            "Arrow / A,D move  |  Space fire  |  P pause  |  Esc quit",
            True,
            settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
