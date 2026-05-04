"""Game-wide configuration constants.

Centralizes every tunable value the game references at runtime: window
geometry, playfield layout, palette, player/enemy kinematics, scoring
table, wave pacing, tractor-beam mechanics, and asset/key bindings.
Players and modders are expected to open this file to retune difficulty
or rebind keys.

Intentionally has no ``pygame`` import so it can be loaded from any
module (including unit tests and tools) without pulling in SDL. Key
bindings are stored as the *names* of pygame key constants and resolved
at the call site via ``getattr(pygame, name)``.
"""

# === Display ===
WINDOW_WIDTH = 1280               # Total window width in pixels (16:9 at 720p height).
WINDOW_HEIGHT = 720               # Total window height in pixels.
FPS = 60                          # Target frame rate; all per-second speeds assume this cadence.

# === Playfield (centered horizontally inside the window) ===
# The arcade-style playfield is a tall vertical strip; the leftover width on
# either side is used for HUD / score panels.
PLAYFIELD_WIDTH = 540             # Active gameplay column width in pixels.
PLAYFIELD_HEIGHT = 720            # Active gameplay column height (full window height).
PLAYFIELD_OFFSET_X = (WINDOW_WIDTH - PLAYFIELD_WIDTH) // 2  # 370 px -- left edge of the playfield.
PLAYFIELD_OFFSET_Y = 0            # Playfield starts flush with the top of the window.

# === Side panels ===
SIDE_PANEL_WIDTH = PLAYFIELD_OFFSET_X  # 370 px -- mirrored on both sides for HUD content.

# === Colors (RGB 0-255) ===
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 40, 40)         # Player ship / danger highlights (slightly desaturated to avoid eye strain).
COLOR_YELLOW = (240, 220, 60)     # Bullets and warning text.
COLOR_BLUE = (60, 120, 240)       # Boss-tier enemies.
COLOR_CYAN = (80, 220, 220)       # Mid-tier enemies.
COLOR_GREEN = (80, 220, 80)       # Bonus/positive feedback.
COLOR_HUD_DIM = (120, 120, 140)   # Inactive/secondary HUD text -- low-contrast on purpose.
COLOR_STAR = (180, 180, 200)      # Parallax starfield -- soft white-blue, never pure white.

# === Player ===
PLAYER_SPEED = 280                # Horizontal travel speed in pixels/second; tuned for ~2 s edge-to-edge.
PLAYER_BULLET_SPEED = 600         # Bullet travel speed in pixels/second.
MAX_PLAYER_BULLETS = 2            # Classic Galaga limit: at most 2 bullets on screen at once.
PLAYER_RESPAWN_DELAY = 0.5        # Seconds of blank time after death before the new ship appears.
PLAYER_START_LIVES = 3            # Lives granted at the beginning of a new game.

# === Enemy ===
ENEMY_BASE_SPEED = 80             # Base formation drift speed in pixels/second; dive speeds scale from this.
ENEMY_BULLET_SPEED = 220          # Enemy projectile speed -- noticeably slower than player bullets so dodging is feasible.
FORMATION_ROWS = 5                # Grid rows in the standard attack formation.
FORMATION_COLS = 8                # Grid columns; 5x8 = 40 enemies per wave (canonical Galaga count).
FORMATION_SLOT_WIDTH = 50         # Horizontal spacing between formation slots in pixels.
FORMATION_SLOT_HEIGHT = 45        # Vertical spacing between formation slots in pixels.
FORMATION_TOP_MARGIN = 80         # Pixels of empty space above the top formation row (HUD breathing room).

# === Scoring ===
SCORE_NORMAL_KILL = 50            # Points for killing an enemy in formation.
SCORE_DIVE_KILL = 100             # Points for killing an enemy mid-dive (double, since they're harder to hit).
SCORE_BOSS_KILL = 150             # Points for killing a boss (top-row) enemy in formation.
SCORE_BONUS_PER_KILL = 200        # Per-kill score during the bonus stage.
SCORE_BONUS_PERFECT = 10000       # One-shot bonus for clearing every enemy in a bonus stage.
LIFE_BONUS_PERFECT = 1            # Extra life awarded on a perfect bonus stage.
SCORE_TRACTOR_KILL = 400          # Points for killing the boss while it is firing the tractor beam (riskier shot).
SCORE_RESCUE_KILL = 800           # Points for shooting the boss that is carrying your captured fighter (rescue payoff).

# === Wave cycle (1-4 normal, 5 boss, 6 bonus) ===
WAVE_CYCLE_LENGTH = 6             # Repeating pattern length; pacing relies on bonus stage every 6th wave.

# === Bonus stage ===
BONUS_STAGE_DURATION = 30.0       # Seconds before the bonus stage auto-ends if not cleared.

# === Tractor beam (boss capture mechanic) ===
TRACTOR_BEAM_PROBABILITY = 0.30          # Per-dive chance the boss attempts a beam attack; 30% keeps it rare but recurring.
TRACTOR_BEAM_LIFETIME = 3.0              # Seconds the beam stays visible before retracting.
TRACTOR_BEAM_TOP_WIDTH = 24              # Beam width in pixels at its narrow end (next to the boss).
TRACTOR_BEAM_BOTTOM_WIDTH = 60           # Beam width in pixels at the wide end (where the player gets caught).
TRACTOR_BEAM_CAPTURE_GRACE = 0.3         # Seconds at the start of the beam during which the player is immune (telegraph window).
TRACTOR_BEAM_STRIPE_HEIGHT = 14          # Pixel height of each animated stripe inside the beam.
TRACTOR_BEAM_STRIPE_SPEED = 240.0        # Stripe scroll speed in pixels/second -- creates the "pulling" illusion.
TRACTOR_BOSS_ALIGN_SPEED = 200.0         # Speed (px/s) at which the boss slides to its firing position.
TRACTOR_BOSS_ALIGN_TARGET_Y = 420        # Y-coordinate the boss descends to before firing the beam.
TRACTOR_RETURN_SPEED = 220.0             # Speed (px/s) the boss climbs back to formation after a beam attack.
TRACTOR_RESCUE_DESCENT_SPEED = 220.0     # Speed (px/s) the captured-ship boss dives at during a rescue attempt.
TRACTOR_RESCUE_TIMER = 5.0               # Seconds to react/shoot the boss before the captured ship is lost.
DUAL_FIGHTER_OFFSET = 22                 # Horizontal pixel gap between the two ships when flying as a dual fighter.

# === Files ===
HIGHSCORE_PATH = "data/highscore.json"   # Persistent high-score table (created on first save).
ASSETS_SPRITES_DIR = "assets/sprites"    # Auto-populated on first run if missing.
ASSETS_AUDIO_DIR = "assets/audio"        # Auto-populated on first run if missing.

# === Key bindings ===
# Stored as tuples of pygame key-constant *names* (without the ``K_`` prefix
# for letter keys). The input layer resolves them at use-site so this module
# can stay pygame-free. Multiple entries per action act as alternates.
KEY_LEFT = ("LEFT", "a")          # Move left: arrow key or A.
KEY_RIGHT = ("RIGHT", "d")        # Move right: arrow key or D.
KEY_FIRE = ("SPACE",)             # Fire bullet.
KEY_PAUSE = ("p",)                # Toggle pause.
KEY_QUIT = ("ESCAPE",)            # Quit the game from anywhere.
