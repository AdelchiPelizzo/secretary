import sounddevice as sd
import numpy as np


SAMPLE_RATE = 44100
CHANNELS = 2
INPUT_DEVICE = 17


def receive_audio():

    print("Listening...")

    block_duration = 0.1

    silence_threshold = 0.015
    silence_duration = 0.8

    warmup_duration = 0.5
    pre_buffer_duration = 0.4

    warmup_blocks = int(warmup_duration / block_duration)
    pre_buffer_blocks = int(pre_buffer_duration / block_duration)

    blocks_read = 0

    audio_blocks = []
    pre_buffer = []

    speech_started = False
    silence_time = 0.0

    def callback(indata, frames, time, status):

        nonlocal speech_started
        nonlocal silence_time
        nonlocal blocks_read
        nonlocal pre_buffer

        audio = indata.copy()

        level = np.sqrt(np.mean(audio ** 2))

        blocks_read += 1

        # Ignore microphone startup transient
        if blocks_read <= warmup_blocks:
            return

        # Keep a small amount of audio before speech detection
        if not speech_started:

            pre_buffer.append(audio)

            if len(pre_buffer) > pre_buffer_blocks:
                pre_buffer.pop(0)

            if level > silence_threshold:
                speech_started = True

                # Include audio immediately before detection
                audio_blocks.extend(pre_buffer)

                print("Speech detected...")

        else:

            audio_blocks.append(audio)

            if level < silence_threshold:
                silence_time += block_duration
            else:
                silence_time = 0.0

    with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            device=INPUT_DEVICE,
            blocksize=int(SAMPLE_RATE * block_duration),
            callback=callback
    ):

        while not speech_started:
            sd.sleep(100)

        while silence_time < silence_duration:
            sd.sleep(100)

    print("Speech finished.")

    return np.concatenate(audio_blocks)


if __name__ == "__main__":
    receive_audio()