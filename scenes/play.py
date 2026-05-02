"""Main gameplay scene: formation + dives + collisions + explosions + lives + tractor beam."""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.enemy import BeeEnemy, BossEnemy, ButterflyEnemy, EnemyState
from entities.explosion import Explosion
from entities.player import Player
from entities.rescuing_ship import RescuingShip
from entities.tractor_beam import TractorBeam
from game import hud
from game.capture import CaptureManager, CaptureMode
from game.difficulty import Difficulty, config_for
from game.scoring import Scoring, load_highscore
from game.wave import WaveController


class PlayScene(Scene):
    def __init__(
        self,
        scoring: Scoring | None = None,
        difficulty: Difficulty = Difficulty.NORMAL,
        dual: bool = False,
    ) -> None:
        self.difficulty = difficulty
        self._diff_cfg = config_for(difficulty)
        if scoring is None:
            scoring = Scoring(lives=self._diff_cfg.starting_lives)
        self.scoring = scoring
        # Player(s) — Group (not GroupSingle) so we can hold 2 in dual mode
        self.player = Player()
        self.players: pygame.sprite.Group = pygame.sprite.Group(self.player)
        if dual:
            self.player.dual_offset = -settings.DUAL_FIGHTER_OFFSET
            self.player.is_left_half = True
            self.player.is_right_half = False
            self.player.pos.x += self.player.dual_offset
            self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))
            second = Player(dual_offset=settings.DUAL_FIGHTER_OFFSET, is_right_half=True)
            self.players.add(second)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.tractor_beams: pygame.sprite.Group = pygame.sprite.Group()
        self.rescuing_ships: pygame.sprite.Group = pygame.sprite.Group()
        self.capture_mgr = CaptureManager()
        if dual:
            self.capture_mgr.state.mode = CaptureMode.DUAL
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
        self._paused = False
        self._highscore = load_highscore()
        self.wave_controller = WaveController(start_wave=self.scoring.wave)
        self._apply_wave_difficulty()
        self._spawn_formation()

    def on_enter(self) -> None:
        audio.play_music("music_stage_start", loop=False)

    def _apply_wave_difficulty(self) -> None:
        p = self.wave_controller.current_params()
        base_rate = 0.5 + 30.0 * p.dive_probability
        self._dive_probability_per_sec = base_rate * self._diff_cfg.dive_freq_multiplier

    def _spawn_formation(self) -> None:
        from game.wave import WaveType

        wave_type = self.wave_controller.current_type()
        is_boss = wave_type == WaveType.BOSS
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                delay = (row * 0.25) + (col * 0.05)
                if is_boss:
                    cls = BossEnemy if row < 2 else ButterflyEnemy
                else:
                    if row == 0:
                        cls = BossEnemy
                    elif row == 1:
                        cls = ButterflyEnemy
                    else:
                        cls = BeeEnemy
                self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        if inp.pause_pressed:
            self._paused = not self._paused
        if self._paused:
            return
        self._time += dt
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        # Player update / respawn (per-ship to support dual)
        alive_players = list(self.players)
        if alive_players:
            self._player_alive = True
            self.player = alive_players[0]
            for p in alive_players:
                p.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        else:
            self._player_alive = False
            self._respawn_timer -= dt
            if (
                self._respawn_timer <= 0
                and self.scoring.lives > 0
                and self.capture_mgr.state.mode != CaptureMode.AWAITING_RESCUE
            ):
                self.player = Player()
                self.players.add(self.player)
                self._player_alive = True

        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for x in self.explosions:
            x.update(dt)
        for b in self.tractor_beams:
            b.update(dt)
        for r in self.rescuing_ships:
            r.update(dt)

        # Dive trigger — roll for tractor beam on bosses
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        if in_formation and random.random() < self._dive_probability_per_sec * dt:
            attacker = random.choice(in_formation)
            self._dive_seed_counter += 1
            tractor_chance = (
                settings.TRACTOR_BEAM_PROBABILITY * self._diff_cfg.tractor_probability_multiplier
            )
            if (
                isinstance(attacker, BossEnemy)
                and self.capture_mgr.can_start_tractor(id(attacker))
                and self._player_alive
                and random.random() < tractor_chance
            ):
                attacker.enter_tractor_align(pygame.Vector2(self.player.pos))
                self.capture_mgr.begin_beam(id(attacker))
            else:
                attacker.start_dive(self.player.pos, self._dive_seed_counter)
                audio.play_sfx("sfx_dive")

        # Spawn TractorBeam for any boss that just entered TRACTOR_BEAMING
        for e in self.enemies:
            if e.state == EnemyState.TRACTOR_BEAMING and not any(
                b.boss is e for b in self.tractor_beams
            ):
                self.tractor_beams.add(TractorBeam(e))
                audio.play_sfx("sfx_dive")

        # Diving enemies may fire
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(
                    self.player.pos,
                    speed_multiplier=self._diff_cfg.enemy_bullet_speed_multiplier,
                )
                if bullet:
                    self.enemy_bullets.add(bullet)

        # Beam-vs-player collision and capture grace
        captured_player = None
        captured_beam = None
        any_in_beam = False
        if self._player_alive and self.tractor_beams:
            for beam in self.tractor_beams:
                left_player = next((p for p in self.players if not p.is_right_half), None)
                if left_player is not None and beam.contains(pygame.Vector2(left_player.pos)):
                    any_in_beam = True
                    captured_player = left_player
                    captured_beam = beam
                    break
        if self.tractor_beams:
            triggered = self.capture_mgr.update_beam(dt, any_in_beam)
            if triggered and captured_player is not None and captured_beam is not None:
                self._perform_capture(captured_beam, captured_player)

        # Naturally-expired beams: end without capture
        for beam in list(self.tractor_beams):
            if beam.expired:
                if beam.boss in self.enemies and beam.boss.state == EnemyState.TRACTOR_BEAMING:
                    self._dive_seed_counter += 1
                    beam.boss.start_dive(self.player.pos, self._dive_seed_counter)
                self.capture_mgr.on_beam_ended()

        # Awaiting-rescue timeout
        if self.capture_mgr.update_awaiting_rescue(dt):
            self._game_over()
            return

        self._handle_collisions()

        if not self.enemies:
            self.wave_controller.advance()
            self.scoring.wave = self.wave_controller.current_wave
            self._apply_wave_difficulty()
            next_type = self.wave_controller.current_type()
            from game.wave import WaveType
            from scenes.transitions import TransitionScene

            if next_type == WaveType.BONUS:
                from scenes.bonus import BonusScene

                assert self.manager
                self.manager.replace(
                    TransitionScene(
                        "CHALLENGING STAGE",
                        lambda: BonusScene(self.scoring, self.difficulty),
                        duration=1.8,
                    )
                )
            else:
                text = (
                    f"STAGE {self.scoring.wave}" if next_type == WaveType.NORMAL else "BOSS STAGE"
                )
                is_dual = self.capture_mgr.state.mode == CaptureMode.DUAL
                assert self.manager
                self.manager.replace(
                    TransitionScene(
                        text,
                        lambda: type(self)(
                            scoring=self.scoring,
                            difficulty=self.difficulty,
                            dual=is_dual,
                        ),
                        duration=1.5,
                    )
                )

    def _handle_collisions(self) -> None:
        # Player bullets vs enemies — branch on boss + capture state
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                handled = False
                if (
                    isinstance(e, BossEnemy)
                    and e.captured_ship is not None
                    and e.state == EnemyState.DIVING
                ):
                    self._perform_rescue(e)
                    handled = True
                elif isinstance(e, BossEnemy) and e.state in (
                    EnemyState.TRACTOR_ALIGNING,
                    EnemyState.TRACTOR_BEAMING,
                ):
                    self.scoring.add_kill("tractor")
                    for beam in list(self.tractor_beams):
                        if beam.boss is e:
                            beam.kill()
                    self.capture_mgr.on_beam_ended()
                else:
                    kind = "dive" if e.state == EnemyState.DIVING else e.score_kind
                    self.scoring.add_kill(kind)
                    if isinstance(e, BossEnemy) and e.captured_ship is not None:
                        # Captor died not via rescue — captured ship lost
                        self.capture_mgr.on_captor_destroyed()
                if not handled:
                    self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                    audio.play_sfx("sfx_explode")

        if not self._player_alive:
            return

        # Enemy bullets vs each player half independently
        for p in list(self.players):
            if pygame.sprite.spritecollide(p, self.enemy_bullets, True):
                self._kill_player_half(p)

        # Diving enemies vs each player half
        for p in list(self.players):
            diving = [
                e
                for e in self.enemies
                if e.state == EnemyState.DIVING and p.rect.colliderect(e.rect)
            ]
            if diving:
                for e in diving:
                    self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                    e.kill()
                self._kill_player_half(p)

    def _kill_player_half(self, p: Player) -> None:
        self.explosions.add(Explosion(pygame.Vector2(p.pos)))
        audio.play_sfx("sfx_player_hit")
        was_dual = len(self.players) >= 2
        p.kill()
        self.scoring.lose_life()
        if was_dual:
            self.capture_mgr.on_dual_lost()
            for other in self.players:
                other.dual_offset = 0
                other.is_left_half = False
                other.is_right_half = False
            return
        self._player_alive = False
        self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        if self.scoring.lives <= 0:
            if self.capture_mgr.state.mode == CaptureMode.CAPTURED:
                self.capture_mgr.state.mode = CaptureMode.AWAITING_RESCUE
                self.capture_mgr.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
            else:
                self._game_over()

    def _perform_capture(self, beam: TractorBeam, captured_player: Player) -> None:
        boss = beam.boss
        self.explosions.add(Explosion(pygame.Vector2(captured_player.pos)))
        was_dual = self.capture_mgr.state.mode == CaptureMode.DUAL
        captured_player.kill()
        if was_dual:
            self.capture_mgr.on_dual_lost()
            for other in self.players:
                other.dual_offset = 0
                other.is_left_half = False
                other.is_right_half = False
        else:
            self._player_alive = False
            self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        self.scoring.lose_life()

        from engine import assets as _assets

        base = _assets.sprite("player").copy()
        dark = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 120))
        base.blit(dark, (0, 0))

        boss.attach_captured_ship(base)
        beam.kill()
        audio.play_sfx("sfx_player_hit")
        self.capture_mgr.on_captured(id(boss), lives_after=self.scoring.lives)

    def _perform_rescue(self, boss: BossEnemy) -> None:
        self.scoring.add_kill("rescue")
        self.explosions.add(Explosion(pygame.Vector2(boss.rect.center)))
        audio.play_sfx("sfx_explode")
        target = next(iter(self.players), None)
        if target is not None and boss.captured_ship is not None:
            self.rescuing_ships.add(
                RescuingShip(
                    pygame.Vector2(boss.rect.center),
                    target,
                    self._complete_rescue,
                )
            )
        boss.captured_ship = None
        self.capture_mgr.on_rescue_eligible_kill()

    def _complete_rescue(self, _ship: RescuingShip) -> None:
        existing = next(iter(self.players), None)
        if existing is None:
            return
        existing.dual_offset = -settings.DUAL_FIGHTER_OFFSET
        existing.is_left_half = True
        existing.is_right_half = False
        right = Player(dual_offset=settings.DUAL_FIGHTER_OFFSET, is_right_half=True)
        right.pos.x = existing.pos.x + 2 * settings.DUAL_FIGHTER_OFFSET
        right.pos.x = max(
            right.rect.width / 2,
            min(settings.PLAYFIELD_WIDTH - right.rect.width / 2, right.pos.x),
        )
        right.rect.center = (int(right.pos.x), int(right.pos.y))
        self.players.add(right)
        self.capture_mgr.on_rescue_complete()
        audio.play_sfx("sfx_extra_life")

    def _game_over(self) -> None:
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
        # Captured ships above their captors
        for e in self.enemies:
            if e.captured_ship is not None:
                cs = e.captured_ship
                self.playfield.blit(
                    cs,
                    cs.get_rect(center=(e.rect.centerx, e.rect.top - cs.get_height() // 2 - 2)),
                )
        self.enemy_bullets.draw(self.playfield)
        self.explosions.draw(self.playfield)
        self.rescuing_ships.draw(self.playfield)
        for beam in self.tractor_beams:
            beam.draw(self.playfield)
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
