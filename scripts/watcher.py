"""Chatdan montaj: jobs/inbox/ ga tushgan topshiriqlarni shu kompyuterda bajaradi.

Ishga tushirish: loyiha papkasidagi start_watcher.bat ni ikki marta bosing
(yoki: .venv\\Scripts\\python.exe scripts\\watcher.py). Oyna ochiq turguncha ishlaydi,
to'xtatish uchun oynani yoping yoki Ctrl+C bosing.

Qanday ishlaydi:
  1) Claude (chatdan) jobs/inbox/<id>.json fayl yozadi.
  2) Watcher uni o'qib, FAQAT quyidagi tayyor amallardan birini bajaradi:
       pipeline, analyze, selftest, preview, git_commit, install_deps
     Ixtiyoriy buyruq bajarilmaydi: topshiriqdagi har bir maydon tekshiriladi va
     faqat shu loyihaning skriptlari (yoki git commit) ishga tushadi.
  3) Natija jobs/done/<id>.json ga, to'liq log jobs/logs/<id>.log ga yoziladi.

Asl videolar o'zgarmaydi (skriptlar ularni faqat o'qiydi).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import common as C

VERSION = 3
JOBS = C.ROOT / "jobs"
INBOX, DONE, LOGS, PREVIEW = JOBS / "inbox", JOBS / "done", JOBS / "logs", JOBS / "preview"
HEARTBEAT = JOBS / "watcher.json"
SCRIPTS = Path(__file__).resolve().parent
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
LANGS = {"uz", "ru", "en", "auto"}
JOB_TIMEOUT = 3 * 3600
DEPS = ["pillow", "opencv-python", "numpy"]   # install_deps amali faqat shularni o'rnatadi
STARTED = time.time()


# ---------------------------------------------------------------- tekshiruv

def _path(value, exts: set, what: str) -> Path:
    """Topshiriqdagi fayl yo'lini tekshiradi: mavjud fayl va to'g'ri kengaytma bo'lishi shart."""
    if not isinstance(value, str) or not value.strip():
        raise C.MontajError(f"{what} yo'li berilmagan.")
    p = Path(value.strip().strip('"'))
    if not p.is_absolute():
        p = C.ROOT / p
    p = p.resolve()
    if not p.is_file():
        raise C.MontajError(f"{what} topilmadi: {p}")
    if p.suffix.lower() not in exts:
        raise C.MontajError(f"{what} kengaytmasi mos emas ({p.suffix}). Mumkin: {', '.join(sorted(exts))}")
    return p


def _flag(opts: dict, key: str) -> bool:
    value = opts.get(key, False)
    if not isinstance(value, bool):
        raise C.MontajError(f"options.{key} true yoki false bo'lishi kerak.")
    return value


def build_command(job: dict) -> tuple[list, dict]:
    """Topshiriqdan buyruq (argumentlar ro'yxati) yasaydi. Noma'lum narsa bo'lsa rad etadi."""
    action = job.get("action")
    opts = job.get("options") or {}
    if not isinstance(opts, dict):
        raise C.MontajError("options obyekt bo'lishi kerak.")
    py = sys.executable
    info: dict = {}

    if action == "pipeline":
        allowed = {"approve_subs", "no_subs", "no_cut", "no_repeats", "force",
                   "language", "model", "silence_db", "music", "brand", "engine", "stills",
                   "no_silence", "remove", "trim"}
        unknown = set(opts) - allowed
        if unknown:
            raise C.MontajError(f"pipeline uchun noma'lum sozlama: {', '.join(sorted(unknown))}")
        video = _path(job.get("video"), C.VIDEO_EXTS, "Video")
        cmd = [py, str(SCRIPTS / "pipeline.py"), str(video)]
        for key in ("remove", "trim"):
            if key in opts:
                if not isinstance(opts[key], str) or not re.fullmatch(r"[0-9.,\- ]{3,400}", opts[key]):
                    raise C.MontajError(f"{key}: \"10-15,22.5-24\" ko'rinishidagi matn bo'lishi kerak.")
                cmd += [f"--{key}", opts[key]]
        for key, arg in (("approve_subs", "--approve-subs"), ("no_subs", "--no-subs"), ("no_cut", "--no-cut"),
                         ("no_repeats", "--no-repeats"), ("force", "--force"), ("no_silence", "--no-silence")):
            if _flag(opts, key):
                cmd.append(arg)
        if "language" in opts:
            if opts["language"] not in LANGS:
                raise C.MontajError(f"language noto'g'ri. Mumkin: {', '.join(sorted(LANGS))}")
            cmd += ["--language", opts["language"]]
        if "model" in opts:
            if not isinstance(opts["model"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-/]{0,80}", opts["model"]):
                raise C.MontajError("model nomi noto'g'ri.")
            cmd += ["--model", opts["model"]]
        if "silence_db" in opts:
            if isinstance(opts["silence_db"], bool) or not isinstance(opts["silence_db"], (int, float)) \
                    or not -80 <= opts["silence_db"] <= -5:
                raise C.MontajError("silence_db -80 va -5 orasidagi son bo'lishi kerak.")
            cmd += [f"--silence-db={opts['silence_db']}"]
        if "music" in opts:
            cmd += ["--music", str(_path(opts["music"], AUDIO_EXTS, "Musiqa"))]
        if "brand" in opts:
            if opts["brand"] not in C.list_brands():
                raise C.MontajError(f"Brend topilmadi: {opts['brand']!r}. Mavjudlari: "
                                    + (", ".join(C.list_brands()) or "hali yo'q"))
            cmd += ["--brand", opts["brand"]]
        if "engine" in opts:
            if opts["engine"] not in ("motion", "ass", "off"):
                raise C.MontajError("engine: motion, ass yoki off bo'lishi kerak.")
            cmd += ["--engine", opts["engine"]]
        if "stills" in opts:
            times = opts["stills"]
            if (not isinstance(times, list) or not 1 <= len(times) <= 12
                    or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in times)):
                raise C.MontajError("stills: 1 tadan 12 tagacha musbat son ro'yxati bo'lishi kerak.")
            cmd += ["--stills", ",".join(f"{float(x):.3f}" for x in times)]
        info = {"video": str(video), "work": str(C.TEMP_DIR / C.slugify(video.stem)),
                "output": str(C.OUTPUT_DIR / f"{C.output_stem(video.stem)}_final.mp4"),
                "stills": "stills" in opts}
        return cmd, info

    if action == "analyze":
        unknown = set(opts) - {"no_whisper"}
        if unknown:
            raise C.MontajError(f"analyze uchun noma'lum sozlama: {', '.join(sorted(unknown))}")
        cmd = [py, str(SCRIPTS / "analyze_samples.py")]
        if _flag(opts, "no_whisper"):
            cmd.append("--no-whisper")
        return cmd, {"report": str(C.TEMP_DIR / "analysis" / "report.json")}

    if action == "selftest":
        unknown = set(opts) - {"no_whisper"}
        if unknown:
            raise C.MontajError(f"selftest uchun noma'lum sozlama: {', '.join(sorted(unknown))}")
        cmd = [py, str(SCRIPTS / "selftest.py")]
        if _flag(opts, "no_whisper"):
            cmd.append("--no-whisper")
        return cmd, {}

    if action == "install_deps":
        if opts:
            raise C.MontajError("install_deps uchun sozlama yo'q.")
        # faqat shu ro'yxatdagi kutubxonalar, faqat .venv ichiga
        return [py, "-m", "pip", "install", "--disable-pip-version-check", *DEPS], {"deps": DEPS}

    if action == "preview":
        if opts:
            raise C.MontajError("preview uchun sozlama yo'q.")
        video = _path(job.get("video"), C.VIDEO_EXTS, "Video")
        return [], {"video": str(video)}

    if action == "git_commit":
        if opts:
            raise C.MontajError("git_commit uchun sozlama yo'q.")
        message = job.get("message")
        if not isinstance(message, str) or not message.strip() or len(message) > 2000:
            raise C.MontajError("git_commit uchun 'message' (2000 belgigacha matn) kerak.")
        return [], {"message": message.strip()}

    raise C.MontajError(f"Noma'lum amal: {action!r}. Mumkin: pipeline, analyze, selftest, preview, "
                        "git_commit, install_deps")


# ---------------------------------------------------------------- bajarish

def write_heartbeat(state: str, job_id: str | None = None) -> None:
    data = {"alive_at": round(time.time(), 1), "started_at": round(STARTED, 1), "pid": os.getpid(),
            "state": state, "job": job_id, "version": VERSION, "root": str(C.ROOT)}
    tmp = HEARTBEAT.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, HEARTBEAT)
    except OSError:
        pass  # fayl band bo'lsa keyingi safar yoziladi


def run_logged(cmd: list, log, job_id: str) -> int:
    """Buyruqni ishga tushiradi, chiqishini logga yozadi, ish paytida 'tirikman' belgisini yangilaydi."""
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONUTF8="1")
    log.write(">> " + " ".join(Path(c).name if i < 2 else c for i, c in enumerate(cmd)) + "\n")
    log.flush()
    proc = subprocess.Popen(cmd, cwd=str(C.ROOT), stdin=subprocess.DEVNULL, stdout=log,
                            stderr=subprocess.STDOUT, env=env)
    began = time.time()
    while True:
        try:
            return proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            write_heartbeat("running", job_id)
            if time.time() - began > JOB_TIMEOUT:
                proc.kill()
                log.write("\n[XATO] Vaqt tugadi, topshiriq to'xtatildi.\n")
                return 124


def make_preview(video: Path, job_id: str) -> str:
    """Videodan 8 ta kadrli bitta rasm yasaydi (Claude natijani ko'rishi uchun)."""
    PREVIEW.mkdir(parents=True, exist_ok=True)
    out = PREVIEW / f"{job_id}.jpg"
    duration = max(0.5, C.ffprobe_info(video)["duration"])
    C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", video, "-an",
           "-vf", f"fps=8/{duration:.3f},scale=-2:480,tile=4x2:padding=6:margin=6", "-frames:v", "1",
           "-q:v", "4", out])
    return str(out)


def tail(path: Path, lines: int = 70) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def collect_pipeline(info: dict, result: dict, job_id: str) -> None:
    """Pipeline natijalarini bitta faylga yig'adi: subtitr matni, kesilgan joylar, yakuniy video."""
    work = Path(info["work"])
    subs = work / "subs.srt"
    if subs.is_file():
        result["subs_srt"] = str(subs)
        result["subs_text"] = subs.read_text(encoding="utf-8-sig", errors="replace")
    cuts = work / "cuts.json"
    if cuts.is_file():
        plan = C.read_json(cuts)
        result["cuts"] = {"duration": plan.get("duration"), "new_duration": plan.get("new_duration"),
                          "removed": plan.get("removed", [])}
    words = work / "cut.words.json"
    if words.is_file():
        low = float(C.load_style()["whisper"].get("low_confidence", 0.5))
        all_words = C.read_json(words).get("words", [])
        result["low_confidence_words"] = [
            {"word": w["word"], "at": w["start"], "prob": w.get("prob")}
            for w in all_words if w.get("prob", 1.0) < low][:60]
        # so'zlar va vaqtlari (kesilgan video bo'yicha): grafik elementlarni vaqtga bog'lash uchun
        result["words"] = [[w["start"], w["end"], w["word"]] for w in all_words][:1500]
    result["brands"] = C.list_brands()
    if (work / "elements.json").is_file():
        result["elements_file"] = str(work / "elements.json")
    if info.get("stills"):
        shot = work / "stills.jpg"
        if result["exit_code"] == 0 and shot.is_file():
            PREVIEW.mkdir(parents=True, exist_ok=True)
            target = PREVIEW / f"{job_id}.jpg"
            target.write_bytes(shot.read_bytes())
            result["preview"] = str(target)
        return
    out = Path(info["output"])
    res_file = work / "result.json"
    if res_file.is_file():   # pipeline yozgan aniq holat (natija yo'li, ogohlantirishlar, platforma tekshiruvi)
        res = C.read_json(res_file)
        for key in ("notes", "checks"):
            if res.get(key):
                result[key] = res[key]
        if res.get("status") == "done" and res.get("output"):
            out = Path(res["output"])
    if result["exit_code"] == 0 and out.is_file():
        result["output"] = str(out)
        result["output_info"] = {k: v for k, v in C.ffprobe_info(out).items() if k != "path"}
        result["preview"] = make_preview(out, job_id)


def run_job(path: Path) -> None:
    job_id = C.slugify(path.stem)
    log_path = LOGS / f"{job_id}.log"
    result = {"id": job_id, "status": "error", "exit_code": None, "log": str(log_path),
              "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    began = time.time()
    C.info(f"[{time.strftime('%H:%M:%S')}] Topshiriq: {job_id}")
    write_heartbeat("running", job_id)
    try:
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            try:
                job = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(job, dict):
                    raise C.MontajError("Topshiriq JSON obyekt bo'lishi kerak.")
                result["action"] = job.get("action")
                cmd, info = build_command(job)
            except (json.JSONDecodeError, C.MontajError) as exc:
                result.update(status="rejected", error=str(exc))
                log.write(f"[RAD ETILDI] {exc}\n")
                C.info(f"    rad etildi: {exc}")
                return
            C.info(f"    amal: {result['action']}" + (f", video: {Path(info['video']).name}" if "video" in info else ""))

            if result["action"] == "preview":
                result["preview"] = make_preview(Path(info["video"]), job_id)
                result["video_info"] = {k: v for k, v in C.ffprobe_info(info["video"]).items() if k != "path"}
                result.update(status="ok", exit_code=0)
            elif result["action"] == "git_commit":
                msg_file = LOGS / f"{job_id}.msg"
                msg_file.write_text(info["message"] + "\n", encoding="utf-8")
                git = "git"
                code = run_logged([git, "add", "-A"], log, job_id)
                if code == 0:
                    pending = subprocess.run([git, "status", "--porcelain"], cwd=str(C.ROOT),
                                             capture_output=True, text=True).stdout.strip()
                    if pending:
                        code = run_logged([git, "commit", "-q", "-F", str(msg_file)], log, job_id)
                    else:
                        log.write("Commit qiladigan o'zgarish yo'q.\n")
                    log.flush()
                    run_logged([git, "log", "--oneline", "-n", "3"], log, job_id)
                result.update(status="ok" if code == 0 else "error", exit_code=code)
            else:
                code = run_logged(cmd, log, job_id)
                result["exit_code"] = code
                result["status"] = "ok" if code == 0 else "need_approval" if (
                    code == 3 and result["action"] == "pipeline") else "error"
                result.update({k: v for k, v in info.items() if k in ("video", "report")})
                if result["action"] == "pipeline":
                    log.flush()
                    collect_pipeline(info, result, job_id)
    except Exception as exc:  # watcher hech qachon yiqilmasligi kerak
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        result["seconds"] = round(time.time() - began, 1)
        result["log_tail"] = tail(log_path)
        C.write_json(result, DONE / f"{job_id}.json")
        try:
            path.unlink()  # bajarilgan topshiriq fayli (jobs/inbox ichida)
        except OSError:
            pass
        C.info(f"    natija: {result['status']} ({result['seconds']}s)")
        write_heartbeat("idle")


def pending_jobs() -> list:
    ready = []
    for p in sorted(INBOX.glob("*.json"), key=lambda x: x.stat().st_mtime):
        try:
            json.loads(p.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            if time.time() - p.stat().st_mtime < 5:
                continue  # fayl hali yozilayotgan bo'lishi mumkin
        ready.append(p)
    return ready


def main() -> int:
    ap = argparse.ArgumentParser(description="jobs/inbox/ dagi montaj topshiriqlarini bajaradi.")
    ap.add_argument("--once", action="store_true", help="Navbatdagi topshiriqlarni bajarib, chiqib ket")
    ap.add_argument("--interval", type=float, default=1.5, help="Tekshirish oralig'i, soniya")
    args = ap.parse_args()

    for d in (INBOX, DONE, LOGS, PREVIEW):
        d.mkdir(parents=True, exist_ok=True)
    C.need_tool("ffmpeg"), C.need_tool("ffprobe")
    C.load_style()
    if HEARTBEAT.is_file() and not args.once:
        try:
            old = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
            if time.time() - float(old.get("alive_at", 0)) < 8 and old.get("pid") != os.getpid():
                raise C.MontajError("Watcher allaqachon boshqa oynada ishlayapti. Ikkinchisi kerak emas.")
        except (json.JSONDecodeError, ValueError, OSError):
            pass

    C.info("Montaj watcher ishlayapti.")
    C.info(f"  Papka: {C.ROOT}")
    C.info("  Claude chatdan topshiriq yuborsa, shu yerda ko'rinadi.")
    C.info("  To'xtatish: shu oynani yoping yoki Ctrl+C.\n")
    write_heartbeat("idle")
    try:
        while True:
            jobs = pending_jobs()
            for job in jobs:
                run_job(job)
            if args.once:
                return 0
            write_heartbeat("idle")
            time.sleep(args.interval)
    finally:
        try:
            HEARTBEAT.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    C.run_main(main)
