"""Title screen -- Press SPACE to start. Arrow/A,D to choose difficulty."""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.difficulty import Difficulty
from game.scoring import load_highscore

_DIFFICULTIES: list[Difficulty] = [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]


class TitleScene(Scene):
    def __init__(self) -> None:
        self._font_big = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 22)
        self._t = 0.0
        self._highscore = load_highscore()
        self._diff_index = 1  # NORMAL by default
        self._prev_left = False
        self._prev_right = False

    @property
    def selected_difficulty(self) -> Difficulty:
        return _DIFFICULTIES[self._diff_index]

    def on_enter(self) -> None:
        audio.play_music("music_intro", loop=True)

    def on_exit(self) -> None:
        audio.stop_music()

    def update(self, dt: float, inp: InputState) -> None:
        self._t += dt
        if inp.left and not self._prev_left:
            self._diff_index = (self._diff_index - 1) % len(_DIFFICULTIES)
        if inp.right and not self._prev_right:
            self._diff_index = (self._diff_index + 1) % len(_DIFFICULTIES)
        self._prev_left = inp.left
        self._prev_right = inp.right

        if inp.fire_pressed:
            from game.difficulty import config_for
            from game.scoring import Scoring
            from scenes.play import PlayScene
            from scenes.transitions import TransitionScene

            cfg = config_for(self.selected_difficulty)
            scoring = Scoring(lives=cfg.starting_lives)
            assert self.manager
            self.manager.replace(
                TransitionScene(
                    "STAGE 1",
                    lambda: PlayScene(scoring=scoring, difficulty=self.selected_difficulty),
                    duration=1.5,
                )
            )

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        title = self._font_big.render("GALAGA", True, settings.COLOR_YELLOW)
        sub = self._font_med.render("CLONE", True, settings.COLOR_HUD_DIM)
        hs = self._font_sm.render(f"HIGH SCORE   {self._highscore}", True, settings.COLOR_CYAN)
        cx = settings.WINDOW_WIDTH // 2
        surface.blit(title, title.get_rect(center=(cx, 180)))
        surface.blit(sub, sub.get_rect(center=(cx, 250)))
        surface.blit(hs, hs.get_rect(center=(cx, 330)))

        diff_y = 430
        diff_label = self._font_sm.render("DIFFICULTY", True, settings.COLOR_HUD_DIM)
        surface.blit(diff_label, diff_label.get_rect(center=(cx, diff_y - 30)))
        labels = ["EASY", "NORMAL", "HARD"]
        spacing = 160
        start_x = cx - spacing
        for i, name in enumerate(labels):
            color = settings.COLOR_WHITE if i == self._diff_index else settings.COLOR_HUD_DIM
            font = self._font_med if i == self._diff_index else self._font_sm
            rendered = font.render(name, True, color)
            surface.blit(rendered, rendered.get_rect(center=(start_x + i * spacing, diff_y)))
        arrow_l = self._font_med.render("<", True, settings.COLOR_CYAN)
        surface.blit(arrow_l, arrow_l.get_rect(center=(cx - 280, diff_y)))
        arrow_r = self._font_med.render(">", True, settings.COLOR_CYAN)
        surface.blit(arrow_r, arrow_r.get_rect(center=(cx + 280, diff_y)))

        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
        controls = self._font_sm.render(
            "Arrow / A,D choose difficulty  |  Space start  |  Esc quit",
            True,
            settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
