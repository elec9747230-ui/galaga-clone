"""Main gameplay scene. Builds up over later tasks."""

import random

import pygame

import settings
from engine.input import InputState
from engine.scene import Scene
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

    def update(self, dt: float, inp: InputState) -> None:
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
