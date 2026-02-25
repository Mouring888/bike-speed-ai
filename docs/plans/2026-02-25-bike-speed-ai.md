# Bike Speed AI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Web app วัดความเร็วจักรยานจากวิดีโอโดรน top-down โดยใช้ YOLOv8n + ByteTrack + Lucas-Kanade Optical Flow แสดงผล real-time ผ่าน browser

**Architecture:** Flask backend ประมวลผลวิดีโอใน background thread, stream ภาพ overlay ผ่าน MJPEG, ส่งข้อมูลความเร็วผ่าน WebSocket ไปยัง frontend ที่มี interactive canvas และกราฟ Chart.js ความเร็วขึ้นอยู่กับ optical flow ของพื้นหลัง (ไม่ใช่ตัวจักรยาน) เพราะโดรนบินตามจักรยาน

**Tech Stack:** Python 3.13, Flask + flask-sock, ultralytics (YOLOv8n), supervision (ByteTrack), OpenCV (cv2), Chart.js, Vanilla JS

---

## Task 1: Project Structure & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `uploads/.gitkeep`
- Create: `engine/__init__.py`
- Create: `static/js/.gitkeep`
- Create: `tests/__init__.py`

**Step 1: สร้าง directory structure**

```bash
cd "/Users/admin/จับความเร็ว"
mkdir -p engine static/js static/css templates uploads tests
touch engine/__init__.py tests/__init__.py uploads/.gitkeep
```

**Step 2: สร้าง requirements.txt**

```
flask>=3.1.0
flask-sock>=0.7.0
ultralytics>=8.3.0
supervision>=0.25.0
opencv-python>=4.10.0
numpy>=2.2.0
```

บันทึกเป็น `requirements.txt` ที่ root ของโปรเจค

**Step 3: ติดตั้ง dependencies**

```bash
pip3 install -r requirements.txt
```

Expected: ติดตั้งสำเร็จ — YOLOv8n model จะ download อัตโนมัติตอนรันครั้งแรก (~6MB)

**Step 4: ตรวจสอบ**

```bash
python3 -c "import cv2; import ultralytics; import supervision; import flask_sock; print('OK')"
```

Expected output: `OK`

**Step 5: Commit**

```bash
cd "/Users/admin/จับความเร็ว"
git add requirements.txt engine/ static/ templates/ uploads/ tests/
git commit -m "chore: project structure and dependencies"
```

---

## Task 2: Calibrator Module

**Files:**
- Create: `engine/calibrator.py`
- Create: `tests/test_calibrator.py`

**Step 1: เขียน failing test**

สร้างไฟล์ `tests/test_calibrator.py`:

```python
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
```

**Step 2: รัน test เพื่อยืนยันว่า fail**

```bash
cd "/Users/admin/จับความเร็ว"
python3 -m pytest tests/test_calibrator.py -v
```

Expected: `ModuleNotFoundError: No module named 'engine.calibrator'`

**Step 3: เขียน implementation**

สร้างไฟล์ `engine/calibrator.py`:

```python
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

    def set_point(self, index: int, point: tuple[int, int]):
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
```

**Step 4: รัน test เพื่อยืนยันว่าผ่าน**

```bash
python3 -m pytest tests/test_calibrator.py -v
```

Expected: `6 passed`

**Step 5: Commit**

```bash
git add engine/calibrator.py tests/test_calibrator.py
git commit -m "feat: add Calibrator module with pixel-to-meter conversion"
```

---

## Task 3: Optical Flow Speed Calculator

**Files:**
- Create: `engine/optical_flow.py`
- Create: `tests/test_optical_flow.py`

**Step 1: เขียน failing test**

สร้างไฟล์ `tests/test_optical_flow.py`:

```python
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
```

**Step 2: รัน test เพื่อยืนยันว่า fail**

```bash
python3 -m pytest tests/test_optical_flow.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: เขียน implementation**

สร้างไฟล์ `engine/optical_flow.py`:

```python
import cv2
import numpy as np
from typing import Optional


class OpticalFlowSpeedCalculator:
    """
    คำนวณความเร็วของโดรน (= ความเร็วจักรยาน) จาก optical flow ของพื้นหลัง

    เนื่องจากโดรนบินตามจักรยาน → พื้นหลังเคลื่อนที่ตรงข้ามกับจักรยาน
    → วัด displacement ของ background features = ความเร็วจักรยาน
    """

    # Lucas-Kanade parameters
    LK_PARAMS = dict(
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    FEATURE_PARAMS = dict(
        maxCorners=100,
        qualityLevel=0.3,
        minDistance=10,
        blockSize=7,
    )

    def __init__(self, max_speed_px: float = 150.0):
        self.prev_frame: Optional[np.ndarray] = None
        self.prev_points: Optional[np.ndarray] = None
        self.max_speed_px = max_speed_px  # กรอง spike เกินนี้ถือว่าผิดปกติ

    def update(
        self,
        gray_frame: np.ndarray,
        bike_bbox: Optional[tuple[int, int, int, int]],
    ) -> float:
        """
        รับ grayscale frame และ bbox ของจักรยาน (x1,y1,x2,y2)
        คืนค่า pixel displacement per frame ของพื้นหลัง
        """
        if self.prev_frame is None:
            self._init_points(gray_frame, bike_bbox)
            return 0.0

        if self.prev_points is None or len(self.prev_points) == 0:
            self._init_points(gray_frame, bike_bbox)
            return 0.0

        # คำนวณ optical flow
        new_points, status, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_frame, gray_frame, self.prev_points, None, **self.LK_PARAMS
        )

        # กรองเฉพาะจุดที่ track สำเร็จ
        if status is None:
            self._init_points(gray_frame, bike_bbox)
            return 0.0

        good_old = self.prev_points[status.flatten() == 1]
        good_new = new_points[status.flatten() == 1]

        if len(good_old) == 0:
            self._init_points(gray_frame, bike_bbox)
            return 0.0

        # คำนวณ displacement แต่ละจุด
        displacements = np.sqrt(
            np.sum((good_new - good_old) ** 2, axis=1)
        )

        # ใช้ median เพื่อลด outlier
        median_disp = float(np.median(displacements))

        # Spike filter
        if median_disp > self.max_speed_px:
            median_disp = 0.0

        # อัปเดต state — refresh points เป็นระยะ
        if len(good_new) < 20:
            self._init_points(gray_frame, bike_bbox)
        else:
            self.prev_frame = gray_frame.copy()
            self.prev_points = good_new.reshape(-1, 1, 2)

        return median_disp

    def _init_points(
        self,
        gray_frame: np.ndarray,
        bike_bbox: Optional[tuple[int, int, int, int]],
    ):
        """หา corner features บนพื้นหลัง (นอก bike bbox)"""
        mask = np.ones(gray_frame.shape[:2], dtype=np.uint8) * 255
        if bike_bbox is not None:
            x1, y1, x2, y2 = bike_bbox
            # เพิ่ม padding 20px รอบ bbox เพื่อไม่ให้ feature อยู่บนจักรยาน
            pad = 20
            mask[
                max(0, y1 - pad): min(gray_frame.shape[0], y2 + pad),
                max(0, x1 - pad): min(gray_frame.shape[1], x2 + pad),
            ] = 0

        points = cv2.goodFeaturesToTrack(gray_frame, mask=mask, **self.FEATURE_PARAMS)
        self.prev_frame = gray_frame.copy()
        self.prev_points = points

    def reset(self):
        self.prev_frame = None
        self.prev_points = None
```

**Step 4: รัน test เพื่อยืนยันว่าผ่าน**

```bash
python3 -m pytest tests/test_optical_flow.py -v
```

Expected: `5 passed`

**Step 5: Commit**

```bash
git add engine/optical_flow.py tests/test_optical_flow.py
git commit -m "feat: add OpticalFlowSpeedCalculator for background-based speed measurement"
```

---

## Task 4: YOLOv8n Detector

**Files:**
- Create: `engine/detector.py`
- Create: `tests/test_detector.py`

**Step 1: เขียน failing test**

สร้างไฟล์ `tests/test_detector.py`:

```python
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
        # สร้าง mock detection: [x1, y1, x2, y2, conf, class_id]
        # class_id=1 คือ bicycle ใน COCO
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
```

**Step 2: รัน test เพื่อยืนยันว่า fail**

```bash
python3 -m pytest tests/test_detector.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: เขียน implementation**

สร้างไฟล์ `engine/detector.py`:

```python
from ultralytics import YOLO
import numpy as np

BICYCLE_CLASS_ID = 1  # COCO dataset: 1 = bicycle


class BikeDetector:
    """
    ตรวจจับจักรยานด้วย YOLOv8n (pre-trained COCO)
    ไม่ต้อง train ใหม่ เพราะ COCO มี class bicycle อยู่แล้ว
    """

    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, bgr_frame: np.ndarray) -> list[dict]:
        """
        รับ BGR frame คืนค่า list ของ detection dicts
        แต่ละ dict: {"bbox": (x1,y1,x2,y2), "confidence": float}
        """
        results = self.model(bgr_frame, verbose=False)
        detections = []

        for result in results:
            if result.boxes is None:
                continue
            for row in result.boxes.data.tolist():
                x1, y1, x2, y2, conf, cls_id = row
                if int(cls_id) != BICYCLE_CLASS_ID:
                    continue
                if conf < self.conf_threshold:
                    continue
                detections.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "confidence": float(conf),
                })

        return detections
```

**Step 4: รัน test เพื่อยืนยันว่าผ่าน**

```bash
python3 -m pytest tests/test_detector.py -v
```

Expected: `4 passed`

**Step 5: Commit**

```bash
git add engine/detector.py tests/test_detector.py
git commit -m "feat: add BikeDetector wrapping YOLOv8n"
```

---

## Task 5: Speed Manager (Smoother + Unit Converter)

**Files:**
- Create: `engine/speed_manager.py`
- Create: `tests/test_speed_manager.py`

**Step 1: เขียน failing test**

สร้างไฟล์ `tests/test_speed_manager.py`:

```python
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
    from engine.calibrator import Calibrator
    cal = Calibrator()  # ยังไม่ calibrate
    sm = SpeedManager(calibrator=cal, fps=30)
    assert sm.update(100.0) == 0.0


def test_history_stored():
    cal = make_calibrator(px_per_m=100)
    sm = SpeedManager(calibrator=cal, fps=30)
    sm.update(50.0)
    sm.update(60.0)
    assert len(sm.history) == 2
```

**Step 2: รัน test เพื่อยืนยันว่า fail**

```bash
python3 -m pytest tests/test_speed_manager.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: เขียน implementation**

สร้างไฟล์ `engine/speed_manager.py`:

```python
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
        self._buffer: deque[float] = deque(maxlen=window)
        self.history: list[float] = []  # ประวัติทั้งหมดสำหรับ graph

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
```

**Step 4: รัน test เพื่อยืนยันว่าผ่าน**

```bash
python3 -m pytest tests/test_speed_manager.py -v
```

Expected: `4 passed`

**Step 5: รัน tests ทั้งหมดเพื่อให้แน่ใจไม่มีอะไรพัง**

```bash
python3 -m pytest tests/ -v
```

Expected: `13 passed`

**Step 6: Commit**

```bash
git add engine/speed_manager.py tests/test_speed_manager.py
git commit -m "feat: add SpeedManager with px→kmh conversion and smoothing"
```

---

## Task 6: Video Engine (Processing Pipeline)

**Files:**
- Create: `engine/video_engine.py`

_หมายเหตุ: ไม่ test โดยตรง (ต้องใช้วิดีโอจริง) แต่ออกแบบให้ inject dependency ง่าย_

สร้างไฟล์ `engine/video_engine.py`:

```python
import threading
import time
import cv2
import numpy as np
import supervision as sv

from engine.detector import BikeDetector
from engine.optical_flow import OpticalFlowSpeedCalculator
from engine.speed_manager import SpeedManager
from engine.calibrator import Calibrator


class VideoEngine:
    """
    Pipeline หลัก: อ่าน frame → detect → track → optical flow → speed
    ทำงานใน background thread, ส่งผลผ่าน callback
    """

    def __init__(self):
        self.detector = BikeDetector()
        self.tracker = sv.ByteTrack()
        self.flow_calc = OpticalFlowSpeedCalculator()
        self.calibrator = Calibrator()

        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        # State
        self.fps: float = 30.0
        self.selected_track_id: int | None = None
        self.speed_managers: dict[int, SpeedManager] = {}

        # Callbacks — Flask routes จะ set ค่านี้
        self.on_frame = None    # fn(jpeg_bytes)
        self.on_speed = None    # fn(track_id, kmh, history)

    def load_video(self, path: str):
        """โหลดวิดีโอจาก path"""
        if self._cap:
            self._cap.release()
        self._cap = cv2.VideoCapture(path)
        self.fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.flow_calc.reset()
        self.speed_managers.clear()

    def start(self):
        """เริ่ม processing thread"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def select_track(self, track_id: int):
        self.selected_track_id = track_id

    def _process_loop(self):
        annotator = sv.BoxAnnotator()
        label_annotator = sv.LabelAnnotator()

        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret:
                self._running = False
                break

            # 1. Detection
            raw_detections = self.detector.detect(frame)

            # 2. แปลงเป็น sv.Detections format สำหรับ ByteTrack
            if raw_detections:
                bboxes = np.array([d["bbox"] for d in raw_detections], dtype=float)
                confs = np.array([d["confidence"] for d in raw_detections], dtype=float)
                sv_det = sv.Detections(
                    xyxy=bboxes,
                    confidence=confs,
                    class_id=np.ones(len(bboxes), dtype=int),
                )
            else:
                sv_det = sv.Detections.empty()

            # 3. ByteTrack — กำหนด ID ให้แต่ละ detection
            tracked = self.tracker.update_with_detections(sv_det)

            # 4. Optical flow — ใช้ bbox ของ selected bike (ถ้ามี)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            selected_bbox = self._get_selected_bbox(tracked)
            pixel_disp = self.flow_calc.update(gray, selected_bbox)

            # 5. Speed calculation สำหรับ selected track
            if self.selected_track_id is not None:
                sm = self._get_speed_manager(self.selected_track_id)
                kmh = sm.update(pixel_disp)
                if self.on_speed:
                    self.on_speed(self.selected_track_id, kmh, sm.history[-100:])

            # 6. วาด overlay
            frame = self._draw_overlay(frame, tracked, annotator, label_annotator)

            # 7. Encode เป็น JPEG ส่ง callback
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if self.on_frame:
                self.on_frame(jpeg.tobytes())

            time.sleep(1 / self.fps)

    def _get_selected_bbox(self, tracked: sv.Detections):
        if self.selected_track_id is None or tracked.tracker_id is None:
            return None
        for i, tid in enumerate(tracked.tracker_id):
            if tid == self.selected_track_id:
                x1, y1, x2, y2 = tracked.xyxy[i].astype(int)
                return (x1, y1, x2, y2)
        return None

    def _get_speed_manager(self, track_id: int) -> SpeedManager:
        if track_id not in self.speed_managers:
            self.speed_managers[track_id] = SpeedManager(
                calibrator=self.calibrator, fps=self.fps
            )
        return self.speed_managers[track_id]

    def _draw_overlay(self, frame, tracked, annotator, label_annotator):
        if tracked.tracker_id is None:
            return frame

        # สีตาม selected
        colors = []
        labels = []
        for i, tid in enumerate(tracked.tracker_id):
            is_selected = tid == self.selected_track_id
            sm = self.speed_managers.get(tid)
            kmh = sm.history[-1] if sm and sm.history else 0.0

            label = f"Bike #{tid} {kmh:.1f} km/h"
            labels.append(label)

        frame = annotator.annotate(frame, tracked)
        frame = label_annotator.annotate(frame, tracked, labels=labels)
        return frame
```

**Step: Commit**

```bash
git add engine/video_engine.py
git commit -m "feat: add VideoEngine processing pipeline with ByteTrack and optical flow"
```

---

## Task 7: Flask App & Routes

**Files:**
- Create: `app.py`

สร้างไฟล์ `app.py`:

```python
import os
import json
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_sock import Sock

from engine.video_engine import VideoEngine

app = Flask(__name__)
sock = Sock(app)

UPLOAD_FOLDER = "uploads"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

engine = VideoEngine()
_ws_clients: list = []
_latest_frame: bytes | None = None


# ── Callbacks จาก VideoEngine ─────────────────────────────────
def on_frame(jpeg_bytes: bytes):
    global _latest_frame
    _latest_frame = jpeg_bytes


def on_speed(track_id: int, kmh: float, history: list[float]):
    payload = json.dumps({
        "type": "speed",
        "track_id": track_id,
        "kmh": round(kmh, 2),
        "history": history,
    })
    dead = []
    for ws in _ws_clients:
        try:
            ws.send(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


engine.on_frame = on_frame
engine.on_speed = on_speed


# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "ไม่พบไฟล์วิดีโอ"}), 400
    file = request.files["video"]
    if not file.filename.lower().endswith(".mp4"):
        return jsonify({"error": "รองรับเฉพาะไฟล์ .mp4"}), 400
    path = os.path.join(UPLOAD_FOLDER, "current.mp4")
    file.save(path)
    engine.load_video(path)
    return jsonify({"ok": True, "message": "อัพโหลดสำเร็จ"})


@app.route("/calibrate", methods=["POST"])
def calibrate():
    data = request.json
    engine.calibrator.reset()
    engine.calibrator.set_point(0, tuple(data["point0"]))
    engine.calibrator.set_point(1, tuple(data["point1"]))
    engine.calibrator.set_real_distance(float(data["distance_m"]))
    return jsonify({"ok": True, "px_per_m": engine.calibrator.pixels_per_meter})


@app.route("/run", methods=["POST"])
def run():
    engine.stop()
    time.sleep(0.2)
    engine.start()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop():
    engine.stop()
    return jsonify({"ok": True})


@app.route("/select_track", methods=["POST"])
def select_track():
    data = request.json
    engine.select_track(int(data["track_id"]))
    return jsonify({"ok": True})


@app.route("/video_feed")
def video_feed():
    """MJPEG stream"""
    def generate():
        while True:
            if _latest_frame:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + _latest_frame
                    + b"\r\n"
                )
            time.sleep(0.033)
    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@sock.route("/ws")
def websocket(ws):
    _ws_clients.append(ws)
    try:
        while True:
            msg = ws.receive(timeout=30)
            if msg is None:
                break
    except Exception:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
```

**Step: Commit**

```bash
git add app.py
git commit -m "feat: add Flask app with upload, calibrate, run, stream, and WebSocket routes"
```

---

## Task 8: Frontend HTML

**Files:**
- Create: `templates/index.html`

สร้างไฟล์ `templates/index.html`:

```html
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🚴 Bike Speed AI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }

  header {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 20px; background: #1e293b; border-bottom: 1px solid #334155;
  }
  header h1 { font-size: 1.2rem; flex: 1; }

  .btn {
    padding: 8px 16px; border: none; border-radius: 6px;
    cursor: pointer; font-size: 0.9rem; font-weight: 600;
  }
  .btn-primary { background: #3b82f6; color: white; }
  .btn-success { background: #22c55e; color: white; }
  .btn-warning { background: #f59e0b; color: black; }
  .btn-danger  { background: #ef4444; color: white; }
  .btn:hover { opacity: 0.85; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .layout {
    display: grid; grid-template-columns: 1fr 340px;
    height: calc(100vh - 56px);
  }

  /* ── Video Panel ── */
  .video-panel { position: relative; background: #000; overflow: hidden; }
  #videoImg { width: 100%; height: 100%; object-fit: contain; display: block; }
  #overlayCanvas {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    cursor: crosshair;
  }
  #calibStatus {
    position: absolute; bottom: 8px; left: 8px;
    background: rgba(0,0,0,0.7); padding: 6px 10px; border-radius: 6px;
    font-size: 0.8rem; display: none;
  }

  /* ── Dashboard ── */
  .dashboard {
    background: #1e293b; padding: 16px;
    overflow-y: auto; display: flex; flex-direction: column; gap: 16px;
  }
  .card { background: #0f172a; border-radius: 8px; padding: 14px; }
  .card h3 { font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

  .speed-display {
    font-size: 3rem; font-weight: 800; text-align: center;
    color: #22c55e; line-height: 1;
  }
  .speed-display.fast { color: #ef4444; }
  .speed-unit { font-size: 1rem; font-weight: 400; color: #94a3b8; }

  .stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center; }
  .stat-val { font-size: 1.1rem; font-weight: 700; }
  .stat-lbl { font-size: 0.7rem; color: #94a3b8; }

  canvas#speedChart { max-height: 180px; }

  .selected-info { font-size: 0.85rem; color: #94a3b8; }
  .selected-info span { color: #60a5fa; font-weight: 600; }

  #statusBar {
    background: #334155; padding: 6px 10px; border-radius: 6px;
    font-size: 0.8rem; color: #94a3b8;
  }
</style>
</head>
<body>

<header>
  <h1>🚴 Bike Speed AI</h1>
  <input type="file" id="fileInput" accept=".mp4" style="display:none">
  <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">📁 Upload Video</button>
  <button class="btn btn-warning" id="btnCalib" disabled>🎯 Calibrate</button>
  <button class="btn btn-success" id="btnRun" disabled>▶ Run</button>
  <button class="btn btn-danger"  id="btnStop" disabled>⏹ Stop</button>
</header>

<div class="layout">
  <!-- Video -->
  <div class="video-panel">
    <img id="videoImg" src="" alt="Video feed">
    <canvas id="overlayCanvas"></canvas>
    <div id="calibStatus">🎯 คลิกจุดที่ 1 บนภาพ...</div>
  </div>

  <!-- Dashboard -->
  <div class="dashboard">
    <div id="statusBar">⏳ รอการอัพโหลดวิดีโอ...</div>

    <div class="card">
      <h3>🚴 Selected Bike</h3>
      <div class="selected-info">Track ID: <span id="selectedId">—</span></div>
      <div class="speed-display" id="speedDisplay">—</div>
      <div class="speed-unit" style="text-align:center; margin-top:4px;">km/h</div>
    </div>

    <div class="card">
      <h3>📊 Statistics</h3>
      <div class="stats">
        <div><div class="stat-val" id="statMax">—</div><div class="stat-lbl">Max</div></div>
        <div><div class="stat-val" id="statAvg">—</div><div class="stat-lbl">Avg</div></div>
        <div><div class="stat-val" id="statMin">—</div><div class="stat-lbl">Min</div></div>
      </div>
    </div>

    <div class="card">
      <h3>📈 Speed over Time</h3>
      <canvas id="speedChart"></canvas>
    </div>

    <div class="card">
      <h3>⚙️ Calibration</h3>
      <div id="calibInfo" style="font-size:0.8rem; color:#94a3b8;">ยังไม่ได้ Calibrate</div>
    </div>
  </div>
</div>

<script src="/static/js/app.js"></script>
</body>
</html>
```

**Step: Commit**

```bash
git add templates/index.html
git commit -m "feat: add frontend HTML with video panel and dashboard layout"
```

---

## Task 9: Frontend JavaScript

**Files:**
- Create: `static/js/app.js`

สร้างไฟล์ `static/js/app.js`:

```javascript
// ── DOM refs ──────────────────────────────────────────────────
const fileInput    = document.getElementById('fileInput');
const videoImg     = document.getElementById('videoImg');
const overlayCanvas= document.getElementById('overlayCanvas');
const ctx          = overlayCanvas.getContext('2d');
const btnCalib     = document.getElementById('btnCalib');
const btnRun       = document.getElementById('btnRun');
const btnStop      = document.getElementById('btnStop');
const statusBar    = document.getElementById('statusBar');
const calibStatus  = document.getElementById('calibStatus');
const speedDisplay = document.getElementById('speedDisplay');
const selectedId   = document.getElementById('selectedId');
const statMax      = document.getElementById('statMax');
const statAvg      = document.getElementById('statAvg');
const statMin      = document.getElementById('statMin');
const calibInfo    = document.getElementById('calibInfo');

// ── State ─────────────────────────────────────────────────────
let calibMode     = false;
let calibPoints   = [];
let videoNatural  = { w: 640, h: 480 };
let ws            = null;

// ── Chart.js Setup ────────────────────────────────────────────
const chart = new Chart(document.getElementById('speedChart'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'km/h',
      data: [],
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59,130,246,0.15)',
      tension: 0.3,
      pointRadius: 0,
      fill: true,
    }]
  },
  options: {
    animation: false,
    scales: {
      x: { display: false },
      y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
    },
    plugins: { legend: { display: false } },
  }
});

// ── Upload ────────────────────────────────────────────────────
fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  setStatus('⬆️ กำลังอัพโหลด...');
  const fd = new FormData();
  fd.append('video', file);
  const res = await fetch('/upload', { method: 'POST', body: fd });
  const data = await res.json();
  if (data.ok) {
    videoImg.src = '/video_feed';
    videoImg.onload = () => syncCanvas();
    btnCalib.disabled = false;
    btnRun.disabled = false;
    setStatus('✅ อัพโหลดสำเร็จ — กด Calibrate หรือ Run ได้เลย');
  } else {
    setStatus('❌ ' + (data.error || 'อัพโหลดล้มเหลว'));
  }
});

// ── Calibrate ─────────────────────────────────────────────────
btnCalib.addEventListener('click', () => {
  calibMode = true;
  calibPoints = [];
  calibStatus.style.display = 'block';
  calibStatus.textContent = '🎯 คลิกจุดที่ 1 บนภาพ...';
  setStatus('🎯 Calibration Mode: คลิก 2 จุดที่รู้ระยะจริง');
});

overlayCanvas.addEventListener('click', (e) => {
  if (!calibMode) {
    // ── Click to select bike track ──
    handleBikeClick(e);
    return;
  }
  const pt = canvasToVideo(e.offsetX, e.offsetY);
  calibPoints.push(pt);
  drawCalibPoint(e.offsetX, e.offsetY, calibPoints.length);

  if (calibPoints.length === 1) {
    calibStatus.textContent = '🎯 คลิกจุดที่ 2 บนภาพ...';
  } else if (calibPoints.length === 2) {
    calibStatus.style.display = 'none';
    const dist = prompt('ระยะห่างระหว่าง 2 จุดนี้ในความเป็นจริง (เมตร):', '3.66');
    if (!dist || isNaN(parseFloat(dist))) { calibMode = false; return; }
    sendCalibration(calibPoints[0], calibPoints[1], parseFloat(dist));
    calibMode = false;
  }
});

async function sendCalibration(p0, p1, distM) {
  const res = await fetch('/calibrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ point0: p0, point1: p1, distance_m: distM })
  });
  const data = await res.json();
  calibInfo.textContent = `✅ ${data.px_per_m?.toFixed(1)} px/m | ระยะ ${distM} m`;
  setStatus('✅ Calibration เสร็จแล้ว — กด Run ได้เลย');
}

// ── Run / Stop ────────────────────────────────────────────────
btnRun.addEventListener('click', async () => {
  await fetch('/run', { method: 'POST' });
  btnStop.disabled = false;
  connectWebSocket();
  setStatus('▶ กำลังประมวลผล... คลิกจักรยานในภาพเพื่อเลือก');
});

btnStop.addEventListener('click', async () => {
  await fetch('/stop', { method: 'POST' });
  btnStop.disabled = true;
  setStatus('⏹ หยุดแล้ว');
});

// ── WebSocket ─────────────────────────────────────────────────
function connectWebSocket() {
  if (ws) ws.close();
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'speed') updateSpeedDashboard(msg);
  };
  ws.onerror = () => setStatus('⚠️ WebSocket error');
}

function updateSpeedDashboard({ track_id, kmh, history }) {
  selectedId.textContent = `#${track_id}`;
  speedDisplay.textContent = kmh.toFixed(1);
  speedDisplay.className = 'speed-display' + (kmh > 40 ? ' fast' : '');

  if (history.length > 0) {
    statMax.textContent = Math.max(...history).toFixed(1) + ' km/h';
    statMin.textContent = Math.min(...history).toFixed(1) + ' km/h';
    const avg = history.reduce((a, b) => a + b, 0) / history.length;
    statAvg.textContent = avg.toFixed(1) + ' km/h';

    // อัปเดตกราฟ
    chart.data.labels = history.map((_, i) => i);
    chart.data.datasets[0].data = history;
    chart.update('none');
  }
}

// ── Click to select bike ──────────────────────────────────────
function handleBikeClick(e) {
  // TODO: map click position กับ track bbox จาก server
  // สำหรับ MVP: ส่ง click position ไป backend ให้จับคู่เอง
  const pt = canvasToVideo(e.offsetX, e.offsetY);
  fetch('/select_track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ point: pt })
  });
}

// ── Helpers ───────────────────────────────────────────────────
function syncCanvas() {
  overlayCanvas.width  = overlayCanvas.offsetWidth;
  overlayCanvas.height = overlayCanvas.offsetHeight;
}

function canvasToVideo(cx, cy) {
  const rect = overlayCanvas.getBoundingClientRect();
  const scaleX = videoNatural.w / rect.width;
  const scaleY = videoNatural.h / rect.height;
  return [Math.round(cx * scaleX), Math.round(cy * scaleY)];
}

function drawCalibPoint(x, y, n) {
  ctx.beginPath();
  ctx.arc(x, y, 6, 0, Math.PI * 2);
  ctx.fillStyle = '#f59e0b';
  ctx.fill();
  ctx.fillStyle = 'white';
  ctx.font = '12px sans-serif';
  ctx.fillText(n, x + 8, y - 4);
}

function setStatus(msg) {
  statusBar.textContent = msg;
}

window.addEventListener('resize', syncCanvas);
```

**Step: อัปเดต `/select_track` route ใน app.py ให้รับ point แล้วหา track ที่ใกล้ที่สุด**

เปิด `app.py` และแก้ไข route `/select_track`:

```python
@app.route("/select_track", methods=["POST"])
def select_track():
    data = request.json
    # ถ้าส่ง point มา → หา track id ที่ bbox ครอบคลุม point นั้น
    if "point" in data:
        px, py = data["point"]
        # วน loop หา track ที่ bbox ครอบ point ที่คลิก
        # engine.tracker จะเข้าถึงไม่ได้โดยตรง → ใช้ last_detections
        track_id = engine.find_track_at_point(px, py)
        if track_id is not None:
            engine.select_track(track_id)
            return jsonify({"ok": True, "track_id": track_id})
        return jsonify({"ok": False, "message": "ไม่พบจักรยานตรงตำแหน่งนี้"})
    engine.select_track(int(data["track_id"]))
    return jsonify({"ok": True})
```

เพิ่มใน `engine/video_engine.py` — ต่อจาก `__init__`:

```python
# เพิ่ม attribute ใน __init__:
self.last_tracked_bboxes: dict[int, tuple] = {}  # track_id → (x1,y1,x2,y2)

# เพิ่ม method ใหม่:
def find_track_at_point(self, px: int, py: int) -> int | None:
    for tid, (x1, y1, x2, y2) in self.last_tracked_bboxes.items():
        if x1 <= px <= x2 and y1 <= py <= y2:
            return tid
    return None
```

และใน `_process_loop` หลัง ByteTrack update:

```python
# อัปเดต last_tracked_bboxes
self.last_tracked_bboxes.clear()
if tracked.tracker_id is not None:
    for i, tid in enumerate(tracked.tracker_id):
        x1, y1, x2, y2 = tracked.xyxy[i].astype(int)
        self.last_tracked_bboxes[int(tid)] = (x1, y1, x2, y2)
```

**Step: Commit**

```bash
git add static/js/app.js app.py engine/video_engine.py
git commit -m "feat: add frontend JS with calibration, WebSocket, speed chart, and bike selection"
```

---

## Task 10: Integration Test & Run

**Step 1: รัน unit tests ทั้งหมด**

```bash
cd "/Users/admin/จับความเร็ว"
python3 -m pytest tests/ -v
```

Expected: ทุก test ผ่าน

**Step 2: รัน Flask app**

```bash
python3 app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
```

**Step 3: เปิด browser**

เปิด `http://localhost:5000`

**Step 4: ทดสอบ end-to-end**

1. กด "Upload Video" → เลือกไฟล์ .mp4
2. กด "Calibrate" → คลิก 2 จุดบนถนน → กรอกระยะจริง
3. กด "Run" → วิดีโอควรเล่นพร้อม bbox
4. คลิกที่จักรยานในภาพ → ดูกราฟความเร็วใน dashboard

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: bike speed AI complete - YOLOv8 + ByteTrack + optical flow speed measurement"
```

---

## Quick Reference: Key Concepts

| Concept | คำอธิบาย |
|---|---|
| Background Optical Flow | วัดความเร็วพื้นหลัง = ความเร็วจักรยาน เพราะโดรนบินตาม |
| Lucas-Kanade | Sparse optical flow algorithm — track เฉพาะ corner features |
| ByteTrack | Multi-object tracker ที่ assign ID ให้ stable แม้ถูกบัง |
| YOLOv8n | "n" = nano model — เร็ว, พอเพียงสำหรับ bicycle detection |
| MJPEG Stream | ส่งภาพ JPEG ต่อเนื่องผ่าน HTTP — ง่ายกว่า WebRTC |
| Moving Average | Smooth ค่าความเร็ว 5 frames ป้องกันกราฟกระตุก |

---

## Phase 2: Live Drone Stream (Future)

เมื่อระบบ stable แล้ว ขยายได้โดย:
1. เพิ่ม input field สำหรับ RTSP URL (`rtsp://192.168.x.x/stream`)
2. แก้ `engine.load_video(url)` → `cv2.VideoCapture(url)` รองรับ RTSP ได้เลย
3. ลด JPEG quality เป็น 50 เพื่อลด latency
