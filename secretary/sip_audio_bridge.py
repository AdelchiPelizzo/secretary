import queue

from secretary import pjsua2 as pj


SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLES_PER_FRAME = 160
BITS_PER_SAMPLE = 16
BYTES_PER_FRAME = 320


class SipAudioBridge(pj.AudioMediaPort):

    def __init__(self):
        super().__init__()

        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        self.frame_count = 0

    def onFrameReceived(self, frame):

        if frame.type != pj.PJMEDIA_FRAME_TYPE_AUDIO:
            return

        if frame.size <= 0:
            return

        data = bytes(frame.buf[:frame.size])

        self.input_queue.put(data)

        self.frame_count += 1

    def onFrameRequested(self, frame):

        frame.type = pj.PJMEDIA_FRAME_TYPE_AUDIO

        try:
            data = self.output_queue.get_nowait()
        except queue.Empty:
            data = bytes(BYTES_PER_FRAME)

        size = min(
            len(data),
            BYTES_PER_FRAME
        )

        frame.buf[:size] = data[:size]
        frame.size = size
