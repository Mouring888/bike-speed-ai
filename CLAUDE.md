# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this project is

**Bike Speed AI** — a single-page Flask web app that measures the speed of a bicycle
in a top-down **drone video** (`.mp4`). The user uploads a video, calibrates a
pixel→meter scale by clicking two points of known real-world distance, then runs a
background pipeline that detects bikes, tracks them, and computes speed in km/h,
streaming the annotated video (MJPEG) and live speed data (WebSocket) to the browser.

**Key insight behind the speed math:** the drone *follows* the bike, so the bike looks
nearly stationary in frame while the **background** moves. Speed is therefore measured
from the optical flow of background features (outside the bike's bbox), not from the
bike's own pixel motion.

## Tech stack

| Layer | Choice |
|---|---|
| Detection | YOLOv8n via `ultralytics`, COCO class `1` = bicycle (no retraining) |
| Tracking | ByteTrack via `supervision` (`sv.ByteTrack`) |
| Speed | Lucas-Kanade sparse optical flow (OpenCV) on background corners |
| Backend | Flask + `flask-sock`, one background processing thread |
| Video transport | MJPEG over HTTP (`multipart/x-mixed-replace`) |
| Frontend | Vanilla JS + Canvas API + Chart.js (CDN) |
| Python | 3.11 (dev env was a conda env named `gold_ai`) |

`numpy` is pinned `<2.0` in `requirements.txt` because torch 2.2.x requires it — do not
bump it without also checking the torch version pulled in by `ultralytics`.

## Layout

```
app.py                    Flask routes, WebSocket hub, MJPEG generator, engine callbacks
engine/
  detector.py             BikeDetector — YOLOv8n wrapper, filters to bicycle + conf threshold
  optical_flow.py         OpticalFlowSpeedCalculator — LK flow on background, px/frame
  calibrator.py           Calibrator — 2 points + real distance → pixels_per_meter
  speed_manager.py        SpeedManager — px/frame → km/h, moving average, history
  video_engine.py         VideoEngine — the pipeline thread that wires it all together
templates/index.html      Whole UI (inline CSS), dark dashboard layout
static/js/app.js          Frontend controller: upload, calibration, WS, chart, click-to-select
tests/                    pytest unit tests, one file per engine module
uploads/                  Uploaded video lands here as current.mp4 (gitignored)
docs/plans/               Design doc + the task-by-task implementation plan
```

## Pipeline (`VideoEngine._process_loop`)

Per frame, in order:

1. `detector.detect(frame)` → list of `{"bbox": (x1,y1,x2,y2), "confidence": float}`
2. Convert to `sv.Detections` (all `class_id = 1`)
3. `tracker.update_with_detections(...)` → stable `tracker_id` per bike
4. Refresh `last_tracked_bboxes` (`track_id → bbox`) — this is what click-to-select queries
5. `flow_calc.update(gray, selected_bbox)` → median background displacement in px/frame
6. If a track is selected: `SpeedManager.update(px)` → km/h, fire `on_speed` callback
7. Draw box + label overlay (`★` prefix marks the selected bike)
8. JPEG-encode (quality 70) and fire `on_frame` callback
9. `time.sleep(1 / fps)` to pace playback

`app.py` sets `engine.on_frame` / `engine.on_speed` at import time: frames go into a
module-level `_latest_frame` that `/video_feed` re-serves at ~30fps; speed payloads are
JSON-broadcast to every socket in `_ws_clients`.

## HTTP / WS API

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Renders `templates/index.html` |
| `/upload` | POST | multipart `video` field, `.mp4` only, ≤500MB → saved as `uploads/current.mp4` |
| `/calibrate` | POST | JSON `{point0, point1, distance_m}` → returns `px_per_m` |
| `/run` | POST | Stops any running thread, then starts the pipeline |
| `/stop` | POST | Sets the cooperative stop flag |
| `/select_track` | POST | JSON `{point: [x,y]}` (hit-test) or `{track_id: n}` |
| `/video_feed` | GET | MJPEG stream consumed by `<img src="/video_feed">` |
| `/ws` | WS | Server→client only: `{type:"speed", track_id, kmh, history}` |

Client-sent WebSocket messages are ignored — the socket exists purely for the server
to push speed updates.

## Development workflow

```bash
# deps (they are NOT preinstalled in fresh containers)
pip install -r requirements.txt
pip install pytest            # dev-only, deliberately not in requirements.txt

python3 -m pytest tests/ -v   # run from the repo root
python3 app.py                # → http://localhost:5001
```

**Always run commands from the repository root.** Modules import absolutely
(`from engine.calibrator import Calibrator`), so a different cwd breaks both the app and
the tests.

The server binds **port 5001**, not 5000 — macOS AirPlay Receiver occupies 5000. Keep it
that way unless the user asks otherwise.

`yolov8n.pt` (~6MB) is downloaded automatically by `ultralytics` on first detector
construction. Model weights (`*.pt`, `*.onnx`) and uploaded videos are gitignored; never
commit them.

## Testing conventions

- Pure-logic modules (`Calibrator`, `SpeedManager`, `OpticalFlowSpeedCalculator`) are
  tested directly — no mocks, no fixtures, plain `assert` with float tolerances.
- `BikeDetector` tests mock the model: `patch("engine.detector.YOLO")`, then set
  `mock_yolo.return_value.return_value = [mock_result]` with
  `mock_result.boxes.data` as an `(N, 6)` array of `[x1, y1, x2, y2, conf, cls_id]`.
  Follow this shape rather than loading real weights — tests must stay offline and fast.
- Optical flow tests build synthetic grayscale frames with injected corner patterns
  (see `make_gray_frame` in `tests/test_optical_flow.py`).
- `VideoEngine` and the Flask routes have no automated tests; they are verified by the
  manual end-to-end run (upload → calibrate → run → click a bike).

## Code conventions

- **Bilingual by design:** identifiers, class names, and commit messages are English;
  docstrings, inline comments, UI strings, and API error messages are **Thai**. Match the
  surrounding style — write new comments and user-facing strings in Thai.
- Section separators in the style `# ── Section ──────────` (Python) and
  `// ═══ Section ═══` (JS) are used in `app.py` and `app.js`; keep them consistent.
- Type hints on public method signatures; docstrings are one-to-three Thai lines.
- Each engine class owns a `reset()` where it has mutable state; the pipeline calls these
  on `load_video`.
- Frontend is dependency-free apart from the Chart.js CDN tag. No build step, no bundler,
  no framework — do not introduce one.
- Status text is set via `setStatus()` with `textContent` (never `innerHTML`).

## Commits and branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:` — one logical unit per commit
  (see `git log`; the whole project was built one module at a time).
- Work on the feature branch assigned for the task; push with
  `git push -u origin <branch>` and open a **draft** PR.

## Known gotchas and rough edges

- **Single global engine.** `app.py` creates one `VideoEngine` at import; the app is
  effectively single-user/single-video. Uploads always overwrite `uploads/current.mp4`.
- **Cooperative stop.** `engine.stop()` only clears `_running`; routes `time.sleep(...)`
  briefly to let the thread exit before restarting. Don't assume the thread is dead the
  instant `stop()` returns.
- **Speed only for the selected track.** A `SpeedManager` is created lazily per track, but
  only the selected one is fed; other bikes show `0.0 km/h` in their labels until selected.
- **One shared flow calculator.** `OpticalFlowSpeedCalculator` is global to the engine and
  masks out only the selected bike's bbox, so unselected bikes still sit on background
  features.
- **`history` grows unbounded** in `SpeedManager`; only the last 100 samples are sent over
  the WebSocket. Long videos will accumulate memory.
- **WebSocket URL is hardcoded `ws://`** in `app.js` — it will fail over HTTPS.
- **Doc drift:** the design doc lists `engine/tracker.py` and `static/js/chart.js`, and the
  plan says Python 3.13 / `numpy>=2.2`. None of those match the built code — ByteTrack is
  used inline in `video_engine.py`, the chart lives in `app.js`, and the runtime is 3.11
  with `numpy<2.0`. Trust the code over `docs/plans/`.
- Accuracy depends entirely on calibration quality; sudden drone rotation, low light, or
  sub-720p footage degrade results. Speeds above `max_speed_px` (150 px/frame) are
  discarded as spikes.

## Not yet implemented

The design doc's "Export CSV" button and the Phase 2 live RTSP stream do not exist. RTSP
would mostly be a matter of passing a `rtsp://` URL to `engine.load_video()` since
`cv2.VideoCapture` accepts it, plus a UI field for the URL.
