# Galaga Clone

Single-player Galaga clone built in Python + Pygame. Personal/learning project.

See [docs/superpowers/specs/2026-05-02-galaga-clone-design.md](docs/superpowers/specs/2026-05-02-galaga-clone-design.md) for the design spec.

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

- Arrow keys / A,D — move
- Space — fire
- P — pause
- Esc — quit

## Develop

```powershell
pytest         # tests
ruff check .   # lint
ruff format .  # format
```
