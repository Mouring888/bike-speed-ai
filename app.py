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
_latest_frame: bytes = b""


# ── Callbacks จาก VideoEngine ─────────────────────────────────
def on_frame(jpeg_bytes: bytes):
    global _latest_frame
    _latest_frame = jpeg_bytes


def on_speed(track_id: int, kmh: float, history: list):
    payload = json.dumps({
        "type": "speed",
        "track_id": track_id,
        "kmh": round(kmh, 2),
        "history": history,
    })
    dead = []
    for ws in list(_ws_clients):
        try:
            ws.send(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_clients:
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
    engine.stop()
    time.sleep(0.2)
    engine.load_video(path)
    return jsonify({"ok": True, "message": "อัพโหลดสำเร็จ"})


@app.route("/calibrate", methods=["POST"])
def calibrate():
    data = request.json
    engine.calibrator.reset()
    engine.calibrator.set_point(0, tuple(data["point0"]))
    engine.calibrator.set_point(1, tuple(data["point1"]))
    engine.calibrator.set_real_distance(float(data["distance_m"]))
    return jsonify({"ok": True, "px_per_m": round(engine.calibrator.pixels_per_meter, 2)})


@app.route("/run", methods=["POST"])
def run():
    engine.stop()
    time.sleep(0.3)
    engine.start()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop_engine():
    engine.stop()
    return jsonify({"ok": True})


@app.route("/select_track", methods=["POST"])
def select_track():
    data = request.json
    if "point" in data:
        px, py = data["point"]
        track_id = engine.find_track_at_point(int(px), int(py))
        if track_id is not None:
            engine.select_track(track_id)
            return jsonify({"ok": True, "track_id": track_id})
        return jsonify({"ok": False, "message": "ไม่พบจักรยานตรงตำแหน่งนี้"})
    engine.select_track(int(data["track_id"]))
    return jsonify({"ok": True})


@app.route("/video_feed")
def video_feed():
    """MJPEG stream — browser เรียกผ่าน <img src="/video_feed">"""
    def generate():
        while True:
            if _latest_frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + _latest_frame
                    + b"\r\n"
                )
            time.sleep(0.033)  # ~30fps

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@sock.route("/ws")
def websocket(ws):
    _ws_clients.append(ws)
    try:
        while True:
            msg = ws.receive(timeout=60)
            if msg is None:
                break
    except Exception:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=False, host="0.0.0.0", port=5001, threaded=True)
