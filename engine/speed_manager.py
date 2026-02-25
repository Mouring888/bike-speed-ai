from collections import deque
from engine.calibrator import Calibrator


class SpeedManager:
    """
    รับ pixel displacement per frame → แปลงเป็น km/h
    พร้อม moving average smoothing
    """

    def __init__(self, calibrator: Calibrator, fps: float, window: int = 5):
        self.calibrator = calibrator
        self.fps = fps
        self.window = window
        self._buffer: deque = deque(maxlen=window)
        self.history: list = []  # ประวัติทั้งหมดสำหรับ graph

    def update(self, pixel_displacement: float) -> float:
        """
        รับ pixel displacement per frame
        คืนค่า km/h หลัง smooth แล้ว
        """
        if not self.calibrator.is_calibrated:
            return 0.0

        meters_per_frame = self.calibrator.pixels_to_meters(pixel_displacement)
        kmh = meters_per_frame * self.fps * 3.6

        self._buffer.append(kmh)
        smoothed = sum(self._buffer) / len(self._buffer)
        self.history.append(round(smoothed, 2))
        return round(smoothed, 2)

    def reset(self):
        self._buffer.clear()
        self.history.clear()
