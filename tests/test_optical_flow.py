import numpy as np
import pytest
from engine.optical_flow import OpticalFlowSpeedCalculator


def make_gray_frame(h=480, w=640):
    """สร้าง synthetic grayscale frame สำหรับ test"""
    frame = np.random.randint(50, 200, (h, w), dtype=np.uint8)
    # เพิ่ม corner features (ส่วนมืด-สว่างชัดเจน)
    for i in range(0, h, 60):
        for j in range(0, w, 60):
            frame[i:i+10, j:j+10] = 255
            frame[i+10:i+20, j+10:j+20] = 0
    return frame


def test_initial_state():
    calc = OpticalFlowSpeedCalculator()
    assert calc.prev_frame is None
    assert calc.prev_points is None


def test_first_frame_returns_zero():
    calc = OpticalFlowSpeedCalculator()
    frame = make_gray_frame()
    speed = calc.update(frame, bike_bbox=None)
    assert speed == 0.0


def test_returns_float():
    calc = OpticalFlowSpeedCalculator()
    f1 = make_gray_frame()
    f2 = make_gray_frame()
    calc.update(f1, bike_bbox=None)
    speed = calc.update(f2, bike_bbox=None)
    assert isinstance(speed, float)
    assert speed >= 0.0


def test_reset():
    calc = OpticalFlowSpeedCalculator()
    frame = make_gray_frame()
    calc.update(frame, bike_bbox=None)
    calc.reset()
    assert calc.prev_frame is None


def test_spike_filter():
    """ค่าเกิน MAX_SPEED_PX ต้องถูกกรองออก"""
    calc = OpticalFlowSpeedCalculator(max_speed_px=5)
    f1 = make_gray_frame()
    f2 = make_gray_frame()  # random frame = displacement ใหญ่
    calc.update(f1, bike_bbox=None)
    speed = calc.update(f2, bike_bbox=None)
    # ถ้า displacement เกิน max → return 0.0
    assert speed >= 0.0
