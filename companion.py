"""
companion.py — ambient-aware desktop robot
requires: pip install pillow sounddevice numpy psutil pywin32
sprites go in ./sprites/ folder
right-click to close
"""

import tkinter as tk
from PIL import Image, ImageTk
import random
import datetime
import os
import threading
import time
import psutil

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False

try:
    import win32gui
    import win32process
    WIN_AVAILABLE = True
except Exception:
    WIN_AVAILABLE = False

# ── config ─────────────────────────────────────────────────────────────────────
SPRITE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
SPRITE_SIZE  = 223
BUBBLE_MS    = 4000
AUDIO_THRESH = 0.015
IDLE_MINUTES = 10

# game process detection — reads local process list only, no network calls
GAME_PROCESS_HINTS = [
    "gameoverlayui.exe",       # Steam overlay = game is running
    "steamwebhelper.exe",      # Steam is open
    "easyanticheat.exe",
    "epicgameslauncher.exe",
    "unrealcefsubprocess.exe",
    "galaxyclient.exe",        # GOG
]

GAME_KEYWORDS    = ["game","steam","epic","roblox","minecraft","godot","unity",
                    "itch","rpg","overwatch","valorant","league","fortnite",
                    "genshin","hollow","celeste","stardew","cookie"]
CODE_KEYWORDS    = ["code","vscode","visual studio","cursor","pycharm",
                    "jetbrains","sublime","notepad++","vim","neovim"]
BROWSER_KEYWORDS = ["chrome","firefox","edge","opera","brave","safari"]

MESSAGES = {
    "morning":   ["good morning! ☀️","rise and grind i guess",
                  "coffee first. everything else second.","gm gm gm",
                  "today is going to be ok"],
    "afternoon": ["how's it going?","don't forget to drink water",
                  "you're doing great","take a break maybe?",
                  "still here. still watching."],
    "evening":   ["almost done for the day!","proud of you tbh",
                  "what did you make today?","evening vibes only",
                  "wind down soon ok?"],
    "night":     ["you should sleep...","it's late. just saying.",
                  "zzzz... oh! still here","night owl detected",
                  "go to bed. please."],
}

GAME_MSGS    = ["ooh are we gaming??","let's GOOOO","no thoughts, only game",
                "i believe in you","don't die 🎮","steam detected 👀",
                "let him cook 🎮"]
CODE_MSGS    = ["still coding huh","you got this","one more bug right?",
                "i see you grinding","ship it 🚀"]
MUSIC_MSGS   = ["🎵 bop","this slaps","i feel it","🎶✨","vibing rn",
                "ok this goes hard"]
DRAG_MSGS    = ["wheeee","put me down!!","wooooah","hey!!","weeee :D"]
IDLE_MSGS    = ["...hello?","you still there?","i'm bored",
                "knock knock","*taps screen*"]
RETURN_MSGS  = ["oh you're back!","there you are!","welcome back :)",
                "i missed you","👀"]
BATTERY_MSGS = ["psst. plug in soon","battery getting low...",
                "charge me... i mean you","⚡ low battery warning"]


def get_time_key():
    h = datetime.datetime.now().hour
    if 6  <= h < 12: return "morning"
    if 12 <= h < 17: return "afternoon"
    if 17 <= h < 21: return "evening"
    return "night"

def get_time_expr():
    return {"morning":"idle","afternoon":"happy",
            "evening":"idle","night":"sleepy"}[get_time_key()]

def active_window_name():
    if not WIN_AVAILABLE:
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return (proc.name() + " " + win32gui.GetWindowText(hwnd)).lower()
    except Exception:
        return ""

def classify_window(name):
    if any(k in name for k in GAME_KEYWORDS):    return "game"
    if any(k in name for k in CODE_KEYWORDS):    return "code"
    if any(k in name for k in BROWSER_KEYWORDS): return "browser"
    return "other"

def is_game_running():
    """Check running processes for signs of Steam/Epic game activity.
    Reads local process list only — no network calls, no external data."""
    try:
        procs = {p.name().lower() for p in psutil.process_iter(["name"])}
        return any(hint in procs for hint in GAME_PROCESS_HINTS)
    except Exception:
        return False

def get_wasapi_loopback_device():
    """Find a WASAPI loopback or Stereo Mix device for system audio capture."""
    if not AUDIO_AVAILABLE:
        return None
    try:
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            name = d["name"].lower()
            if d["max_input_channels"] > 0 and any(
                k in name for k in ("loopback","stereo mix","wave out mix","what u hear")
            ):
                return i
    except Exception:
        pass
    return None


# ── app ────────────────────────────────────────────────────────────────────────
class Companion:
    def __init__(self, root):
        self.root = root
        self.root.title("pip")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.configure(bg="#010101")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        # ── physics state ──────────────────────────────────────────────────────
        self.phys_x    = float(sw - SPRITE_SIZE - 20)
        self.phys_y    = float(sh - SPRITE_SIZE - 80)
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.target_x  = self.phys_x
        self.target_y  = self.phys_y
        self.is_dragging   = False
        self.drag_said_msg = False
        self._press_x  = 0
        self._press_y  = 0

        self.root.geometry(
            f"{SPRITE_SIZE}x{SPRITE_SIZE+60}+{int(self.phys_x)}+{int(self.phys_y)}"
        )

        # ── companion state ────────────────────────────────────────────────────
        self.current_expr  = "idle"
        self.is_dancing    = False
        self.dance_offset  = 0
        self.dance_dir     = 1
        self.was_idle      = False
        self.last_active   = time.time()
        self.last_window   = ""
        self.bubble_active = False
        self.game_notified = False

        # ── sprites ────────────────────────────────────────────────────────────
        self.sprites = {}
        for name in ["idle","happy","surprised","annoyed","talking","sleepy"]:
            path = os.path.join(SPRITE_DIR, f"{name}.png")
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA").resize(
                    (SPRITE_SIZE, SPRITE_SIZE), Image.NEAREST)
                self.sprites[name] = ImageTk.PhotoImage(img)
        if not self.sprites:
            raise RuntimeError(f"No sprites found in {SPRITE_DIR}")
        if "sleepy" not in self.sprites:
            self.sprites["sleepy"] = self.sprites.get("annoyed",
                                     next(iter(self.sprites.values())))

        # ── speech bubble ──────────────────────────────────────────────────────
        self.bubble_var = tk.StringVar()
        self.bubble = tk.Label(
            root, textvariable=self.bubble_var,
            bg="#1a1a2e", fg="#a0d8ef",
            font=("Courier New", 10, "bold"),
            wraplength=200, justify="center",
            padx=8, pady=5, relief="flat", bd=0,
        )
        self.bubble.place_forget()

        # ── sprite label ───────────────────────────────────────────────────────
        self.label = tk.Label(root, bg="#010101", bd=0, highlightthickness=0)
        self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
        self.set_expr("idle")

        # ── bindings ───────────────────────────────────────────────────────────
        self.label.bind("<ButtonPress-1>",   self.on_press)
        self.label.bind("<B1-Motion>",       self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>",        lambda e: self.root.destroy())
        self.bubble.bind("<Button-3>",       lambda e: self.root.destroy())

        # ── loopback device ────────────────────────────────────────────────────
        self.loopback_device = get_wasapi_loopback_device()

        # ── start loops ────────────────────────────────────────────────────────
        self.schedule_ambient()
        if AUDIO_AVAILABLE:
            threading.Thread(target=self.audio_loop, daemon=True).start()
        self.dance_tick()
        self.physics_tick()

    # ── expressions ────────────────────────────────────────────────────────────
    def set_expr(self, name):
        if name in self.sprites:
            self.label.configure(image=self.sprites[name])
            self.current_expr = name

    def show_bubble(self, text, expr=None, duration=BUBBLE_MS):
        if expr:
            self.set_expr(expr)
        self.bubble_var.set(text)
        self.bubble.place(x=0, y=0, width=SPRITE_SIZE, height=55)
        self.bubble_active = True
        self.root.after(duration, self.hide_bubble)

    def hide_bubble(self):
        self.bubble.place_forget()
        self.bubble_active = False
        if not self.is_dancing:
            self.set_expr(get_time_expr())

    # ── ragdoll drag ───────────────────────────────────────────────────────────
    def on_press(self, event):
        self.is_dragging   = True
        self.drag_said_msg = False
        self._press_x = event.x_root
        self._press_y = event.y_root
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.set_expr("surprised")
        self.last_active = time.time()
        self.was_idle = False

    def on_drag(self, event):
        self.target_x = event.x_root - SPRITE_SIZE // 2
        self.target_y = event.y_root - SPRITE_SIZE // 2
        if not self.drag_said_msg and (
            abs(event.x_root - self._press_x) > 10 or
            abs(event.y_root - self._press_y) > 10
        ):
            self.drag_said_msg = True
            self.show_bubble(random.choice(DRAG_MSGS), "surprised", duration=2000)

    def on_release(self, event):
        self.is_dragging = False
        self.vel_x *= 0.4
        self.vel_y *= 0.4
        if not self.bubble_active:
            self.set_expr(get_time_expr())

    # ── physics ────────────────────────────────────────────────────────────────
    def physics_tick(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        if self.is_dragging:
            # spring toward mouse
            dx = self.target_x - self.phys_x
            dy = self.target_y - self.phys_y
            self.vel_x = self.vel_x * 0.6 + dx * 0.25
            self.vel_y = self.vel_y * 0.6 + dy * 0.25
        else:
            # gravity + damping
            self.vel_y += 0.8
            self.vel_x *= 0.88
            self.vel_y *= 0.88
            # bounce off screen edges
            if self.phys_x < 0:
                self.phys_x = 0;              self.vel_x =  abs(self.vel_x) * 0.5
            if self.phys_x > sw - SPRITE_SIZE:
                self.phys_x = sw - SPRITE_SIZE; self.vel_x = -abs(self.vel_x) * 0.5
            if self.phys_y < 0:
                self.phys_y = 0;              self.vel_y =  abs(self.vel_y) * 0.5
            if self.phys_y > sh - SPRITE_SIZE - 60:
                self.phys_y = sh - SPRITE_SIZE - 60; self.vel_y = -abs(self.vel_y) * 0.3

        self.phys_x += self.vel_x
        self.phys_y += self.vel_y
        self.root.geometry(f"+{int(self.phys_x)}+{int(self.phys_y)}")
        self.root.after(16, self.physics_tick)   # ~60fps

    # ── dance ──────────────────────────────────────────────────────────────────
    def dance_tick(self):
        if self.is_dancing and not self.is_dragging:
            self.dance_offset += self.dance_dir * 3
            if abs(self.dance_offset) >= 10:
                self.dance_dir *= -1
            self.label.place(x=0, y=60+self.dance_offset,
                             width=SPRITE_SIZE, height=SPRITE_SIZE)
        self.root.after(60, self.dance_tick)

    def start_dance(self):
        if not self.is_dancing:
            self.is_dancing = True
            self.set_expr("happy")
            if not self.bubble_active:
                self.show_bubble(random.choice(MUSIC_MSGS), duration=3000)

    def stop_dance(self):
        if self.is_dancing:
            self.is_dancing = False
            self.dance_offset = 0
            self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
            self.set_expr(get_time_expr())

    # ── audio — WASAPI loopback first, mic fallback ────────────────────────────
    def audio_loop(self):
        silent_streak = 0
        device = self.loopback_device
        if device is not None:
            print(f"[pip] system audio via loopback device {device}")
        else:
            print("[pip] no loopback found — using mic. enable Stereo Mix in Windows sound settings for system audio.")

        while True:
            try:
                kwargs = dict(frames=2048, samplerate=44100,
                              channels=1, dtype="float32", blocking=True)
                if device is not None:
                    kwargs["device"] = device
                chunk = sd.rec(**kwargs)
                rms = float(np.sqrt(np.mean(chunk**2)))
                if rms > AUDIO_THRESH:
                    silent_streak = 0
                    self.root.after(0, self.start_dance)
                else:
                    silent_streak += 1
                    if silent_streak > 8:
                        self.root.after(0, self.stop_dance)
            except Exception as e:
                print(f"[pip] audio error: {e}")
                time.sleep(5)

    # ── ambient awareness ──────────────────────────────────────────────────────
    def schedule_ambient(self):
        self.root.after(15000, self.ambient_check)

    def ambient_check(self):
        now = time.time()

        # idle / return
        idle_secs = now - self.last_active
        if idle_secs > IDLE_MINUTES * 60:
            if not self.was_idle:
                self.was_idle = True
                self.show_bubble(random.choice(IDLE_MSGS), "sleepy")
        else:
            if self.was_idle:
                self.was_idle = False
                self.show_bubble(random.choice(RETURN_MSGS), "surprised")

        # window + process awareness
        win       = active_window_name()
        kind      = classify_window(win)
        game_proc = is_game_running()

        if win != self.last_window or (game_proc and not self.game_notified):
            self.last_window = win
            if (kind == "game" or game_proc) and not self.bubble_active:
                self.game_notified = True
                self.show_bubble(random.choice(GAME_MSGS), "happy")
            elif kind == "code" and not self.bubble_active:
                self.game_notified = False
                if random.random() < 0.3:
                    self.show_bubble(random.choice(CODE_MSGS), "idle")
            else:
                if not game_proc:
                    self.game_notified = False

        # battery
        try:
            batt = psutil.sensors_battery()
            if batt and not batt.power_plugged and batt.percent < 20:
                if not self.bubble_active:
                    self.show_bubble(random.choice(BATTERY_MSGS), "annoyed")
        except Exception:
            pass

        # random ambient
        if random.random() < 0.15 and not self.bubble_active and not self.is_dancing:
            self.show_bubble(random.choice(MESSAGES[get_time_key()]), "talking")

        self.schedule_ambient()


if __name__ == "__main__":
    root = tk.Tk()
    Companion(root)
    root.mainloop()
