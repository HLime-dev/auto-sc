#!/usr/bin/env python3
"""
skip_intro.py

Simple companion script for Termux: watches for a "joined" trigger file
(written by your existing monitor/auto-rejoin program), then taps the
screen to skip the intro screen after joining a Roblox map/server.

HOW TO WIRE IT UP:
  Since each Roblox instance here has its OWN package name
  (com.roblox.clientx, com.roblox.clientv, com.roblox.clientw,
  com.roblox.clienty), your monitor can just write the package name
  that joined, same as before:

      echo "com.roblox.clientx" > /data/data/com.termux/files/home/joined.flag

  or in Python:

      with open("/data/data/com.termux/files/home/joined.flag", "w") as f:
          f.write(package_name)

  This script polls for that file, reads which package joined, and taps
  the CENTER of that window (since tap position doesn't matter beyond
  "somewhere on the window" for skipping the intro).

CONFIGURE PACKAGE_CONFIG below with the center point of each window.
Find each window's center by taking a full-screen screenshot and
estimating (or measuring) the midpoint of that window's visible area.
"""

import subprocess
import time
import os

# ---- CONFIG (edit these) ----
FLAG_FILE = "/data/data/com.termux/files/home/joined.flag"
POLL_INTERVAL = 1  # how often to check for the flag file
TAP_DELAY = 2       # seconds to wait after join before tapping

# One entry per package = one entry per window. Just the center
# point of that window's visible area on screen.
PACKAGE_CONFIG = {
    "com.roblox.clientx": {"center": (1020, 220)},
    "com.roblox.clientv": {"center": (250, 570)},
    "com.roblox.clientw": {"center": (730, 570)},
    "com.roblox.clienty": {"center": (1150, 570)},
    # add more windows here as needed...
}
# ------------------------------


def tap(x, y):
    subprocess.run(["input", "tap", str(x), str(y)])
    print(f"Tapped ({x}, {y})")


def handle_join(package):
    config = PACKAGE_CONFIG.get(package)
    if not config:
        print(f"No config for package '{package}' — skipping")
        return

    print(f"Join detected for {package} — tapping window center")
    time.sleep(TAP_DELAY)
    x, y = config["center"]
    tap(x, y)
    print(f"Done with join cycle for {package}")


def main():
    print("Watching for join flag...")
    while True:
        if os.path.exists(FLAG_FILE):
            with open(FLAG_FILE, "r") as f:
                package = f.read().strip()
            os.remove(FLAG_FILE)  # consume it immediately so it doesn't re-trigger
            if package:
                handle_join(package)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
