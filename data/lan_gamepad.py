"""
LAN Gamepad Server for Songoku 7
- Run this script on the PC that is running the game.
- Open the displayed LAN URL on phones/tablets connected to the same Wi-Fi.
- Select Player 1 or Player 2. Hold buttons to hold keys; release to release keys.

Install:
    py -m pip install flask flask-socketio pynput

Run:
    py lan_gamepad.py
"""

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
from pynput.keyboard import Controller, Key, KeyCode
import socket
import threading

app = Flask(__name__)
app.config["SECRET_KEY"] = "lan-gamepad-local"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
keyboard = Controller()
key_lock = threading.Lock()

# Keys the game uses. The browser sends only these allow-listed key names.
KEY_MAP = {
    "a": "a", "w": "w", "s": "s", "d": "d",
    "j": "j", "k": "k", "l": "l", "u": "u", "i": "i", "o": "o",
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    # Người chơi 2: gửi cả phím số hàng trên lẫn bàn phím số (Numpad) để game nào cũng nhận.
    "1": ("1", KeyCode.from_vk(0x61)), "2": ("2", KeyCode.from_vk(0x62)),
    "3": ("3", KeyCode.from_vk(0x63)), "4": ("4", KeyCode.from_vk(0x64)),
    "5": ("5", KeyCode.from_vk(0x65)), "6": ("6", KeyCode.from_vk(0x66)),
}


def hw_press(key_name):
    keys = KEY_MAP[key_name]
    for k in keys if isinstance(keys, tuple) else (keys,):
        keyboard.press(k)


def hw_release(key_name):
    keys = KEY_MAP[key_name]
    for k in keys if isinstance(keys, tuple) else (keys,):
        keyboard.release(k)

# Track pressed keys by socket so disconnecting a phone cannot leave keys stuck.
pressed_by_sid = {}


def get_lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def press_key(key_name):
    if key_name not in KEY_MAP:
        return
    with key_lock:
        hw_press(key_name)


def release_key(key_name):
    if key_name not in KEY_MAP:
        return
    with key_lock:
        hw_release(key_name)


@app.route("/")
def index():
    return render_template_string(PAGE)


@socketio.on("key_down")
def on_key_down(data):
    key_name = str((data or {}).get("key", "")).lower()
    if key_name not in KEY_MAP:
        return
    sid = request.sid
    with key_lock:
        already_pressed = key_name in pressed_by_sid.setdefault(sid, set())
        if not already_pressed:
            pressed_by_sid[sid].add(key_name)
            hw_press(key_name)
            print(f"[key_down] {key_name}")
    emit("status", {"text": "Đã kết nối · đang điều khiển"}, to=sid)


@socketio.on("key_up")
def on_key_up(data):
    key_name = str((data or {}).get("key", "")).lower()
    if key_name not in KEY_MAP:
        return
    sid = request.sid
    with key_lock:
        # Release the physical key only if no other phone/socket is holding it.
        if sid in pressed_by_sid:
            pressed_by_sid[sid].discard(key_name)
        still_held = any(key_name in keys for keys in pressed_by_sid.values())
        if not still_held:
            hw_release(key_name)
            print(f"[key_up]   {key_name}")


@socketio.on("release_all")
def on_release_all():
    sid = request.sid
    with key_lock:
        keys = pressed_by_sid.pop(sid, set())
        for key_name in keys:
            if not any(key_name in other for other in pressed_by_sid.values()):
                hw_release(key_name)


@socketio.on("disconnect")
def on_disconnect():
    on_release_all()


PAGE = r"""
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#000000">
<title>Controller</title>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<style>
:root { color-scheme: dark; --bg:#000; --fg:#fff; --line:#555; --panel:#111; --vh:100dvh; --vw:100vw; --pad:min(calc(var(--vh) - 16px), calc(var(--vw) * 0.36)); }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html,body { -webkit-touch-callout:none; -webkit-user-select:none; user-select:none; width:100%; height:100%; margin:0; background:var(--bg); color:var(--fg); font-family:Arial,sans-serif; overflow:hidden; touch-action:manipulation; }
body { min-height:100dvh; }
#choose { width:100%; height:100%; display:flex; flex-direction:column; gap:12px; align-items:center; justify-content:center; }
.choice { width:min(260px,80vw); padding:14px 20px; text-align:center; border:1px solid #777; color:#fff; background:#111; font-size:18px; font-weight:600; user-select:none; cursor:pointer; }
.choice:active { background:#fff; color:#000; }
#controller { display:none; width:100%; height:var(--vh); padding: max(8px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left)); gap:10px; }
#controller.active { display:flex; flex-direction:column; }
.padrow { display:flex; align-items:center; justify-content:space-between; gap:10px; flex:1; min-height:0; }
.side { display:flex; flex-direction:column; justify-content:center; flex:none; width:var(--pad); }
.mid { flex:1; display:flex; align-items:center; justify-content:center; min-width:0; }
#status { color:#f33; font-size:clamp(24px,calc(var(--vh) * 0.1),48px); font-weight:700; text-align:center; user-select:none; }
#status.ok { color:#2e6; }
.dpad { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); grid-template-rows:repeat(3,minmax(0,1fr)); gap:clamp(5px,1.5vw,12px); width:var(--pad); height:var(--pad); }
.key { min-width:0; min-height:0; border:1px solid #777; background:var(--panel); color:#fff; border-radius:0; font-size:clamp(16px,calc(var(--vh) * 0.06),36px); font-weight:600; touch-action:none; user-select:none; }
.key:active,.key.down { background:#fff; color:#000; }
.blank { visibility:hidden; }
.actiongrid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); grid-template-rows:repeat(2,minmax(0,1fr)); gap:clamp(5px,1.5vw,12px); width:var(--pad); height:calc(var(--pad) * 0.62); }
.actiongrid .key { font-size:clamp(16px,calc(var(--vh) * 0.07),36px); }
/* Máy đang cầm dọc: xoay giao diện 90° để luôn hiển thị nằm ngang */
@media (orientation:portrait) {
  :root { --vh:100vw; --vw:100dvh; }
  #controller.active { position:fixed; top:0; left:0; width:100dvh; height:100vw; transform-origin:top left; transform:translateX(100vw) rotate(90deg); }
}
</style>
</head>
<body>
<div id="choose">
  <button class="choice" data-player="1">Người chơi 1</button>
  <button class="choice" data-player="2">Người chơi 2</button>
</div>
<div id="controller">
  <div class="padrow">
    <section class="side"><div class="dpad" id="dpad"></div></section>
    <div class="mid"><div id="status">P1</div></div>
    <section class="side"><div class="actiongrid" id="actions"></div></section>
  </div>
</div>
<script>
const socket = io();
const statusEl = document.getElementById('status');
let player = 1;
let connected = false;
function updateStatus() {
  statusEl.textContent = 'P' + player;
  statusEl.classList.toggle('ok', connected);
}
socket.on('connect', () => { connected = true; updateStatus(); });
socket.on('disconnect', () => { connected = false; updateStatus(); });
const dpad = document.getElementById('dpad');
const actions = document.getElementById('actions');
const activeButtons = new Map();

async function enterFullscreenLandscape() {
  try {
    if (screen.orientation && screen.orientation.lock) {
      await screen.orientation.lock('landscape');
    }
  } catch (_) {}
  try {
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
    }
  } catch (_) {}
}
function releaseAllLocal() {
  socket.emit('release_all');
  activeButtons.clear();
  document.querySelectorAll('.key.down').forEach(b => b.classList.remove('down'));
}
function makeButton(label, key, blank=false) {
  const b = document.createElement('button');
  b.className = 'key' + (blank ? ' blank' : '');
  b.textContent = label;
  b.dataset.key = key;
  const down = e => {
    e.preventDefault();
    if (blank || b.classList.contains('down')) return;
    b.classList.add('down');
    try { b.setPointerCapture(e.pointerId); } catch (_) {}
    const count = (activeButtons.get(key) || 0) + 1;
    activeButtons.set(key, count);
    if (count === 1) socket.emit('key_down', {key});
  };
  const up = e => {
    e.preventDefault();
    if (blank || !b.classList.contains('down')) return;
    b.classList.remove('down');
    const count = Math.max(0, (activeButtons.get(key) || 1) - 1);
    if (!count) {
      activeButtons.delete(key);
      socket.emit('key_up', {key});
    } else activeButtons.set(key, count);
  };
  b.addEventListener('pointerdown', down);
  ['pointerup','pointercancel','lostpointercapture'].forEach(ev => b.addEventListener(ev, up));
  // Giữ lâu trên điện thoại sinh contextmenu: chỉ chặn menu, không nhả phím
  b.addEventListener('contextmenu', e => e.preventDefault());
  return b;
}
function render() {
  updateStatus();
  dpad.innerHTML = '';
  actions.innerHTML = '';
  const dirs = player === 1
    ? [['','',true],['W','w'],['','',true],['A','a'],['','',true],['D','d'],['','',true],['S','s'],['','',true]]
    : [['','',true],['↑','up'],['','',true],['←','left'],['','',true],['→','right'],['','',true],['↓','down'],['','',true]];
  dirs.forEach(([label,key,blank]) => dpad.append(makeButton(label,key,blank)));
  const controls = player === 1
    ? [['J','j'],['K','k'],['L','l'],['U','u'],['I','i'],['O','o']]
    : [['1','1'],['2','2'],['3','3'],['4','4'],['5','5'],['6','6']];
  controls.forEach(([label,key]) => actions.append(makeButton(label,key)));
}
document.querySelectorAll('.choice').forEach(btn => btn.addEventListener('click', async () => {
  player = Number(btn.dataset.player);
  document.getElementById('choose').style.display = 'none';
  document.getElementById('controller').classList.add('active');
  render();
  await enterFullscreenLandscape();
}));
// Đã thoát toàn màn hình: chạm vào bất kỳ đâu sẽ vào lại toàn màn hình
document.addEventListener('pointerup', () => {
  if (document.getElementById('controller').classList.contains('active') && !document.fullscreenElement) {
    enterFullscreenLandscape();
  }
});
window.addEventListener('blur', releaseAllLocal);
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAllLocal(); });
window.addEventListener('pagehide', releaseAllLocal);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    ip = get_lan_ip()
    print("\n=== Songoku 7 LAN Gamepad ===")
    print("Mo tren PC:  http://127.0.0.1:5000")
    print(f"Mo tren dien thoai cung Wi-Fi: http://{ip}:5000")
    print("Nhan Ctrl+C de dung server.\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
