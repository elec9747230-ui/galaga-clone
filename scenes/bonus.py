"""Bonus (challenging) stage. Enemies enter, don't fire, perfect = +10000 + 1 life."""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy
from entities.explosion import Explosion
from entities.player import Player
from game import hud
from game.scoring import Scoring, load_highscore


class BonusScene(Scene):
    """Reuses player + bullets but no enemy fire and time-limited."""

    def __init__(self, scoring: Scoring) -> None:
        self.scoring = scoring
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface((settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT))
        rng = random.Random(101)
        self._stars = [
            (
                rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
                rng.randint(0, settings.PLAYFIELD_HEIGHT - 1),
            )
            for _ in range(60)
        ]
        self._formation_phase = [0.0]
        self._time = 0.0
        self._initial_count = settings.FORMATION_ROWS * settings.FORMATION_COLS
        self._kills = 0
        self._paused = False
        self._highscore = load_highscore()
        self._spawn()
        audio.play_music("music_bonus", loop=False)

    def _spawn(self) -> None:
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = 0.5 + (row * 0.4) + (col * 0.08)
                self.enemies.add(BeeEnemy(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        if inp.pause_pressed:
            self._paused = not self._paused
        if self._paused:
            return
        self._time += dt
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        self.player.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        for b in self.player_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                self.scoring.add_kill("bonus")
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")
                self._kills += 1

        if self._time > settings.BONUS_STAGE_DURATION or not self.enemies:
            self._finish()

    def _finish(self) -> None:
        if self._kills == self._initial_count:
            self.scoring.score += settings.SCORE_BONUS_PERFECT
            for _ in range(settings.LIFE_BONUS_PERFECT):
                self.scoring.gain_life()
            audio.play_sfx("sfx_extra_life")
        self.scoring.wave += 1
        from scenes.play import PlayScene
        from scenes.transitions import TransitionScene

        assert self.manager
        self.manager.replace(
            TransitionScene(
                f"STAGE {self.scoring.wave}",
                lambda: PlayScene(scoring=self.scoring),
                duration=1.5,
            )
        )

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.explosions.draw(self.playfield)
        if self._paused:
            overlay = pygame.Surface(
                (settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 160))
            self.playfield.blit(overlay, (0, 0))
            f = pygame.font.SysFont("consolas", 48, bold=True)
            text = f.render("PAUSED", True, settings.COLOR_WHITE)
            rect = text.get_rect(
                center=(settings.PLAYFIELD_WIDTH // 2, settings.PLAYFIELD_HEIGHT // 2)
            )
            self.playfield.blit(text, rect)
        surface.blit(self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y))
        hud.draw_left(surface, self.scoring, self._highscore)
        hud.draw_right(surface, self.scoring, self._highscore)
