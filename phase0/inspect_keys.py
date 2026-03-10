"""Inspect available feature keys from MusicExtractor."""
import essentia.standard as es

features, _ = es.MusicExtractor(
    lowlevelStats=["mean", "stdev"],
    rhythmStats=["mean", "stdev"],
    tonalStats=["mean", "stdev"],
)("fixtures/sine_440hz.wav")

# Print all keys containing 'mfcc'
print("=== MFCC keys ===")
for key in sorted(features.descriptorNames()):
    if "mfcc" in key.lower():
        print(f"  {key}: shape={features[key].shape if hasattr(features[key], 'shape') else 'scalar'}")

# Print all keys containing 'hpcp'
print("\n=== HPCP keys ===")
for key in sorted(features.descriptorNames()):
    if "hpcp" in key.lower():
        print(f"  {key}: shape={features[key].shape if hasattr(features[key], 'shape') else 'scalar'}")

# Print rhythm keys
print("\n=== Rhythm keys ===")
for key in sorted(features.descriptorNames()):
    if "rhythm" in key.lower():
        val = features[key]
        shape = val.shape if hasattr(val, 'shape') else type(val).__name__
        print(f"  {key}: {shape}")

# Print spectral keys
print("\n=== Spectral keys ===")
for key in sorted(features.descriptorNames()):
    if "spectral" in key.lower() and "mean" in key.lower():
        print(f"  {key}")
