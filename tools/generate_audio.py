"""Generate WAV files: SFX + chiptune recreations of original Galaga melodies.

Personal/learning use only — original Galaga BGM melodies are Bandai Namco IP.
"""

import wave
from pathlib import Path

import numpy as np

import settings

OUT_DIR = Path(settings.ASSETS_AUDIO_DIR)
SAMPLE_RATE = 22050  # 22kHz, plenty for 8-bit style


# ---------- WAV writing ----------


def _write_wav(name: str, samples: np.ndarray) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    with wave.open(str(OUT_DIR / f"{name}.wav"), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm.tobytes())


# ---------- Waveform helpers ----------


def _square(freq: float, duration: float, duty: float = 0.5, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return np.where(phase < duty, volume, -volume)


def _triangle(freq: float, duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return (4 * np.abs(phase - 0.5) - 1) * volume


def _noise(duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    return (np.random.uniform(-1, 1, n) * volume).astype(np.float32)


def _sweep(f_start: float, f_end: float, duration: float, volume: float = 0.5) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    freqs = np.linspace(f_start, f_end, n)
    phases = np.cumsum(2 * np.pi * freqs / SAMPLE_RATE)
    return np.sign(np.sin(phases)) * volume


def _envelope(samples: np.ndarray, attack: float = 0.01, release: float = 0.05) -> np.ndarray:
    n = len(samples)
    a = int(SAMPLE_RATE * attack)
    r = int(SAMPLE_RATE * release)
    env = np.ones(n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return samples * env


def _silence(duration: float) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * duration))


# ---------- Note → frequency ----------


# Equal temperament; A4 = 440Hz
def _freq(note: str) -> float:
    """e.g. 'A4', 'C#5', 'Bb3'."""
    name = note[:-1]
    octave = int(note[-1])
    semitones = {
        "C": -9,
        "C#": -8,
        "Db": -8,
        "D": -7,
        "D#": -6,
        "Eb": -6,
        "E": -5,
        "F": -4,
        "F#": -3,
        "Gb": -3,
        "G": -2,
        "G#": -1,
        "Ab": -1,
        "A": 0,
        "A#": 1,
        "Bb": 1,
        "B": 2,
    }
    n = semitones[name] + (octave - 4) * 12
    return 440.0 * (2 ** (n / 12))


def _melody(notes: list[tuple[str, float]], volume: float = 0.4) -> np.ndarray:
    """notes: list of (note_or_'rest', duration_seconds)."""
    parts = []
    for note, dur in notes:
        if note == "rest":
            parts.append(_silence(dur))
        else:
            wave_data = _square(_freq(note), dur, duty=0.5, volume=volume)
            parts.append(_envelope(wave_data, attack=0.005, release=0.03))
    return np.concatenate(parts)


# ---------- SFX ----------


def sfx_shoot() -> None:
    s = _sweep(880, 220, 0.08, volume=0.4)
    _write_wav("sfx_shoot", _envelope(s, attack=0.001, release=0.04))


def sfx_explode() -> None:
    n = _noise(0.25, volume=0.6)
    fade = np.linspace(1.0, 0.0, len(n)) ** 2
    _write_wav("sfx_explode", n * fade)


def sfx_player_hit() -> None:
    s = _sweep(440, 80, 0.4, volume=0.5)
    _write_wav("sfx_player_hit", _envelope(s, attack=0.005, release=0.1))


def sfx_extra_life() -> None:
    parts = [
        _envelope(_square(_freq("C5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("E5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("G5"), 0.08, volume=0.4)),
        _envelope(_square(_freq("C6"), 0.18, volume=0.4)),
    ]
    _write_wav("sfx_extra_life", np.concatenate(parts))


def sfx_dive() -> None:
    s = _sweep(660, 220, 0.18, volume=0.35)
    _write_wav("sfx_dive", _envelope(s, attack=0.005, release=0.06))


# ---------- Music (chiptune recreations) ----------


def music_intro() -> None:
    """Galaga intro fanfare — short heroic phrase."""
    notes = [
        ("G4", 0.15),
        ("C5", 0.15),
        ("E5", 0.15),
        ("G5", 0.30),
        ("E5", 0.15),
        ("G5", 0.45),
        ("rest", 0.10),
        ("F5", 0.15),
        ("D5", 0.15),
        ("B4", 0.30),
        ("C5", 0.45),
    ]
    _write_wav("music_intro", _melody(notes))


def music_stage_start() -> None:
    """Short stage-start jingle."""
    notes = [
        ("E5", 0.12),
        ("G5", 0.12),
        ("C6", 0.24),
        ("rest", 0.06),
        ("E5", 0.12),
        ("G5", 0.12),
        ("C6", 0.36),
    ]
    _write_wav("music_stage_start", _melody(notes))


def music_challenging_stage() -> None:
    """Bonus stage music — playful bouncy loop (~4s)."""
    notes = [
        ("C5", 0.12),
        ("E5", 0.12),
        ("G5", 0.12),
        ("C6", 0.12),
        ("G5", 0.12),
        ("E5", 0.12),
        ("C5", 0.24),
        ("D5", 0.12),
        ("F5", 0.12),
        ("A5", 0.12),
        ("D6", 0.12),
        ("A5", 0.12),
        ("F5", 0.12),
        ("D5", 0.24),
        ("E5", 0.12),
        ("G5", 0.12),
        ("B5", 0.12),
        ("E6", 0.12),
        ("D6", 0.12),
        ("C6", 0.12),
        ("B5", 0.12),
        ("A5", 0.12),
        ("G5", 0.36),
    ]
    _write_wav("music_bonus", _melody(notes))


def music_game_over() -> None:
    notes = [
        ("C5", 0.20),
        ("B4", 0.20),
        ("A4", 0.20),
        ("G4", 0.20),
        ("F4", 0.20),
        ("E4", 0.20),
        ("D4", 0.20),
        ("C4", 0.60),
    ]
    _write_wav("music_game_over", _melody(notes))


def main() -> None:
    sfx_shoot()
    sfx_explode()
    sfx_player_hit()
    sfx_extra_life()
    sfx_dive()
    music_intro()
    music_stage_start()
    music_challenging_stage()
    music_game_over()
    print(f"Audio written to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
