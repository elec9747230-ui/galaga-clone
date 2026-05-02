# Galaga Clone

Single-player Galaga clone built in Python + Pygame. Personal/learning project.

See [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](docs/superpowers/specs/2026-05-02-galaga-clone-design.md) for the design spec.

## Features

- Authentic 5x8 enemy formation with curved entry paths
- Dive attacks with sine-wave wobble
- Wave cycle: 4 normal -> 1 boss -> 1 bonus, repeating, with rising difficulty
- Bonus (challenging) stages with perfect bonus (+10000 + extra life)
- Programmatically generated pixel sprites + chiptune music + SFX (no external assets)
- Persistent high score
- Side-panel HUD (score, lives, wave, accuracy, kills, controls)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
python main.py
```

Assets (sprites + audio) are auto-generated on first run. To regenerate manually:

```powershell
python -m tools.generate_sprites
python -m tools.generate_audio
```

## Controls

- Arrow keys / A,D -- move
- Space -- fire (max 2 bullets on screen)
- P -- pause
- Esc -- quit

## Develop

```powershell
pytest         # tests
ruff check .   # lint
ruff format .  # format
```

## License

Personal project. Original Galaga is (c) Bandai Namco; this is a non-distributed clone for educational purposes only.
