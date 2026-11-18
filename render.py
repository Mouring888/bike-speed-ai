"""
render.py — headless batch renderer (the sellable deliverable).

Takes a drone-follow cycling video and produces:
  * <out>.mp4  — the original footage with a broadcast-style speed graphic burned in
  * <out>.csv  — per-frame speed data (time_s, kmh) for editors / graphics systems

No browser, no clicking. Works without YOLO (--no-detect masks the frame centre,
where a follow-cam keeps the rider), so it runs on any laptop with only OpenCV.

Usage:
  python render.py input.mp4 --px-per-m 42.5 -o output
  python render.py input.mp4 --calib 100,200,500,200 --distance 10 -o output
"""
import argparse
import csv
import math
import sys

import cv2
import numpy as np

from engine.calibrator import Calibrator
from engine.optical_flow import OpticalFlowSpeedCalculator
from engine.speed_manager import SpeedManager


def build_calibrator(args) -> Calibrator:
    cal = Calibrator()
    if args.px_per_m:
        cal.set_point(0, (0, 0))
        cal.set_point(1, (args.px_per_m, 0))
        cal.set_real_distance(1.0)
    elif args.calib and args.distance:
        x0, y0, x1, y1 = (float(v) for v in args.calib.split(","))
        cal.set_point(0, (x0, y0))
        cal.set_point(1, (x1, y1))
        cal.set_real_distance(args.distance)
    else:
        sys.exit("Calibration required: --px-per-m N  or  --calib x0,y0,x1,y1 --distance M")
    return cal


def centre_mask_bbox(w: int, h: int, frac: float) -> tuple:
    """Follow-cam keeps the rider near the centre; exclude that box from flow."""
    bw, bh = int(w * frac), int(h * frac)
    return ((w - bw) // 2, (h - bh) // 2, (w + bw) // 2, (h + bh) // 2)


def draw_speed_graphic(frame, kmh: float, history: list, unit: str, max_speed: float):
    """Lower-third speed box + sparkline. Pure OpenCV so it runs anywhere."""
    h, w = frame.shape[:2]
    s = max(w / 1920, 0.5)  # scale relative to 1080p
    bx, by = int(40 * s), int(h - 190 * s)
    bw, bh = int(520 * s), int(150 * s)

    overlay = frame.copy()
    cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
    cv2.rectangle(frame, (bx, by), (bx + int(8 * s), by + bh), (0, 200, 255), -1)

    value = kmh if unit == "km/h" else kmh * 0.621371
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(frame, f"{value:5.1f}", (bx + int(28 * s), by + int(100 * s)),
                font, 2.6 * s, (255, 255, 255), max(2, int(4 * s)), cv2.LINE_AA)
    cv2.putText(frame, unit.upper(), (bx + int(30 * s), by + int(134 * s)),
                font, 0.8 * s, (0, 200, 255), max(1, int(2 * s)), cv2.LINE_AA)

    # sparkline of recent speed
    pts = history[-150:]
    if len(pts) > 1:
        gx0, gx1 = bx + int(270 * s), bx + bw - int(20 * s)
        gy0, gy1 = by + int(25 * s), by + bh - int(25 * s)
        top = max(max_speed, max(pts) * 1.1, 1e-6)
        poly = [
            (int(gx0 + (gx1 - gx0) * i / (len(pts) - 1)),
             int(gy1 - (gy1 - gy0) * min(v / top, 1.0)))
            for i, v in enumerate(pts)
        ]
        cv2.polylines(frame, [np.array(poly, np.int32)], False, (0, 200, 255),
                      max(1, int(2 * s)), cv2.LINE_AA)
    return frame


def render(args) -> dict:
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        sys.exit(f"Cannot open video: {args.input}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cal = build_calibrator(args)
    flow = OpticalFlowSpeedCalculator()
    sm = SpeedManager(calibrator=cal, fps=fps, window=args.smooth)

    detector = None
    if not args.no_detect:
        try:
            from engine.detector import BikeDetector
            detector = BikeDetector()
        except Exception as e:  # ultralytics/torch missing → fall back
            print(f"[render] detector unavailable ({e.__class__.__name__}); using centre mask")

    writer = cv2.VideoWriter(f"{args.output}.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    fallback_bbox = centre_mask_bbox(w, h, args.mask_frac)

    rows, frame_idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        bbox = fallback_bbox
        if detector is not None:
            dets = detector.detect(frame)
            if dets:
                bbox = max(dets, key=lambda d: d["confidence"])["bbox"]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kmh = sm.update(flow.update(gray, bbox))
        rows.append((round(frame_idx / fps, 3), kmh))
        writer.write(draw_speed_graphic(frame, kmh, sm.history, args.unit, args.max_speed))
        frame_idx += 1

    cap.release()
    writer.release()

    with open(f"{args.output}.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["time_s", "kmh"])
        wr.writerows(rows)

    speeds = [k for _, k in rows if k > 0]
    stats = {
        "frames": frame_idx,
        "avg_kmh": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
        "max_kmh": round(max(speeds), 2) if speeds else 0.0,
    }
    print(f"[render] {stats['frames']} frames → {args.output}.mp4 / .csv  "
          f"avg {stats['avg_kmh']} km/h, max {stats['max_kmh']} km/h")
    return stats


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Burn a speed graphic into drone cycling footage.")
    p.add_argument("input")
    p.add_argument("-o", "--output", default="speed_output", help="output path without extension")
    p.add_argument("--px-per-m", type=float, help="known pixels-per-metre at ground level")
    p.add_argument("--calib", help="two reference points x0,y0,x1,y1 (pixels)")
    p.add_argument("--distance", type=float, help="real distance between --calib points (m)")
    p.add_argument("--unit", choices=["km/h", "mph"], default="km/h")
    p.add_argument("--smooth", type=int, default=15, help="moving-average window (frames)")
    p.add_argument("--max-speed", type=float, default=60.0, help="sparkline scale (km/h)")
    p.add_argument("--mask-frac", type=float, default=0.3, help="centre mask size when no detector")
    p.add_argument("--no-detect", action="store_true", help="skip YOLO; mask frame centre")
    return p.parse_args(argv)


if __name__ == "__main__":
    render(parse_args())
