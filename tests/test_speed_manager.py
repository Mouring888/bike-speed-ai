import pytest
from engine.speed_manager import SpeedManager
from engine.calibrator import Calibrator


def make_calibrator(px_per_m: float) -> Calibrator:
    cal = Calibrator()
    cal.set_point(0, (0, 0))
    cal.set_point(1, (int(px_per_m), 0))
    cal.set_real_distance(1.0)
    return cal


def test_converts_pixels_to_kmh():
    """100 px/frame × 30 fps × (1m/100px) × 3.6 = 108 km/h"""
    cal = make_calibrator(px_per_m=100)
    sm = SpeedManager(calibrator=cal, fps=30)
    kmh = sm.update(100.0)
    assert abs(kmh - 108.0) < 1.0


def test_smoothing_averages_values():
    cal = make_calibrator(px_per_m=100)
    sm = SpeedManager(calibrator=cal, fps=10, window=3)
    sm.update(100.0)  # 36 km/h
    sm.update(200.0)  # 72 km/h
    result = sm.update(300.0)  # 108 km/h → avg = 72
    assert abs(result - 72.0) < 1.0


def test_zero_when_not_calibrated():
    cal = Calibrator()  # ยังไม่ calibrate
    sm = SpeedManager(calibrator=cal, fps=30)
    assert sm.update(100.0) == 0.0


def test_history_stored():
    cal = make_calibrator(px_per_m=100)
    sm = SpeedManager(calibrator=cal, fps=30)
    sm.update(50.0)
    sm.update(60.0)
    assert len(sm.history) == 2
