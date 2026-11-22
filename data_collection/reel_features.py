"""Measures every saved reel (data/reels/*.mp4) so reels can be compared and modelled.

  .venv/bin/python reel_features.py            (the data_collection environment)

Per reel, in three resumable stages (each saved to data/reel_parts/, so a stopped run continues where it ended):
  1. video    length, frames per second, has sound, scene cuts (PySceneDetect ContentDetector at its published default
              threshold, 27), and 3 frames from the first 3 seconds (0.5 s, 1.5 s, 2.5 s) saved for stage 2.
  2. opening  on those 3 frames: text on screen (EasyOCR, same rule as pictures: 4+ letters/digits), a face and how
              the jewellery is shown (Model D: frozen CLIP + the heads trained on the person-checked pictures).
  3. voice    seconds of speech/singing (Silero VAD, all reels). Optional stage "t": faster-whisper transcripts (multilingual "small"), keeping only stretches Whisper itself
              accepts as speech (its own defaults: no_speech_prob < 0.6, avg_logprob > -1). Singing counts as speech
              for Whisper; this is a known limit and is checked by a person on a sample.
Writes datasets/reels_dataset.csv (one row per reel, joined to the post's numbers).
"""
from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REELS, FRAMES, PARTS = HERE / "data" / "reels", HERE / "data" / "reel_frames", HERE / "data" / "reel_parts"
OPENING_SECONDS = (0.5, 1.5, 2.5)


# ---------- stage 1: video ----------
def _video_one(path: str) -> dict:
    import cv2
    from scenedetect import ContentDetector, detect

    code = Path(path).stem
    row = {"shortcode": code}
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    row["fps"] = round(fps, 2)
    row["duration_s"] = round(n / fps, 2) if fps else None
    for k, t in enumerate(OPENING_SECONDS):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if ok:
            cv2.imwrite(str(FRAMES / f"{code}_{k}.jpg"), frame)
    cap.release()
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
    row["has_sound"] = bool(probe.stdout.strip())
    try:
        scenes = detect(path, ContentDetector())                     # default threshold 27
        row["shots"] = max(len(scenes), 1)
        firsts = [s[0].get_seconds() for s in scenes[1:]]
        row["cut_in_first_3s"] = any(t <= 3 for t in firsts)
    except Exception as exc:  # noqa: BLE001 - one broken file must not stop the rest
        row["shots"], row["cut_in_first_3s"], row["error"] = None, None, str(exc)[:120]
    return row


def stage_video(paths: list[Path]) -> pd.DataFrame:
    out = PARTS / "video.csv"
    done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["shortcode"])
    todo = [str(p) for p in paths if p.stem not in set(done["shortcode"])]
    print(f"stage 1 video: {len(done)} done, {len(todo)} to do", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for k, r in enumerate(ex.map(_video_one, todo, chunksize=4), 1):
            rows.append(r)
            if k % 50 == 0 or k == len(todo):
                done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
                done.to_csv(out, index=False)
                rows = []
                print(f"  video {k}/{len(todo)}", flush=True)
    return pd.read_csv(out)


# ---------- stage 2: opening frames ----------
def stage_opening(codes: list[str]) -> pd.DataFrame:
    import easyocr
    import joblib
    import open_clip
    import torch
    from PIL import Image

    out = PARTS / "opening.csv"
    done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["shortcode"])
    todo = [c for c in codes if c not in set(done["shortcode"]) and (FRAMES / f"{c}_0.jpg").exists()]
    print(f"stage 2 opening: {len(done)} done, {len(todo)} to do", flush=True)
    if not todo:
        return done
    heads = joblib.load(HERE / "models" / "picture_heads.joblib")["heads"]
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    model.eval()
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    rows = []
    for k, c in enumerate(todo, 1):
        frames = [Image.open(f).convert("RGB") for i in range(len(OPENING_SECONDS)) if (f := FRAMES / f"{c}_{i}.jpg").exists()]
        with torch.no_grad():
            f = model.encode_image(torch.stack([preprocess(im) for im in frames]))
            X = (f / f.norm(dim=-1, keepdim=True)).numpy()
        face = heads["face"].predict(X)
        shown = heads["jewellery_shown"].predict(X)
        texts = []
        for im in frames:
            im.thumbnail((1080, 1080))
            texts.append(" ".join(t for _, t, conf in reader.readtext(np.asarray(im)) if conf >= 0.3))
        text = " | ".join(texts)
        rows.append({"shortcode": c, "face_in_first_3s": bool((face == "face").any()),
                     "jewellery_shown_first_frame": shown[0],
                     "text_in_first_3s": len(re.sub(r"[^A-Za-z0-9]", "", text)) >= 4, "opening_text": text[:300]})
        if k % 50 == 0 or k == len(todo):
            done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
            done.to_csv(out, index=False)
            rows = []
            print(f"  opening {k}/{len(todo)}", flush=True)
    return pd.read_csv(out)


# ---------- stage 3: voice ----------
def _audio(path: Path) -> np.ndarray:
    """The sound track as 16 kHz mono floats, decoded by ffmpeg (faster-whisper's own decoder fails with new PyAV)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def stage_vad(paths: list[Path], has_sound: dict[str, bool]) -> pd.DataFrame:
    """Seconds of speech or singing per reel: Silero VAD (the trained speech detector shipped with faster-whisper).
    Fast (~0.1 s per reel). It cannot tell talking from singing; a person checks a sample for that."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    rows = []
    for k, p in enumerate(paths, 1):
        secs = 0.0
        if has_sound.get(p.stem, True):
            try:
                vad = get_speech_timestamps(_audio(p), VadOptions())
                secs = round(sum(x["end"] - x["start"] for x in vad) / 16000, 1)
            except Exception:  # noqa: BLE001 - e.g. a file with a broken sound track counts as no speech
                secs = 0.0
        rows.append({"shortcode": p.stem, "vad_speech_seconds": secs})
        if k % 200 == 0:
            print(f"  vad {k}/{len(paths)}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(PARTS / "vad.csv", index=False)
    return out


def stage_voice(paths: list[Path], has_sound: dict[str, bool]) -> pd.DataFrame:
    """Optional (slow, ~18 s per reel on this CPU): Whisper transcripts of reels with speech, for what reels talk about."""
    from faster_whisper import WhisperModel
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    out = PARTS / "voice.csv"
    done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["shortcode"])
    todo = [p for p in paths if p.stem not in set(done["shortcode"])]
    print(f"stage 3 voice: {len(done)} done, {len(todo)} to do", flush=True)
    if not todo:
        return done
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=6)
    rows = []
    for k, p in enumerate(todo, 1):
        row = {"shortcode": p.stem, "vad_speech_seconds": 0.0, "speech_seconds": 0.0, "speech_words": 0,
               "speech_language": None, "transcript": ""}
        if has_sound.get(p.stem, True):
            try:
                audio = _audio(p)
                # Silero VAD (the trained speech detector inside faster-whisper) first: Whisper only runs on reels with speech
                vad = get_speech_timestamps(audio, VadOptions())
                row["vad_speech_seconds"] = round(sum(x["end"] - x["start"] for x in vad) / 16000, 1)
                if vad:
                    segs, info = model.transcribe(audio, beam_size=1, vad_filter=True)
                    kept = [s for s in segs if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
                    row["speech_seconds"] = round(sum(s.end - s.start for s in kept), 1)
                    row["transcript"] = " ".join(s.text.strip() for s in kept)[:600]
                    row["speech_words"] = len(row["transcript"].split())
                    row["speech_language"] = info.language if kept else None
            except Exception as exc:  # noqa: BLE001
                row["transcript"] = f"[failed: {str(exc)[:80]}]"
        rows.append(row)
        if k % 5 == 0 or k == len(todo):
            done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
            done.to_csv(out, index=False)
            rows = []
            print(f"  voice {k}/{len(todo)}", flush=True)
    return pd.read_csv(out)


def main(stages: str = "123") -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    posts = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    reels = posts[posts["format"] == "reel"]
    paths = [REELS / f"{c}.mp4" for c in reels["shortcode"] if (REELS / f"{c}.mp4").exists()]
    print(f"{len(paths)} reels saved of {len(reels)} reels in the dataset", flush=True)
    video = stage_video(paths) if "1" in stages else pd.read_csv(PARTS / "video.csv")
    opening = stage_opening([p.stem for p in paths]) if "2" in stages else pd.read_csv(PARTS / "opening.csv")
    sound = dict(zip(video["shortcode"], video["has_sound"]))
    vad = stage_vad(paths, sound) if "3" in stages else pd.read_csv(PARTS / "vad.csv")
    if "t" in stages:                                          # transcripts: optional, slow
        stage_voice(paths, sound)
    d = video.merge(opening, on="shortcode", how="left").merge(vad, on="shortcode", how="left")
    if (PARTS / "voice.csv").exists():                         # transcripts done so far (not used as a feature)
        tr = pd.read_csv(PARTS / "voice.csv")[["shortcode", "speech_language", "transcript"]]
        d = d.merge(tr, on="shortcode", how="left")
    d["cuts_per_10s"] = ((d["shots"] - 1) / d["duration_s"] * 10).round(2)
    d["speech_share"] = (d["vad_speech_seconds"] / d["duration_s"]).clip(upper=1).round(2)
    d["has_voice"] = d["vad_speech_seconds"].fillna(0) >= 1.0       # at least 1 s: shorter blips are mostly noise
    keep = ["handle", "shortcode", "post_url", "posted_at", "followers", "likes", "comments", "views", "views_per_follower",
            "lift", "young_post", "part_of_day", "weekend", "caption_words", "caption_language", "hashtag_count", "is_collab"]
    d = reels[keep].merge(d, on="shortcode")
    d.to_csv(HERE / "datasets" / "reels_dataset.csv", index=False)
    print(f"reels_dataset.csv: {len(d)} reels from {d['handle'].nunique()} shops")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "123")
