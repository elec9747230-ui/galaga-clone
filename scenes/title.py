"""Title screen scene.

Entry point of the scene flow (title -> play -> bonus/gameover). Displays the
game logo, current high score, a difficulty selector (EASY / NORMAL / HARD),
and a blinking "PRESS SPACE TO START" prompt. Arrow keys (or A/D) cycle the
selected difficulty; the fire key (Space) commits the choice and transitions
into the gameplay scene.

Pressing Space does not jump straight to ``PlayScene``; instead it replaces
this scene with a ``TransitionScene`` that displays a "STAGE 1" banner before
constructing and entering ``PlayScene``. This keeps the user-perceived flow
consistent with later wave transitions.
"""

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from game.difficulty import Difficulty
from game.scoring import load_highscore

# Order matters — the index is used to drive the left/right selector cycling
# and to color/size the corresponding label in draw().
_DIFFICULTIES: list[Difficulty] = [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]


class TitleScene(Scene):
    """The pre-game title screen and difficulty picker.

    Attributes:
        _font_big: Large bold font used for the "GALAGA" logo.
        _font_med: Medium bold font used for subtitles and the start prompt.
        _font_sm: Small font for high score, controls hint, and dim labels.
        _t: Elapsed seconds since the scene started; drives the prompt blink.
        _highscore: High score loaded from disk on entry, displayed on screen.
        _diff_index: Index into ``_DIFFICULTIES`` for the currently highlighted
            difficulty. Defaults to 1 (NORMAL).
        _prev_left: Previous-frame state of the left input, used for edge
            detection so a held key does not rapidly cycle the selector.
        _prev_right: Previous-frame state of the right input (same purpose).
    """

    def __init__(self) -> None:
        """Build fonts, load the high score, and default the selector to NORMAL."""
        self._font_big = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_sm = pygame.font.SysFont("consolas", 22)
        self._t = 0.0
        self._highscore = load_highscore()
        self._diff_index = 1  # NORMAL by default
        # Edge-detection latches: we only advance the selector on the rising
        # edge of left/right so holding the key does not spam the cycle.
        self._prev_left = False
        self._prev_right = False

    @property
    def selected_difficulty(self) -> Difficulty:
        """Returns the Difficulty currently highlighted by the selector."""
        return _DIFFICULTIES[self._diff_index]

    def on_enter(self) -> None:
        """Start looping intro music when the title scene becomes active."""
        # Music switch: looping intro track plays for the entire title screen.
        audio.play_music("music_intro", loop=True)

    def on_exit(self) -> None:
        """Stop intro music as the title scene is replaced by the next scene."""
        # Stop here so the brief silence before the stage-start jingle is clean.
        audio.stop_music()

    def update(self, dt: float, inp: InputState) -> None:
        """Advance the prompt timer, handle selector cycling, and start the game.

        Args:
            dt: Frame delta time in seconds.
            inp: Current input snapshot (left/right cycle, fire commits).
        """
        self._t += dt
        # Rising-edge detection prevents the selector from cycling every frame
        # while the player simply holds a direction key.
        if inp.left and not self._prev_left:
            self._diff_index = (self._diff_index - 1) % len(_DIFFICULTIES)
        if inp.right and not self._prev_right:
            self._diff_index = (self._diff_index + 1) % len(_DIFFICULTIES)
        self._prev_left = inp.left
        self._prev_right = inp.right

        if inp.fire_pressed:
            # Local imports avoid a circular dependency at module load time
            # (scenes.play imports back into scenes via transitions).
            from game.difficulty import config_for
            from game.scoring import Scoring
            from scenes.play import PlayScene
            from scenes.transitions import TransitionScene

            cfg = config_for(self.selected_difficulty)
            scoring = Scoring(lives=cfg.starting_lives)
            # Scene transition: title -> "STAGE 1" banner -> play. We use
            # `replace` so the title is dropped from the stack rather than
            # parked beneath the transition.
            assert self.manager
            self.manager.replace(
                TransitionScene(
                    "STAGE 1",
                    lambda: PlayScene(scoring=scoring, difficulty=self.selected_difficulty),
                    duration=1.5,
                )
            )

    def draw(self, surface: pygame.Surface) -> None:
        """Render the title, high score, difficulty selector, and start prompt.

        Args:
            surface: The window surface to draw the title screen onto.
        """
        # Pure presentation — no game state is mutated here.
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

        # Blink the prompt at ~1 Hz: visible for 0.5s, hidden for 0.5s.
        if int(self._t * 2) % 2 == 0:
            prompt = self._font_med.render("PRESS SPACE TO START", True, settings.COLOR_WHITE)
            surface.blit(prompt, prompt.get_rect(center=(cx, 540)))
        controls = self._font_sm.render(
            "Arrow / A,D choose difficulty  |  Space start  |  Esc quit",
            True,
            settings.COLOR_HUD_DIM,
        )
        surface.blit(controls, controls.get_rect(center=(cx, 620)))
