"""Muhitni tekshiradi: Python kutubxonalari va ffmpeg bor-yo'qligi.

    python scripts/check_env.py

Hammasi joyida bo'lsa oxirgi qatorda "libs-ok" chiqadi (chiqish kodi 0).
"""
from __future__ import annotations

import importlib
import shutil
import sys

import common as C

LIBS = [("faster_whisper", "faster-whisper"), ("scenedetect", "scenedetect"),
        ("cv2", "opencv-python"), ("numpy", "numpy")]


def main() -> int:
    C.info(f"Python {sys.version.split()[0]} ({sys.executable})")
    missing = []
    for module, package in LIBS:
        try:
            mod = importlib.import_module(module)
            C.info(f"  [bor]  {package} {getattr(mod, '__version__', '')}")
        except Exception as exc:  # ImportError yoki DLL yuklash xatosi
            missing.append(package)
            C.info(f"  [YO'Q] {package}: {exc}")
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        C.info(f"  [{'bor' if path else 'YOQ'}]  {tool}{(': ' + path) if path else ''}")
        if not path:
            missing.append(tool)
    if missing:
        C.info("Yetishmaydi: " + ", ".join(missing))
        return 1
    C.info("libs-ok")
    return 0


if __name__ == "__main__":
    C.run_main(main)
