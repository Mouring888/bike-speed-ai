import math


class Calibrator:
    """แปลง pixel distance เป็น meter โดยใช้ 2 จุด reference จากผู้ใช้"""

    def __init__(self):
        self._points = [None, None]
        self._real_distance_m = None

    @property
    def is_calibrated(self) -> bool:
        return (
            self._points[0] is not None
            and self._points[1] is not None
            and self._real_distance_m is not None
        )

    @property
    def pixels_per_meter(self) -> float:
        if not self.is_calibrated:
            raise RuntimeError("Calibrator not set. Call set_point() and set_real_distance() first.")
        p0, p1 = self._points
        pixel_dist = math.sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2)
        return pixel_dist / self._real_distance_m

    def set_point(self, index: int, point: tuple):
        """บันทึกจุด calibration (index 0 หรือ 1)"""
        if index not in (0, 1):
            raise ValueError("index ต้องเป็น 0 หรือ 1")
        self._points[index] = point

    def set_real_distance(self, meters: float):
        """กำหนดระยะจริงระหว่าง 2 จุด (หน่วยเมตร)"""
        if meters <= 0:
            raise ValueError("ระยะต้องมากกว่า 0")
        self._real_distance_m = meters

    def pixels_to_meters(self, pixels: float) -> float:
        """แปลง pixel distance เป็น meter"""
        if not self.is_calibrated:
            raise RuntimeError("Calibrator not set.")
        return pixels / self.pixels_per_meter

    def reset(self):
        """รีเซ็ต calibration"""
        self._points = [None, None]
        self._real_distance_m = None
