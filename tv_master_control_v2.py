"""
COLTRONS FIRST ALERT WEATHER - MASTER CONTROL v3
===============================================

Built around the five scenes you actually have in OBS right now:

    PROGRAM    WEATHER    RADAR    SEVENDAY    STATEWIDE

Anything else is listed as OPTIONAL. On connect this panel asks OBS for its real
scene list, then lights up the buttons for scenes that exist and greys out the
ones that don't - so the moment you add "CURRENT" or "ALERT" in OBS, hit
RESCAN and the button turns on. Nothing to edit in this file.

SETUP
-----
1. pip install obsws-python
2. OBS > Tools > WebSocket Server Settings > enable, copy the password below.
3. Run wx_feed.py in another terminal (that's what feeds the graphics).
4. python3 tv_master_control_v2.py
"""

import json
import os
import time
import tkinter as tk
from tkinter import messagebox

import obsws_python as obs

# ====== CHANGE THESE IF NEEDED ======
OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "Jklmnx8fhb7i31CZ"

WX_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "graphics", "data", "wx.json")
# ====================================

# ---------------------------------------------------------------- scene map
# label shown on the button  ->  exact OBS scene name
# LIVE = confirmed working in your OBS today.
LIVE_SCENES = [
    ("PROGRAM",   "PROGRAM"),
    ("WEATHER",   "WEATHER"),
    ("RADAR",     "RADAR"),
    ("SEVENDAY",  "SEVENDAY"),
    ("STATEWIDE", "STATEWIDE"),
]

# Scenes you may add later. Buttons stay greyed out until they exist in OBS.
OPTIONAL_SCENES = [
    ("CURRENT",       "CURRENT"),
    ("HOURLY",        "HOURLY"),
    ("ALERT",         "ALERT"),
    ("STATION ID",    "STATION ID"),
    ("NEWS DESK",     "NEWS DESK"),
    ("BREAKING NEWS", "BREAKING NEWS"),
    ("COMMERCIAL",    "COMMERCIAL"),
    ("OVERNIGHT",     "OVERNIGHT"),
]

# Auto weather block. Anything not present in OBS is skipped automatically.
# (label, seconds on air)
WEATHER_BLOCK = [
    ("WEATHER",   20),
    ("RADAR",     26),
    ("STATEWIDE", 18),
    ("SEVENDAY",  22),
    ("CURRENT",   18),   # skipped until you build a CURRENT scene
    ("HOURLY",    18),   # skipped until you build an HOURLY scene
]

# When a warning hits, cut to the first of these that exists in OBS.
ALERT_PRIORITY = ["ALERT", "BREAKING NEWS", "RADAR", "WEATHER"]

BG = "#111318"
LIVE_C = "#123152"
OPT_C = "#1b1e26"
DEAD_FG = "#4a5364"


class TVControl:
    def __init__(self, root):
        self.root = root
        self.root.title("COLTRONS FIRST ALERT WEATHER - MASTER CONTROL")
        self.root.geometry("960x720")
        self.root.configure(bg=BG)

        self.client = None
        self.obs_scenes = set()      # what OBS actually reports
        self.buttons = {}            # label -> tk.Button
        self.labels = dict(LIVE_SCENES + OPTIONAL_SCENES)

        self.auto_on = False
        self.auto_index = 0
        self.auto_job = None
        self.alert_watch_on = True
        self.last_alert_key = None

        tk.Label(root, text="COLTRONS FIRST ALERT WEATHER",
                 font=("Arial", 22, "bold"), fg="white", bg=BG).pack(pady=(16, 0))
        tk.Label(root, text="MASTER CONTROL", font=("Arial", 12, "bold"),
                 fg="#7f8da3", bg=BG).pack()

        bar = tk.Frame(root, bg=BG)
        bar.pack(pady=(10, 4))
        self.status = tk.Label(bar, text="\u25cf DISCONNECTED", font=("Arial", 11, "bold"),
                               fg="#ff5b5b", bg=BG)
        self.status.pack(side="left", padx=10)
        self.feed_status = tk.Label(bar, text="\u25cf FEED: unknown",
                                    font=("Arial", 11, "bold"), fg="#ff5b5b", bg=BG)
        self.feed_status.pack(side="left", padx=10)

        self.onair = tk.Label(root, text="ON AIR: -", font=("Arial", 14, "bold"),
                              fg="#4ee08a", bg=BG)
        self.onair.pack(pady=(2, 6))

        # ---------- live scenes ----------
        self._section(root, "ON AIR NOW   (1 - 5  or  F1 - F5)")
        g1 = tk.Frame(root, bg=BG)
        g1.pack(fill="x", padx=22)
        for i, (label, _) in enumerate(LIVE_SCENES):
            self._scene_button(g1, label, 0, i, LIVE_C, big=True)
        for i in range(len(LIVE_SCENES)):
            g1.columnconfigure(i, weight=1)

        # ---------- optional scenes ----------
        self._section(root, "OPTIONAL   (greyed out until the scene exists in OBS)")
        g2 = tk.Frame(root, bg=BG)
        g2.pack(fill="x", padx=22)
        for i, (label, _) in enumerate(OPTIONAL_SCENES):
            self._scene_button(g2, label, i // 4, i % 4, OPT_C)
        for i in range(4):
            g2.columnconfigure(i, weight=1)

        # ---------- automation ----------
        self._section(root, "AUTOMATION")
        auto = tk.Frame(root, bg=BG)
        auto.pack(fill="x", padx=22)

        self.auto_btn = tk.Button(auto, text="\u25b6 START AUTO WEATHER BLOCK  (Space)",
                                  font=("Arial", 12, "bold"), bg="#1f7a4d", fg="white",
                                  relief="flat", command=self.toggle_auto)
        self.auto_btn.pack(side="left", padx=5, pady=6, fill="x", expand=True)

        self.watch_btn = tk.Button(auto, text="FIRST ALERT WATCH: ON",
                                   font=("Arial", 12, "bold"), bg="#8b3030", fg="white",
                                   relief="flat", command=self.toggle_watch)
        self.watch_btn.pack(side="left", padx=5, pady=6, fill="x", expand=True)

        self.auto_label = tk.Label(root, text="Auto block idle.", font=("Arial", 10),
                                   fg="#7f8da3", bg=BG)
        self.auto_label.pack(pady=(2, 8))

        # ---------- bottom ----------
        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill="x", padx=22, pady=(0, 16))
        for text, color, cmd in [
            ("CONNECT TO OBS", "#1f7a4d", self.connect),
            ("RESCAN SCENES", "#2a5b9b", self.rescan),
            ("START RECORDING", "#8b3030", self.start_recording),
            ("STOP RECORDING", "#555b66", self.stop_recording),
            ("START STREAM", "#2a5b9b", self.start_stream),
            ("STOP STREAM", "#555b66", self.stop_stream),
        ]:
            tk.Button(bottom, text=text, font=("Arial", 10, "bold"), bg=color,
                      fg="white", relief="flat", command=cmd).pack(side="left", padx=3)

        self.found_label = tk.Label(root, text="Connect to see which scenes OBS reports.",
                                    font=("Arial", 9), fg="#5f6c80", bg=BG,
                                    wraplength=900, justify="left")
        self.found_label.pack(padx=26, pady=(0, 12), anchor="w")

        # ---------- hotkeys ----------
        for i, (label, _) in enumerate(LIVE_SCENES, start=1):
            root.bind(str(i), lambda e, s=label: self.switch_scene(s))
            root.bind(f"<F{i}>", lambda e, s=label: self.switch_scene(s))
        root.bind("<space>", lambda e: self.toggle_auto())
        root.bind("<F12>", lambda e: self.rescan())

        self.connect()
        self.tick()

    # ------------------------------------------------------------------- ui
    def _section(self, parent, text):
        tk.Label(parent, text=text, font=("Arial", 10, "bold"), fg="#5f6c80", bg=BG,
                 anchor="w").pack(fill="x", padx=26, pady=(12, 4))

    def _scene_button(self, parent, label, row, col, color, big=False):
        b = tk.Button(parent, text=label, font=("Arial", 12 if big else 10, "bold"),
                      bg=color, fg="white", activebackground="#3b4352",
                      activeforeground="white", relief="flat", height=3 if big else 2,
                      command=lambda s=label: self.switch_scene(s))
        b.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        self.buttons[label] = b

    def paint_buttons(self):
        """Enable buttons whose scene OBS actually has; grey out the rest."""
        live_labels = {l for l, _ in LIVE_SCENES}
        for label, btn in self.buttons.items():
            exists = self.labels[label] in self.obs_scenes if self.obs_scenes else \
                     label in live_labels
            base = LIVE_C if label in live_labels else OPT_C
            if exists:
                btn.config(state="normal", bg=base, fg="white")
            else:
                btn.config(state="disabled", bg="#15171d", fg=DEAD_FG,
                           disabledforeground=DEAD_FG)

    def has(self, label):
        if not self.obs_scenes:
            return label in {l for l, _ in LIVE_SCENES}
        return self.labels.get(label, label) in self.obs_scenes

    # ------------------------------------------------------------------ OBS
    def connect(self):
        try:
            self.client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT,
                                        password=OBS_PASSWORD, timeout=3)
            self.status.config(text="\u25cf CONNECTED TO OBS", fg="#4ee08a")
            self.rescan()
        except Exception as e:
            self.client = None
            self.status.config(text="\u25cf CONNECTION FAILED", fg="#ff5b5b")
            self.paint_buttons()
            messagebox.showerror(
                "OBS Connection",
                "Could not connect to OBS.\n\n"
                "Make sure OBS is open and WebSocket is enabled.\n\n"
                f"Details: {e}")

    def rescan(self):
        """Ask OBS for its real scene list and repaint the panel."""
        if not self.client:
            return
        try:
            resp = self.client.get_scene_list()
            names = [s.get("sceneName") for s in resp.scenes]
            self.obs_scenes = {n for n in names if n}
            known = set(self.labels.values())
            extra = sorted(self.obs_scenes - known)
            missing = [l for l, n in LIVE_SCENES if n not in self.obs_scenes]
            txt = f"OBS reports {len(self.obs_scenes)} scenes: " + ", ".join(sorted(self.obs_scenes))
            if extra:
                txt += f"\nNot on this panel yet: {', '.join(extra)}  (add them to OPTIONAL_SCENES)"
            if missing:
                txt += f"\nExpected but missing: {', '.join(missing)}"
            self.found_label.config(text=txt)
        except Exception as e:
            self.found_label.config(text=f"Could not read scene list: {e}")
        self.paint_buttons()

    def switch_scene(self, label):
        if not self.client:
            self.connect()
        if not self.client:
            return
        scene = self.labels.get(label, label)
        if self.obs_scenes and scene not in self.obs_scenes:
            self.auto_label.config(text=f"Skipped {scene} - not in OBS.")
            return
        try:
            self.client.set_current_program_scene(scene)
            self.onair.config(text=f"ON AIR: {scene}")
        except Exception as e:
            messagebox.showerror("Scene Error",
                                 f"Could not switch to:\n{scene}\n\nDetails: {e}")

    def start_recording(self):
        self._safe(lambda c: c.start_record(), "Recording")

    def stop_recording(self):
        self._safe(lambda c: c.stop_record(), "Recording")

    def start_stream(self):
        self._safe(lambda c: c.start_stream(), "Stream")

    def stop_stream(self):
        self._safe(lambda c: c.stop_stream(), "Stream")

    def _safe(self, fn, title):
        if not self.client:
            self.connect()
        if self.client:
            try:
                fn(self.client)
            except Exception as e:
                messagebox.showerror(title, str(e))

    # ---------------------------------------------------- auto weather block
    def block(self):
        """Only the steps whose scenes exist in OBS."""
        return [(l, s) for l, s in WEATHER_BLOCK if self.has(l)]

    def toggle_auto(self):
        self.auto_on = not self.auto_on
        if self.auto_on:
            if not self.block():
                self.auto_on = False
                self.auto_label.config(text="No weather scenes found - nothing to rotate.")
                return
            self.auto_index = 0
            self.auto_btn.config(text="\u25a0 STOP AUTO WEATHER BLOCK  (Space)", bg="#8b3030")
            self.run_auto()
        else:
            if self.auto_job:
                self.root.after_cancel(self.auto_job)
                self.auto_job = None
            self.auto_btn.config(text="\u25b6 START AUTO WEATHER BLOCK  (Space)", bg="#1f7a4d")
            self.auto_label.config(text="Auto block stopped.")

    def run_auto(self):
        if not self.auto_on:
            return
        steps = self.block()
        if not steps:
            self.toggle_auto()
            return
        label, seconds = steps[self.auto_index % len(steps)]
        self.switch_scene(label)
        nxt = steps[(self.auto_index + 1) % len(steps)][0]
        self.auto_label.config(
            text=f"AUTO ({len(steps)} scenes): {label} for {seconds}s  \u2192  next: {nxt}")
        self.auto_index += 1
        self.auto_job = self.root.after(seconds * 1000, self.run_auto)

    # ------------------------------------------------------ first alert watch
    def toggle_watch(self):
        self.alert_watch_on = not self.alert_watch_on
        self.watch_btn.config(
            text=f"FIRST ALERT WATCH: {'ON' if self.alert_watch_on else 'OFF'}",
            bg="#8b3030" if self.alert_watch_on else "#555b66")

    def alert_target(self):
        for label in ALERT_PRIORITY:
            if self.has(label):
                return label
        return None

    def read_feed(self):
        try:
            with open(WX_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def tick(self):
        data = self.read_feed()
        if not data:
            self.feed_status.config(text="\u25cf FEED: not running", fg="#ff5b5b")
        else:
            try:
                age = int(time.time() - os.path.getmtime(WX_JSON))
            except Exception:
                age = 0
            alerts = data.get("alerts") or []
            if age > 900:
                self.feed_status.config(text=f"\u25cf FEED: stale ({age // 60}m)",
                                        fg="#ffb02e")
            elif alerts:
                self.feed_status.config(text=f"\u25cf FEED: LIVE - {len(alerts)} ALERT(S)",
                                        fg="#ff5b5b")
            else:
                self.feed_status.config(text="\u25cf FEED: LIVE - all clear", fg="#4ee08a")

            key = "|".join(sorted(f"{a.get('event')}~{a.get('expires_label')}"
                                  for a in alerts))
            if self.alert_watch_on and alerts and key != self.last_alert_key:
                target = self.alert_target()
                if target:
                    self.switch_scene(target)
                    self.auto_label.config(
                        text=f"FIRST ALERT: cut to {target} - {alerts[0].get('event')}")
            self.last_alert_key = key

        self.root.after(5000, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    TVControl(root)
    root.mainloop()
