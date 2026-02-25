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

    def detect(self, bgr_frame: np.ndarray) -> list:
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
