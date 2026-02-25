// ══════════════════════════════════════════════
//  Bike Speed AI — Frontend Controller
// ══════════════════════════════════════════════

// ── DOM refs ──────────────────────────────────
const fileInput     = document.getElementById('fileInput');
const videoImg      = document.getElementById('videoImg');
const overlayCanvas = document.getElementById('overlayCanvas');
const ctx           = overlayCanvas.getContext('2d');
const btnCalib      = document.getElementById('btnCalib');
const btnRun        = document.getElementById('btnRun');
const btnStop       = document.getElementById('btnStop');
const statusBar     = document.getElementById('statusBar');
const calibHint     = document.getElementById('calibHint');
const speedDisplay  = document.getElementById('speedDisplay');
const selectedId    = document.getElementById('selectedId');
const statMax       = document.getElementById('statMax');
const statAvg       = document.getElementById('statAvg');
const statMin       = document.getElementById('statMin');
const calibInfo     = document.getElementById('calibInfo');

// ── App State ─────────────────────────────────
let calibMode    = false;
let calibPoints  = [];
let videoSize    = { w: 640, h: 480 };
let ws           = null;
let isRunning    = false;

// ── Chart.js Setup ────────────────────────────
const chart = new Chart(document.getElementById('speedChart'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'km/h',
      data: [],
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59,130,246,0.12)',
      borderWidth: 2,
      tension: 0.35,
      pointRadius: 0,
      fill: true,
    }]
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { display: false },
      y: {
        beginAtZero: true,
        ticks: { color: '#64748b', font: { size: 10 } },
        grid:  { color: '#1e293b' }
      }
    },
    plugins: { legend: { display: false } },
  }
});


// ══════════════════════════════════════════════
//  Upload Video
// ══════════════════════════════════════════════
fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;

  setStatus('⬆️ กำลังอัพโหลด... ' + file.name);
  const fd = new FormData();
  fd.append('video', file);

  try {
    const res  = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.ok) {
      videoImg.src    = '/video_feed?' + Date.now();
      videoImg.onload = syncCanvas;
      btnCalib.disabled = false;
      btnRun.disabled   = false;
      setStatus('✅ อัพโหลดสำเร็จ — กด 🎯 Calibrate แล้ว ▶ Run');
    } else {
      setStatus('❌ ' + (data.error || 'อัพโหลดล้มเหลว'));
    }
  } catch (e) {
    setStatus('❌ Network error: ' + e.message);
  }
});


// ══════════════════════════════════════════════
//  Calibration
// ══════════════════════════════════════════════
btnCalib.addEventListener('click', () => {
  calibMode   = true;
  calibPoints = [];
  ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  calibHint.style.display = 'block';
  calibHint.textContent   = '🎯 คลิกจุดที่ 1 บนภาพ (เช่น มุมเส้นกีฬา)';
  setStatus('🎯 Calibration Mode — คลิก 2 จุดที่รู้ระยะจริง');
});

overlayCanvas.addEventListener('click', async (e) => {
  if (!calibMode) {
    await handleBikeClick(e);
    return;
  }

  const pt = canvasToVideo(e.offsetX, e.offsetY);
  calibPoints.push(pt);
  drawCalibDot(e.offsetX, e.offsetY, calibPoints.length);

  if (calibPoints.length === 1) {
    calibHint.textContent = '🎯 คลิกจุดที่ 2 บนภาพ...';
  } else if (calibPoints.length >= 2) {
    calibHint.style.display = 'none';
    const dist = prompt(
      'ระยะห่างระหว่าง 2 จุดนี้ในความเป็นจริง (เมตร):\nเช่น เส้นกีฬาห่างกัน 3.66 เมตร',
      '3.66'
    );
    calibMode = false;
    if (!dist || isNaN(parseFloat(dist))) {
      setStatus('⚠️ ยกเลิก Calibration');
      return;
    }
    await sendCalibration(calibPoints[0], calibPoints[1], parseFloat(dist));
  }
});

async function sendCalibration(p0, p1, distM) {
  try {
    const res  = await fetch('/calibrate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ point0: p0, point1: p1, distance_m: distM }),
    });
    const data = await res.json();
    if (data.ok) {
      calibInfo.textContent = '✅ Calibrated\n' + data.px_per_m + ' px/m\nระยะอ้างอิง ' + distM + ' m';
      calibInfo.className   = 'done';
      setStatus('✅ Calibration เสร็จ — กด ▶ Run เพื่อเริ่มวิเคราะห์');
    }
  } catch (e) {
    setStatus('❌ Calibration error: ' + e.message);
  }
}


// ══════════════════════════════════════════════
//  Run / Stop
// ══════════════════════════════════════════════
btnRun.addEventListener('click', async () => {
  await fetch('/run', { method: 'POST' });
  isRunning        = true;
  btnStop.disabled = false;
  connectWebSocket();
  setStatus('● กำลังประมวลผล — คลิกจักรยานในภาพเพื่อเลือกติดตาม');
});

btnStop.addEventListener('click', async () => {
  await fetch('/stop', { method: 'POST' });
  isRunning        = false;
  btnStop.disabled = true;
  if (ws) { ws.close(); ws = null; }
  setStatus('⏹ หยุดแล้ว — กด ▶ Run เพื่อเริ่มใหม่');
});


// ══════════════════════════════════════════════
//  WebSocket — รับข้อมูล speed real-time
// ══════════════════════════════════════════════
function connectWebSocket() {
  if (ws) ws.close();
  ws = new WebSocket('ws://' + location.host + '/ws');

  ws.onopen    = () => console.log('[WS] connected');
  ws.onclose   = () => console.log('[WS] disconnected');
  ws.onerror   = () => setStatus('⚠️ WebSocket error — ลอง refresh');

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === 'speed') updateDashboard(msg);
    } catch (_) {}
  };
}

function updateDashboard({ track_id, kmh, history }) {
  selectedId.textContent   = '#' + track_id;
  speedDisplay.textContent = kmh.toFixed(1);
  speedDisplay.className   = 'speed-big' + (kmh > 40 ? ' fast' : '');

  if (!history || history.length === 0) return;

  const mx  = Math.max(...history);
  const mn  = Math.min(...history);
  const avg = history.reduce((a, b) => a + b, 0) / history.length;
  statMax.textContent = mx.toFixed(1);
  statMin.textContent = mn.toFixed(1);
  statAvg.textContent = avg.toFixed(1);

  chart.data.labels           = history.map((_, i) => i);
  chart.data.datasets[0].data = history;
  chart.update('none');
}


// ══════════════════════════════════════════════
//  Click-to-Select Bike
// ══════════════════════════════════════════════
async function handleBikeClick(e) {
  if (!isRunning) return;
  const pt = canvasToVideo(e.offsetX, e.offsetY);
  try {
    const res  = await fetch('/select_track', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ point: pt }),
    });
    const data = await res.json();
    if (data.ok && data.track_id != null) {
      setStatus('🎯 เลือก Bike #' + data.track_id + ' แล้ว — ดูกราฟด้านขวา');
    } else {
      setStatus('⚠️ ไม่พบจักรยานตรงจุดที่คลิก — ลองคลิกบน bounding box');
    }
  } catch (err) {
    console.error(err);
  }
}


// ══════════════════════════════════════════════
//  Helpers
// ══════════════════════════════════════════════

/** แปลง canvas click → video coordinate จริง (คำนึง object-fit: contain) */
function canvasToVideo(cx, cy) {
  const rect       = overlayCanvas.getBoundingClientRect();
  const imgAspect  = videoSize.w / videoSize.h;
  const canvAspect = rect.width  / rect.height;

  let drawW, drawH, offX = 0, offY = 0;
  if (imgAspect > canvAspect) {
    drawW = rect.width;
    drawH = rect.width / imgAspect;
    offY  = (rect.height - drawH) / 2;
  } else {
    drawH = rect.height;
    drawW = rect.height * imgAspect;
    offX  = (rect.width - drawW) / 2;
  }

  const vx = Math.round(((cx - offX) / drawW) * videoSize.w);
  const vy = Math.round(((cy - offY) / drawH) * videoSize.h);
  return [
    Math.max(0, Math.min(videoSize.w - 1, vx)),
    Math.max(0, Math.min(videoSize.h - 1, vy)),
  ];
}

/** วาดจุด calibration บน canvas overlay */
function drawCalibDot(x, y, n) {
  ctx.beginPath();
  ctx.arc(x, y, 7, 0, Math.PI * 2);
  ctx.fillStyle   = '#f59e0b';
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth   = 2;
  ctx.stroke();
  ctx.fillStyle = '#fff';
  ctx.font      = 'bold 13px sans-serif';
  ctx.fillText(String(n), x + 10, y - 6);
}

/** sync canvas size กับ element */
function syncCanvas() {
  overlayCanvas.width  = overlayCanvas.offsetWidth;
  overlayCanvas.height = overlayCanvas.offsetHeight;
  if (videoImg.naturalWidth > 0) {
    videoSize.w = videoImg.naturalWidth;
    videoSize.h = videoImg.naturalHeight;
  }
}

/** แสดง status text (plain text เท่านั้น) */
function setStatus(text) {
  statusBar.textContent = text;
}

// ── Init ──────────────────────────────────────
window.addEventListener('resize', syncCanvas);
window.addEventListener('load',   syncCanvas);
