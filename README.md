# Pip 🤖

Pip is a tiny pixel art desktop companion that lives on your screen and actually pays attention.

He dances when Spotify is playing, gets hyped when you open a game, pesters you when you've been idle too long, comments on the weather, keeps a diary of your day, and talks back when you type to him. He doesn't do much. He's just there. And somehow that's enough.

---

## What Pip does

| Trigger | Reaction |
|---|---|
| Spotify playing | Dances and shows the song name |
| New song | Updates the bubble with the track |
| Game detected (Steam / Epic) | Gets excited, cheers you on |
| Coding (VS Code, etc.) | Occasionally drops a comment |
| Idle too long | Gets sleepy, starts pestering you |
| Come back from idle | Surprised and happy |
| Battery under 20% | Annoyed, tells you to plug in |
| New hour | Notes the time passing |
| Time of day | Mood and messages shift morning → night |
| Weather (if city is set) | Comments on rain, sun, snow, etc. |
| Seasonal / holidays | Special messages in October and December |
| Git repo not committed | Bugs you about it |
| Long session | Screen time check-ins |
| Click | Squishes, says something |
| Double click | Jumps |
| Drag | Ragdoll physics, says something |
| Shake rapidly | Goes dizzy |
| Throw hard | Bounces off screen edges |

---

## Setup

**Requirements:** Python 3.8+, Windows recommended (for full app-awareness)

```bash
pip install pillow psutil pywin32 requests
```

Drop your sprites in the `sprites/` folder, then:

```bash
python companion.py
```

---

## Sprites

Pip expects six PNGs in `sprites/`:

```
idle.png · happy.png · surprised.png · annoyed.png · talking.png · sleepy.png
```

Each should be 223×223px with a transparent background. Swap them out for your own art anytime.

---

## Controls

| Input | Action |
|---|---|
| Left click | Squish + says something |
| Double click | Jumps |
| Drag | Ragdoll floaty physics |
| Shake during drag | Goes dizzy |
| Throw fast | Bounces off walls |
| Hover | Glow ring appears |

### Icon bar (always visible below Pip)

| Icon | Left click | Right click |
|---|---|---|
| 🤍 | Pet Pip (+mood) | Show current mood |
| 🍪 | Feed Pip (+food) | Show hunger level |
| 🎵 | Now playing | Open diary |
| 🎮 | Current game | Screen time |
| 🏆 | Achievements | — |
| 💬 | Talk to Pip | — |
| ⚙ | Settings | — |
| ✕ | Close Pip | — |

---

## Settings

Open ⚙ to configure:

- **Name** — what Pip calls himself on startup
- **Idle timeout** — minutes before he gets bored
- **City** — for weather (uses wttr.in, no API key needed)
- **Git repos** — semicolon-separated paths to repos to watch
- **Git warn after** — minutes since last commit before he bugs you
- **Personality** — `chill` / `hype` / `sleepy`

---

## Local files (not pushed to git)

```
settings.json   — your personal config
state.json      — mood, achievements, food level, session data
pip_log.json    — pip's diary
```

Each generates fresh on first run, so anyone who clones the repo gets their own clean slate.

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
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Achievements

| Achievement | How to unlock |
|---|---|
| 🤍 first touch | Pet Pip once |
| 🐾 lap cat | Pet Pip 10 times |
| 💕 beloved | Pet Pip 50 times |
| 🌀 dizzy maker | Shake Pip once |
| 🎡 chaos agent | Shake Pip 5 times |
| 🚀 yeet | Throw Pip once |
| 🎯 pip launcher | Throw Pip 10 times |
| 🍪 feeder | Feed Pip once |
| 👨‍🍳 chef | Feed Pip 10 times |
| ⏰ long session | 3 hours in one session |
| 🌙 no life (affectionate) | 6 hours in one session |

---

## Credits

Built with Python, tkinter, and too much affection for small robots.