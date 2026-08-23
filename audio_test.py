import sounddevice as sd
import numpy as np

INPUT_DEVICE = 31
OUTPUT_DEVICE = 14

SAMPLE_RATE = 44100
CHANNELS = 1
DURATION = 5

print("Recording for 5 seconds...")

recording = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    device=INPUT_DEVICE
)

sd.wait()

print("Recording finished.")
print("Playing recording...")

sd.play(
    recording,
    samplerate=SAMPLE_RATE,
    device=OUTPUT_DEVICE
)

sd.wait()

print("Playback finished.")