# Pip 

Pip is a tiny pixel art desktop companion that lives on your screen and actually pays attention.

He dances when music is playing, gets hyped when you open a game, pesters you when you've been idle too long, and goes to sleep at 2am whether you like it or not. He doesn't do much. He's just there. And somehow that's enough.


---

## What Pip does

| Trigger | Reaction |
|---|---|
| Music / audio detected | Bobs up and down, happy expression |
| You open a game | Gets excited, cheers you on |
| You're in VS Code / coding | Occasionally comments (not too often) |
| Idle for 10+ minutes | Gets sleepy, starts pestering you |
| You come back from idle | Surprised, happy you're back |
| Battery under 20% | Annoyed, warns you to plug in |
| Time of day | Mood and messages shift morning → night |
| You click him | Says something, switches to talking expression |

---

## Setup

**Requirements:** Python 3.8+, Windows (for full app-awareness features)

```bash
pip install pillow sounddevice numpy psutil pywin32
```

Drop your sprites in the `sprites/` folder, then:

```bash
python companion.py
```

Right-click Pip to close him.

---

## Sprites

Pip expects six PNGs at `sprites/`:

```
idle.png · happy.png · surprised.png · annoyed.png · talking.png · sleepy.png
```

Each should be 223×223px with a transparent background. Swap them out for your own art anytime.

---

## Project structure

```
pip/
├── companion.py
├── sprites/
│   ├── idle.png
│   ├── happy.png
│   ├── surprised.png
│   ├── annoyed.png
│   ├── talking.png
│   └── sleepy.png
├── requirements.txt
└── README.md
```

---

## Controls

| Input | Action |
|---|---|
| Left click | Pip says something |
| Click + drag | Move Pip anywhere |
| Right click | Close |

---

## Notes

**Audio:** Pip listens to your default mic input by default. To detect system audio (music through speakers), set up a loopback device like [VB-Cable](https://vb-audio.com/Cable/) in Windows sound settings.

**Window awareness:** Requires `pywin32`. On non-Windows systems Pip still runs, he just won't know what app you're in.

---

## Credits

Built with Python, tkinter, and too much affection for small robots.
