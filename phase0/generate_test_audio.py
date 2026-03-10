"""Generate test audio fixtures for Phase 0."""

import numpy as np
import struct
import wave
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def generate_sine_wav(
    filepath: Path,
    freq: float = 440.0,
    duration: float = 5.0,
    sample_rate: int = 44100,
    amplitude: float = 0.8,
) -> None:
    """Generate a mono WAV file with a sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    samples = (amplitude * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)

    with wave.open(str(filepath), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(samples.tobytes())


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 440 Hz sine wave, 5 seconds
    generate_sine_wav(FIXTURES_DIR / "sine_440hz.wav", freq=440.0, duration=5.0)
    print(f"Generated: {FIXTURES_DIR / 'sine_440hz.wav'}")

    # 1000 Hz sine wave, 3 seconds (different timbre)
    generate_sine_wav(FIXTURES_DIR / "sine_1000hz.wav", freq=1000.0, duration=3.0)
    print(f"Generated: {FIXTURES_DIR / 'sine_1000hz.wav'}")


if __name__ == "__main__":
    main()
