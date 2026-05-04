"""Game-over scene.

Terminal node of the gameplay flow (title -> play -> bonus/gameover). When the
player runs out of lives in ``PlayScene`` (or the post-capture rescue window
expires), the play scene replaces itself with this scene. We display the final
score and accuracy, persist a new high score if the run beat the previous
record, and wait for the player to press the fire key to return to the title.

A short input lockout is applied at the start of the scene so a button-press
that was still being held when the player died does not immediately skip the
results screen.
"""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.scoring import Scoring, load_highscore, save_highscore


class GameOverScene(Scene):
    """End-of-run results screen.

    Attributes:
        scoring: The completed run's scoring snapshot (score, kills, accuracy).
        _font_big: Large bold font for the "GAME OVER" headline.
        _font_med: Medium bold font for score and high-score notification.
        _font_sm: Small font for the kills/accuracy line and continue prompt.
        _t: Elapsed seconds; used for the input lockout and prompt gating.
        is_new_high: True iff this run's score beat the previously saved
            high score; used to display the "NEW HIGH SCORE!" banner.
    """

    def __init__(self, scoring: Scoring) -> None:
        """Capture final scoring, persist a new high score if applicable, and start music.

        Args:
            scoring: Final ``Scoring`` from the completed ``PlayScene`` run.
        """
        self.scoring = scoring
        self._font_big = pygame.font.SysFont("consolas", 64, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 20)
        self._t = 0.0
        prev = load_highscore()
        self.is_new_high = scoring.score > prev
        # Persist immediately so the value survives even if the player force-quits
        # from this screen rather than returning to the title.
        if self.is_new_high:
            save_highscore(scoring.score)
        # Music switch: one-shot game-over jingle (no loop — silence afterwards).
        audio.play_music("music_game_over", loop=False)

    def update(self, dt: float, inp: InputState) -> None:
        """Advance the lockout timer and return to the title when the player confirms.

        Args:
            dt: Frame delta time in seconds.
            inp: Current input snapshot; the fire key acknowledges the screen.
        """
        self._t += dt
        # 1-second input lockout: ignore fire presses early so a held shot from
        # the moment of death does not skip the results screen instantly.
        if self._t > 1.0 and inp.fire_pressed:
            # Local import avoids a circular reference between scene modules.
            from scenes.title import TitleScene

            # Scene-stack: replace game-over with a fresh title scene (no nesting).
            assert self.manager
            self.manager.replace(TitleScene())

    def draw(self, surface: pygame.Surface) -> None:
        """Render the results layout (headline, score, kills, optional new-high, prompt).

        Args:
            surface: The window surface to render onto.
        """
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
        # Hide the continue prompt while the input lockout is still active so
        # the user is not invited to press a key that would be ignored.
        if self._t > 1.0:
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
