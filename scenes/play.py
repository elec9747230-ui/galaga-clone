"""Main gameplay scene with player + enemy formation."""

import math
import random

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy, BossEnemy, ButterflyEnemy
from entities.player import Player


class PlayScene(Scene):
    def __init__(self) -> None:
        self.player = Player()
        self.players = pygame.sprite.GroupSingle(self.player)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface((settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT))
        rng = random.Random(7)
        self._stars = [
            (
                rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
                rng.randint(0, settings.PLAYFIELD_HEIGHT - 1),
            )
            for _ in range(60)
        ]
        self._formation_phase = [0.0]
        self._time = 0.0
        self._spawn_formation()

    def _spawn_formation(self) -> None:
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = (row * 0.25) + (col * 0.05)
                if row == 0:
                    cls = BossEnemy
                elif row == 1:
                    cls = ButterflyEnemy
                else:
                    cls = BeeEnemy
                self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        self._time += dt
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        self.player.update(dt, inp, self.player_bullets)
        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        surface.blit(self.playfield, (settings.PLAYFIELD_OFFSET_X, settings.PLAYFIELD_OFFSET_Y))
