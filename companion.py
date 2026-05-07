import tkinter as tk
from PIL import Image, ImageTk
import random
import datetime
import os

# ── config ────────────────────────────────────────────────────────────────────
SPRITE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_SIZE = 223
BUBBLE_DURATION = 4000  # ms

MESSAGES = {
    "morning": [
        "good morning! ☀️",
        "rise and grind i guess",
        "coffee first. everything else second.",
        "today is going to be ok",
        "gm gm gm",
    ],
    "afternoon": [
        "how's it going?",
        "don't forget to drink water",
        "you're doing great",
        "take a break maybe?",
        "still here. still watching.",
    ],
    "evening": [
        "almost done for the day!",
        "proud of you tbh",
        "what did you make today?",
        "evening vibes only",
        "wind down soon ok?",
    ],
    "night": [
        "you should sleep...",
        "it's late. just saying.",
        "zzzz... oh! still here",
        "night owl detected",
        "go to bed. please.",
    ],
}

def get_time_state():
    h = datetime.datetime.now().hour
    if 6 <= h < 12:
        return "morning", "idle"
    elif 12 <= h < 17:
        return "afternoon", "happy"
    elif 17 <= h < 21:
        return "evening", "idle"
    else:
        return "night", "sleepy"


# ── app ───────────────────────────────────────────────────────────────────────
class Companion:
    def __init__(self, root):
        self.root = root
        self.root.title("companion")
        self.root.overrideredirect(True)          # no window border
        self.root.attributes("-topmost", True)    # always on top
        self.root.attributes("-transparentcolor", "#010101")  # chroma key bg
        self.root.configure(bg="#010101")
        self.root.resizable(False, False)

        # position bottom right
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{SPRITE_SIZE}x{SPRITE_SIZE+60}+{sw-SPRITE_SIZE-20}+{sh-SPRITE_SIZE-80}")

        # load sprites
        self.sprites = {}
        for name in ["idle", "happy", "surprised", "annoyed", "talking", "sleepy"]:
            path = os.path.join(SPRITE_DIR, f"{name}.png")
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA").resize((SPRITE_SIZE, SPRITE_SIZE), Image.NEAREST)
                self.sprites[name] = ImageTk.PhotoImage(img)
        
        # fallback if sleepy missing
        if "sleepy" not in self.sprites and "annoyed" in self.sprites:
            self.sprites["sleepy"] = self.sprites["annoyed"]

        # speech bubble label (above sprite)
        self.bubble_var = tk.StringVar()
        self.bubble = tk.Label(
            root,
            textvariable=self.bubble_var,
            bg="#1a1a2e",
            fg="#a0d8ef",
            font=("Courier New", 10, "bold"),
            wraplength=200,
            justify="center",
            padx=8,
            pady=5,
            relief="flat",
            bd=0,
        )
        self.bubble.place(x=0, y=0, width=SPRITE_SIZE, height=55)
        self.bubble.place_forget()

        # sprite label
        self.label = tk.Label(root, bg="#010101", bd=0, highlightthickness=0)
        self.label.place(x=0, y=60, width=SPRITE_SIZE, height=SPRITE_SIZE)

        # set initial expression based on time
        _, expr = get_time_state()
        self.set_expression(expr)

        # dragging
        self._drag_x = 0
        self._drag_y = 0
        self.label.bind("<ButtonPress-1>", self.on_click)
        self.label.bind("<B1-Motion>", self.on_drag)

        # right click to quit
        self.label.bind("<Button-3>", lambda e: self.root.destroy())

        # auto message timer
        self.schedule_message()

    def set_expression(self, name):
        if name in self.sprites:
            self.label.configure(image=self.sprites[name])
            self.current = name

    def show_bubble(self, text, expr=None):
        if expr:
            self.set_expression(expr)
        self.bubble_var.set(text)
        self.bubble.place(x=0, y=0, width=SPRITE_SIZE, height=55)
        self.root.after(BUBBLE_DURATION, self.hide_bubble)

    def hide_bubble(self):
        self.bubble.place_forget()
        _, expr = get_time_state()
        self.set_expression(expr)

    def on_click(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        # show a message on click
        time_key, _ = get_time_state()
        msg = random.choice(MESSAGES[time_key])
        self.show_bubble(msg, "talking")

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def schedule_message(self):
        # random message every 3-7 minutes
        delay = random.randint(3 * 60 * 1000, 7 * 60 * 1000)
        self.root.after(delay, self.auto_message)

    def auto_message(self):
        time_key, expr = get_time_state()
        msg = random.choice(MESSAGES[time_key])
        self.show_bubble(msg, "talking")
        self.schedule_message()


# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = Companion(root)
    root.mainloop()
