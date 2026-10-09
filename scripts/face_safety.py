"""Face safety over time: nothing may cover the speaker's face, including entrances, exits and transitions.

Measured inside the real render (compose.py), on EVERY frame where an overlay is active:
  1. before the overlays are drawn (after fit + zoom) the face is found with YuNet on a downscaled copy;
  2. after all overlays are drawn, the share of face-box pixels that changed (> 40 grey levels) is the coverage.
Captions, cards, heroes, groups, stickers and their exits all count. Detection runs AFTER intentional
layout/background replacements, so a speaker in a split/stage is still protected. Flash is measured separately
from overlays. Every detected face is checked; missed faces and low-contrast changes remain limitations.
Result: temp/<nom>/face_safety.json (runs of frames over the limit, with the active elements) — used by
quality_gate.py as a hard check. Limit: plan quality_targets.max_face_cover or style quality.max_face_cover (0.03).
"""
from __future__ import annotations

import math

import numpy as np

import common as C

MODEL = C.ROOT / "assets" / "models" / "face_yunet.onnx"
REPLACING = {"broll", "stage", "scene", "grade", "flash"}
EXPAND = (0.18, 0.28, 0.18, 0.12)          # left, top (hair), right, bottom (chin) as a share of the face size


class FaceMonitor:
    def __init__(self, ctx, layers: list, style: dict, limit: float | None = None, scale_h: int = 480):
        import cv2
        self.cv2 = cv2
        self.W, self.H, self.fps = ctx.W, ctx.H, ctx.fps
        self.limit = float(limit if limit is not None else style.get("quality", {}).get("max_face_cover", 0.03))
        self.overlays = [l for l in layers if getattr(l, "el_type", "") not in REPLACING and not getattr(l, "behind_person", False)]
        self.sh = scale_h
        self.sw = max(2, int(round(scale_h * self.W / self.H)))
        self.det = cv2.FaceDetectorYN.create(str(MODEL), "", (self.sw, self.sh), 0.6, 0.3, 20) if MODEL.is_file() else None
        self.box = None
        self.base = None
        self.extra_boxes = []
        self.bases = []
        self.rows = []                      # (frame, t, coverage, [refs])
        self.checked = self.faces = 0

    def _face(self, frame):
        small = self.cv2.resize(frame, (self.sw, self.sh), interpolation=self.cv2.INTER_AREA)
        _, faces = self.det.detect(np.ascontiguousarray(small[..., ::-1]))
        if faces is None or not len(faces):
            return None
        boxes=[]
        for face in sorted(faces, key=lambda f:f[2]*f[3], reverse=True):
            x, y, w, h = face[:4]
            sx, sy = self.W/self.sw, self.H/self.sh
            x0, y0 = (x-w*EXPAND[0])*sx, (y-h*EXPAND[1])*sy
            x1, y1 = (x+w*(1+EXPAND[2]))*sx, (y+h*(1+EXPAND[3]))*sy
            x0,y0=max(0,int(x0)),max(0,int(y0));x1,y1=min(self.W,int(math.ceil(x1))),min(self.H,int(math.ceil(y1)))
            if x1-x0>4 and y1-y0>4:boxes.append((x0,y0,x1,y1))
        self.extra_boxes=boxes[1:]
        return boxes[0] if boxes else None

    def before(self, frame, t: float) -> None:
        self.box = self.base = None
        self.extra_boxes, self.bases = [], []
        if self.det is None or not any(l.active(t) for l in self.overlays):
            return
        self.box = self._face(frame)
        self.checked += 1
        if self.box:
            self.faces += 1
            x0, y0, x1, y1 = self.box
            self.base = frame[y0:y1, x0:x1].copy()
            self.bases=[(box, frame[box[1]:box[3],box[0]:box[2]].copy()) for box in [self.box]+self.extra_boxes]

    def after(self, frame, t: float, index: int) -> None:
        if self.box is None or self.base is None:
            return
        for rank,(box, base) in enumerate(self.bases):
            x0,y0,x1,y1=box
            diff=np.abs(frame[y0:y1,x0:x1].astype(np.int16)-base.astype(np.int16)).max(axis=2)
            cover=float((diff>40).mean())
            if cover>.002:
                refs=[getattr(l,'el_ref',type(l).__name__) for l in self.overlays if l.active(t)]
                self.rows.append((index,round(t,3),round(cover,4),refs,
                                  [round(v/d,3) for v,d in zip(box,(self.W,self.H,self.W,self.H))],rank))

    def report(self) -> dict:
        bad = [r for r in self.rows if r[2] > self.limit]
        runs, cur = [], None
        for f, t, cov, refs, box, rank in sorted(bad,key=lambda r:(r[5],r[0])):
            if cur and rank==cur['face_rank'] and f == cur["end_frame"] + 1:
                cur.update(end_frame=f, end=t, max_cover=max(cur["max_cover"], cov))
                cur["elements"] = sorted(set(cur["elements"]) | set(refs))
            else:
                cur = {"start_frame": f, "end_frame": f, "start": t, "end": t, "max_cover": cov, "elements": refs, "face_box": box, "face_rank":rank}
                runs.append(cur)
        return {"method": "per-frame YuNet face box after background/layout layers, before overlays vs after overlays; "
                          "changed-pixel share > limit = covered", "limit": self.limit,
                "frames_checked": self.checked, "frames_with_face": self.faces,
                "max_cover": max((r[2] for r in self.rows), default=0.0),
                "detector_available": self.det is not None,
                "verification": 'measured' if self.det is not None and self.faces else 'unverified_no_face',
                "violations": runs, "ok": self.det is not None and not runs}


def summary(rep: dict) -> str:
    if not rep.get('detector_available', True):
        return 'YUZ XAVFSIZLIGI [XATO]: YuNet modeli mavjud emas; o‘lchov tekshirilmagan.'
    if rep.get('verification') == 'unverified_no_face':
        return 'YUZ XAVFSIZLIGI [OGOH]: faol grafik kadrlarda yuz aniqlanmadi; qo‘lda tekshiring.'
    if rep["ok"]:
        return f"YUZ XAVFSIZLIGI [OK]: {rep['frames_checked']} kadr tekshirildi, eng ko'p yopilish {rep['max_cover']:.1%}"
    parts = [f"{v['start']:.2f}-{v['end']:.2f}s {v['max_cover']:.0%} ({', '.join(v['elements'])})" for v in rep["violations"][:6]]
    return "YUZ XAVFSIZLIGI [XATO]: yuz yopildi: " + "; ".join(parts)
