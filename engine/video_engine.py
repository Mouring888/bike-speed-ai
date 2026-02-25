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

        self._cap = None
        self._thread = None
        self._running = False

        # State
        self.fps: float = 30.0
        self.selected_track_id = None
        self.speed_managers: dict = {}
        self.last_tracked_bboxes: dict = {}  # track_id → (x1,y1,x2,y2)

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
        self.last_tracked_bboxes.clear()

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

    def find_track_at_point(self, px: int, py: int):
        """หา track_id ที่ bbox ครอบคลุม point ที่คลิก"""
        for tid, (x1, y1, x2, y2) in self.last_tracked_bboxes.items():
            if x1 <= px <= x2 and y1 <= py <= y2:
                return tid
        return None

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

            # 4. อัปเดต last_tracked_bboxes สำหรับ click-to-select
            self.last_tracked_bboxes.clear()
            if tracked.tracker_id is not None:
                for i, tid in enumerate(tracked.tracker_id):
                    x1, y1, x2, y2 = tracked.xyxy[i].astype(int)
                    self.last_tracked_bboxes[int(tid)] = (x1, y1, x2, y2)

            # 5. Optical flow — ใช้ bbox ของ selected bike (ถ้ามี)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            selected_bbox = self._get_selected_bbox(tracked)
            pixel_disp = self.flow_calc.update(gray, selected_bbox)

            # 6. Speed calculation สำหรับ selected track
            if self.selected_track_id is not None:
                sm = self._get_speed_manager(self.selected_track_id)
                kmh = sm.update(pixel_disp)
                if self.on_speed:
                    self.on_speed(self.selected_track_id, kmh, sm.history[-100:])

            # 7. วาด overlay
            frame = self._draw_overlay(frame, tracked, label_annotator, annotator)

            # 8. Encode เป็น JPEG ส่ง callback
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

    def _draw_overlay(self, frame, tracked, label_annotator, annotator):
        if tracked.tracker_id is None:
            return frame

        labels = []
        for i, tid in enumerate(tracked.tracker_id):
            sm = self.speed_managers.get(int(tid))
            kmh = sm.history[-1] if sm and sm.history else 0.0
            prefix = "★ " if int(tid) == self.selected_track_id else ""
            labels.append(f"{prefix}Bike #{tid}  {kmh:.1f} km/h")

        frame = annotator.annotate(frame, tracked)
        frame = label_annotator.annotate(frame, tracked, labels=labels)
        return frame
