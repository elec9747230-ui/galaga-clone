"""HUD rendering for left and right side panels.

Reads from a Scoring instance every frame.
"""

import pygame

import settings
from engine import assets
from game.scoring import Scoring

_font_cache: dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("consolas", size, bold=True)
    return _font_cache[size]


def draw_left(surface: pygame.Surface, scoring: Scoring, highscore: int) -> None:
    panel = pygame.Surface((settings.SIDE_PANEL_WIDTH, settings.WINDOW_HEIGHT))
    panel.fill(settings.COLOR_BLACK)

    logo = assets.sprite("logo")
    panel.blit(logo, (40, 30))

    label = _font(18).render("SCORE", True, settings.COLOR_HUD_DIM)
    panel.blit(label, (40, 130))
    val = _font(36).render(f"{scoring.score:>8}", True, settings.COLOR_WHITE)
    panel.blit(val, (40, 154))

    lives_label = _font(18).render("LIVES", True, settings.COLOR_HUD_DIM)
    panel.blit(lives_label, (40, 360))
    ship = assets.sprite("player")
    for i in range(scoring.lives):
        panel.blit(ship, (40 + i * (ship.get_width() + 6), 388))

    controls = [
        "MOVE  : Arrow / A,D",
        "FIRE  : Space",
        "PAUSE : P",
        "QUIT  : Esc",
    ]
    f = _font(14)
    for i, line in enumerate(controls):
        panel.blit(f.render(line, True, settings.COLOR_HUD_DIM), (40, 540 + i * 22))

    surface.blit(panel, (0, 0))


def draw_right(surface: pygame.Surface, scoring: Scoring, highscore: int) -> None:
    panel = pygame.Surface((settings.SIDE_PANEL_WIDTH, settings.WINDOW_HEIGHT))
    panel.fill(settings.COLOR_BLACK)

    hs_label = _font(18).render("HIGH SCORE", True, settings.COLOR_HUD_DIM)
    panel.blit(hs_label, (40, 30))
    hs_val = _font(28).render(f"{highscore:>8}", True, settings.COLOR_YELLOW)
    panel.blit(hs_val, (40, 56))

    w_label = _font(18).render("WAVE", True, settings.COLOR_HUD_DIM)
    panel.blit(w_label, (40, 200))
    w_val = _font(36).render(f"{scoring.wave:>3}", True, settings.COLOR_CYAN)
    panel.blit(w_val, (40, 226))

    acc_label = _font(18).render("ACCURACY", True, settings.COLOR_HUD_DIM)
    panel.blit(acc_label, (40, 400))
    pct = scoring.accuracy() * 100
    acc_val = _font(28).render(f"{pct:5.1f}%", True, settings.COLOR_GREEN)
    panel.blit(acc_val, (40, 426))

    k_label = _font(18).render("KILLS", True, settings.COLOR_HUD_DIM)
    panel.blit(k_label, (40, 540))
    k_val = _font(28).render(f"{scoring.enemies_killed:>5}", True, settings.COLOR_WHITE)
    panel.blit(k_val, (40, 566))

    surface.blit(panel, (settings.PLAYFIELD_OFFSET_X + settings.PLAYFIELD_WIDTH, 0))
