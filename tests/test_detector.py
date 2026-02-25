import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from engine.detector import BikeDetector


def make_bgr_frame(h=480, w=640):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_detector_initializes():
    with patch("engine.detector.YOLO") as mock_yolo:
        mock_yolo.return_value = MagicMock()
        det = BikeDetector()
        assert det is not None


def test_detect_returns_list():
    with patch("engine.detector.YOLO") as mock_yolo:
        mock_result = MagicMock()
        mock_result.boxes = MagicMock()
        mock_result.boxes.data = np.array([]).reshape(0, 6)
        mock_yolo.return_value.return_value = [mock_result]

        det = BikeDetector()
        frame = make_bgr_frame()
        detections = det.detect(frame)
        assert isinstance(detections, list)


def test_detect_filters_by_confidence():
    """ต้องกรอง detection ที่ confidence < 0.5"""
    with patch("engine.detector.YOLO") as mock_yolo:
        mock_result = MagicMock()
        mock_result.boxes = MagicMock()
        mock_result.boxes.data = np.array([
            [100, 100, 200, 200, 0.9, 1],  # bicycle, high conf → ผ่าน
            [300, 300, 400, 400, 0.3, 1],  # bicycle, low conf → ตัดออก
        ])
        mock_yolo.return_value.return_value = [mock_result]

        det = BikeDetector(conf_threshold=0.5)
        detections = det.detect(make_bgr_frame())
        assert len(detections) == 1
        assert detections[0]["confidence"] > 0.5


def test_detection_dict_keys():
    """แต่ละ detection ต้องมี keys: bbox, confidence"""
    with patch("engine.detector.YOLO") as mock_yolo:
        mock_result = MagicMock()
        mock_result.boxes = MagicMock()
        mock_result.boxes.data = np.array([
            [10, 20, 110, 120, 0.85, 1],
        ])
        mock_yolo.return_value.return_value = [mock_result]

        det = BikeDetector()
        detections = det.detect(make_bgr_frame())
        assert len(detections) == 1
        d = detections[0]
        assert "bbox" in d
        assert "confidence" in d
        x1, y1, x2, y2 = d["bbox"]
        assert x1 == 10 and y1 == 20
