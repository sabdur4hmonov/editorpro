"""Videoda yuz qayerdaligini topadi (zoom va kadrni to'g'ri kesish uchun).

    python scripts/face.py input/video.mp4

OpenCV ning YuNet modeli ishlatiladi (assets/models/face_yunet.onnx). Model yoki OpenCV
funksiyasi bo'lmasa None qaytadi va tizim kadr markazidan foydalanadi.
"""
from __future__ import annotations

import argparse
import statistics
import subprocess
from pathlib import Path

import numpy as np

import common as C

MODEL = C.ROOT / "assets" / "models" / "face_yunet.onnx"


def detect(video: str | Path, samples: int = 10, quiet: bool = False, style: dict | None = None) -> dict | None:
    """Yuz markazi va o'lchami (kadrga nisbatan 0..1). Topilmasa None."""
    try:
        import cv2
    except ImportError:
        return None
    if not hasattr(cv2, "FaceDetectorYN") or not MODEL.is_file():
        if not quiet:
            C.warn("Yuzni aniqlash o'chiq (model yoki OpenCV funksiyasi yo'q). Kadr markazi ishlatiladi.")
        return None
    meta = C.ffprobe_info(video)
    if not meta["has_video"] or meta["duration"] <= 0 or not meta["height"]:
        return None
    h = 480
    w = max(2, int(round(h * meta["width"] / meta["height"] / 2)) * 2)
    count = max(3, min(samples, int(meta["duration"]) + 1))
    cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(video), "-an",
           "-vf", f"fps={count}/{meta['duration']:.3f},scale={w}:{h}", "-frames:v", str(count),
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.run(cmd, capture_output=True)
    frames = len(proc.stdout) // (w * h * 3)
    if proc.returncode != 0 or frames == 0:
        return None
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)  # keraksiz ogohlantirishlarni yashirish
    except Exception:
        pass
    import hardware
    backend,target=hardware.opencv_backend(cv2,(style or {}).get('hardware',{}).get('onnx','auto'))
    def create(cpu=False):
        return cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), 0.6, 0.3, 50,
                                        cv2.dnn.DNN_BACKEND_OPENCV if cpu else backend,
                                        cv2.dnn.DNN_TARGET_CPU if cpu else target)
    try:
        try: det=create()
        except cv2.error:
            if target==cv2.dnn.DNN_TARGET_CPU: raise
            C.warn('YuNet CUDA init failed; CPU fallback.')
            target=cv2.dnn.DNN_TARGET_CPU; det=create(cpu=True)
    except Exception as exc:
        if not quiet:
            C.warn(f"Yuz modelini yuklab bo'lmadi ({exc}). Kadr markazi ishlatiladi.")
        return None
    found = []
    for i in range(frames):
        img = np.frombuffer(proc.stdout, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3)
        try:
            _, faces = det.detect(img)
        except cv2.error:
            if target!=cv2.dnn.DNN_TARGET_CPU:
                C.warn('YuNet CUDA inference failed; CPU fallback.')
                target=cv2.dnn.DNN_TARGET_CPU
                det=create(cpu=True)
                _,faces=det.detect(img)
            else: faces = None
        if faces is None or len(faces) == 0:
            continue
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]  # eng katta yuz
        found.append(((x + fw / 2) / w, (y + fh / 2) / h, fw / w, fh / h))
    if len(found) < max(2, frames * 0.4):
        return None
    def med(i: int) -> float:
        return round(float(statistics.median(float(f[i]) for f in found)), 4)

    return {"cx": med(0), "cy": med(1), "w": med(2), "h": med(3),
            "hits": len(found), "frames": frames}


def main() -> int:
    ap = argparse.ArgumentParser(description="Videoda yuz joylashuvini topadi.")
    ap.add_argument("video")
    args = ap.parse_args()
    res = detect(C.need_file(args.video, "Video"))
    if res is None:
        C.info("Yuz topilmadi.")
        return 1
    C.info(f"Yuz markazi: x={res['cx']}, y={res['cy']} (kadrga nisbatan), "
           f"o'lchami {res['w']}x{res['h']}, {res['hits']}/{res['frames']} kadrda topildi")
    return 0


if __name__ == "__main__":
    C.run_main(main)
