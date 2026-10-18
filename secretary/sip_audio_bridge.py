import queue
import uuid

from secretary import pjsua2 as pj


SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLES_PER_FRAME = 160
BITS_PER_SAMPLE = 16
FRAME_TIME_USEC = 20000
BYTES_PER_FRAME = SAMPLES_PER_FRAME * CHANNELS * (BITS_PER_SAMPLE // 8)


class SipAudioBridge(pj.AudioMediaPort):

    def __init__(self):
        super().__init__()

        self.bridge_id = uuid.uuid4().hex[:8]

        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.pending_output = b""
        self.frame_count = 0
        self.closed = False

        fmt = pj.MediaFormatAudio()
        fmt.init(
            pj.PJMEDIA_FORMAT_PCM,
            SAMPLE_RATE,
            CHANNELS,
            FRAME_TIME_USEC,
            BITS_PER_SAMPLE,
        )

        self.createPort(
            f"SipAudioBridge-{self.bridge_id}",
            fmt,
        )

        print(
            f"[AUDIO BRIDGE] Created SIP media port "
            f"bridge_id={self.bridge_id}, "
            f"rate={SAMPLE_RATE}, channels={CHANNELS}, "
            f"bytes_per_frame={BYTES_PER_FRAME}"
        )

    def onFrameReceived(self, frame):

        if self.closed:
            return

        if frame.type != pj.PJMEDIA_FRAME_TYPE_AUDIO:
            return

        if frame.size <= 0:
            return

        data = bytes(frame.buf[:frame.size])
        self.input_queue.put(data)

        self.frame_count += 1

        if self.frame_count == 1:
            print(
                f"[AUDIO BRIDGE] First received frame: "
                f"bridge_id={self.bridge_id}, "
                f"bytes={len(data)}"
            )

    def onFrameRequested(self, frame):
        frame.type = pj.PJMEDIA_FRAME_TYPE_AUDIO

        if self.closed:
            data = bytes(BYTES_PER_FRAME)
        else:
            # Fetch another chunk only when the pending data is insufficient.
            if len(self.pending_output) < BYTES_PER_FRAME:
                try:
                    chunk = self.output_queue.get_nowait()
                    self.pending_output += chunk
                except queue.Empty:
                    pass

            # Send exactly one 320-byte frame and preserve any remainder.
            data = self.pending_output[:BYTES_PER_FRAME]
            self.pending_output = self.pending_output[BYTES_PER_FRAME:]

            # Fill any missing bytes with silence.
            if len(data) < BYTES_PER_FRAME:
                data += bytes(BYTES_PER_FRAME - len(data))

        frame.buf[:BYTES_PER_FRAME] = data
        frame.size = BYTES_PER_FRAME

    def stop(self):

        self.closed = True

        self.pending_output = b""

        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break

        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        print(
            f"[AUDIO BRIDGE] Stopped bridge_id={self.bridge_id}"
        )