# class Call:
#
#     def __init__(self, call_id, caller_number=None, called_number=None):
#         self.call_id = call_id
#         self.caller_number = caller_number
#         self.called_number = called_number
#         self.language = None
#         self.messages = []
#
#         self.appointment = {
#             "title": None,
#             "date": None,
#             "time": None,
#             "duration_minutes": None
#         }
#
#         self.appointment_status = "NONE"

import queue
import threading

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 8000
CHANNELS = 1
BLOCKSIZE = 320

# sounddevice device IDs
INPUT_DEVICE = 3     # CABLE Output
OUTPUT_DEVICE = 6    # CABLE Input


class AudioBridge:

    def __init__(self):

        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        self.running = False

        self.input_stream = None
        self.output_stream = None

    def start(self):

        if self.running:
            return

        self.running = True

        self.input_stream = sd.InputStream(
            device=INPUT_DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCKSIZE,
            callback=self._input_callback,
        )

        self.output_stream = sd.OutputStream(
            device=OUTPUT_DEVICE,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCKSIZE,
            callback=self._output_callback,
        )

        self.input_stream.start()
        self.output_stream.start()

        print("[AUDIO] VB-CABLE bridge started.")

    def _input_callback(
        self,
        indata,
        frames,
        time,
        status
    ):

        if status:
            print("[AUDIO INPUT]", status)

        self.input_queue.put(
            indata[:, 0].tobytes()
        )

    def _output_callback(
        self,
        outdata,
        frames,
        time,
        status
    ):

        if status:
            print("[AUDIO OUTPUT]", status)

        required = frames * 2

        try:
            data = self.output_queue.get_nowait()
        except queue.Empty:
            data = b""

        if len(data) < required:
            data += b"\x00" * (
                required - len(data)
            )

        outdata[:, 0] = np.frombuffer(
            data[:required],
            dtype=np.int16
        )

    def stop(self):

        self.running = False

        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None

        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None

        print("[AUDIO] VB-CABLE bridge stopped.")


class Call:

    def __init__(
        self,
        call_id,
        caller_number=None,
        called_number=None
    ):

        self.call_id = call_id
        self.caller_number = caller_number
        self.called_number = called_number
        self.language = None
        self.messages = []

        self.appointment = {
            "title": None,
            "date": None,
            "time": None,
            "duration_minutes": None
        }

        self.appointment_status = "NONE"

        self.audio_port = AudioBridge()