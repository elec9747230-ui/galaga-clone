"""Main gameplay scene.

This is the central node of the scene flow (title -> play -> bonus/gameover)
and the only scene that drives a full simulation tick. It owns the player
ship(s), the enemy formation, all projectile and explosion sprite groups, the
capture/rescue state machine, the tractor-beam visual, the wave controller
that decides what comes next, and the scoring object that survives across
scene swaps.

Each tick the scene:
  1. Toggles or honors the pause flag.
  2. Updates the player(s) — including the dual-fighter halves earned from a
     successful rescue — or the respawn timer when no player is alive.
  3. Updates every entity sprite group.
  4. Rolls dive/tractor decisions for in-formation enemies.
  5. Resolves collisions: player bullets vs enemies, enemy bullets vs each
     player half, and diving-enemy bodies vs each player half.
  6. Drives the capture/rescue UX flow (beam contact, capture animation,
     rescue arrival, dual-ship reattachment).
  7. Advances the wave when the formation is empty and hands off to the
     appropriate next scene (next play wave, bonus stage, or game over).

Update and draw are kept strictly separate: ``update`` mutates state, ``draw``
only reads it, so paused frames render correctly without re-running the sim.
"""

import math
import random

import pygame

import settings
from engine import audio
from engine.input import InputState
from engine.scene import Scene
from entities.captured_animation import CapturedAnimation
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
    """Active gameplay scene: formation, dives, collisions, captures, lives, waves.

    Attributes:
        difficulty: Difficulty selected on the title screen; preserved across
            wave transitions so successive ``PlayScene`` instances stay in sync.
        _diff_cfg: Resolved per-difficulty config (lives, dive freq, tractor
            probability multiplier, enemy bullet speed).
        scoring: Persistent scoring object carried across scenes within a run.
        player: The "primary" player ship reference. In dual mode this is the
            left half; updated when a player ship dies and a new one spawns.
        players: Sprite group holding 1 (solo) or 2 (dual) player halves. We
            use Group rather than GroupSingle so dual mode can hold two ships.
        player_bullets: Active player projectiles (collide with enemies).
        enemies: Active formation/diving enemies (collide with player bullets,
            and their bodies hit the player while diving).
        enemy_bullets: Projectiles fired by diving enemies (hit the player).
        explosions: Visual-only explosion sprites, no collisions.
        tractor_beams: Active boss tractor-beam visuals; collide-test against
            the player to detect capture.
        rescuing_ships: Animated ships flying down to merge with the player
            after a captured ship is freed (rescue UX flow).
        captured_animations: Animated ship sprites being pulled up the beam
            to attach to a boss after a successful capture.
        capture_mgr: State machine that tracks beam start/end, capture, the
            awaiting-rescue grace window, and dual mode.
        playfield: Off-screen surface for the inner playfield; composed onto
            the window with an offset so HUD columns can occupy the sides.
        _stars: Deterministic starfield speckle positions.
        _formation_phase: Single-element list shared by reference with every
            enemy so they all sway in sync without per-enemy state writes.
        _time: Elapsed scene time, drives formation phase.
        _dive_seed_counter: Monotonic counter providing a fresh "seed" for
            each dive so two enemies never trace identical paths.
        _dive_probability_per_sec: Computed Poisson-style rate for triggering
            a dive each frame; scales with wave and difficulty.
        _respawn_timer: Seconds remaining before the next player respawn.
        _player_alive: Whether at least one player ship currently exists.
        _paused: Player-pause flag (toggled by the pause input).
        _highscore: High score loaded once for HUD display.
        wave_controller: Decides current wave type (NORMAL, BOSS, BONUS) and
            advances the wave counter when the formation is cleared.
    """

    def __init__(
        self,
        scoring: Scoring | None = None,
        difficulty: Difficulty = Difficulty.NORMAL,
        dual: bool = False,
    ) -> None:
        """Construct sprite groups, formation, and wave/capture state.

        Args:
            scoring: Carried-over scoring; if None, a fresh ``Scoring`` is
                created with the per-difficulty starting-lives count.
            difficulty: Selected difficulty for this run.
            dual: True if the previous wave ended in dual-fighter mode (a
                rescued ship is still attached). Spawns a second player half
                and seeds the capture state machine accordingly.
        """
        self.difficulty = difficulty
        self._diff_cfg = config_for(difficulty)
        if scoring is None:
            scoring = Scoring(lives=self._diff_cfg.starting_lives)
        self.scoring = scoring
        # Player(s) — Group (not GroupSingle) so we can hold 2 in dual mode.
        # Only Group supports multi-membership and per-half collision testing.
        self.player = Player()
        self.players: pygame.sprite.Group = pygame.sprite.Group(self.player)
        if dual:
            # Carry-over dual mode from a previous wave: shift the existing
            # ship to the left half and spawn a second ship for the right
            # half so the player keeps the rescued formation across waves.
            self.player.dual_offset = -settings.DUAL_FIGHTER_OFFSET
            self.player.is_left_half = True
            self.player.is_right_half = False
            self.player.pos.x += self.player.dual_offset
            self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))
            second = Player(dual_offset=settings.DUAL_FIGHTER_OFFSET, is_right_half=True)
            self.players.add(second)
        # Collision groups:
        #   player_bullets <-> enemies        (bullets kill enemies)
        #   enemy_bullets  <-> each player    (bullets kill player halves)
        #   enemies(diving) <-> each player   (body collision kills both)
        #   tractor_beams  <-> player (left half) (capture trigger)
        self.player_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.enemy_bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.explosions: pygame.sprite.Group = pygame.sprite.Group()
        self.tractor_beams: pygame.sprite.Group = pygame.sprite.Group()
        self.rescuing_ships: pygame.sprite.Group = pygame.sprite.Group()
        self.captured_animations: pygame.sprite.Group = pygame.sprite.Group()
        self.capture_mgr = CaptureManager()
        if dual:
            # Inform the capture FSM that we are already in dual so the next
            # capture event correctly transitions through "DUAL -> lost half".
            self.capture_mgr.state.mode = CaptureMode.DUAL
        self.playfield = pygame.Surface((settings.PLAYFIELD_WIDTH, settings.PLAYFIELD_HEIGHT))
        # Deterministic starfield (fixed seed) so the backdrop is reproducible.
        rng = random.Random(7)
        self._stars = [
            (
                rng.randint(0, settings.PLAYFIELD_WIDTH - 1),
                rng.randint(0, settings.PLAYFIELD_HEIGHT - 1),
            )
            for _ in range(60)
        ]
        # Single-element list passed by reference to every enemy: writing
        # _formation_phase[0] each frame propagates without iterating enemies.
        self._formation_phase = [0.0]
        self._time = 0.0
        # Distinct seed per dive so RNG-driven dive paths don't repeat.
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
        """Play the stage-start jingle, then queue the looping gameplay BGM."""
        from game.wave import WaveType

        # Music switching: a one-shot jingle plays first, then the looping
        # gameplay BGM is scheduled to start once the jingle has had time to
        # finish — avoids overlapping audio while still feeling continuous.
        audio.play_music("music_stage_start", loop=False)
        is_boss = self.wave_controller.current_type() == WaveType.BOSS
        bgm = "music_boss_stage" if is_boss else "music_gameplay"
        audio.play_music_after(bgm, delay=1.8, loop=True)

    def _apply_wave_difficulty(self) -> None:
        """Recompute the per-second dive probability from the current wave/difficulty."""
        p = self.wave_controller.current_params()
        # Empirical base rate: 0.5 + 30 * waveDiveProb gives a good ramp from
        # the early-wave drip to mid-game pressure; difficulty multiplier then
        # scales the whole curve uniformly.
        base_rate = 0.5 + 30.0 * p.dive_probability
        self._dive_probability_per_sec = base_rate * self._diff_cfg.dive_freq_multiplier

    def _spawn_formation(self) -> None:
        """Populate the formation grid with the right enemy mix for the wave type."""
        from game.wave import WaveType

        wave_type = self.wave_controller.current_type()
        is_boss = wave_type == WaveType.BOSS
        for row in range(settings.FORMATION_ROWS):
            for col in range(settings.FORMATION_COLS):
                # Stagger entry by row+col so the formation streams in like a
                # diagonal sweep rather than appearing simultaneously.
                delay = (row * 0.25) + (col * 0.05)
                if is_boss:
                    # Boss waves: front two rows are bosses (worth more, can
                    # tractor) and the rest are butterflies (no bees).
                    cls = BossEnemy if row < 2 else ButterflyEnemy
                else:
                    # Normal waves: standard galaga pyramid (bosses up top,
                    # butterflies in the middle, bees on the bottom rows).
                    if row == 0:
                        cls = BossEnemy
                    elif row == 1:
                        cls = ButterflyEnemy
                    else:
                        cls = BeeEnemy
                self.enemies.add(cls(row, col, self._formation_phase, entry_delay=delay))

    def update(self, dt: float, inp: InputState) -> None:
        """Run one full simulation tick: input, motion, captures, collisions, waves.

        Args:
            dt: Frame delta time in seconds.
            inp: Current input snapshot (movement, fire, pause).
        """
        # Pause toggle: edge-triggered by the input layer. When paused, every
        # subsystem below is skipped; only draw() runs, so the scene freezes.
        if inp.pause_pressed:
            self._paused = not self._paused
        if self._paused:
            return
        # Audio tick drives delayed-music scheduling started in on_enter().
        audio.tick(dt)
        self._time += dt
        # Shared formation phase: all enemies sway from one source of truth.
        self._formation_phase[0] = self._time * (2 * math.pi / 4.0)

        # ---- Player update / respawn (per-ship to support dual mode) ----
        alive_players = list(self.players)
        if alive_players:
            self._player_alive = True
            # Keep self.player pointing at *some* live ship (left if present)
            # so other systems referencing `self.player.pos` keep working.
            self.player = alive_players[0]
            for p in alive_players:
                p.update(dt, inp, self.player_bullets, on_shot=self.scoring.add_shot)
        else:
            # No live ship — count down the respawn timer.
            self._player_alive = False
            self._respawn_timer -= dt
            can_respawn = (
                self._respawn_timer <= 0
                and self.scoring.lives > 0
                # AWAITING_RESCUE means lives ran out *during* a capture: we
                # hold a chance for rescue rather than respawning a new ship.
                and self.capture_mgr.state.mode != CaptureMode.AWAITING_RESCUE
            )
            # During an active capture, also wait for the captor boss to finish
            # carrying the ship back to its formation slot — respawning sooner
            # would have a fresh ship visible while the captured one is still
            # mid-animation, which looks broken.
            if can_respawn and self.capture_mgr.state.mode == CaptureMode.CAPTURED:
                can_respawn = any(
                    e.captured_ship is not None and e.state == EnemyState.IN_FORMATION
                    for e in self.enemies
                )
            if can_respawn:
                self.player = Player()
                self.players.add(self.player)
                self._player_alive = True

        # ---- Per-group entity updates ----
        # Manual loops (not Group.update) so we can pass dt explicitly and
        # avoid the *args contract, keeping each entity's signature precise.
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
        for a in self.captured_animations:
            a.update(dt)

        # ---- Wave/dive state: roll for a dive (or tractor beam on bosses) ----
        in_formation = [e for e in self.enemies if e.is_in_formation()]
        # Poisson-style trigger: each frame is an independent Bernoulli with
        # rate scaled by dt, so the long-run dive frequency tracks
        # _dive_probability_per_sec regardless of frame rate.
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
                # Boss begins the tractor sequence: align over the player,
                # then drop a beam. The capture FSM tracks the attempt so a
                # second simultaneous attempt cannot start.
                attacker.enter_tractor_align(pygame.Vector2(self.player.pos))
                self.capture_mgr.begin_beam(id(attacker))
            else:
                # Normal dive — non-boss or boss when tractor is unavailable.
                attacker.start_dive(self.player.pos, self._dive_seed_counter)
                audio.play_sfx("sfx_dive")

        # Spawn the TractorBeam visual exactly when a boss transitions into
        # TRACTOR_BEAMING. Guard against duplicates by checking existing beams.
        for e in self.enemies:
            if e.state == EnemyState.TRACTOR_BEAMING and not any(
                b.boss is e for b in self.tractor_beams
            ):
                self.tractor_beams.add(TractorBeam(e))
                audio.play_sfx("sfx_dive")

        # Diving enemies may fire — only "diving" because formation enemies
        # never shoot in this clone. Speed multiplier scales with difficulty.
        for e in list(self.enemies):
            if hasattr(e, "maybe_fire"):
                bullet = e.maybe_fire(
                    self.player.pos,
                    speed_multiplier=self._diff_cfg.enemy_bullet_speed_multiplier,
                )
                if bullet:
                    self.enemy_bullets.add(bullet)

        # ---- Capture flow: beam-vs-player collision and capture grace ----
        # Only the LEFT half of the player can be captured (mirrors the
        # original arcade rule), so we explicitly skip is_right_half ships.
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
            # Capture FSM accumulates time-in-beam; returns True the frame the
            # capture grace expires while the player is still inside the cone.
            triggered = self.capture_mgr.update_beam(dt, any_in_beam)
            if triggered and captured_player is not None and captured_beam is not None:
                self._perform_capture(captured_beam, captured_player)

        # Naturally-expired beams. If a capture is in flight (CAPTURED or
        # AWAITING_RESCUE), keep the beam visible until the pull-up animation
        # arrives at the boss — _on_capture_animation_arrived kills it then.
        # Otherwise the beam ended without a capture: send the boss back into
        # a normal dive so it doesn't hover indefinitely.
        capture_in_flight = self.capture_mgr.state.mode in (
            CaptureMode.CAPTURED,
            CaptureMode.AWAITING_RESCUE,
        )
        for beam in list(self.tractor_beams):
            if beam.expired and not capture_in_flight:
                if beam.boss in self.enemies and beam.boss.state == EnemyState.TRACTOR_BEAMING:
                    self._dive_seed_counter += 1
                    beam.boss.start_dive(self.player.pos, self._dive_seed_counter)
                self.capture_mgr.on_beam_ended()
                beam.kill()

        # Awaiting-rescue timeout: if the player ran out of lives mid-capture
        # and the rescue grace expired without a kill, the run is over.
        if self.capture_mgr.update_awaiting_rescue(dt):
            self._game_over()
            return

        self._handle_collisions()

        # ---- Wave advance: formation cleared -> hand off to next scene ----
        if not self.enemies:
            self.wave_controller.advance()
            self.scoring.wave = self.wave_controller.current_wave
            self._apply_wave_difficulty()
            next_type = self.wave_controller.current_type()
            from game.wave import WaveType
            from scenes.transitions import TransitionScene

            if next_type == WaveType.BONUS:
                # Bonus stage path: longer banner, dedicated scene class.
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
                # Normal/boss path: re-create *this* class via type(self) so
                # any subclass keeps its identity across wave boundaries.
                text = (
                    f"STAGE {self.scoring.wave}" if next_type == WaveType.NORMAL else "BOSS STAGE"
                )
                # Carry dual-fighter state into the next wave so a player who
                # rescued a ship retains both halves at the start of the next.
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
        """Resolve bullet, beam, and body collisions and route them to scoring/effects."""
        # ---- Player bullets vs enemies (groupcollide consumes both) ----
        # We branch on boss + capture state so a captor boss carrying a ship
        # routes to the rescue flow instead of a plain kill.
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, True, True)
        for _bullet, enemies_hit in hits.items():
            for e in enemies_hit:
                handled = False
                if isinstance(e, BossEnemy) and e.captured_ship is not None:
                    # Boss carrying captured ship killed -> rescue path runs
                    # explosion + rescuer spawn itself, so skip generic FX.
                    self._perform_rescue(e)
                    handled = True
                elif isinstance(e, BossEnemy) and e.state in (
                    EnemyState.TRACTOR_ALIGNING,
                    EnemyState.TRACTOR_BEAMING,
                ):
                    # Killing a boss while it is mid-tractor-attempt awards
                    # a special "tractor" score and cancels the beam cleanly.
                    self.scoring.add_kill("tractor")
                    for beam in list(self.tractor_beams):
                        if beam.boss is e:
                            beam.kill()
                    self.capture_mgr.on_beam_ended()
                else:
                    # Diving enemies are worth more than the same enemy when
                    # sitting in formation — pick the kind accordingly.
                    kind = "dive" if e.state == EnemyState.DIVING else e.score_kind
                    self.scoring.add_kill(kind)
                if not handled:
                    self.explosions.add(Explosion(pygame.Vector2(e.rect.center)))
                    audio.play_sfx("sfx_explode")

        if not self._player_alive:
            # No live ship to take damage — skip enemy-side collision checks.
            return

        # ---- Enemy bullets vs each player half independently ----
        # Per-half check is required so a hit on the right half doesn't kill
        # the left half (and vice versa) in dual-fighter mode.
        for p in list(self.players):
            if pygame.sprite.spritecollide(p, self.enemy_bullets, True):
                self._kill_player_half(p)

        # ---- Diving enemy bodies vs each player half ----
        # Both ship and enemy die: the enemy explodes immediately, the half
        # is routed through the death path which handles lives/respawn.
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
        """Destroy one player ship, decrement lives, and route to respawn or game-over.

        Args:
            p: The player half (single or one of the two dual halves) to kill.
        """
        self.explosions.add(Explosion(pygame.Vector2(p.pos)))
        audio.play_sfx("sfx_player_hit")
        # Snapshot before kill: was_dual decides whether the surviving half
        # collapses back to solo mode or whether we trigger the respawn timer.
        was_dual = len(self.players) >= 2
        p.kill()
        self.scoring.lose_life()
        if was_dual:
            # Dual -> solo collapse: the surviving half is recentered (offsets
            # cleared) and the capture FSM is told dual mode ended.
            self.capture_mgr.on_dual_lost()
            for other in self.players:
                other.dual_offset = 0
                other.is_left_half = False
                other.is_right_half = False
            return
        # Solo death: arm the respawn timer; respawn is gated in update().
        self._player_alive = False
        self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        if self.scoring.lives <= 0:
            # Out of lives. Special case: if a ship is currently captured, the
            # player still has one chance to rescue it for free — switch to
            # AWAITING_RESCUE and start the grace timer instead of ending.
            if self.capture_mgr.state.mode == CaptureMode.CAPTURED:
                self.capture_mgr.state.mode = CaptureMode.AWAITING_RESCUE
                self.capture_mgr.state.rescue_timer = settings.TRACTOR_RESCUE_TIMER
            else:
                self._game_over()

    def _perform_capture(self, beam: TractorBeam, captured_player: Player) -> None:
        """Begin the capture UX: silently remove the player and start the pull-up animation.

        Args:
            beam: The tractor beam currently containing the player.
            captured_player: The player ship being captured (always the left half).
        """
        boss = beam.boss
        captured_pos = pygame.Vector2(captured_player.pos)
        was_dual = self.capture_mgr.state.mode == CaptureMode.DUAL
        # Remove the player ship visually but DO NOT spawn an explosion: the
        # ship is being captured, not destroyed — destruction visuals would
        # be misleading and the lose_life() below covers the lives accounting.
        captured_player.kill()
        if was_dual:
            # Dual -> solo collapse on capture: the right half remains and is
            # recentered. Capture FSM is informed so it can transition states.
            self.capture_mgr.on_dual_lost()
            for other in self.players:
                other.dual_offset = 0
                other.is_left_half = False
                other.is_right_half = False
        else:
            self._player_alive = False
            # Respawn is gated on the captor boss returning to formation
            # (see update() respawn block); the timer is just a minimum delay.
            self._respawn_timer = settings.PLAYER_RESPAWN_DELAY
        self.scoring.lose_life()

        # Spawn the pull-up animation; on arrival the callback attaches the
        # ship sprite to the boss so it visibly carries it back to formation.
        self.captured_animations.add(
            CapturedAnimation(captured_pos, boss, self._on_capture_animation_arrived)
        )
        audio.play_sfx("sfx_tractor_capture")
        self.capture_mgr.on_captured(id(boss), lives_after=self.scoring.lives)
        # The beam stays visible during the animation so the player sees the
        # pull-up; it is killed in _on_capture_animation_arrived once done.

    def _on_capture_animation_arrived(
        self, _anim: CapturedAnimation, ship_surface: pygame.Surface
    ) -> None:
        """Attach the captured ship sprite to its captor boss and dismiss the beam.

        Args:
            _anim: The CapturedAnimation that just finished its travel.
            ship_surface: The pre-rendered captured-ship surface to attach.
        """
        boss = _anim.boss
        if boss in self.enemies:
            boss.attach_captured_ship(ship_surface)
        # Beam was kept alive specifically until this moment — drop it now.
        for beam in list(self.tractor_beams):
            if beam.boss is boss:
                beam.kill()

    def _perform_rescue(self, boss: BossEnemy) -> None:
        """Trigger the rescue UX: explode the captor and send the freed ship to the player.

        Args:
            boss: The captor boss that was just killed while carrying a ship.
        """
        # "rescue" kill kind awards bonus score in addition to the normal boss kill.
        self.scoring.add_kill("rescue")
        self.explosions.add(Explosion(pygame.Vector2(boss.rect.center)))
        audio.play_sfx("sfx_explode")
        target = next(iter(self.players), None)
        if target is not None and boss.captured_ship is not None:
            # RescuingShip animates from the boss position down to the live
            # player ship; on arrival it invokes _complete_rescue which
            # promotes the player to dual-fighter mode.
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
        """Convert the surviving solo player into a dual-fighter pair.

        Args:
            _ship: The RescuingShip that has finished its arrival animation.
        """
        existing = next(iter(self.players), None)
        if existing is None:
            # Edge case: player died after the rescuer launched but before it
            # arrived. Nothing to merge into; bail silently.
            return
        # Promote existing ship to the left half and spawn a fresh right half
        # at twice the offset (so the gap matches the configured dual spacing),
        # clamped inside the playfield bounds.
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
        # Reuse the extra-life jingle as a celebratory cue for the rescue.
        audio.play_sfx("sfx_extra_life")

    def _game_over(self) -> None:
        """Replace this scene with the GameOverScene, finalizing the run."""
        # Local import keeps scenes/play.py free of a static dep on gameover.
        from scenes.gameover import GameOverScene

        # Scene-stack swap: play -> gameover (no nesting, no return path).
        assert self.manager
        self.manager.replace(GameOverScene(self.scoring))

    def draw(self, surface: pygame.Surface) -> None:
        """Render the playfield (starfield, sprites, captures, beams), pause, HUD.

        Args:
            surface: The window surface; the playfield is composited at the
                configured offset to leave room for the HUD on the sides.
        """
        # Pure render — no game-state mutation. Layer order is significant.
        surface.fill(settings.COLOR_BLACK)
        self.playfield.fill(settings.COLOR_BLACK)
        for sx, sy in self._stars:
            self.playfield.set_at((sx, sy), settings.COLOR_STAR)
        self.players.draw(self.playfield)
        self.player_bullets.draw(self.playfield)
        self.enemies.draw(self.playfield)
        # Captured ships ride visibly above their captor bosses — drawn in a
        # dedicated pass because they are not their own sprites, just an
        # attached surface stored on the boss.
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
        # Beams are drawn UNDER the captured-animation sprite so the ship is
        # clearly visible "riding" the beam during the pull-up.
        for beam in self.tractor_beams:
            beam.draw(self.playfield)
        self.captured_animations.draw(self.playfield)
        if self._paused:
            # Pause overlay: dim the playfield (alpha 160) and stamp "PAUSED".
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
        # HUD columns sit on the window surface (not the playfield) so they
        # are not affected by the pause overlay or playfield offset.
        hud.draw_left(surface, self.scoring, self._highscore)
        hud.draw_right(surface, self.scoring, self._highscore)
