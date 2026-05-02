"""Main gameplay scene: formation + dives + collisions + explosions + lives."""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy, BossEnemy, ButterflyEnemy
from entities.explosion import Explosion
from entities.player import Player
from game import hud
from game.scoring import Scoring, load_highscore
from game.wave import WaveController


class PlayScene(Scene):
    def __init__(self, scoring: Scoring | None = None) -> None:
        self.scoring = scoring or Scoring()
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
        self._dive_seed_counter = 1
        self._dive_probability_per_sec = 0.25
        self._respawn_timer = 0.0
        self._player_alive = True
        self._highscore = load_highscore()
        self.wave_controller = WaveController(start_wave=self.scoring.wave)
        self._apply_wave_difficulty()
        self._spawn_formation()

    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        self._dive_probability_per_sec = 0.20 + 0.5 * p.dive_probability

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

        if self._player_alive:
            self.player.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        else:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0 and self.scoring.lives > 0:
                self.player = Player()
                self.players = pygame.sprite.GroupSingle(self.player)
                self._player_alive = True

        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt * 60:
            attacker = random.choice(in_formation)
            self._dive_seed_counter += 1
            attacker.start_dive(self.player.pos, self._dive_seed_counter)
            audio.play_sfx("sfx_dive")

        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(self.player.pos)
                if bullet:
                    self.enemy_bullets.add(bullet)

        self._handle_collisions()

        if not self.enemies:
            self.wave_controller.advance()
            self.scoring.wave = self.wave_controller.current_wave
            self._apply_wave_difficulty()
            self._spawn_formation()

    def _handle_collisions(self) -> None:
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                kind = "dive" if e.state.value == "diving" else e.score_kind
                self.scoring.add_kill(kind)
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")

        if not self._player_alive:
            return

        if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
            self._kill_player()
            return

        diving_collisions = [
            e
            for e in self.enemies
            if e.state.value == "diving" and self.player.rect.colliderect(e.rect)
        ]
        if diving_collisions:
            for e in diving_collisions:
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                e.kill()
            self._kill_player()

    def _kill_player(self) -> None:
        self.explosions.add(Explosion(pygame.Vector2(self.player.pos)))
        audio.play_sfx("sfx_player_hit")
        self.scoring.lose_life()
        self.players.empty()
        self._player_alive = False
        self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        if self.scoring.lives <= 0:
            from scenes.gameover import GameOverScene

            assert self.manager
            self.manager.replace(GameOverScene(self.scoring))

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
        hud.draw_left(surface, self.scoring, self._highscore)
        hud.draw_right(surface, self.scoring, self._highscore)
