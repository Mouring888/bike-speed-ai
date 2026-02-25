import pytest
from engine.calibrator import Calibrator


def test_initial_state_not_calibrated():
    cal = Calibrator()
    assert cal.is_calibrated is False


def test_set_two_points_and_distance():
    cal = Calibrator()
    cal.set_point(0, (100, 200))
    cal.set_point(1, (400, 200))
    cal.set_real_distance(3.66)  # เมตร
    assert cal.is_calibrated is True


def test_pixels_per_meter():
    cal = Calibrator()
    # จุด 2 จุด ห่างกัน 300 pixels = 3.0 เมตร → 100 px/m
    cal.set_point(0, (0, 0))
    cal.set_point(1, (300, 0))
    cal.set_real_distance(3.0)
    assert abs(cal.pixels_per_meter - 100.0) < 0.01


def test_pixels_to_meters():
    cal = Calibrator()
    cal.set_point(0, (0, 0))
    cal.set_point(1, (200, 0))
    cal.set_real_distance(2.0)  # 200px = 2m → 100px/m
    assert abs(cal.pixels_to_meters(50) - 0.5) < 0.001


def test_not_calibrated_raises():
    cal = Calibrator()
    with pytest.raises(RuntimeError):
        cal.pixels_to_meters(100)


def test_reset():
    cal = Calibrator()
    cal.set_point(0, (0, 0))
    cal.set_point(1, (100, 0))
    cal.set_real_distance(1.0)
    cal.reset()
    assert cal.is_calibrated is False
