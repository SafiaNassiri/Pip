"""
companion.py — Pip, ambient-aware desktop robot
requires: pip install pillow psutil pywin32 requests
sprites go in ./sprites/
hover over Pip for the menu
"""

import tkinter as tk
import threading, time, random, datetime, os, json, sys, traceback, subprocess
import psutil

try:
    import win32gui, win32process, win32api
    WIN_AVAILABLE = True
except Exception:
    WIN_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

# ── paths ──────────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE, "sprites")
SETTINGS_F = os.path.join(BASE, "settings.json")
STATE_F    = os.path.join(BASE, "state.json")      # mood, achievements, etc.
LOG_F      = os.path.join(BASE, "pip_log.json")    # diary entries

SPRITE_SIZE  = 223
BUBBLE_MS    = 4000

DEFAULT_SETTINGS = {
    "idle_minutes": 10,
    "personality":  "chill",
    "name":         "Pip",
    "git_dirs":     [],          # list of repo paths to watch
    "city":         "",          # for weather
    "git_warn_minutes": 30,
}

DEFAULT_STATE = {
    "mood":         0,           # -10 to 10, 0 = neutral
    "pets":         0,
    "shakes":       0,
    "throws":       0,
    "feeds":        0,
    "session_start": None,
    "achievements": [],
    "last_git_check": None,
    "last_weather":   None,
    "weather_cache":  None,
    "food_level":   5,           # 0-10, affects mood
}

ACHIEVEMENTS = {
    "first_pet":    {"label": "🤍 first touch",     "desc": "pet pip for the first time",      "key": "pets",   "n": 1},
    "pet10":        {"label": "🐾 lap cat",          "desc": "pet pip 10 times",                "key": "pets",   "n": 10},
    "pet50":        {"label": "💕 beloved",          "desc": "pet pip 50 times",                "key": "pets",   "n": 50},
    "first_shake":  {"label": "🌀 dizzy maker",      "desc": "shake pip for the first time",    "key": "shakes", "n": 1},
    "shake5":       {"label": "🎡 chaos agent",      "desc": "shake pip 5 times",               "key": "shakes", "n": 5},
    "first_throw":  {"label": "🚀 yeet",             "desc": "throw pip for the first time",    "key": "throws", "n": 1},
    "throw10":      {"label": "🎯 pip launcher",     "desc": "throw pip 10 times",              "key": "throws", "n": 10},
    "first_feed":   {"label": "🍪 feeder",           "desc": "feed pip for the first time",     "key": "feeds",  "n": 1},
    "feed10":       {"label": "👨‍🍳 chef",             "desc": "feed pip 10 times",               "key": "feeds",  "n": 10},
    "screen3h":     {"label": "⏰ long session",     "desc": "3 hours in one session",          "key": "_time",  "n": 3},
    "screen6h":     {"label": "🌙 no life (affectionate)", "desc": "6 hours in one session",   "key": "_time",  "n": 6},
}

FOODS = ["🍪","🍕","🍩","🍎","🧁","🌮","🍓","☕","🍜","🍫"]

GAME_PROCESS_HINTS = [
    "gameoverlayui.exe","steamwebhelper.exe","easyanticheat.exe",
    "epicgameslauncher.exe","unrealcefsubprocess.exe","galaxyclient.exe",
]
# processes that should never be detected as games
SELF_PROCESS_NAMES = {"python.exe","pythonw.exe","pip.exe"}
GAME_KEYWORDS    = ["game","steam","epic","roblox","minecraft","godot","unity",
                    "itch","rpg","overwatch","valorant","league","fortnite",
                    "genshin","hollow","celeste","stardew","cookie"]
CODE_KEYWORDS    = ["code","vscode","visual studio","cursor","pycharm",
                    "jetbrains","sublime","notepad++","vim","neovim"]
BROWSER_KEYWORDS = ["chrome","firefox","edge","opera","brave","safari"]

# ── seasonal / weather ─────────────────────────────────────────────────────────
def get_season():
    m = datetime.datetime.now().month
    if m in (12, 1, 2):  return "winter"
    if m in (3, 4, 5):   return "spring"
    if m in (6, 7, 8):   return "summer"
    return "autumn"

SEASON_MSGS = {
    "winter":  ["it's cold out there 🌨️","cozy szn","winter mode activated","stay warm out there"],
    "spring":  ["spring is here 🌸","everything's blooming","fresh air szn","love this weather"],
    "summer":  ["it's hot out there ☀️","summer brain","stay hydrated!!","beach szn"],
    "autumn":  ["fall vibes 🍂","cozy season is HERE","leaves are falling","pumpkin szn"],
}

WEATHER_MSGS = {
    "clear":       ["nice weather out there ☀️","get some sun today","it's beautiful outside"],
    "clouds":      ["cloudy day 🌤️","overcast vibes","moody weather"],
    "rain":        ["it's raining 🌧️","stay inside","rainy day cozy szn","don't forget an umbrella"],
    "snow":        ["it's snowing!! ❄️","snow day!!","so pretty outside","bundle up"],
    "thunderstorm":["storm outside ⛈️","stay inside!!","thunder and lightning","cozy inside time"],
    "mist":        ["foggy out there 🌫️","mysterious weather","spooky fog vibes"],
}

OCTOBER_MSGS  = ["spooky szn 🎃","halloween is coming","👻","trick or treat","spooky hours"]
DECEMBER_MSGS = ["holiday szn 🎄","it's the most wonderful time","cozy december","✨🎄✨"]

# ── message banks ──────────────────────────────────────────────────────────────
PERSONALITIES = {
    "chill": {
        "morning":    ["good morning ☀️","gm gm","coffee first","today's gonna be ok","rise and shine"],
        "afternoon":  ["how's it going?","drink some water","you're doing great","still here ✨","breaks are valid"],
        "evening":    ["almost there!","proud of you tbh","what'd you make today?","evening vibes"],
        "night":      ["night owl hours 🌙","just us and the void ✨","the night is young","midnight oil"],
        "game":       ["ooh gaming time","let's gooo 🎮","i believe in you","no thoughts only game"],
        "code":       ["still at it huh","you got this","one more bug","grinding i see 👀","ship it 🚀"],
        "idle":       ["...hello?","you still there?","*taps screen*","knock knock","pip pip?"],
        "return":     ["oh you're back!","there you are!","welcome back","i missed you 👀"],
        "pet":        ["hehe ^^","uwu","stop it","♡","heehee","^//^"],
        "drag":       ["wheeee","hey!!","put me down","wooah","weeee :D"],
        "battery":    ["plug in soon","low battery...","⚡ charge","hey. battery."],
        "hour":       ["another hour passes","tick tock","time flies huh","still here ✨"],
        "yawn":       ["*yawns*","...zzzz","sleepy","so tired rn"],
        "stretch":    ["*stretches*","ahhhh","feeling stiff","*wiggle*"],
        "lookaround": ["👀","hm?","...","what was that","*looks around*"],
        "dizzy":      ["dizzy...","x_x","spinning...","woozy","make it stop"],
        "jump":       ["!!","ack!","hey!","woah!","eep!"],
        "throw":      ["wheee!!","i'm free!!","catch me!!","yeet","wooooo"],
        "wall":       ["ow","bonk","that's a wall","...ouch","*bonk*"],
        "hungry":     ["i'm hungry...","feed me?","tummy rumbling","could eat","🍽️?"],
        "full":       ["so full","that was good","thank you ♡","mmm","*happy*"],
        "grumpy":     ["hmph","...","leave me alone","not in the mood","ugh"],
        "happy_mood": ["feeling good ♡","great day","love it here","☀️☀️","vibing hard"],
        "git_warn":   ["hey. commit your code.","push something","git commit...","your repo's dusty 👀","when did you last commit?"],
        "screen_time":["you've been here a while","take a break?","go touch grass","eyes tired?","screen time check 👀"],
        "feed_full":  ["i'm full!","can't eat more","already stuffed","save it for later","no more!"],
        "weather_idle": {
            "clear":        ["it's nice out today ☀️","sunny outside rn","perfect weather tbh"],
            "clouds":       ["kinda cloudy out there","overcast vibes today","grey skies..."],
            "rain":         ["it's raining outside 🌧️","rainy day energy","cozy rain day"],
            "snow":         ["it's snowing!! ❄️","snow outside!!","everything's white out there"],
            "thunderstorm": ["storm outside ⛈️","thunder outside rn","wild weather today"],
            "mist":         ["foggy out there 🌫️","can't see far today","mysterious outside"],
        },
        "talk_response": ["hmm","interesting","oh?","tell me more","i see i see","noted ✓","...really?","wow","no way","💭"],
    },
    "hype": {
        "morning":    ["LET'S GO ☀️","RISE AND GRIND","TODAY WE WIN","GOOD MORNING!!"],
        "afternoon":  ["KEEP GOING","HYDRATE","YOU'RE KILLING IT","NO STOPPING"],
        "evening":    ["ALMOST THERE!!!","SO PROUD","WHAT A DAY","EVENING HYPE"],
        "night":      ["NIGHT OWL GANG 🦉","WE DON'T SLEEP","NIGHT MODE ON","LETS GOOO 🌙"],
        "game":       ["GAMING LET'S GO!!","GET IN THERE!!","YOU GOT THIS!!","DESTROY THEM 🎮"],
        "code":       ["CODE HARDER","BUG GOES BRRRR","SHIP IT!!!","10X ENERGY"],
        "idle":       ["HEY!!","HELLO???","TAP TAP","WAKE UP!!!"],
        "return":     ["YOU'RE BACK!!!","YESSS","LET'S GOOO","FINALLY!!"],
        "pet":        ["YESSS","I LOVE THIS","MORE","♡♡♡","BESTIE"],
        "drag":       ["WHEEEEEEE","AHHHHH","SO FUN","FASTER!!!"],
        "battery":    ["PLUG IN NOW!!","BATTERY CRITICAL","CHARGE ME","⚡⚡⚡"],
        "hour":       ["ANOTHER HOUR CONQUERED","TIME FLIES","KEEP GOING"],
        "yawn":       ["NO SLEEP ONLY GRIND","*aggressive yawn*","TIRED BUT STRONG"],
        "stretch":    ["*MAXIMUM STRETCH*","AHHHHHH","POWER STRETCH"],
        "lookaround": ["👀👀","WHAT WAS THAT","!!!","HM???"],
        "dizzy":      ["DIZZY BUT MAKE IT FASHION","X_X","SPINNING TO WIN"],
        "jump":       ["!!!!!","STARTLED","HEY!!!","WOAH!!!"],
        "throw":      ["WHEEEEE!!!","FREEDOM!!!","I'M FLYING","MAXIMUM YEET"],
        "wall":       ["OW!!","BONK!!","THAT'S A WALL!!!","*BONK*"],
        "hungry":     ["FEED ME!!","I NEED FOOD","HUNGRY HUNGRY PIP","🍽️🍽️"],
        "full":       ["AMAZING FOOD","THANK YOU!!!","SO FULL SO HAPPY","DELICIOUS"],
        "grumpy":     ["GRUMPY","LEAVE ME ALONE","NOT NOW","HMPH!!"],
        "happy_mood": ["FEELING AMAZING","BEST DAY EVER","LOVE IT HERE","☀️☀️☀️"],
        "git_warn":   ["COMMIT YOUR CODE NOW","PUSH IT","GIT COMMIT!!!","DUSTY REPO DETECTED"],
        "screen_time":["TAKE A BREAK NOW","EYES NEED REST","GO OUTSIDE!!","SCREEN TIME ALERT"],
        "feed_full":  ["I'M FULL!!","NO MORE FOOD","STUFFED","SAVE IT"],
    },
    "sleepy": {
        "morning":    ["...morning","five more minutes","ugh","coffee. now."],
        "afternoon":  ["still tired","mhm","okay","..."],
        "evening":    ["almost bedtime","so close","tired","zzz soon"],
        "night":      ["finally night","🌙","sleepy hours","zzzzzz"],
        "game":       ["oh. gaming. okay","...good luck","zz— gaming??","mmkay"],
        "code":       ["...code","still going huh","okay","zz"],
        "idle":       ["zzz","...","sleeping","hm?"],
        "return":     ["oh. hi.","you're back","...hey","mhm"],
        "pet":        ["...♡","mhm","sleepy happy","zz ^^"],
        "drag":       ["...whee","zzz-whoa","hm","okay"],
        "battery":    ["...plug in","battery low","zzz charge","mm"],
        "hour":       ["...another hour","time is fake","okay","mhm"],
        "yawn":       ["*yawns extensively*","so sleepy","zzzzz","*mega yawn*"],
        "stretch":    ["*barely stretches*","...ahh","mhm","zzz-stretch"],
        "lookaround": ["...","hm","zz?","*slow blink*"],
        "dizzy":      ["...dizzy","hm","zz-whoa","woozy"],
        "jump":       ["...!","oh","hm!","...oh"],
        "throw":      ["...wheee","oh","okay then","...flying"],
        "wall":       ["...ow","hm","bonk","..."],
        "hungry":     ["...hungry","food?","...","tummy","zz hungry"],
        "full":       ["...full","thank you","mhm","...good"],
        "grumpy":     ["...","go away","not now","ugh"],
        "happy_mood": ["...happy","feeling okay","mhm ♡","...nice"],
        "git_warn":   ["...commit","git...","push something","...repo"],
        "screen_time":["...break?","tired eyes","...grass","zz screen time"],
        "feed_full":  ["...full","no more","...","zz full"],
    },
}

# ── persistence ────────────────────────────────────────────────────────────────
def load_settings():
    try:
        with open(SETTINGS_F) as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        return dict(DEFAULT_SETTINGS)

def save_settings(s):
    try:
        with open(SETTINGS_F, "w") as f:
            json.dump(s, f, indent=2)
        print(f"[pip] settings saved to {SETTINGS_F}")
    except Exception as e:
        print(f"[pip] ERROR saving settings: {e}")

def load_state():
    try:
        with open(STATE_F) as f:
            return {**DEFAULT_STATE, **json.load(f)}
    except Exception:
        return dict(DEFAULT_STATE)

def save_state(s):
    try:
        with open(STATE_F, "w") as f:
            json.dump(s, f, indent=2)
    except Exception as e:
        print(f"[pip] ERROR saving state: {e}")

# ── log / diary ───────────────────────────────────────────────────────────────
def load_log():
    try:
        with open(LOG_F) as f: return json.load(f)
    except Exception: return []

def append_log(entry):
    """Append an entry dict with timestamp to the log."""
    try:
        log = load_log()
        log.append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            **entry
        })
        # keep last 200 entries
        log = log[-200:]
        with open(LOG_F, "w") as f: json.dump(log, f, indent=2)
    except Exception as e:
        print(f"[pip] log error: {e}")

# ── system helpers ─────────────────────────────────────────────────────────────
def get_taskbar_height():
    if not WIN_AVAILABLE: return 40
    try:
        hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            return max(win32api.GetSystemMetrics(1) - rect[1], 0)
    except Exception: pass
    return 40

def active_window_name():
    if not WIN_AVAILABLE: return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return (psutil.Process(pid).name() + " " +
                win32gui.GetWindowText(hwnd)).lower()
    except Exception: return ""

def classify_window(name):
    if any(k in name for k in GAME_KEYWORDS):    return "game"
    if any(k in name for k in CODE_KEYWORDS):    return "code"
    if any(k in name for k in BROWSER_KEYWORDS): return "browser"
    return "other"

def is_game_running():
    try:
        procs = {p.name().lower() for p in psutil.process_iter(["name"])}
        return any(h in procs for h in GAME_PROCESS_HINTS)
    except Exception: return False

def is_self_window(name):
    """Return True if the active window is Pip itself."""
    return any(s in name for s in ("python pip","pythonw pip","pip settings",
                                    "pip achievements","companion.py"))

def get_active_game_name():
    if not WIN_AVAILABLE: return None
    skip_procs  = {"steam.exe","steamwebhelper.exe","python.exe","pythonw.exe", "explorer.exe","searchhost.exe","shellexperiencehost.exe"}
    skip_titles = {"program manager","settings","taskbar","pip","start","python"}
    try:
        results = []
        def handler(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd): return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc  = psutil.Process(pid)
                pname = proc.name().lower()
                title = win32gui.GetWindowText(hwnd).strip()
                if (pname not in skip_procs and title and len(title) > 2
                        and not any(s in title.lower() for s in skip_titles)):
                    results.append((title, pname))
            except Exception: pass
        win32gui.EnumWindows(handler, None)
        def clean_title(t):
            # Cookie Clicker format: "123,456 cookies - Cookie Clicker"
            # split on dash/pipe and take the last non-numeric part
            import re as _re
            parts = _re.split(r"[-|]", t)
            for part in reversed(parts):
                part = part.strip()
                if part and not _re.match(r"^[0-9,. ]+", part):
                    return part
            return parts[-1].strip() if parts else t
        for title, pname in results:
            if not any(b in pname for b in ("chrome","firefox","edge","opera")):
                return clean_title(title) or title
        return clean_title(results[0][0]) if results else None
    except Exception: return None

def get_spotify_track():
    if not WIN_AVAILABLE: return None
    try:
        results = []
        def handler(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd): return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if "spotify" in psutil.Process(pid).name().lower():
                    t = win32gui.GetWindowText(hwnd)
                    if t and " - " in t and t != "Spotify":
                        results.append(t)
            except Exception: pass
        win32gui.EnumWindows(handler, None)
        return results[0] if results else None
    except Exception: return None

def get_battery():
    try:
        b = psutil.sensors_battery()
        if b: return b.percent, b.power_plugged
    except Exception: pass
    return None, None

def get_weather(city):
    """Fetch weather from wttr.in — no API key needed."""
    if not REQUESTS_AVAILABLE or not city: return None
    try:
        r = requests.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            desc = data["current_condition"][0]["weatherDesc"][0]["value"].lower()
            # map to our categories
            for key in ("thunderstorm","snow","rain","mist","cloud","clear"):
                if key in desc: return key
            return "clear"
    except Exception: pass
    return None

def check_git_repos(dirs, warn_hours):
    """Check if any repo hasn't had a commit recently."""
    stale = []
    for d in dirs:
        if not os.path.isdir(d): continue
        try:
            result = subprocess.run(
                ["git", "-C", d, "log", "-1", "--format=%ct"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                ts   = int(result.stdout.strip())
                age  = (time.time() - ts) / 3600   # hours
                name = os.path.basename(d.rstrip("/\\"))
                if age > warn_hours:
                    stale.append((name, int(age)))
        except Exception: pass
    return stale

def get_session_hours(state):
    if not state.get("session_start"): return 0
    try:
        start = datetime.datetime.fromisoformat(state["session_start"])
        delta = datetime.datetime.now() - start
        return delta.total_seconds() / 3600
    except Exception: return 0


# ── companion ──────────────────────────────────────────────────────────────────
class Companion:
    def __init__(self, root):
        self.root     = root
        self.settings = load_settings()
        self.state    = load_state()

        # start session timer
        self.state["session_start"] = datetime.datetime.now().isoformat()
        save_state(self.state)

        self.root.title("pip")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.configure(bg="#010101")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.sw        = sw
        self.sh        = sh
        self.taskbar_h = get_taskbar_height()
        self.floor_y   = sh - self.taskbar_h - SPRITE_SIZE - 60

        # ── physics ────────────────────────────────────────────────────────────
        self.phys_x      = float(sw - SPRITE_SIZE - 20)
        self.phys_y      = float(self.floor_y)
        self.vel_x       = 0.0
        self.vel_y       = 0.0
        self.target_x    = self.phys_x
        self.target_y    = self.phys_y
        self.is_dragging = False
        self.drag_said   = False
        self._press_x    = 0
        self._press_y    = 0
        self._last_drag_x = 0
        self._last_dx    = 0
        self._dir_changes = 0

        # ── state ──────────────────────────────────────────────────────────────
        self.current_expr   = "idle"
        self.is_dizzy       = False
        self._squish_active = False
        self.bubble_active  = False
        self.game_notified  = False
        self.was_idle       = False
        self.last_active    = time.time()
        self.last_window    = ""
        self.last_track     = None
        self.last_hour      = datetime.datetime.now().hour
        self.idle_tick      = 0
        self._dancing       = False
        self._dance_offset  = 0
        self._dance_dir     = 1
        self._wall_bounce_pending = False

        # weather cache
        self._weather_checked = False
        self._current_weather = self.state.get("weather_cache", None)

        # new achievement queue
        self._achievement_queue = []

        # pomodoro
        self._pomodoro_active  = False
        self._pomodoro_working = True
        self._pomodoro_session = 0
        self._pomodoro_end     = 0

        BAR_H = 28
        self.BAR_H = BAR_H
        self.root.geometry(
            f"{SPRITE_SIZE}x{SPRITE_SIZE+60+BAR_H}"
            f"+{int(self.phys_x)}+{int(self.phys_y)}"
        )

        # ── sprites ────────────────────────────────────────────────────────────
        self.sprites = {}
        if PIL_AVAILABLE:
            for name in ["idle","happy","surprised","annoyed","talking","sleepy"]:
                path = os.path.join(SPRITE_DIR, f"{name}.png")
                if os.path.exists(path):
                    img = Image.open(path).convert("RGBA").resize(
                        (SPRITE_SIZE, SPRITE_SIZE), Image.NEAREST)
                    self.sprites[name] = ImageTk.PhotoImage(img)
        if not self.sprites:
            raise RuntimeError(f"No sprites found in {SPRITE_DIR}")
        for fb, src in [("sleepy","annoyed"),("annoyed","idle"),("talking","idle"),
                        ("happy","idle"),("surprised","idle")]:
            if fb not in self.sprites:
                self.sprites[fb] = self.sprites.get(src, next(iter(self.sprites.values())))

        # ── glow canvas (behind sprite) ────────────────────────────────────────
        self.glow_canvas = tk.Canvas(
            root, width=SPRITE_SIZE, height=SPRITE_SIZE,
            bg="#010101", highlightthickness=0, bd=0
        )
        self.glow_canvas.place(x=0, y=60)
        self.glow_visible = False

        # ── bubble ─────────────────────────────────────────────────────────────
        self.bubble_var = tk.StringVar()
        self.bubble = tk.Label(
            root, textvariable=self.bubble_var,
            bg="#0d0d1a", fg="#a0d8ef",
            font=("Courier New", 9, "bold"),
            wraplength=200, justify="center",
            padx=6, pady=4, relief="flat", bd=0,
        )
        self.bubble.place_forget()

        # ── sprite label ───────────────────────────────────────────────────────
        self.label = tk.Label(root, bg="#010101", bd=0, highlightthickness=0)
        self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
        self.set_expr("idle")

        # ── icon bar (always visible below sprite) ─────────────────────────────
        self.bar = tk.Frame(root, bg="#0d0d1a", height=self.BAR_H)
        self.bar.place(x=0, y=60+SPRITE_SIZE, width=SPRITE_SIZE, height=self.BAR_H)

        BAR_BTN = {"bg":"#0d0d1a","fg":"#4a4a8a","font":("Courier New",11),
                    "relief":"flat","bd":0,"cursor":"hand2","padx":2,
                    "activebackground":"#1a1a2e","activeforeground":"#a0d8ef"}

        def make_btn(icon, left_cmd, right_cmd=None):
            b = tk.Button(self.bar, text=icon, command=left_cmd, **BAR_BTN)
            b.pack(side="left", expand=True)
            if right_cmd:
                b.bind("<Button-3>", lambda e: right_cmd())
            return b

        make_btn("🤍", self._pet,                self._show_mood)
        make_btn("🍪", self._feed,               self._show_food_level)
        make_btn("🎵", self._show_now_playing,   self._show_log)
        make_btn("🎮", self._show_current_game,  self._show_screen_time)
        make_btn("🏆", self._show_achievements,  None)
        make_btn("🍅", self._open_pomodoro,      None)
        make_btn("💬", self._open_talk,          None)
        make_btn("⚙",  self._open_settings,     None)
        tk.Button(self.bar, text="✕", command=self.root.destroy,
                    bg="#0d0d1a", fg="#5a2a2a", font=("Courier New",11),
                    relief="flat", bd=0, cursor="hand2", padx=2,
                    activebackground="#1a1a2e", activeforeground="#ff6b6b").pack(side="left", expand=True)

        # ── bindings ───────────────────────────────────────────────────────────
        for w in (self.label, self.bubble, self.glow_canvas):
            w.bind("<ButtonPress-1>",   self.on_press)
            w.bind("<B1-Motion>",       self.on_drag)
            w.bind("<ButtonRelease-1>", self.on_release)
            w.bind("<Double-Button-1>", self.on_double_click)
            w.bind("<Enter>",           self.on_hover)
            w.bind("<Leave>",           self.on_leave)

        # ── start loops ────────────────────────────────────────────────────────
        self.physics_tick()
        self.dance_tick()
        self.idle_behavior_tick()
        self.schedule_ambient()
        self.achievement_display_tick()

        # settings live-reload
        self._settings_mtime = self._get_settings_mtime()
        self._settings_reload_tick()

        # clipboard watcher
        self._last_clipboard   = ""
        self._clipboard_enabled = True
        self._clipboard_tick()

        # greet on startup — varied messages
        name = self.settings.get("name", "Pip")
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            greet_pool = [
                f"good morning ☀️ i'm {name}",
                f"morning! i'm {name} ♡",
                f"rise and shine~ i'm {name}",
            ]
        elif 12 <= hour < 18:
            greet_pool = [
                f"hey! i'm {name} ♡",
                f"hi there! i'm {name}",
                f"afternoon~ i'm {name} ✨",
            ]
        elif 18 <= hour < 22:
            greet_pool = [
                f"evening ✨ i'm {name}",
                f"hey! back again? i'm {name}",
                f"evening vibes~ i'm {name} ♡",
            ]
        else:
            greet_pool = [
                f"night owl hours 🌙 i'm {name}",
                f"up late? i'm {name} ♡",
                f"just us and the void~ i'm {name}",
            ]
        self.root.after(800, lambda: self.show_bubble(
            random.choice(greet_pool), "happy", duration=2800))

    # ── helpers ────────────────────────────────────────────────────────────────
    def msg(self, key):
        p    = self.settings.get("personality", "chill")
        bank = PERSONALITIES.get(p, PERSONALITIES["chill"])
        return random.choice(bank.get(key, ["..."]))

    # ── settings live-reload ───────────────────────────────────────────────────
    def _get_settings_mtime(self):
        try:
            return os.path.getmtime(SETTINGS_F)
        except Exception:
            return 0

    def _settings_reload_tick(self):
        try:
            mtime = self._get_settings_mtime()
            if mtime != self._settings_mtime:
                self._settings_mtime = mtime
                new_settings = load_settings()
                changed = [k for k in new_settings if new_settings[k] != self.settings.get(k)]
                self.settings = new_settings
                if changed:
                    print(f"[pip] settings reloaded (changed: {', '.join(changed)})")
                    if "city" in changed:
                        self._weather_checked = False   # re-fetch weather
                    self.show_bubble("settings reloaded ✓", duration=1800)
        except Exception as e:
            print(f"[pip] settings reload error: {e}")
        self.root.after(3000, self._settings_reload_tick)

    # ── clipboard watcher ──────────────────────────────────────────────────────
    def _clipboard_tick(self):
        if self._clipboard_enabled:
            try:
                text = self.root.clipboard_get()
                if text and text != self._last_clipboard:
                    self._last_clipboard = text
                    self._on_clipboard_change(text)
            except Exception:
                pass   # clipboard empty or unavailable
        self.root.after(2500, self._clipboard_tick)

    def _on_clipboard_change(self, text):
        if self.bubble_active or self._dancing:
            return
        stripped = text.strip()
        if not stripped:
            return

        import re as _re

        # URL
        if _re.match(r"https?://\S{8,}", stripped):
            domain = _re.sub(r"https?://([^/]+).*", r"\1", stripped)
            domain = domain if len(domain) < 28 else domain[:25] + "…"
            msgs = [f"ooh a link~ {domain}", f"saving that link 🔗", f"link copied ✓"]
            self.show_bubble(random.choice(msgs), "idle", duration=2500)
            return

        lines = stripped.splitlines()

        # code-ish (multiple lines, has brackets/semicolons/indents)
        code_score = sum([
            stripped.count("{") + stripped.count("}") > 1,
            stripped.count(";") > 2,
            len([l for l in lines if l.startswith(("    ", "\t"))]) > 1,
            any(kw in stripped for kw in ("def ","function ","class ","import ","const ","var ","return ")),
        ])
        if len(lines) > 2 and code_score >= 2:
            msgs = ["ooh code snippet 👀", "copying code i see", "snippet saved ✓", "that looks like code 🖥️"]
            self.show_bubble(random.choice(msgs), "talking", duration=2500)
            return

        # long text (paragraph+)
        if len(stripped) > 200:
            words = len(stripped.split())
            msgs = [f"that's a lot of text 📋", f"copied {words} words", "big copy ✓"]
            self.show_bubble(random.choice(msgs), "idle", duration=2200)

    # ── pomodoro mode ──────────────────────────────────────────────────────────
    POMODORO_WORK_MIN  = 25
    POMODORO_BREAK_MIN = 5

    def _start_pomodoro(self):
        self._pomodoro_active  = True
        self._pomodoro_working = True
        self._pomodoro_session = 0
        self._pomodoro_end     = time.time() + self.POMODORO_WORK_MIN * 60
        self.show_bubble(
            f"🍅 focus mode!\n{self.POMODORO_WORK_MIN} min work session", "happy", duration=3000)
        append_log({"text": "pomodoro started"})
        self._pomodoro_tick()

    def _stop_pomodoro(self):
        self._pomodoro_active = False
        self.show_bubble("🍅 pomodoro stopped", "idle", duration=2000)
        append_log({"text": f"pomodoro ended after {self._pomodoro_session} sessions"})

    def _pomodoro_tick(self):
        if not getattr(self, "_pomodoro_active", False):
            return
        remaining = self._pomodoro_end - time.time()
        if remaining <= 0:
            if self._pomodoro_working:
                # work done → break time
                self._pomodoro_session += 1
                self._pomodoro_working  = False
                self._pomodoro_end      = time.time() + self.POMODORO_BREAK_MIN * 60
                msgs = [
                    f"🍅 session {self._pomodoro_session} done!\ntake a {self.POMODORO_BREAK_MIN} min break ☕",
                    f"work block done ✓\nbreak time! {self.POMODORO_BREAK_MIN} mins",
                    f"🍅 x{self._pomodoro_session} nice work!\nbreaking now ♡",
                ]
                self.show_bubble(random.choice(msgs), "happy", duration=5000)
                append_log({"text": f"pomodoro session {self._pomodoro_session} complete"})
            else:
                # break done → back to work
                self._pomodoro_working = True
                self._pomodoro_end     = time.time() + self.POMODORO_WORK_MIN * 60
                msgs = [
                    f"break over! back to work 🍅\n{self.POMODORO_WORK_MIN} mins",
                    "let's go! focus time 🍅",
                    "break done~ work mode 🍅",
                ]
                self.show_bubble(random.choice(msgs), "happy", duration=3500)
        else:
            # mid-session nudges at ~halfway
            half = (self.POMODORO_WORK_MIN * 60) / 2
            elapsed = (self._pomodoro_end - time.time())
            # nudge when ~1 min left
            if self._pomodoro_working and 55 < remaining < 65 and not self.bubble_active:
                self.show_bubble("🍅 one minute left!", "idle", duration=3000)

        self.root.after(10000, self._pomodoro_tick)   # check every 10s

    def _open_pomodoro(self):
        if getattr(self, "_pomodoro_active", False):
            # show status
            remaining = max(0, self._pomodoro_end - time.time())
            mins      = int(remaining // 60)
            secs      = int(remaining % 60)
            phase     = "work 🍅" if self._pomodoro_working else "break ☕"
            self.show_bubble(
                f"pomodoro: {phase}\n{mins}:{secs:02d} left  (session {self._pomodoro_session})",
                "idle", duration=4000)
            return

        win = tk.Toplevel(self.root)
        win.title("pomodoro")
        win.configure(bg="#0d0d1a")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        px, py = int(self.phys_x), int(self.phys_y)
        win.geometry(f"240x200+{px}+{max(0,py-220)}")

        tk.Label(win, text="🍅  pomodoro",
                    bg="#0d0d1a", fg="#a0d8ef",
                    font=("Courier New", 11, "bold")).pack(pady=(12, 6))

        tk.Label(win,
                    text=f"{self.POMODORO_WORK_MIN} min work · {self.POMODORO_BREAK_MIN} min break",
                    bg="#0d0d1a", fg="#5a5a8a",
                    font=("Courier New", 8)).pack()

        # custom duration row
        tk.Label(win, text="work minutes:",
                    bg="#0d0d1a", fg="#a0d8ef",
                    font=("Courier New", 8, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        work_var = tk.StringVar(value=str(self.POMODORO_WORK_MIN))
        tk.Entry(win, textvariable=work_var,
                    bg="#1a1a2e", fg="#ffffff",
                    font=("Courier New", 9), relief="flat", bd=4,
                    insertbackground="white", width=6).pack(anchor="w", padx=20)

        def start():
            try:
                mins = max(1, int(work_var.get()))
                self.__class__.POMODORO_WORK_MIN = mins
            except ValueError:
                pass
            win.destroy()
            self._start_pomodoro()

        tk.Button(win, text="▶  start focus",
                    command=start,
                    bg="#1a1a2e", fg="#a0d8ef",
                    font=("Courier New", 10, "bold"),
                    relief="flat", padx=14, pady=6,
                    cursor="hand2").pack(pady=(12, 4))

    def _base_expr(self):
        mood = self.state.get("mood", 0)
        if mood <= -5: return "annoyed"
        h = datetime.datetime.now().hour
        if   6  <= h < 12: return "idle"
        elif 12 <= h < 17: return "happy"
        elif 17 <= h < 21: return "idle"
        else:               return "sleepy"

    def set_expr(self, name):
        if name in self.sprites:
            self.label.configure(image=self.sprites[name])
            self.current_expr = name

    def show_bubble(self, text, expr=None, duration=BUBBLE_MS):
        if expr: self.set_expr(expr)
        self.bubble_var.set(text)
        self.bubble.place(x=0, y=0, width=SPRITE_SIZE, height=55)
        self.bubble_active = True
        self.root.after(duration, self.hide_bubble)

    def hide_bubble(self):
        self.bubble.place_forget()
        self.bubble_active = False
        self.set_expr(self._base_expr())

    def _shift_mood(self, delta):
        self.state["mood"] = max(-10, min(10, self.state.get("mood", 0) + delta))
        save_state(self.state)

    # ── achievements ───────────────────────────────────────────────────────────
    def _check_achievements(self):
        earned = self.state.get("achievements", [])
        for key, ach in ACHIEVEMENTS.items():
            if key in earned: continue
            stat_key = ach["key"]
            if stat_key == "_time":
                val = get_session_hours(self.state)
            else:
                val = self.state.get(stat_key, 0)
            if val >= ach["n"]:
                earned.append(key)
                self.state["achievements"] = earned
                save_state(self.state)
                self._achievement_queue.append(ach)
                print(f"[pip] achievement unlocked: {ach['label']}")

    def achievement_display_tick(self):
        if self._achievement_queue and not self.bubble_active:
            ach = self._achievement_queue.pop(0)
            self.show_bubble(f"🏆 {ach['label']}\n{ach['desc']}", "happy", duration=4000)
        self.root.after(500, self.achievement_display_tick)

    # ── hover menu ─────────────────────────────────────────────────────────────
    def on_hover(self, event):
        self._show_glow()

    def on_leave(self, event):
        self.root.after(300, self._hide_glow)

    def _show_glow(self):
        if self.glow_visible: return
        self.glow_visible = True
        c = self.glow_canvas
        c.delete("glow")
        cx, cy = SPRITE_SIZE // 2, SPRITE_SIZE // 2
        # layered rings fading outward
        for i, (r, color) in enumerate([
            (104, "#1a1a3a"),
            (98,  "#1e2048"),
            (90,  "#222460"),
            (80,  "#2a2e80"),
            (70,  "#3030a0"),
        ]):
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2, tags="glow")

    def _hide_glow(self):
        if not self.glow_visible: return
        # only hide if cursor actually left
        try:
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            wx = self.root.winfo_rootx()
            wy = self.root.winfo_rooty()
            ww = SPRITE_SIZE
            wh = SPRITE_SIZE + 60
            if wx <= mx <= wx+ww and wy <= my <= wy+wh:
                return  # still hovering
        except Exception: pass
        self.glow_visible = False
        self.glow_canvas.delete("glow")

    def _pet(self):
        self.state["pets"] = self.state.get("pets", 0) + 1
        self._shift_mood(1)
        save_state(self.state)
        self._check_achievements()
        self.set_expr("happy")
        self.show_bubble(self.msg("pet"), duration=2500)

    def _feed(self):
        food_level = self.state.get("food_level", 5)
        if food_level >= 10:
            self.show_bubble(self.msg("feed_full"), "annoyed", duration=2000)
            return
        food = random.choice(FOODS)
        self.state["feeds"]      = self.state.get("feeds", 0) + 1
        self.state["food_level"] = min(10, food_level + 2)
        self._shift_mood(2)
        save_state(self.state)
        self._check_achievements()
        self.show_bubble(f"{food} yum!", "happy", duration=2500)

    def _show_now_playing(self):
        track = get_spotify_track()
        if track:
            display = track if len(track) < 32 else track[:29]+"..."
            self.show_bubble(f"🎵 {display}", "happy", duration=4000)
        else:
            self.show_bubble("nothing playing rn", "idle", duration=2500)

    def _show_current_game(self):
        if is_game_running():
            name = get_active_game_name()
            if name:
                display = name if len(name) < 28 else name[:25]+"..."
                self.show_bubble(f"🎮 {display}", "happy", duration=4000)
            else:
                self.show_bubble("game running! 🎮", "happy", duration=2500)
        else:
            self.show_bubble("no game detected", "idle", duration=2500)

    def _show_screen_time(self):
        hours = get_session_hours(self.state)
        mins  = int((hours % 1) * 60)
        h     = int(hours)
        self.show_bubble(f"⏰ {h}h {mins}m this session", "idle", duration=3000)

    def _show_achievements(self):
        earned = self.state.get("achievements", [])
        if not earned:
            self.show_bubble("no achievements yet\ninteract with me!", "idle", duration=3000)
            return
        # show in a small window
        win = tk.Toplevel(self.root)
        win.title("achievements")
        win.configure(bg="#0d0d1a")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        px, py = int(self.phys_x), int(self.phys_y)
        win.geometry(f"260x{min(500, 80 + len(earned)*52)}+{px}+{max(0,py-540)}")

        tk.Label(win, text="🏆 achievements",
                    bg="#0d0d1a", fg="#a0d8ef",
                    font=("Courier New",10,"bold")).pack(pady=(10,6))

        for key in earned:
            ach = ACHIEVEMENTS.get(key)
            if not ach: continue
            tk.Label(win, text=f"{ach['label']}",
                        bg="#0d0d1a", fg="#ffffff",
                        font=("Courier New",9,"bold")).pack(anchor="w", padx=16)
            tk.Label(win, text=ach['desc'],
                        bg="#0d0d1a", fg="#5a5a8a",
                        font=("Courier New",8)).pack(anchor="w", padx=24, pady=(0,4))

        tk.Button(win, text="close", command=win.destroy,
                    bg="#1a1a2e", fg="#a0d8ef",
                    font=("Courier New",9,"bold"),
                    relief="flat", padx=10, pady=3,
                    cursor="hand2").pack(pady=8)

    def _show_mood(self):
        mood = self.state.get("mood", 0)
        if mood > 5:   label, expr = "feeling great ♡", "happy"
        elif mood > 0: label, expr = "doing okay", "idle"
        elif mood == 0:label, expr = "neutral i guess", "idle"
        elif mood > -5:label, expr = "a little grumpy", "annoyed"
        else:          label, expr = "not happy rn", "annoyed"
        self.show_bubble(f"mood: {label} ({mood:+d}/10)", expr, duration=3000)

    def _show_food_level(self):
        food = self.state.get("food_level", 5)
        bar  = "█" * food + "░" * (10 - food)
        self.show_bubble(f"hunger: {bar} {food}/10", "idle", duration=3000)

    def _show_log(self):
        """Open pip diary window."""
        log = load_log()
        win = tk.Toplevel(self.root)
        win.title("pip's diary")
        win.configure(bg="#0d0d1a")
        win.resizable(True, True)
        win.attributes("-topmost", True)
        px, py = int(self.phys_x), int(self.phys_y)
        win.geometry(f"300x400+{max(0,px-80)}+{max(0,py-440)}")

        tk.Label(win, text="📓  pip's diary",
                    bg="#0d0d1a", fg="#a0d8ef",
                    font=("Courier New",10,"bold")).pack(pady=(10,4))

        frame = tk.Frame(win, bg="#0d0d1a")
        frame.pack(fill="both", expand=True, padx=8, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        lb = tk.Text(frame, bg="#0d0d1a", fg="#a0d8ef",
                        font=("Courier New",8), relief="flat",
                        wrap="word", state="disabled",
                        yscrollcommand=sb.set)
        lb.pack(fill="both", expand=True)
        sb.config(command=lb.yview)

        lb.config(state="normal")
        if not log:
            lb.insert("end", "nothing yet...\npip is still observing.")
        else:
            for entry in reversed(log[-50:]):
                t    = entry.get("time","")
                text = entry.get("text","")
                lb.insert("end", f"[{t}]\n{text}\n\n")
        lb.config(state="disabled")

        tk.Button(win, text="clear log", command=lambda: self._clear_log(win),
                    bg="#1a1a2e", fg="#ff6b6b",
                    font=("Courier New",8), relief="flat",
                    cursor="hand2", padx=8, pady=3).pack(pady=6)

    def _clear_log(self, win):
        try:
            with open(LOG_F, "w") as f: json.dump([], f)
            win.destroy()
            self.show_bubble("diary cleared", duration=1500)
        except Exception as e:
            print(f"[pip] clear log error: {e}")

    def _open_talk(self):
        """Small input window to talk to Pip."""
        win = tk.Toplevel(self.root)
        win.title("talk to pip")
        win.configure(bg="#0d0d1a")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        px, py = int(self.phys_x), int(self.phys_y)
        win.geometry(f"260x100+{px}+{max(0,py-120)}")

        tk.Label(win, text="say something to pip",
                    bg="#0d0d1a", fg="#5a5a8a",
                    font=("Courier New",8)).pack(pady=(8,4))

        entry_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=entry_var,
                            bg="#1a1a2e", fg="#ffffff",
                            font=("Courier New",10), relief="flat",
                            bd=6, insertbackground="white", width=24)
        entry.pack(padx=16, pady=2)
        entry.focus()

        def send(event=None):
            text = entry_var.get().strip()
            if not text: return
            win.destroy()
            self._handle_talk(text)

        entry.bind("<Return>", send)
        tk.Button(win, text="send", command=send,
                    bg="#1a1a2e", fg="#a0d8ef",
                    font=("Courier New",9,"bold"),
                    relief="flat", padx=10, pady=3,
                    cursor="hand2").pack(pady=6)

    def _handle_talk(self, text):
        """Pip responds to something you said."""
        text_l = text.lower()
        # log it
        append_log({"text": f"you: {text}"})

        # keyword responses
        if any(w in text_l for w in ("hello","hi","hey","hiya")):
            resp = f"hi!! ♡"
        elif any(w in text_l for w in ("how are you","you ok","you good")):
            mood = self.state.get("mood",0)
            resp = "doing great actually ♡" if mood > 0 else "could be better tbh" if mood < 0 else "i'm okay!"
        elif any(w in text_l for w in ("good morning","morning")):
            resp = "good morning!! ☀️"
        elif any(w in text_l for w in ("good night","night","bye","goodbye")):
            resp = "goodnight ♡ see you"
        elif any(w in text_l for w in ("thank","thanks","ty")):
            resp = "of course ♡"
        elif any(w in text_l for w in ("i love you","love you","ily")):
            resp = "♡♡♡"
            self._shift_mood(2)
        elif any(w in text_l for w in ("i'm tired","im tired","so tired","exhausted")):
            resp = "get some rest 💙"
        elif any(w in text_l for w in ("i'm hungry","im hungry","food")):
            resp = "me too 🍪"
        elif any(w in text_l for w in ("i'm sad","im sad","sad","unhappy","depressed")):
            resp = "i'm here ♡"
            self._shift_mood(1)
        elif any(w in text_l for w in ("i'm happy","im happy","happy","great","amazing")):
            resp = "that's wonderful!! ♡"
            self._shift_mood(1)
        elif any(w in text_l for w in ("stop","leave me alone","go away","shut up")):
            resp = "ok ok... 😶"
            self._shift_mood(-1)
        elif "?" in text:
            resp = random.choice(["hm... i'm not sure","good question","🤔","maybe?","possibly!"])
        else:
            p = self.settings.get("personality","chill")
            bank = PERSONALITIES.get(p, PERSONALITIES["chill"])
            resp = random.choice(bank.get("talk_response", ["..."]))

        append_log({"text": f"pip: {resp}"})
        self.show_bubble(resp, "talking", duration=3000)
        self._shift_mood(1)  # talking makes pip happier

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("pip settings")
        win.configure(bg="#0d0d1a")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        px, py = int(self.phys_x), int(self.phys_y)
        win.geometry(f"280x460+{px}+{max(0,py-480)}")

        LBL = {"bg":"#0d0d1a","fg":"#a0d8ef","font":("Courier New",9,"bold")}
        INP = {"bg":"#1a1a2e","fg":"#ffffff","font":("Courier New",9), "relief":"flat","bd":4,"insertbackground":"white","width":18}

        tk.Label(win, text="⚙  settings",
                    bg="#0d0d1a", fg="#a0d8ef",
                    font=("Courier New",11,"bold")).pack(pady=(12,8))

        def field(label, var):
            tk.Label(win, text=label, **LBL).pack(anchor="w", padx=16)
            tk.Entry(win, textvariable=var, **INP).pack(anchor="w", padx=16, pady=(0,8))

        name_var  = tk.StringVar(value=self.settings.get("name","Pip"))
        idle_var  = tk.StringVar(value=str(self.settings.get("idle_minutes",10)))
        city_var  = tk.StringVar(value=self.settings.get("city",""))
        git_var   = tk.StringVar(value=";".join(self.settings.get("git_dirs",[])))
        warn_var  = tk.StringVar(value=str(self.settings.get("git_warn_minutes",30)))

        field("name", name_var)
        field("idle timeout (minutes)", idle_var)
        field("city (for weather)", city_var)
        field("git repos (sep. by ;)", git_var)
        field("git warn after (minutes)", warn_var)

        tk.Label(win, text="personality", **LBL).pack(anchor="w", padx=16)
        pers_var = tk.StringVar(value=self.settings.get("personality","chill"))
        row = tk.Frame(win, bg="#0d0d1a")
        row.pack(anchor="w", padx=16, pady=(0,10))
        for p in ("chill","hype","sleepy"):
            tk.Radiobutton(row, text=p, variable=pers_var, value=p,
                            bg="#0d0d1a", fg="#a0d8ef", selectcolor="#1a1a2e",
                            activebackground="#0d0d1a", activeforeground="#fff",
                            font=("Courier New",9)).pack(side="left", padx=4)

        # status label shown after save
        status_var = tk.StringVar(value="")
        status_lbl = tk.Label(win, textvariable=status_var, bg="#0d0d1a", font=("Courier New", 8))
        status_lbl.pack()

        def save():
            self.settings["name"]           = name_var.get().strip() or "Pip"
            self.settings["personality"]    = pers_var.get()
            self.settings["city"]           = city_var.get().strip()
            self.settings["git_warn_minutes"] = int(warn_var.get()) if warn_var.get().isdigit() else 30
            try: self.settings["idle_minutes"] = max(1, int(idle_var.get()))
            except ValueError: pass
            raw_dirs = [d.strip() for d in git_var.get().split(";") if d.strip()]
            self.settings["git_dirs"] = raw_dirs
            try:
                save_settings(self.settings)
                self._weather_checked = False
                status_var.set("✓ saved!")
                status_lbl.config(fg="#4adf8a")
                win.after(800, win.destroy)
                self.show_bubble("saved ✓", duration=1500)
            except Exception as e:
                status_var.set(f"✗ error: {e}")
                status_lbl.config(fg="#ff6b6b")
                print(f"[pip] settings save error: {e}")

        tk.Button(win, text="💾  save settings", command=save,
                    bg="#1a1a2e", fg="#a0d8ef",
                    font=("Courier New", 10, "bold"),
                    relief="flat", padx=16, pady=6,
                    cursor="hand2").pack(pady=(8,4))

    # ── interactions ───────────────────────────────────────────────────────────
    def on_press(self, event):
        self._hide_glow()
        # don't start dragging yet — wait to see if mouse moves
        self.is_dragging  = False
        self._drag_started = False
        self.drag_said    = False
        self._press_x     = event.x_root
        self._press_y     = event.y_root
        self._last_drag_x = event.x_root
        self._last_dx     = 0
        self._dir_changes = 0
        self.vel_x = self.vel_y = 0.0
        self.last_active  = time.time()
        self.was_idle     = False

    def on_drag(self, event):
        dx = abs(event.x_root - self._press_x)
        dy = abs(event.y_root - self._press_y)
        # only start drag after moving 8px — avoids accidental drag on tap
        if not self._drag_started:
            if dx > 8 or dy > 8:
                self._drag_started = True
                self.is_dragging   = True
                self.set_expr("surprised")
            else:
                return   # still looks like a tap, ignore

        self._check_shake(event)
        self.target_x = event.x_root - SPRITE_SIZE // 2
        self.target_y = event.y_root - SPRITE_SIZE // 2
        if not self.drag_said:
            self.drag_said = True
            self.show_bubble(self.msg("drag"), duration=2000)

    def on_release(self, event):
        dx = abs(event.x_root - self._press_x)
        dy = abs(event.y_root - self._press_y)

        if not self._drag_started:
            # clean tap — do the squish
            self._squish()
            if not self.bubble_active:
                self.show_bubble(self.msg(
                    "morning" if 6 <= datetime.datetime.now().hour < 12 else
                    "afternoon" if datetime.datetime.now().hour < 17 else
                    "evening" if datetime.datetime.now().hour < 21 else "night"
                ), "talking", duration=2500)

        self.is_dragging   = False
        self._drag_started = False

        speed = abs(self.vel_x) + abs(self.vel_y)
        if speed > 5:
            self.state["throws"] = self.state.get("throws", 0) + 1
            save_state(self.state)
            self._check_achievements()
            if not self.bubble_active:
                self.show_bubble(self.msg("throw"), "surprised", duration=1500)
        elif self._drag_started is False and not self.bubble_active:
            self.set_expr(self._base_expr())

    def on_double_click(self, event):
        if self.is_dizzy: return
        self.vel_y = -16
        self.vel_x = random.choice([-6, 6])
        self.state["throws"] = self.state.get("throws", 0) + 1
        save_state(self.state)
        self._check_achievements()
        self.show_bubble(self.msg("jump"), "surprised", duration=1200)

    def _squish(self):
        if self._squish_active: return
        self._squish_active = True
        self.label.place(x=-10, y=70, width=SPRITE_SIZE+20, height=SPRITE_SIZE-10)
        self.root.after(80,  lambda: self.label.place(
            x=5, y=54, width=SPRITE_SIZE-10, height=SPRITE_SIZE+10))
        self.root.after(160, lambda: self.label.place(
            x=0, y=60, width=SPRITE_SIZE,    height=SPRITE_SIZE))
        self.root.after(165, lambda: setattr(self, "_squish_active", False))

    def _check_shake(self, event):
        x  = event.x_root
        dx = x - self._last_drag_x
        if (dx > 4 and self._last_dx < -4) or (dx < -4 and self._last_dx > 4):
            self._dir_changes += 1
            if self._dir_changes >= 5 and not self.is_dizzy:
                self._go_dizzy()
        self._last_dx     = dx
        self._last_drag_x = x

    def _go_dizzy(self):
        self.is_dizzy     = True
        self._dir_changes = 0
        self.state["shakes"] = self.state.get("shakes", 0) + 1
        self._shift_mood(-1)
        save_state(self.state)
        self._check_achievements()
        self.show_bubble(self.msg("dizzy"), "surprised", duration=3000)
        n = [0]
        def wobble():
            if n[0] < 10:
                off = 9 if n[0] % 2 == 0 else -9
                self.label.place(x=off, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
                n[0] += 1
                self.root.after(70, wobble)
            else:
                self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
                self.root.after(3200, lambda: setattr(self, "is_dizzy", False))
        wobble()

    # ── physics ────────────────────────────────────────────────────────────────
    def physics_tick(self):
        sw       = self.sw
        floor_y  = self.floor_y

        if self.is_dragging:
            dx = self.target_x - self.phys_x
            dy = self.target_y - self.phys_y
            self.vel_x = self.vel_x * 0.55 + dx * 0.28
            self.vel_y = self.vel_y * 0.55 + dy * 0.28
        else:
            speed = abs(self.vel_x) + abs(self.vel_y)
            if speed > 0.4:
                self.vel_y += 0.75          # gravity
                self.vel_x *= 0.985         # very low air friction = floaty
                self.vel_y *= 0.985

                # ── wall bounces ───────────────────────────────────────────────
                if self.phys_x <= 0:
                    self.phys_x = 0
                    self.vel_x  = abs(self.vel_x) * 0.75
                    self._on_wall_bounce()

                elif self.phys_x >= sw - SPRITE_SIZE:
                    self.phys_x = sw - SPRITE_SIZE
                    self.vel_x  = -abs(self.vel_x) * 0.75
                    self._on_wall_bounce()

                if self.phys_y <= 0:
                    self.phys_y = 0
                    self.vel_y  = abs(self.vel_y) * 0.6

                elif self.phys_y >= floor_y:
                    self.phys_y  = floor_y
                    self.vel_y   = -abs(self.vel_y) * 0.38
                    self.vel_x  *= 0.82     # ground friction
                    # small floor bounce reaction
                    if abs(self.vel_y) > 3 and not self.bubble_active:
                        self.set_expr("surprised")
                        self.root.after(400, lambda: self.set_expr(self._base_expr()))
            else:
                # settled
                self.vel_x  = 0.0
                self.vel_y  = 0.0
                self.phys_y = floor_y

        self.phys_x += self.vel_x
        self.phys_y += self.vel_y
        self.root.geometry(f"+{int(self.phys_x)}+{int(self.phys_y)}")
        self.root.after(16, self.physics_tick)

    def _on_wall_bounce(self):
        if self._wall_bounce_pending: return
        self._wall_bounce_pending = True
        if not self.bubble_active:
            self.show_bubble(self.msg("wall"), "surprised", duration=1200)
        self.root.after(1500, lambda: setattr(self, "_wall_bounce_pending", False))

    # ── dance ──────────────────────────────────────────────────────────────────
    def dance_tick(self):
        if self._dancing and not self.is_dragging:
            self._dance_offset += self._dance_dir * 3
            if abs(self._dance_offset) >= 9: self._dance_dir *= -1
            self.label.place(x=0, y=60+self._dance_offset, width=SPRITE_SIZE, height=SPRITE_SIZE)
        self.root.after(60, self.dance_tick)

    def _start_dance(self, track=None):
        if not self._dancing:
            self._dancing      = True
            self._dance_offset = 0
            self._dance_dir    = 1
            self.set_expr("happy")
            if not self.bubble_active and track:
                display = track if len(track) < 30 else track[:27]+"..."
                self.show_bubble(f"🎵 {display}", duration=4000)

    def _stop_dance(self):
        if self._dancing:
            self._dancing      = False
            self._dance_offset = 0
            self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
            self.set_expr(self._base_expr())

    # ── idle micro-behaviors ───────────────────────────────────────────────────
    def idle_behavior_tick(self):
        if (not self.is_dragging and not self._dancing
                and not self.bubble_active and not self.is_dizzy):
            self.idle_tick += 1
            # drain food level slowly
            if self.idle_tick % 30 == 0:
                self.state["food_level"] = max(0, self.state.get("food_level",5) - 1)
                save_state(self.state)
                if self.state["food_level"] <= 2 and not self.bubble_active:
                    self.show_bubble(self.msg("hungry"), "annoyed", duration=3000)
                    self._shift_mood(-1)

            if self.idle_tick >= random.randint(12, 25):
                self.idle_tick = 0
                self._do_idle_behavior()

        self.root.after(2000, self.idle_behavior_tick)

    def _do_idle_behavior(self):
        has_weather = bool(self._current_weather)
        action = random.choices(
            ["yawn","stretch","weather_comment","lookaround","nothing"],
            weights=[2, 2, 3 if has_weather else 0, 3, 5]
        )[0]
        if action == "yawn":
            self.set_expr("sleepy")
            self.show_bubble(self.msg("yawn"), duration=2500)
            self.root.after(2600, lambda: self.set_expr(self._base_expr()))
        elif action == "stretch":
            self.show_bubble(self.msg("stretch"), duration=2000)
        elif action == "weather_comment":
            if self._current_weather:
                p    = self.settings.get("personality","chill")
                bank = PERSONALITIES.get(p, PERSONALITIES["chill"])
                msgs = bank.get("weather_idle", {}).get(self._current_weather)
                if msgs:
                    self.show_bubble(random.choice(msgs), "idle", duration=3000)
        elif action == "lookaround":
            self.label.place(x=8,  y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)
            self.root.after(500, lambda: self.label.place(
                x=-8, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE))
            self.root.after(1000, lambda: self.label.place(
                x=0,  y=60, width=SPRITE_SIZE, height=SPRITE_SIZE))
            if random.random() < 0.5:
                self.show_bubble(self.msg("lookaround"), duration=2000)

    # ── ambient awareness ──────────────────────────────────────────────────────
    def schedule_ambient(self):
        self.root.after(15000, self.ambient_check)

    def ambient_check(self):
        now  = time.time()
        hour = datetime.datetime.now().hour
        month = datetime.datetime.now().month

        # new hour
        if hour != self.last_hour:
            self.last_hour = hour
            if not self.bubble_active and not self._dancing:
                self.show_bubble(self.msg("hour"), "idle", duration=3000)

        # idle / return
        idle_mins = self.settings.get("idle_minutes", 10)
        if now - self.last_active > idle_mins * 60:
            if not self.was_idle:
                self.was_idle = True
                if not self.bubble_active:
                    self.show_bubble(self.msg("idle"), "sleepy")
        else:
            if self.was_idle:
                self.was_idle = False
                self.show_bubble(self.msg("return"), "surprised")

        # log notable events
        self._log_tick = getattr(self, "_log_tick", 0) + 1
        if self._log_tick >= 4:   # every ~60s
            self._log_tick = 0
            h2 = datetime.datetime.now().hour
            if 6 <= h2 < 12:   tod = "morning"
            elif h2 < 17:      tod = "afternoon"
            elif h2 < 21:      tod = "evening"
            else:              tod = "night"
            entry_parts = [f"{tod} vibes"]
            if self._current_weather:
                entry_parts.append(f"weather: {self._current_weather}")
            mood = self.state.get("mood",0)
            if mood > 3:   entry_parts.append("mood: happy")
            elif mood < -3:entry_parts.append("mood: grumpy")
            append_log({"text": " · ".join(entry_parts)})

        # spotify dance
        track = get_spotify_track()
        if track:
            if track != self.last_track:
                self.last_track = track
                self._start_dance(track)
            elif not self._dancing:
                self._start_dance()
        else:
            if self.last_track:
                self.last_track = None
                self._stop_dance()

        # game detection
        if not self._dancing:
            win       = active_window_name()
            kind      = classify_window(win)
            game_proc = is_game_running()
            if win != self.last_window or (game_proc and not self.game_notified):
                self.last_window = win
                if (kind == "game" or game_proc) and not self.bubble_active and not is_self_window(win):
                    self.game_notified = True
                    name = get_active_game_name()
                    msg  = (f"playing {name[:22]}? 🎮" if name else self.msg("game"))
                    self.show_bubble(msg, "happy")
                elif kind == "code" and not self.bubble_active:
                    self.game_notified = False
                    if random.random() < 0.3:
                        self.show_bubble(self.msg("code"), "idle")
                else:
                    if not game_proc: self.game_notified = False

        # screen time check
        hours = get_session_hours(self.state)
        self._check_achievements()
        if hours > 2 and random.random() < 0.1 and not self.bubble_active:
            self.show_bubble(self.msg("screen_time"), "idle", duration=3000)

        # git check (in background thread)
        git_dirs = self.settings.get("git_dirs", [])
        if git_dirs:
            last = self.state.get("last_git_check")
            if not last or (now - float(last)) > 3600:   # check every hour
                self.state["last_git_check"] = now
                save_state(self.state)
                threading.Thread(target=self._check_git_bg, daemon=True).start()

        # weather (once per session)
        city = self.settings.get("city","")
        if city and not self._weather_checked:
            self._weather_checked = True
            threading.Thread(target=self._check_weather_bg, daemon=True).start()

        # seasonal / special month messages
        if random.random() < 0.05 and not self.bubble_active:
            if month == 10:
                self.show_bubble(random.choice(OCTOBER_MSGS), "happy", duration=3000)
            elif month == 12:
                self.show_bubble(random.choice(DECEMBER_MSGS), "happy", duration=3000)
            elif random.random() < 0.3:
                season = get_season()
                self.show_bubble(random.choice(SEASON_MSGS[season]), "idle", duration=3000)

        # battery
        pct, plugged = get_battery()
        if pct and not plugged and pct < 20 and not self.bubble_active:
            self.show_bubble(self.msg("battery"), "annoyed")

        # random ambient
        if (random.random() < 0.12 and not self.bubble_active
                and not self._dancing and not self.game_notified):
            key = ("morning" if 6 <= hour < 12 else
                    "afternoon" if hour < 17 else
                    "evening" if hour < 21 else "night")
            # mood affects random messages
            mood = self.state.get("mood", 0)
            if mood > 5:
                self.show_bubble(self.msg("happy_mood"), "happy")
            elif mood < -5:
                self.show_bubble(self.msg("grumpy"), "annoyed")
            else:
                self.show_bubble(self.msg(key), "talking")

        self.schedule_ambient()

    def _check_git_bg(self):
        dirs      = self.settings.get("git_dirs", [])
        warn_mins = self.settings.get("git_warn_minutes", 30)
        warn_h    = warn_mins / 60
        stale     = check_git_repos(dirs, warn_h)
        if stale:
            name, age = stale[0]
            msg = f"{name}: {age}h since last commit"
            print(f"[pip] git warning: {msg}")
            self.root.after(0, lambda: self.show_bubble(
                self.msg("git_warn") + f"\n({name})", "annoyed", duration=5000))

    def _check_weather_bg(self):
        city    = self.settings.get("city","")
        weather = get_weather(city)
        if weather:
            self._current_weather = weather
            self.state["weather_cache"] = weather
            save_state(self.state)
            msgs = WEATHER_MSGS.get(weather, WEATHER_MSGS["clear"])
            msg  = random.choice(msgs)
            print(f"[pip] weather in {city}: {weather}")
            append_log({"text": f"weather check: {weather} in {city}"})
            self.root.after(2000, lambda: self.show_bubble(msg, "idle", duration=4000))


# ── entry ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    def on_exception(exc_type, exc_value, exc_tb):
        print("\n── pip crashed ──────────────────────────────────", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)
        print("─────────────────────────────────────────────────\n", file=sys.stderr)

    sys.excepthook = on_exception

    try:
        root = tk.Tk()

        def tk_exception_handler(exc, val, tb):
            on_exception(exc, val, tb)

        root.report_callback_exception = tk_exception_handler
        app = Companion(root)
        root.mainloop()

    except Exception:
        print("\n── pip failed to start ──────────────────────────", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("─────────────────────────────────────────────────\n", file=sys.stderr)
        input("press enter to close...")
        sys.exit(1)