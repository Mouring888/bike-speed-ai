"""End-to-end test: synthesise a panning video at a known speed and check the render."""
import csv

import cv2
import numpy as np

from render import parse_args, render

FPS, W, H = 30, 640, 360
PX_PER_FRAME = 5          # background shift per frame
PX_PER_M = 10             # calibration
EXPECTED_KMH = PX_PER_FRAME / PX_PER_M * FPS * 3.6   # = 54 km/h


def make_panning_video(path):
    rng = np.random.default_rng(0)
    texture = (rng.random((H, W + PX_PER_FRAME * 90)) * 255).astype(np.uint8)
    texture = cv2.GaussianBlur(texture, (5, 5), 0)
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(60):
        x = i * PX_PER_FRAME
        vw.write(cv2.cvtColor(texture[:, x:x + W], cv2.COLOR_GRAY2BGR))
    vw.release()


def test_render_recovers_known_speed(tmp_path):
    src = tmp_path / "in.mp4"
    out = tmp_path / "out"
    make_panning_video(src)

    stats = render(parse_args([str(src), "-o", str(out), "--px-per-m", str(PX_PER_M),
                               "--no-detect", "--smooth", "5"]))

    assert stats["frames"] == 60
    assert abs(stats["avg_kmh"] - EXPECTED_KMH) < EXPECTED_KMH * 0.15

    with open(f"{out}.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 60
    cap = cv2.VideoCapture(f"{out}.mp4")
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 60
