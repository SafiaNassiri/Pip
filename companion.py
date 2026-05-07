"""
companion.py — ambient-aware desktop robot
requires: pip install pillow sounddevice numpy psutil pywin32
place in same folder as: idle.png happy.png surprised.png annoyed.png talking.png sleepy.png
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

# ── config ────────────────────────────────────────────────────────────────────
SPRITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
SPRITE_SIZE  = 223
BUBBLE_MS    = 4000
AUDIO_THRESH = 0.02        # RMS threshold for "music playing"
IDLE_MINUTES = 10

GAME_KEYWORDS    = ["game","steam","epic","roblox","minecraft","godot","unity",
                    "itch","rpg","overwatch","valorant","league","fortnite",
                    "genshin","hollow","celeste","stardew"]
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
                "i believe in you","don't die 🎮"]
CODE_MSGS    = ["still coding huh","you got this","one more bug right?",
                "i see you grinding","ship it 🚀"]
MUSIC_MSGS   = ["🎵 bop","this slaps","i feel it","🎶✨","vibing rn"]
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


# ── app ───────────────────────────────────────────────────────────────────────
class Companion:
    def __init__(self, root):
        self.root = root
        self.root.title("companion")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.configure(bg="#010101")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(
            f"{SPRITE_SIZE}x{SPRITE_SIZE+60}+{sw-SPRITE_SIZE-20}+{sh-SPRITE_SIZE-80}"
        )

        # state
        self.current_expr = "idle"
        self.is_dancing   = False
        self.dance_offset = 0
        self.dance_dir    = 1
        self.was_idle     = False
        self.last_active  = time.time()
        self.last_window  = ""
        self.bubble_active = False

        # sprites
        self.sprites = {}
        for name in ["idle","happy","surprised","annoyed","talking","sleepy"]:
            path = os.path.join(SPRITE_DIR, f"{name}.png")
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA").resize(
                    (SPRITE_SIZE, SPRITE_SIZE), Image.NEAREST)
                self.sprites[name] = ImageTk.PhotoImage(img)
        if "sleepy" not in self.sprites:
            self.sprites["sleepy"] = self.sprites.get("annoyed", self.sprites["idle"])

        # speech bubble
        self.bubble_var = tk.StringVar()
        self.bubble = tk.Label(
            root, textvariable=self.bubble_var,
            bg="#1a1a2e", fg="#a0d8ef",
            font=("Courier New", 10, "bold"),
            wraplength=200, justify="center",
            padx=8, pady=5, relief="flat", bd=0,
        )
        self.bubble.place_forget()

        # sprite
        self.label = tk.Label(root, bg="#010101", bd=0, highlightthickness=0)
        self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
        self.set_expr("idle")

        # bindings
        self._dx = self._dy = 0
        self.label.bind("<ButtonPress-1>", self.on_click)
        self.label.bind("<B1-Motion>",     self.on_drag)
        self.label.bind("<Button-3>",      lambda e: self.root.destroy())
        self.bubble.bind("<Button-3>",     lambda e: self.root.destroy())

        # start everything
        self.schedule_ambient()
        if AUDIO_AVAILABLE:
            threading.Thread(target=self.audio_loop, daemon=True).start()
        self.dance_tick()

    # ── expressions ───────────────────────────────────────────────────────────
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

    # ── drag ──────────────────────────────────────────────────────────────────
    def on_click(self, event):
        self._dx, self._dy = event.x, event.y
        self.last_active = time.time()
        self.was_idle = False
        self.show_bubble(random.choice(MESSAGES[get_time_key()]), "talking")

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    # ── dance ─────────────────────────────────────────────────────────────────
    def dance_tick(self):
        if self.is_dancing:
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

    # ── audio (background thread) ──────────────────────────────────────────────
    def audio_loop(self):
        silent_streak = 0
        while True:
            try:
                chunk = sd.rec(2048, samplerate=44100, channels=1,
                               dtype="float32", blocking=True)
                rms = float(np.sqrt(np.mean(chunk**2)))
                if rms > AUDIO_THRESH:
                    silent_streak = 0
                    self.root.after(0, self.start_dance)
                else:
                    silent_streak += 1
                    if silent_streak > 8:
                        self.root.after(0, self.stop_dance)
            except Exception:
                time.sleep(5)

    # ── ambient awareness ─────────────────────────────────────────────────────
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

        # window awareness
        win  = active_window_name()
        kind = classify_window(win)
        if win != self.last_window:
            self.last_window = win
            if kind == "game" and not self.bubble_active:
                self.show_bubble(random.choice(GAME_MSGS), "happy")
            elif kind == "code" and not self.bubble_active:
                if random.random() < 0.3:
                    self.show_bubble(random.choice(CODE_MSGS), "idle")

        # battery
        try:
            batt = psutil.sensors_battery()
            if batt and not batt.power_plugged and batt.percent < 20:
                if not self.bubble_active:
                    self.show_bubble(random.choice(BATTERY_MSGS), "annoyed")
        except Exception:
            pass

        # random ambient (low freq)
        if random.random() < 0.15 and not self.bubble_active and not self.is_dancing:
            self.show_bubble(random.choice(MESSAGES[get_time_key()]), "talking")

        self.schedule_ambient()


if __name__ == "__main__":
    root = tk.Tk()
    Companion(root)
    root.mainloop()
