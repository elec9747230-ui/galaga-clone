"""Bonus ("challenging") stage scene.

Periodically inserted between normal play waves (title -> play -> bonus -> play
-> ... -> gameover). The wave controller in ``PlayScene`` decides when a bonus
stage is due; it then replaces itself with a transition into this scene.

Bonus-stage rules differ from regular play:
  * Enemies fly their entry pattern but do **not** fire and do **not** dive.
  * Collisions between diving enemies and the player are not relevant.
  * The stage is time-limited (``BONUS_STAGE_DURATION``); it also ends early
    if every enemy is destroyed.
  * If the player kills every enemy spawned (a "perfect"), a flat score
    bonus and an extra life are awarded.

When the stage ends, control transitions back to ``PlayScene`` for the next
regular wave via a "STAGE N" banner.
"""

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
from game.difficulty import Difficulty
from game.scoring import Scoring, load_highscore


class BonusScene(Scene):
    """Time-limited "challenging" stage with non-firing enemies and a perfect bonus.

    Attributes:
        difficulty: Difficulty carried over from the run; passed back to the
            next ``PlayScene`` when the bonus stage ends.
        scoring: Live scoring object shared with the rest of the run.
        player: The single player ship for this stage.
        players: GroupSingle holding ``player`` for sprite-group draw.
        player_bullets: Active player projectiles (collision group).
        enemies: Active bonus-stage enemies (collision group).
        explosions: Visual-only explosion sprites.
        playfield: Off-screen surface representing the play area; blitted onto
            the window at the playfield offset so the HUD can occupy the sides.
        _stars: Precomputed (x, y) starfield speckle positions.
        _formation_phase: Single-element list passed by reference into enemies
            so all share one synchronized phase value for formation sway.
        _time: Elapsed scene time, drives the formation phase and end-condition.
        _initial_count: Number of enemies spawned at the start; used to detect
            a "perfect" clear when ``_kills`` equals this value.
        _kills: Enemies destroyed by the player so far this stage.
        _paused: Player-pause flag (toggled by the pause input).
        _highscore: High score loaded once for HUD display.
    """

    def __init__(self, scoring: Scoring, difficulty: Difficulty = Difficulty.NORMAL) -> None:
        """Spawn the formation, set up sprite groups, and start bonus music.

        Args:
            scoring: Live scoring object to mutate (kills, perfect bonus, etc.).
            difficulty: Difficulty to forward into the next ``PlayScene``.
        """
        self.difficulty = difficulty
        self.scoring = scoring
        self.player = Player()
        # GroupSingle is fine here: bonus stage never has dual-fighter mode.
        self.players = pygame.sprite.GroupSingle(self.player)
        # Collision groups: bullets vs. enemies is the only collision check.
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.playfield = pygame.Surface((settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT))
        # Deterministic star pattern (fixed seed) so the bonus stage backdrop
        # looks identical across runs and hardware.
        rng = random.Random(101)
        self._stars = [
            (
                rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
                rng.randint(0, settings.PLAYFIELD_HEIGHT - 1),
            )
            for _ in range(60)
        ]
        # Single-element list shared by reference with all enemies; updating
        # _formation_phase[0] propagates to every enemy each frame without
        # iterating them.
        self._formation_phase = [0.0]
        self._time = 0.0
        self._initial_count = settings.FORMATION_ROWS * settings.FORMATION_COLS
        self._kills = 0
        self._paused = False
        self._highscore = load_highscore()
        self._spawn()
        # Music switch: dedicated bonus-stage track (looped while stage runs).
        audio.play_music("music_bonus", loop=True)

    def _spawn(self) -> None:
        """Populate the formation grid with bee enemies, staggered by entry delay."""
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                # Per-cell delay so the entrance reads as a wave rather than a
                # simultaneous pop-in (rows further back enter later).
                delay = 0.5 + (row * 0.4) + (col * 0.08)
                self.enemies.add(BeeEnemy(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        """Step the simulation: pause handling, motion, collisions, end check.

        Args:
            dt: Frame delta time in seconds.
            inp: Current input snapshot.
        """
        # Pause toggle: edge-triggered by the input layer so a held key does
        # not flicker the pause state.
        if inp.pause_pressed:
            self._paused = not self._paused
        if self._paused:
            # Pause logic: skip *all* simulation; draw() still renders the
            # overlay. Time does not advance, so the stage timer also pauses.
            return
        self._time += dt
        # Drive the shared formation phase; 4-second period chosen empirically
        # to match the visual sway in the original game.
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        self.player.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        # Manual update calls (rather than Group.update) so we can pass dt
        # explicitly without the implicit *args dance.
        for b in self.player_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)

        # Collision: player_bullets vs enemies. Both groups use dokill=True so
        # the bullet is consumed and the enemy removed in one pass.
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                # Score/kills tracking: "bonus" kind feeds the bonus-stage
                # tally separately from regular gameplay kills.
                self.scoring.add_kill("bonus")
                self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                audio.play_sfx("sfx_explode")
                self._kills += 1

        # End conditions: time expired OR every enemy destroyed.
        if self._time > settings.BONUS_STAGE_DURATION or not self.enemies:
            self._finish()

    def _finish(self) -> None:
        """Award the perfect bonus if applicable and transition back to PlayScene."""
        # Perfect bonus path: only fires when every spawned enemy was killed.
        # Awards a fixed score plus one or more extra lives (configurable).
        if self._kills == self._initial_count:
            self.scoring.score += settings.SCORE_BONUS_PERFECT
            for _ in range(settings.LIFE_BONUS_PERFECT):
                self.scoring.gain_life()
            audio.play_sfx("sfx_extra_life")
        # Advance the wave counter so the upcoming PlayScene starts on the
        # correct stage number for HUD and difficulty scaling.
        self.scoring.wave += 1
        # Local imports break a circular dependency: scenes.play imports back
        # into scenes via transitions which would otherwise re-enter this module.
        from scenes.play import PlayScene
        from scenes.transitions import TransitionScene

        # Scene-stack swap: bonus -> "STAGE N" banner -> next PlayScene.
        assert self.manager
        self.manager.replace(
            TransitionScene(
                f"STAGE {self.scoring.wave}",
                lambda: PlayScene(scoring=self.scoring, difficulty=self.difficulty),
                duration=1.5,
            )
        )

    def draw(self, surface: pygame.Surface) -> None:
        """Render starfield, sprites, optional pause overlay, and HUD.

        Args:
            surface: The window surface; the playfield is composited onto it
                with the configured offset to leave room for the HUD columns.
        """
        # Draw is read-only with respect to game state — kept strictly separate
        # from update() so a paused scene can still render correctly.
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        self.explosions.draw(self.playfield)
        if self._paused:
            # Pause overlay: semi-transparent dim plus a centered "PAUSED" label.
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
        # HUD columns straddle the playfield (left = score/lives, right = waves).
        hud.draw_left(surface, self.scoring, self._highscore)
        hud.draw_right(surface, self.scoring, self._highscore)
