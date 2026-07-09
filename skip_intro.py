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

  NEW: you no longer need to hardcode package names or coordinates.
  On startup, this script:
    1. Runs `pm list packages` and auto-finds every installed package
       starting with "com.roblox" — no manual list needed.
    2. For each of those packages, tries to read its window bounds via
       `dumpsys window windows` and computes the center point
       automatically.
  If auto-detection of a window's bounds fails (e.g. app not currently
  visible), you can still set a manual override in MANUAL_OVERRIDES
  below.
"""

import subprocess
import time
import os
import re

# ---- CONFIG ----
FLAG_FILE = "/data/data/com.termux/files/home/joined.flag"
POLL_INTERVAL = 1     # how often to check for the flag file
TAP_DELAY = 2         # seconds to wait after join before tapping
PACKAGE_PREFIX = "com.roblox"

# Optional: manually force a center point for a package if
# auto-detection doesn't work for it (e.g. window fully hidden at
# startup). Leave empty to rely fully on auto-detection.
MANUAL_OVERRIDES = {
    # "com.roblox.clientx": (1020, 220),
}
# ------------------------------


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def find_roblox_packages():
    """Auto-detect installed packages starting with com.roblox"""
    output = run("pm list packages")
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            pkg = line.replace("package:", "").strip()
            if pkg.startswith(PACKAGE_PREFIX):
                packages.append(pkg)
    return packages


def get_window_center(package):
    """Try to find the on-screen bounds of a package's window and
    return its center point (x, y). Returns None if not found."""
    output = run(f"dumpsys window windows | grep -A 5 '{package}'")
    # Look for a bounds pattern like: mFrame=[left,top][right,bottom]
    match = re.search(r"\[(\-?\d+),(\-?\d+)\]\[(\-?\d+),(\-?\d+)\]", output)
    if not match:
        return None
    left, top, right, bottom = map(int, match.groups())
    if right <= left or bottom <= top:
        return None
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    return (center_x, center_y)


def build_package_config():
    """Build the package->center mapping using auto-detection first,
    falling back to manual overrides."""
    config = {}
    for pkg in find_roblox_packages():
        center = get_window_center(pkg)
        if center is None and pkg in MANUAL_OVERRIDES:
            center = MANUAL_OVERRIDES[pkg]
        if center:
            config[pkg] = center
            print(f"Configured {pkg} -> center {center}")
        else:
            print(f"WARNING: could not determine window bounds for {pkg} "
                  f"(add it to MANUAL_OVERRIDES to fix)")
    return config


def tap(x, y):
    subprocess.run(["input", "tap", str(x), str(y)])
    print(f"Tapped ({x}, {y})")


def handle_join(package, config):
    center = config.get(package)
    if not center:
        # try a fresh lookup in case the window just appeared
        center = get_window_center(package) or MANUAL_OVERRIDES.get(package)
    if not center:
        print(f"No known center for package '{package}' — skipping")
        return

    print(f"Join detected for {package} — tapping window center")
    time.sleep(TAP_DELAY)
    tap(*center)
    print(f"Done with join cycle for {package}")


def main():
    print("Scanning for installed Roblox packages...")
    config = build_package_config()
    print(f"Tracking {len(config)} package(s): {list(config.keys())}")
    print("Watching for join flag...")
    while True:
        if os.path.exists(FLAG_FILE):
            with open(FLAG_FILE, "r") as f:
                package = f.read().strip()
            os.remove(FLAG_FILE)  # consume it immediately so it doesn't re-trigger
            if package:
                handle_join(package, config)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
