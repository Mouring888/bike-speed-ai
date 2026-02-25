# Bike Speed AI — Design Document
**Date:** 2026-02-25
**Status:** Approved

---

## Overview

Web application สำหรับวัดความเร็วจักรยานจากวิดีโอโดรน (top-down view) โดยใช้ YOLOv8n detection, ByteTrack tracking และ Lucas-Kanade Optical Flow สำหรับคำนวณความเร็ว แสดงผลแบบ real-time ผ่าน browser พร้อม interactive canvas และกราฟความเร็วตามเวลา

---

## Architecture

```
Browser (Frontend)
  ├── Upload Panel (.mp4)
  ├── Video Canvas + BBox Overlay (click to select bike)
  └── Speed Dashboard (Chart.js speed graph)
        │
        │ HTTP POST (upload) + WebSocket (stream + speed data)
        ▼
Flask Backend (Python)
  ├── /upload endpoint
  ├── VideoEngine (background thread)
  │     └── Processing Pipeline:
  │           Frame → YOLOv8n → ByteTrack → Optical Flow → Speed → Overlay → Stream
  └── /ws WebSocket (broadcast speed data to browser)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Detection | YOLOv8n (ultralytics) — class "bicycle" from COCO |
| Tracking | ByteTrack (via supervision library) |
| Speed Measurement | Lucas-Kanade sparse optical flow (OpenCV) |
| Backend | Flask + flask-sock (WebSocket) |
| Video Streaming | MJPEG stream over HTTP |
| Frontend | Vanilla JS + Canvas API + Chart.js |

---

## Speed Calculation — Background Optical Flow

เนื่องจากโดรนบินตามจักรยาน จักรยานจึงดูค่อนข้างนิ่งในภาพ แต่พื้นหลังเคลื่อนที่

```
1. Shi-Tomasi corner detection บนพื้นหลัง (นอก bicycle bbox)
2. Lucas-Kanade optical flow ติดตามจุด feature ข้าม frame
3. คำนวณ median displacement (dx, dy) ของจุดพื้นหลัง
4. pixel_speed = √(dx² + dy²) per frame
5. meter_speed = pixel_speed × (m/pixel calibration ratio)
6. km/h = meter_speed × fps × 3.6
7. Moving average 5 frames เพื่อ smooth ค่า
```

**Calibration:** ผู้ใช้คลิก 2 จุดบนภาพ (เช่น เส้นสนาม) แล้วกรอกระยะทางจริง (เมตร)

---

## File Structure

```
bike-speed-ai/
├── app.py                  # Flask server + WebSocket + routes
├── engine/
│   ├── detector.py         # YOLOv8n wrapper
│   ├── tracker.py          # ByteTrack wrapper
│   ├── optical_flow.py     # Lucas-Kanade speed calculation
│   ├── calibrator.py       # Pixel→Meter conversion + calibration state
│   └── video_engine.py     # Processing pipeline (background thread)
├── static/
│   ├── js/app.js           # UI logic, WebSocket client, canvas interaction
│   └── js/chart.js         # Chart.js speed graph initialization
├── templates/
│   └── index.html          # Single page UI
├── uploads/                # Temp video storage
└── requirements.txt
```

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🚴 Bike Speed AI          [Upload Video]  [Calibrate] [▶ Run] │
├───────────────────────────────────────┬─────────────────────────┤
│        VIDEO CANVAS                   │  📊 Speed Dashboard     │
│   [Bike #1] 28.3 km/h (yellow bbox)  │  Selected: Bike #2      │
│   [Bike #2] 42.1 km/h (blue bbox)    │  ┌─────────────────┐   │
│                                       │  │   42  km/h      │   │
│   🎯 Calibration: click 2 points     │  └─────────────────┘   │
│      on known distance                │  Speed Graph (Chart.js) │
│                                       │  Max / Avg / Min        │
│                                       │  [Export CSV]           │
└───────────────────────────────────────┴─────────────────────────┘
```

**Color coding:**
- 🟡 Yellow bbox = unselected bikes
- 🔵 Blue bbox = selected bike (tracked)
- 🔴 Red speed label = speed > 40 km/h

---

## Interaction Flow

1. อัพโหลด .mp4 (max 500MB)
2. กด [Calibrate] → คลิก 2 จุดบน canvas → กรอกระยะจริง (เมตร)
3. กด [▶ Run] → pipeline เริ่มทำงาน
4. คลิกที่ bbox ของจักรยานใน canvas → เลือก track นั้น
5. Dashboard แสดง speed history ของจักรยานที่เลือก

---

## Error Handling

| สถานการณ์ | การรับมือ |
|---|---|
| ไม่พบจักรยาน | แสดง "No bike detected", กราฟหยุดชั่วคราว |
| Optical flow feature น้อย | ใช้ speed = 0, flag "Low confidence" |
| Speed spike > 150 km/h | ตัดทิ้ง (unrealistic) |
| FPS < 10 | แจ้งเตือนผู้ใช้ว่าความแม่นยำลดลง |
| ไฟล์ > 500MB | Reject ก่อน upload |

---

## Known Limitations

- ความแม่นยำขึ้นอยู่กับคุณภาพ calibration
- โดรนหมุน/เอียงฉับพลันทำให้ค่าผิดพลาดชั่วคราว
- ต้องการแสงสว่างเพียงพอสำหรับ optical flow
- วิดีโอควรมีความละเอียด ≥ 720p

---

## Future: Live Stream Extension

Phase 2 จะเพิ่ม:
- รับ RTSP stream จากโดรนโดยตรง (`cv2.VideoCapture("rtsp://...")`)
- WebRTC สำหรับ latency ต่ำ
- เปลี่ยน source จาก file upload เป็น live feed URL
