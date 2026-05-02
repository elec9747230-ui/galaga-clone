"""Game over screen -- show final score, save high score, return to title."""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.scoring import Scoring, load_highscore, save_highscore


class GameOverScene(Scene):
    def __init__(self, scoring: Scoring) -> None:
        self.scoring = scoring
        self._font_big = pygame.font.SysFont("consolas", 64, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 20)
        self._t = 0.0
        prev = load_highscore()
        self.is_new_high = scoring.score > prev
        if self.is_new_high:
            save_highscore(scoring.score)
        audio.play_music("music_game_over", loop=False)

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if self._t > 1.0 and inp.fire_pressed:
            from scenes.title import TitleScene

            assert self.manager
            self.manager.replace(TitleScene())

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        title = self._font_big.render("GAME OVER", True, settings.COLOR_RED)
        score = self._font_med.render(f"Score: {self.scoring.score}", True, settings.COLOR_WHITE)
        kills = self._font_sm.render(
            f"Kills: {self.scoring.enemies_killed}    Accuracy: {self.scoring.accuracy() * 100:.1f}%",
            True,
            settings.COLOR_HUD_DIM,
        )
        new_hs = (
            self._font_med.render("NEW HIGH SCORE!", True, settings.COLOR_YELLOW)
            if self.is_new_high
            else None
        )
        prompt = self._font_sm.render("Press SPACE to continue", True, settings.COLOR_HUD_DIM)

        cx = settings.WINDOW_WIDTH // 2
        surface.blit(title, title.get_rect(center=(cx, 200)))
        surface.blit(score, score.get_rect(center=(cx, 290)))
        surface.blit(kills, kills.get_rect(center=(cx, 340)))
        if new_hs:
            surface.blit(new_hs, new_hs.get_rect(center=(cx, 400)))
        if self._t > 1.0:
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
