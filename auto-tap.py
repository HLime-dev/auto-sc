#!/usr/bin/env python3
"""
Monitor & Auto-Tap untuk Termux (Root Required)
=================================================
Fitur:
1. Detect Package  -> pilih manual dari daftar aplikasi terinstall,
                       atau auto-select dari aplikasi yang sedang foreground
2. Auto Tap         -> monitor kondisi package terpilih (aktif/tidak aktif di foreground)
                       lalu jalankan simulasi tap otomatis selama package tsb aktif

Catatan:
- Butuh root (su) dan Termux.
- Gunakan hanya untuk aplikasi/skenario milik sendiri (testing, automation pribadi).
"""

import subprocess
import time
import re
import sys
import json
import os

CONFIG_FILE = "autotap_config.json"


# ---------------------------------------------------------
# Util: jalankan command via root
# ---------------------------------------------------------
def run_su(cmd, timeout=6):
    try:
        result = subprocess.run(
            ["su", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"[Error su] {e}")
        return ""


def check_root():
    out = run_su("id")
    if "uid=0" not in out:
        print("❌ Root tidak terdeteksi. Pastikan device sudah di-root dan izinkan akses su untuk Termux.")
        sys.exit(1)
    print("✅ Root OK\n")


# ---------------------------------------------------------
# 1. DETECT PACKAGE
# ---------------------------------------------------------
def get_installed_packages():
    """Daftar package terinstall (versi ringkas, hanya third-party app)"""
    out = run_su("pm list packages -3")  # -3 = hanya user-installed apps
    packages = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.append(line.replace("package:", ""))
    return sorted(packages)


def get_foreground_package():
    """Deteksi package yang sedang aktif di foreground"""
    output = run_su("dumpsys activity activities | grep mResumedActivity")
    if not output:
        output = run_su("dumpsys window | grep mCurrentFocus")

    match = re.search(r"([a-zA-Z0-9_.]+)/[a-zA-Z0-9_.]+", output)
    if match:
        return match.group(1)
    return None


def detect_package_menu():
    print("\n=== DETECT PACKAGE ===")
    print("1) Pilih manual dari daftar aplikasi terinstall")
    print("2) Auto-select dari aplikasi yang sedang dibuka sekarang")
    choice = input("Pilih opsi [1/2]: ").strip()

    if choice == "1":
        print("\nMengambil daftar aplikasi terinstall...")
        packages = get_installed_packages()
        if not packages:
            print("Tidak ada package ditemukan.")
            return None

        for i, pkg in enumerate(packages, 1):
            print(f"{i}. {pkg}")

        idx = input("\nMasukkan nomor package yang dipilih: ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(packages):
            selected = packages[int(idx) - 1]
            print(f"✅ Package dipilih: {selected}")
            return selected
        else:
            print("Input tidak valid.")
            return None

    elif choice == "2":
        print("\nBuka aplikasi target sekarang di HP kamu...")
        input("Tekan ENTER setelah aplikasi target aktif di layar...")
        pkg = get_foreground_package()
        if pkg:
            print(f"✅ Terdeteksi package aktif: {pkg}")
            return pkg
        else:
            print("Gagal mendeteksi package aktif.")
            return None
    else:
        print("Pilihan tidak valid.")
        return None


# ---------------------------------------------------------
# 2. AUTO TAP + MONITOR
# ---------------------------------------------------------
def tap(x, y):
    run_su(f"input tap {x} {y}")


def get_screen_size():
    """Ambil resolusi layar untuk validasi koordinat (opsional)"""
    out = run_su("wm size")
    match = re.search(r"(\d+)x(\d+)", out)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def setup_tap_points():
    """Minta user memasukkan satu atau lebih titik koordinat tap"""
    width, height = get_screen_size()
    if width and height:
        print(f"Resolusi layar terdeteksi: {width}x{height}")

    points = []
    print("\nMasukkan koordinat tap (format: x,y). Kosongkan lalu ENTER untuk selesai.")
    while True:
        raw = input(f"Titik #{len(points)+1} (contoh 540,1200): ").strip()
        if raw == "":
            break
        try:
            x_str, y_str = raw.split(",")
            points.append((int(x_str.strip()), int(y_str.strip())))
        except ValueError:
            print("Format salah, gunakan: x,y")

    if not points:
        print("Tidak ada titik tap yang ditentukan, pakai default (tengah layar).")
        if width and height:
            points = [(width // 2, height // 2)]
        else:
            points = [(500, 1000)]

    return points


def auto_tap_monitor(package, tap_points, tap_interval=1.0, check_interval=2.0):
    """
    Loop utama:
    - Cek apakah 'package' sedang foreground
    - Jika aktif -> lakukan tap sesuai titik yang ditentukan (looping)
    - Jika tidak aktif -> berhenti tap, tunggu sampai aktif lagi (atau keluar jika user stop)
    """
    print(f"\n=== AUTO TAP + MONITOR: {package} ===")
    print("Ctrl+C untuk berhenti kapan saja.\n")

    last_status = None
    tap_index = 0
    last_check_time = 0

    try:
        while True:
            now = time.time()

            # Cek status foreground berkala (tidak tiap loop biar hemat resource)
            if now - last_check_time >= check_interval:
                current_fg = get_foreground_package()
                is_active = (current_fg == package)
                last_check_time = now

                if is_active != last_status:
                    ts = time.strftime("%H:%M:%S")
                    if is_active:
                        print(f"[{ts}] ✅ {package} AKTIF di layar -> mulai auto-tap")
                    else:
                        print(f"[{ts}] ⏸️  {package} TIDAK aktif (foreground: {current_fg}) -> tap dihentikan sementara")
                    last_status = is_active

            # Tap hanya jika package sedang aktif
            if last_status:
                x, y = tap_points[tap_index % len(tap_points)]
                tap(x, y)
                print(f"   -> tap di ({x}, {y})")
                tap_index += 1
                time.sleep(tap_interval)
            else:
                time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n⏹️  Auto-tap dihentikan oleh user.")


# ---------------------------------------------------------
# CONFIG SAVE/LOAD (opsional biar tidak input ulang tiap run)
# ---------------------------------------------------------
def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Konfigurasi disimpan ke {CONFIG_FILE}")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------
def main_menu():
    check_root()

    selected_package = None
    tap_points = None

    while True:
        print("\n===== MENU UTAMA =====")
        print("1. Detect Package")
        print("2. Jalankan Auto Tap + Monitor")
        print("3. Muat konfigurasi tersimpan")
        print("4. Keluar")
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            pkg = detect_package_menu()
            if pkg:
                selected_package = pkg

        elif choice == "2":
            if not selected_package:
                print("⚠️  Package belum dipilih. Jalankan menu 1 dulu.")
                continue

            tap_points = setup_tap_points()

            try:
                interval_raw = input("Interval tap dalam detik (default 1.0): ").strip()
                tap_interval = float(interval_raw) if interval_raw else 1.0
            except ValueError:
                tap_interval = 1.0

            save = input("Simpan konfigurasi ini untuk next run? (y/n): ").strip().lower()
            if save == "y":
                save_config({
                    "package": selected_package,
                    "tap_points": tap_points,
                    "tap_interval": tap_interval
                })

            auto_tap_monitor(selected_package, tap_points, tap_interval)

        elif choice == "3":
            cfg = load_config()
            if cfg:
                selected_package = cfg["package"]
                tap_points = [tuple(p) for p in cfg["tap_points"]]
                tap_interval = cfg.get("tap_interval", 1.0)
                print(f"✅ Konfigurasi dimuat: package={selected_package}, titik={tap_points}, interval={tap_interval}")
                run_now = input("Jalankan sekarang? (y/n): ").strip().lower()
                if run_now == "y":
                    auto_tap_monitor(selected_package, tap_points, tap_interval)
            else:
                print("Tidak ada konfigurasi tersimpan.")

        elif choice == "4":
            print("Keluar. Sampai jumpa 👋")
            break

        else:
            print("Pilihan tidak valid.")


if __name__ == "__main__":
    main_menu()
