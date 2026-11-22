"""Layer 6: what the captions say, what the pictures show and how the reels open.

Measured with models trained on Pakistani jewellery shops (Development/data_collection):
  caption type   Model C, a fine-tuned multilingual MiniLM (offer, price, call to order, product details, ...)
  picture tags   Model D, frozen CLIP ViT-B-32 + heads trained on 300 person-checked pictures (face, jewellery worn)
  reel opening   from the reel itself: a face / text on screen in the first 3 seconds (Model D + EasyOCR),
                 scene cuts (PySceneDetect), length, and speech or singing (Silero VAD)
How a gap is found (same rules as the other layers):
  1. your competitor does it more often than you (Fisher exact test), and
  2. it works: their posts with it beat their other posts (Mann-Whitney), or it was proven across Pakistani
     jewellery shops (each shop compared with itself, Wilcoxon, corrected for many traits: jewellery_evidence.json).
  Both corrected for testing many traits (Benjamini-Hochberg). Otherwise, at most a few are shown as "worth testing".
Every part is optional: a missing model file or library only skips that part, and the app says so.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

from . import media_scoring as ms, post_results as pr
from .gap_common import NOT_PROVEN, P_SHOWN, P_STRONG, Pair, _evidence, _gap, _p, bh_accept, count_text, more_text

logger = logging.getLogger("optistratix.analysis.content")

MODELS = Path(__file__).parent / "models"
CAPTION_DIR = MODELS / "caption_model"
PICTURE_HEADS = MODELS / "picture_heads.joblib"
EVIDENCE_FILE = MODELS / "jewellery_evidence.json"
MAX_REELS = 20                 # an engineering limit: reels are big downloads
OPENING_SECONDS = (0.5, 1.5, 2.5)
MAX_WORTH_TESTING = 3
_cache: dict[str, Any] = {}

# trait key -> (column, scope, short name, what the competitor does, idea, gap kind)
TRAITS = {
    "face":           ("face", "all", "a face", "shows a person's face in their pictures",
                       "Try showing the jewellery on a person, face in the frame, in a few posts.", "picture"),
    "worn":           ("worn", "all", "jewellery worn", "shows the jewellery being worn",
                       "Try photos of the jewellery worn on a model instead of laid on a table.", "picture"),
    "price":          ("cap_price", "all", "the price", "states the price in the caption",
                       "Try writing the price in a few captions.", "caption"),
    "offer":          ("cap_offer", "all", "an offer", "announces an offer or sale in the caption",
                       "Try a clear offer (discount, free delivery, bundle) in a few captions.", "caption"),
    "call_to_order":  ("cap_call_to_order", "all", "how to order", "tells people how to order (DM, WhatsApp, website)",
                       "End your captions with how to order: DM, WhatsApp number or website.", "caption"),
    "product_details": ("cap_product_details", "all", "product details", "describes the product (material, size, colours)",
                        "Add the material, size and colours to your captions.", "caption"),
    "new_arrival":    ("cap_new_arrival", "all", "new arrivals", "announces new arrivals and restocks",
                       "Announce new arrivals and restocks in your captions.", "caption"),
    "review":         ("cap_review", "all", "customer reviews", "shares customer reviews and delivered orders",
                       "Share a few customer reviews or delivered orders.", "caption"),
    "event_season":   ("cap_event_season", "all", "events and seasons", "ties posts to events (Eid, weddings, Valentine's)",
                       "Tie a few posts to the coming event or season.", "caption"),
    "reel_face":      ("face_in_first_3s", "reel", "a face in the first 3 seconds", "opens their reels with a face",
                       "Start a few reels with a person on screen in the first 3 seconds.", "reel"),
    "reel_text":      ("text_in_first_3s", "reel", "text in the first 3 seconds", "opens their reels with text on screen",
                       "Start a few reels with a short line of text on screen.", "reel"),
    "reel_cut":       ("cut_in_first_3s", "reel", "a quick cut in the first 3 seconds", "changes the shot within the first 3 seconds of their reels",
                       "Try changing the shot within the first 3 seconds of a reel.", "reel"),
    "reel_voice":     ("has_voice", "reel", "a voice", "has someone speaking or singing in their reels",
                       "Try a short voice-over in a few reels.", "reel"),
    "reel_fast":      ("fast_editing", "reel", "fast editing", "edits their reels with more, shorter shots",
                       "Try reels with more, shorter shots.", "reel"),
    "reel_short":     ("short_reel", "reel", "shorter reels", "keeps their reels short",
                       "Try a few shorter reels.", "reel"),
}
CAPTION_LABELS = ["offer", "new_arrival", "price", "call_to_order", "product_details", "review", "behind_the_scenes",
                  "event_season", "other"]


# ------------------------------------------------------------------ what can run here
def _lib(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:  # noqa: BLE001
        return False


def status() -> dict[str, dict[str, Any]]:
    return {
        "captions": {"available": CAPTION_DIR.exists() and _lib("transformers"),
                     "missing": "" if CAPTION_DIR.exists() else "models/caption_model"},
        "pictures": {"available": PICTURE_HEADS.exists() and _lib("open_clip") and _lib("joblib"),
                     "missing": "" if PICTURE_HEADS.exists() else "models/picture_heads.joblib"},
        "reels": {"available": PICTURE_HEADS.exists() and _lib("open_clip") and _lib("cv2"), "missing": ""},
    }


def evidence() -> dict[str, Any]:
    if "evidence" not in _cache:
        try:
            _cache["evidence"] = json.loads(EVIDENCE_FILE.read_text())
        except Exception:  # noqa: BLE001 - the layer still works on the pair alone
            _cache["evidence"] = {}
    return _cache["evidence"]


# ------------------------------------------------------------------ Model C: caption type
def _caption_model():
    if "caption" not in _cache:
        import torch
        from transformers import AutoModel, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(CAPTION_DIR)
        enc = AutoModel.from_pretrained(CAPTION_DIR).eval()
        saved = torch.load(CAPTION_DIR / "head.pt", map_location="cpu")
        head = torch.nn.Linear(enc.config.hidden_size, len(saved["labels"]))
        head.load_state_dict(saved["head"])
        _cache["caption"] = (tok, enc, head.eval(), saved["labels"])
    return _cache["caption"]


def caption_labels(captions: pd.Series) -> pd.DataFrame:
    import torch

    tok, enc, head, labels = _caption_model()
    texts = captions.fillna("").astype(str).str.replace(r"#\S+", "", regex=True).str.strip().tolist()
    probs = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="pt")
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            probs.append(torch.sigmoid(head((h * m).sum(1) / m.sum(1))).numpy())
    p = np.concatenate(probs) if probs else np.zeros((0, len(labels)))
    y = (p >= 0.5).astype(int)
    none = y.sum(1) == 0
    y[none, p[none].argmax(1)] = 1                       # every caption gets its most likely label at least
    out = pd.DataFrame(y, columns=[f"cap_{l}" for l in labels], index=captions.index).astype(bool)
    empty = pd.Series([t == "" for t in texts], index=captions.index)
    out.loc[empty, :] = False                            # no caption: nothing to label
    return out


# ------------------------------------------------------------------ Model D: picture tags
def _picture_model():
    if "picture" not in _cache:
        import joblib
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
        _cache["picture"] = (model.eval(), preprocess, joblib.load(PICTURE_HEADS)["heads"])
    return _cache["picture"]


def picture_tags(images: list[Image.Image]) -> list[dict[str, Any]]:
    import torch

    if not images:
        return []
    model, preprocess, heads = _picture_model()
    with torch.no_grad():
        f = model.encode_image(torch.stack([preprocess(im.convert("RGB")) for im in images]))
        X = (f / f.norm(dim=-1, keepdim=True)).numpy()
    face, shown = heads["face"].predict(X), heads["jewellery_shown"].predict(X)
    return [{"face": a == "face", "shown": b} for a, b in zip(face, shown)]


# ------------------------------------------------------------------ reels
def _ocr_text(img: Image.Image) -> str:
    if "ocr" not in _cache:
        import easyocr

        _cache["ocr"] = easyocr.Reader(["en"], gpu=False, verbose=False)
    im = img.convert("RGB")
    im.thumbnail((1080, 1080))
    return " ".join(t for _, t, conf in _cache["ocr"].readtext(np.asarray(im)) if conf >= 0.3)


def _speech_seconds(path: str) -> float:
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, timeout=120).stdout
    if not raw:
        return 0.0
    vad = get_speech_timestamps(np.frombuffer(raw, dtype=np.float32), VadOptions())
    return sum(x["end"] - x["start"] for x in vad) / 16000


def _reel(path: str) -> tuple[dict[str, Any], list[Image.Image], Image.Image | None]:
    """Length, cuts, speech, and frames (the 3 opening frames + a cover frame) of one saved reel."""
    import cv2

    cap = cv2.VideoCapture(path)
    fps, n = cap.get(cv2.CAP_PROP_FPS) or 0, cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    row: dict[str, Any] = {"duration_s": n / fps if fps else None}
    frames = []
    for t in (*OPENING_SECONDS, 1.0):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        frames.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)) if ok else None)
    cap.release()
    try:
        from scenedetect import ContentDetector, detect

        scenes = detect(path, ContentDetector())                 # PySceneDetect's published default threshold
        row["shots"] = max(len(scenes), 1)
        row["cut_in_first_3s"] = any(s[0].get_seconds() <= 3 for s in scenes[1:])
    except Exception:  # noqa: BLE001
        row["shots"], row["cut_in_first_3s"] = None, None
    try:
        row["speech_s"] = _speech_seconds(path)
    except Exception:  # noqa: BLE001
        row["speech_s"] = None
    return row, [f for f in frames[:3] if f is not None], frames[3]


def _fetch(kind: str, url: str) -> bytes | None:
    return ms._download(url, 40_000_000 if kind == "video" else 12_000_000) if url else None


def measure(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Adds the caption, picture and reel columns to a posts table (missing parts stay empty)."""
    st = status()
    out = pd.DataFrame(index=df.index)
    stats = {"captions": 0, "pictures": 0, "reels": 0, "failed": 0}
    if st["captions"]["available"] and not df.empty:
        try:
            out = out.join(caption_labels(df["caption"]))
            stats["captions"] = int(len(df))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Caption model failed: %s", exc)
    if not st["pictures"]["available"] or df.empty:
        return out, stats
    is_video = df["media_type"].fillna("").astype(str).str.lower().eq("video")
    reels = set(df[is_video].sort_values("when", ascending=False).head(MAX_REELS).index)
    jobs = [(i, "video" if is_video[i] else "image", df.at[i, "media_url"]) for i in df.index if (not is_video[i]) or i in reels]
    with ThreadPoolExecutor(max_workers=ms.WORKERS) as pool:
        blobs = dict(zip([j[0] for j in jobs], pool.map(lambda j: _fetch(j[1], j[2]), jobs)))
    stills, still_idx, opening = [], [], {}
    reel_rows: dict[int, dict[str, Any]] = {}
    for i, kind, _ in jobs:
        data = blobs.get(i)
        if data is None:
            stats["failed"] += 1
            continue
        try:
            if kind == "image":
                stills.append(Image.open(io.BytesIO(data)).convert("RGB")); still_idx.append(i)
                continue
            fd, path = tempfile.mkstemp(suffix=".mp4")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                row, first, cover = _reel(path)
            finally:
                os.unlink(path)
            reel_rows[i], opening[i] = row, first
            if cover is not None:
                stills.append(cover); still_idx.append(i)
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the rest
            logger.info("Could not read post %s: %s", i, exc)
            stats["failed"] += 1
    for col in ("face", "worn", "face_in_first_3s", "text_in_first_3s", "cut_in_first_3s", "has_voice", "duration_s", "cuts_per_10s"):
        out[col] = pd.Series(None, index=out.index, dtype=object)
    for i, tag in zip(still_idx, picture_tags(stills)):
        out.at[i, "face"], out.at[i, "worn"] = bool(tag["face"]), tag["shown"] == "worn"
    stats["pictures"] = len(still_idx)
    for i, row in reel_rows.items():
        first = opening.get(i) or []
        tags = picture_tags(first)
        text = " ".join(_ocr_text(f) for f in first) if first else ""
        dur = row.get("duration_s")
        out.at[i, "face_in_first_3s"] = any(t["face"] for t in tags) if tags else None
        out.at[i, "text_in_first_3s"] = len(re.sub(r"[^A-Za-z0-9]", "", text)) >= 4 if first else None
        out.at[i, "cut_in_first_3s"] = row.get("cut_in_first_3s")
        out.at[i, "has_voice"] = None if row.get("speech_s") is None else row["speech_s"] >= 1.0
        out.at[i, "duration_s"] = dur
        out.at[i, "cuts_per_10s"] = None if not dur or row.get("shots") is None else (row["shots"] - 1) / dur * 10
        stats["reels"] += 1
    return out, stats


# ------------------------------------------------------------------ the gaps
def _domain_line(key: str) -> tuple[str, bool]:
    ev = evidence().get("traits", {}).get(key)
    if not ev:
        return "", False
    proven = ev.get("verdict") == "helps (proven)"
    if ev.get("effect_x") is None:
        return "", False
    line = (f"Across {ev['shops_tested']} Pakistani jewellery shops (each compared with itself), posts with {TRAITS[key][2]} "
            f"got about {ev['effect_x']:.1f} times the shop's usual {ev['measure']}"
            + (f", better in {ev['shops_where_better']} of {ev['shops_tested']} shops." if proven else
               ". That was not proven, so it may not hold for every shop."))
    return line, proven and ev["effect_x"] > 1


def _relative(d: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    """Numeric reel traits as yes/no against the competitor's own usual reel (their median)."""
    d = d.copy()
    reels = other[other["format"] == "video / reel"]
    for col, new, higher in (("cuts_per_10s", "fast_editing", True), ("duration_s", "short_reel", False)):
        if col in d and col in reels and reels[col].notna().sum() >= pr.MIN_GROUP:
            med = float(reels[col].median())
            yes = (d[col] > med) if higher else (d[col] < med)
            d[new] = yes.astype(object).where(d[col].notna(), None)     # not measured stays empty
    return d


# ------------------------------------------------------------------ plain words for a shop owner
# trait key -> (what to do, what kind of post it is, one concrete thing to try)
PLAIN = {
    "face": ("Show a person with your jewellery", "Posts that show a person", "Post 3 photos of your jewellery worn by a model this week."),
    "worn": ("Show your jewellery being worn", "Posts that show the jewellery worn", "Photograph a few pieces worn, not only laid on a table."),
    "price": ("Write the price in your captions", "Captions that state the price", "Add the price to your next few captions."),
    "offer": ("Mention offers and sales", "Captions with an offer, a sale or free delivery", "Run one clear offer and say it in the caption."),
    "call_to_order": ("Tell people how to order", "Captions that say how to order", "End each caption with how to order: DM, WhatsApp or website."),
    "product_details": ("Describe the product", "Captions with the material, size and colours", "Add the material, size and colours to your captions."),
    "new_arrival": ("Announce new arrivals", "Posts announcing new pieces or restocks", "Post your next new piece as a \"New arrival\"."),
    "review": ("Share customer reviews", "Posts with customer reviews or delivered orders", "Share a happy customer's message or a delivered order."),
    "event_season": ("Post for events and seasons", "Posts tied to Eid, weddings or other events", "Plan a few posts for the next event or season."),
    "reel_face": ("Start reels with a person on screen", "Reels that show a person in the first 3 seconds", "Start your next 3 reels with a person wearing the piece."),
    "reel_text": ("Start reels with a short line of text", "Reels with text on screen in the first 3 seconds", "Put a short headline on screen at the start of your reels."),
    "reel_cut": ("Change the shot quickly in reels", "Reels that change the shot in the first 3 seconds", "Cut to a new shot within the first 3 seconds."),
    "reel_voice": ("Talk in your reels", "Reels where someone speaks or sings", "Add a short voice-over that describes the piece."),
    "reel_fast": ("Make reels from more, shorter shots", "Reels with faster editing", "Try a reel made of several short shots."),
    "reel_short": ("Keep reels short", "Shorter reels", "Try a few shorter reels."),
}


_count, _more = count_text, more_text


def _works_line(key: str) -> str:
    """One plain sentence on what jewellery shops gained, or '' when it was not proven for them."""
    ev = evidence().get("traits", {}).get(key) or {}
    if ev.get("verdict") != "helps (proven)" or not ev.get("effect_x"):
        return ""
    return f"For jewellery shops on Instagram, {PLAIN[key][1].lower()} get {_more(ev['effect_x'], ev['measure'])}."


def _how_found(key: str) -> list[str]:
    """The method, for the 'How we found this' section only."""
    ev = evidence().get("traits", {}).get(key) or {}
    t = evidence().get("typical", {}).get(key) or {}
    out = []
    if ev.get("effect_x"):
        out.append(f"Jewellery-shop evidence: {ev.get('shops_tested')} Pakistani jewellery shops that sometimes do this and "
                   f"sometimes not, each compared with itself; {ev.get('shops_where_better')} did better with it "
                   f"(Wilcoxon signed-rank, corrected for testing many traits, p = {ev.get('p_corrected', 1):.4f}).")
    if t.get("shops"):
        out.append(f"Usual share at a jewellery shop: {t['typical_share']:.0%} of its {('reels' if TRAITS[key][1] == 'reel' else 'posts')} "
                   f"(median over {t['shops']} shops in our dataset).")
    return out


MODEL_LINE = {
    "caption": "What the caption says: our caption model (a multilingual language model fine-tuned on 1,462 labelled captions).",
    "picture": "What the picture shows: our picture model (CLIP picture features with a head trained on 300 person-checked pictures).",
    "reel": "How the reel opens: frames from the first 3 seconds (our picture model and text reading), scene cuts and speech detection.",
}


def analyze(pair: Pair, up: pd.DataFrame, cp: pd.DataFrame, stats_u: dict, stats_c: dict):
    gaps: list[dict] = []
    info: dict[str, Any] = {"status": "ran", "parts": status(), "measured": {"user": stats_u, "competitor": stats_c},
                            "gaps": 0, "worth_testing": 0, "tested": 0, "market_gaps": 0, "comparison": [], "strengths": []}
    if not any(v["available"] for v in info["parts"].values()):
        info["status"] = "not_available"
        return gaps, info
    cp, up = _relative(cp, cp), _relative(up, cp)
    typical = evidence().get("typical", {})

    # ---- measure every trait on both accounts
    rows: dict[str, dict] = {}
    for key, (col, scope, name, does, idea, kind) in TRAITS.items():
        if col not in cp or col not in up:
            continue
        noun = "reels" if scope == "reel" else "posts"
        c = cp[cp["format"] == "video / reel"] if scope == "reel" else cp
        u = up[up["format"] == "video / reel"] if scope == "reel" else up
        c, u = c[c[col].notna()], u[u[col].notna()]
        if len(u) < pr.MIN_GROUP:
            continue
        mc, mu = c[col].astype(bool), u[col].astype(bool)
        k_c, k_u = int(mc.sum()), int(mu.sum())
        _, proven = _domain_line(key)
        rows[key] = {"c": c, "u": u, "mc": mc, "mu": mu, "k_c": k_c, "k_u": k_u, "n_c": len(c), "n_u": len(u),
                     "noun": noun, "kind": kind, "proven": proven, "t": (typical.get(key) or {}).get("typical_share")}

    # ---- your competitor does it more, and it works (on their own posts, or for jewellery shops)
    cand: dict[str, float] = {}
    for key, r in rows.items():
        if r["n_c"] < 2 * pr.MIN_GROUP or r["k_c"] < pr.MIN_GROUP or r["k_c"] / r["n_c"] <= r["k_u"] / r["n_u"]:
            continue
        r["lift"], r["p_work"] = pr.group_lift(r["c"], r["mc"]), pr.group_p(r["c"], r["mc"], "greater")
        if not r["proven"] and (r["lift"] is None or r["lift"] <= 1):
            continue
        cand[key] = pr.more_often_p(r["k_c"], r["n_c"], r["k_u"], r["n_u"])
    info["tested"] = len(cand)
    more_often = bh_accept(cand)
    works = bh_accept({k: rows[k]["p_work"] for k in cand if rows[k]["p_work"] is not None})
    proven = [k for k in more_often if k in works or rows[k]["proven"]]
    rest = sorted((k for k in cand if k not in proven and cand[k] < P_SHOWN),
                  key=lambda k: (not rows[k]["proven"], cand[k]))[:MAX_WORTH_TESTING]
    for key in sorted(proven, key=cand.get) + rest:
        r, (title, what, tip) = rows[key], PLAIN[key]
        is_proven = key in proven
        saw = (f"Your competitor: {_count(r['k_c'], r['n_c'], r['noun'], 'their')}. "
               f"You: {_count(r['k_u'], r['n_u'], r['noun'])}.")
        if r.get("lift") and r["lift"] > 1:
            saw += f" Their {r['noun']} like this got {_more(r['lift'], 'likes and comments')} than their other {r['noun']}."
        if _works_line(key):
            saw += " " + _works_line(key)
        top = r["c"][r["mc"]].sort_values("results", ascending=False).head(3)
        mine = r["u"].sort_values("results", ascending=False).head(2)
        numbers = [{"label": f"{what}", "you": f"{r['k_u']} of {r['n_u']}", "competitor": f"{r['k_c']} of {r['n_c']}",
                    "typical": None}]
        tech = [f"Fisher exact test (they do it more often): {_p(cand[key])}, corrected for testing {len(cand)} things."]
        if r.get("p_work") is not None:
            tech.append(f"Mann-Whitney test on their own {r['noun']} (with vs without): {_p(r['p_work'])}.")
        tech += [MODEL_LINE[r["kind"]]] + _how_found(key)
        if is_proven:
            strong = cand[key] < P_STRONG and (r["proven"] or (r.get("p_work") or 1) < P_STRONG)
            gaps.append(_gap(
                pair.project_id, f"{title}: your competitor does, you rarely do", saw, pair.why(tip), "content",
                pair.how_sure("High" if strong else "Medium"),
                _evidence(top, pair.who, pair.ca) + _evidence(mine, pair.me, pair.ua),
                {"kind": r["kind"], "who": pair.who, "context": pair.context, "numbers": numbers, "technical": tech,
                 "examples": [pr.example(x, "competitor") for _, x in top.iterrows()] + [pr.example(x, "you") for _, x in mine.iterrows()]}))
            info["gaps"] += 1
        else:
            gaps.append(_gap(
                pair.project_id, f"Worth trying: {title[0].lower() + title[1:]}", saw + " This could still be chance, so test it first.",
                tip + " Then compare the likes and comments with your usual posts.", "content", "Low", _evidence(top, pair.who, pair.ca),
                {"kind": r["kind"], "who": pair.who, "context": pair.context, "unproven": True, "numbers": numbers, "technical": tech,
                 "examples": [pr.example(x, "competitor") for _, x in top.iterrows()]}))
            info["worth_testing"] += 1

    # ---- the check-up: do more of this / you're doing well / your competitor does this; nothing else is shown
    shown = set(proven) | set(rest)
    for key, r in rows.items():
        title, what, tip = PLAIN[key]
        share_u, share_c = r["k_u"] / r["n_u"], (r["k_c"] / r["n_c"] if r["n_c"] else 0.0)
        you, them = _count(r["k_u"], r["n_u"], r["noun"]), _count(r["k_c"], r["n_c"], r["noun"], "their") if r["n_c"] else None
        group = None
        if r["proven"] and share_u < max(r["t"] or 0.0, share_c, 0.2):
            group = "do_more"
        elif r["proven"] and r["k_u"] > 0:
            group = "doing_well"
        elif (r["n_c"] and r["k_c"] >= pr.MIN_GROUP and share_c > share_u
              and pr.more_often_p(r["k_c"], r["n_c"], r["k_u"], r["n_u"]) < P_SHOWN):
            group = "competitor_does"
        if group is None:
            continue
        info["comparison"].append({
            "key": key, "kind": r["kind"], "group": group, "title": title, "why": _works_line(key), "tip": tip,
            "you_text": you[0].upper() + you[1:], "competitor_text": (them[0].upper() + them[1:]) if them else None,
            "you_share": round(share_u, 3), "competitor_share": round(share_c, 3) if r["n_c"] else None})

        if group == "doing_well" and share_u > share_c:
            info["strengths"].append({"kind": r["kind"], "label": f"{title}: you already do this",
                                      "detail": f"You: {you}. Your competitor: {them}. {_works_line(key)} Keep it up."})

        # a market gap: proven for jewellery shops, and you do it less than the usual jewellery shop
        if group != "do_more" or key in shown or r["t"] is None or share_u >= r["t"]:
            continue
        low = r["u"].sort_values("results").head(2)
        typ = f"about 1 in {max(2, round(1 / r['t']))} {r['noun']}" if r["t"] > 0 else None
        gaps.append(_gap(
            pair.project_id, title,
            f"{_works_line(key)} You: {you}. Your competitor: {them}.",
            tip + " Then compare the results with your usual posts.", "content",
            pair.how_sure("Medium", uses_context=False), _evidence(low, pair.me, pair.ua),
            {"kind": r["kind"], "who": pair.me, "context": pair.context, "market": True,
             "examples": [pr.example(x, "you") for _, x in low.iterrows()],
             "numbers": [{"label": what, "you": f"{r['k_u']} of {r['n_u']}",
                          "competitor": f"{r['k_c']} of {r['n_c']}" if r["n_c"] else None, "typical": typ}],
             "technical": ["Compared with jewellery shops on Instagram, not only with your competitor."] + [MODEL_LINE[r["kind"]]]
                          + _how_found(key)}))
        info["market_gaps"] += 1
    order = {"do_more": 0, "doing_well": 1, "competitor_does": 2}
    info["comparison"].sort(key=lambda x: order[x["group"]])
    return gaps, info
