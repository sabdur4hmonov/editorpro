"""CPU odam niqobi: OpenCV Zoo PPHumanSeg. Model ruxsatsiz yuklanmaydi."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request

import numpy as np
import common as C
from motion import cv2

MODEL = C.ROOT / "assets/models/pphumanseg.onnx"
SIZE = 6163938
SHA256 = "552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24"
SOURCE = "https://github.com/opencv/opencv_zoo/tree/main/models/human_segmentation_pphumanseg"
WEIGHTS = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx"
LICENSE = "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/human_segmentation_pphumanseg/LICENSE"


def verify(path: Path = MODEL) -> bool:
    return path.is_file() and path.stat().st_size == SIZE and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256


def download() -> None:
    if verify():
        C.info("Model avvaldan mavjud, SHA256 mos.")
        return
    if MODEL.exists():
        raise C.MontajError("Mavjud model SHA256 mos emas; ustiga yozilmadi.")
    try:
        with urllib.request.urlopen(WEIGHTS, timeout=60) as response:
            data = response.read(SIZE + 1)
        if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
            raise C.MontajError("Model hajmi yoki SHA256 mos emas; saqlanmadi.")
        with urllib.request.urlopen(LICENSE, timeout=30) as response:
            license_text = response.read().decode("utf-8")
    except OSError as error:
        raise C.MontajError(f"Model yuklanmadi: {error}") from error
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    MODEL.with_name("pphumanseg-LICENSE.txt").write_text(license_text, encoding="utf-8")
    MODEL.write_bytes(data)
    C.write_json({"source": SOURCE, "url": WEIGHTS, "bytes": SIZE, "sha256": SHA256,
                  "license": "Apache-2.0", "notice": "Copyright (c) 2021 PaddlePaddle Authors"},
                 MODEL.with_suffix(".credit.json"))
    C.info(f"Model tayyor: {MODEL} ({SIZE} bayt, SHA256 mos)")


class PersonMask:
    def __init__(self):
        if not verify():
            raise C.MontajError("PPHumanSeg modeli yo'q yoki SHA256 mos emas. Avval foydalanuvchi roziligi bilan "
                                "person_mask.py --download --allow-download. Model o'zi yuklanmaydi.")
        try:
            self.net = cv2.dnn.readNet(str(MODEL))
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except cv2.error as error:
            raise C.MontajError(f"PPHumanSeg ochilmadi: {error}") from error

    def infer(self, rgb: np.ndarray) -> np.ndarray:
        # Upstream: RGB, 192x192, mean/std 0.5 after division by 255.
        image = cv2.resize(rgb, (192, 192)).astype(np.float32) / 127.5 - 1.0
        self.net.setInput(cv2.dnn.blobFromImage(image))
        try:
            output = self.net.forward()
        except cv2.error as error:
            raise C.MontajError(f"PPHumanSeg hisoblash xatosi: {error}") from error
        if output.shape != (1, 2, 192, 192):
            raise C.MontajError(f"PPHumanSeg kutilmagan chiqish: {output.shape}")
        labels = np.argmax(output[0], axis=0).astype(np.float32)
        alpha = cv2.resize(labels, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
        return cv2.GaussianBlur(alpha, (0, 0), 0.7).clip(0, 1)


def restore_person(background: np.ndarray, original: np.ndarray, alpha: np.ndarray) -> None:
    a = alpha[..., None]
    background[:] = np.round(original * a + background * (1 - a)).clip(0, 255).astype(np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help=f"Modelni yuklash ({SIZE} bayt)")
    parser.add_argument("--allow-download", action="store_true", help="Foydalanuvchi shu model/hajmga rozi")
    args = parser.parse_args()
    if args.download:
        if not args.allow_download:
            C.info(f"RUXSAT KERAK: PPHumanSeg {SIZE} bayt. --allow-download faqat aniq rozilikdan keyin.")
            return 4
        download()
    else:
        C.info(f"PPHumanSeg: {'mavjud, SHA256 mos' if verify() else 'yoq yoki hash mos emas'}; {SIZE} bayt")
    return 0


if __name__ == "__main__":
    C.run_main(main)
