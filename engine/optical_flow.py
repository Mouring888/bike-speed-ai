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
        bike_bbox: Optional[tuple],
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

        # อัปเดต state — refresh points เมื่อเหลือน้อย
        if len(good_new) < 20:
            self._init_points(gray_frame, bike_bbox)
        else:
            self.prev_frame = gray_frame.copy()
            self.prev_points = good_new.reshape(-1, 1, 2)

        return median_disp

    def _init_points(
        self,
        gray_frame: np.ndarray,
        bike_bbox: Optional[tuple],
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
