#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-click dependency installation and test runner for the ROV controller project.
- Verifies Python version (3.8+)
- Installs dependencies from requirements.txt
- Checks FFmpeg availability (warns if missing)
- Runs unittest discovery

Usage:
  python scripts/setup_and_test.py
"""
import os
import shutil
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(PROJECT_ROOT, 'requirements.txt')


def run(cmd, cwd=None, check=False):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, text=True)


def check_python_version():
    if sys.version_info < (3, 8):
        print(f"[ERROR] Python 3.8+ required. Detected: {sys.version.split()[0]}")
        sys.exit(2)
    print(f"[OK] Python version: {sys.version.split()[0]}")


def ensure_pip():
    try:
        import pip  # noqa: F401
        print("[OK] pip is available")
    except Exception:
        print("[INFO] pip not found. Attempting to bootstrap...")
        subprocess.check_call([sys.executable, '-m', 'ensurepip', '--upgrade'])
    # Optional: upgrade pip (non-fatal on failure)
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=False)
    except Exception:
        pass


def install_requirements():
    if not os.path.exists(REQUIREMENTS):
        print(f"[WARN] requirements.txt not found at {REQUIREMENTS}")
        return
    print("[INFO] Installing dependencies from requirements.txt ...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS], text=True)
    if result.returncode != 0:
        print("[ERROR] Dependency installation failed. See output above.")
        sys.exit(result.returncode)
    print("[OK] Dependencies installed")


def check_ffmpeg():
    path = shutil.which('ffmpeg')
    if path:
        print(f"[OK] FFmpeg found: {path}")
    else:
        print("[WARN] FFmpeg not found in PATH. Video streaming features may not work.\n"
              "      Install FFmpeg and add it to PATH (see README.md > 安装步骤).")


def run_tests():
    print("\n[INFO] Running test discovery: python -m unittest discover\n")
    start = time.time()
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test*.py'], text=True,
                            cwd=PROJECT_ROOT)
    duration = time.time() - start
    print(f"\n[INFO] Test run completed in {duration:.2f}s with exit code {result.returncode}")
    if result.returncode == 0:
        print("[OK] Tests completed (note: it's fine if 0 tests were discovered in current repo state).")
    return result.returncode


def main():
    print("=== ROV Controller — Setup & Test ===")
    print(f"Project root: {PROJECT_ROOT}")
    check_python_version()
    ensure_pip()
    install_requirements()
    check_ffmpeg()
    exit_code = run_tests()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
