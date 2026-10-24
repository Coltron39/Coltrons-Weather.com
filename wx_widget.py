"""
COLTRONS FIRST ALERT WEATHER - DESK WIDGET
==========================================

A small always-on-top panel to keep in the corner of your screen while you
stream. Three buttons, nothing else to think about:

    WEATHER ANIMATION   runs the weather block - WEATHER, RADAR, STATEWIDE,
                        SEVENDAY - one after another on a loop. Press it
                        again to stop and go back to where you were.
    BED TIME            cuts to your OVERNIGHT scene (the bed time slate).
    BACK ON AIR         cuts back to PROGRAM.

Tick AUTO and it handles bed time by itself: OVERNIGHT at 9 PM, PROGRAM at
8 AM. Leave the widget running overnight and you never touch it.

SETUP
-----
1. pip install obsws-python
2. OBS > Tools > WebSocket Server Settings > enable, paste the password below.
3. python3 wx_widget.py

Scenes that don't exist in OBS are skipped, so nothing here can crash your
stream. Space bar toggles the animation.
"""

import time
import tkinter as tk

import obsws_python as obs

# ====== CHANGE THESE IF NEEDED ======
OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "Jklmnx8fhb7i31CZ"

# The weather animation: (scene name in OBS, seconds on air)
ANIMATION = [
    ("WEATHER",   20),
    ("RADAR",     26),
    ("STATEWIDE", 18),
    ("SEVENDAY",  22),
]

OVERNIGHT_SCENE = "OVERNIGHT"    # your bed time slate scene
PROGRAM_SCENE = "PROGRAM"        # what you come back to in the morning

BED_TIME = "21:00"               # 9 PM
REOPEN = "08:00"                 # 8 AM
# ====================================

BG = "#0d1016"
CARD = "#161a22"
INK = "#e9f3ff"
DIM = "#7f8da3"
CYAN = "#35c8ff"
RED = "#e2001a"


def to_minutes(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


class Widget:
    def __init__(self, root):
        self.root = root
        root.title("FIRST ALERT WIDGET")
        root.geometry("330x340")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.resizable(False, False)

        self.client = None
        self.scenes = set()
        self.running = False
        self.index = 0
        self.ends_at = 0
        self.return_to = None
        self.auto = tk.BooleanVar(value=False)
        self.auto.trace_add("write", lambda *_: setattr(self, "auto_did", None))
        self.auto_did = None          # last state AUTO applied: True night, False day

        # ---------- header ----------
        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(head, text="FIRST ALERT", font=("Arial", 13, "bold"),
                 fg=INK, bg=BG).pack(side="left")
        self.dot = tk.Label(head, text="\u25cf", font=("Arial", 13, "bold"),
                            fg="#ff5b5b", bg=BG)
        self.dot.pack(side="right")

        self.now_label = tk.Label(root, text="ON AIR: -", font=("Arial", 10, "bold"),
                                  fg=DIM, bg=BG)
        self.now_label.pack()

        # ---------- the big one ----------
        self.anim_btn = tk.Button(
            root, text="\u25b6  WEATHER ANIMATION", font=("Arial", 14, "bold"),
            fg="white", bg="#1f7a4d", activebackground="#2a9c63",
            relief="flat", bd=0, height=3, cursor="hand2",
            command=self.toggle)
        self.anim_btn.pack(fill="x", padx=14, pady=(10, 4))

        self.step = tk.Label(root, text="idle", font=("Arial", 11, "bold"),
                             fg=CYAN, bg=BG)
        self.step.pack(pady=(0, 8))

        # ---------- night / morning ----------
        row = tk.Frame(root, bg=BG)
        row.pack(fill="x", padx=14)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        self.bed_btn = tk.Button(row, text="BED TIME", font=("Arial", 11, "bold"),
                                 fg="white", bg="#2b3550", activebackground="#3a4870",
                                 relief="flat", bd=0, height=2, cursor="hand2",
                                 command=self.bed_time)
        self.bed_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.air_btn = tk.Button(row, text="BACK ON AIR", font=("Arial", 11, "bold"),
                                 fg="white", bg=RED, activebackground="#ff3b2f",
                                 relief="flat", bd=0, height=2, cursor="hand2",
                                 command=self.back_on_air)
        self.air_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        tk.Checkbutton(root, text=f"AUTO  bed time {BED_TIME}  \u00b7  back {REOPEN}",
                       variable=self.auto, font=("Arial", 9, "bold"),
                       fg=DIM, bg=BG, activebackground=BG, activeforeground=INK,
                       selectcolor=CARD, bd=0, highlightthickness=0).pack(pady=(12, 0))

        self.msg = tk.Label(root, text="connecting to OBS...", font=("Arial", 9),
                            fg=DIM, bg=BG, wraplength=300)
        self.msg.pack(pady=(6, 0))

        root.bind("<space>", lambda e: self.toggle())
        root.bind("<Escape>", lambda e: self.stop())

        self.connect()
        self.tick()

    # ------------------------------------------------------------ OBS plumbing
    def connect(self):
        try:
            self.client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT,
                                        password=OBS_PASSWORD, timeout=3)
            self.rescan()
            self.dot.config(fg="#4ee08a")
            self.msg.config(text="connected")
        except Exception as e:
            self.client = None
            self.dot.config(fg="#ff5b5b")
            self.msg.config(text=f"OBS not reachable - {e}")

    def rescan(self):
        try:
            data = self.client.get_scene_list()
            self.scenes = {s["sceneName"] for s in data.scenes}
        except Exception:
            self.scenes = set()

    def cut(self, scene):
        """Switch scenes, quietly doing nothing if that scene isn't in OBS."""
        if not self.client:
            self.connect()
            if not self.client:
                return False
        if self.scenes and scene not in self.scenes:
            self.msg.config(text=f"no scene named {scene} in OBS")
            return False
        try:
            self.client.set_current_program_scene(scene)
            self.now_label.config(text=f"ON AIR: {scene}")
            return True
        except Exception as e:
            self.dot.config(fg="#ff5b5b")
            self.msg.config(text=f"cut failed - {e}")
            self.client = None
            return False

    def current_scene(self):
        try:
            return self.client.get_current_program_scene().scene_name
        except Exception:
            return None

    # ------------------------------------------------------------ the animation
    def playlist(self):
        """Only the steps whose scenes actually exist."""
        if not self.scenes:
            return list(ANIMATION)
        return [(s, secs) for s, secs in ANIMATION if s in self.scenes]

    def toggle(self):
        self.stop() if self.running else self.start()

    def start(self):
        if not self.client:
            self.connect()
        self.rescan()
        steps = self.playlist()
        if not steps:
            self.msg.config(text="none of the weather scenes exist yet")
            return
        self.return_to = self.current_scene()
        self.running = True
        self.index = 0
        self.ends_at = 0                      # forces an immediate cut
        self.anim_btn.config(text="\u25a0  STOP ANIMATION", bg="#8b3030",
                             activebackground="#a33a3a")
        self.msg.config(text=f"{len(steps)} scenes on a loop")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.anim_btn.config(text="\u25b6  WEATHER ANIMATION", bg="#1f7a4d",
                             activebackground="#2a9c63")
        self.step.config(text="idle")
        if self.return_to:
            self.cut(self.return_to)
        self.msg.config(text="stopped")

    # ------------------------------------------------------------ heartbeat
    def tick(self):
        now = time.time()

        if self.running:
            steps = self.playlist()
            if not steps:
                self.stop()
            elif now >= self.ends_at:
                scene, secs = steps[self.index % len(steps)]
                if self.cut(scene):
                    self.ends_at = now + secs
                    self.index += 1
                else:
                    self.index += 1          # skip a scene that won't take
                    self.ends_at = now + 1
            else:
                scene, _ = steps[(self.index - 1) % len(steps)]
                self.step.config(text=f"{scene}  \u00b7  {int(self.ends_at - now)}s")

        if self.auto.get():
            self.check_bedtime()

        self.root.after(500, self.tick)

    def is_night(self):
        t = time.localtime()
        mins = t.tm_hour * 60 + t.tm_min
        bed, open_ = to_minutes(BED_TIME), to_minutes(REOPEN)
        return (mins >= bed or mins < open_) if bed > open_ else (bed <= mins < open_)

    def check_bedtime(self):
        """Cut once whenever we cross into night or into morning. Turning AUTO on
        mid-evening puts the slate up right away rather than waiting for 9 PM."""
        night = self.is_night()
        if self.auto_did == night:
            return
        self.auto_did = night
        self.bed_time() if night else self.back_on_air()

    # ------------------------------------------------------------ buttons
    def bed_time(self):
        self.stop()
        if self.cut(OVERNIGHT_SCENE):
            self.msg.config(text="bed time - slate is up until 8 AM")

    def back_on_air(self):
        self.stop()
        if self.cut(PROGRAM_SCENE):
            self.msg.config(text="good morning - back on air")


if __name__ == "__main__":
    root = tk.Tk()
    Widget(root)
    root.mainloop()
