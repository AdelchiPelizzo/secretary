import sounddevice as sd
import numpy as np

INPUT_DEVICE = 17
SAMPLE_RATE = 44100
CHANNELS = 2

print("Listening to:")
print(sd.query_devices(INPUT_DEVICE))
print()
print("Speak into the phone or make a test sound.")
print("Press Ctrl+C to stop.")

def callback(indata, frames, time, status):
    if status:
        print(status)

    level = np.max(np.abs(indata))

    if level > 0.01:
        print(f"Audio level: {level:.3f}")

with sd.InputStream(
    device=INPUT_DEVICE,
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    callback=callback
):
    while True:
        sd.sleep(1000)