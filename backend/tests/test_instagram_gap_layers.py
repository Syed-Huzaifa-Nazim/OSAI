"""Layers 3 and 4: topics, hashtags, picture and video scores, and the content report."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image, ImageFilter

from app.analysis.instagram import (
    cnn_features, engine, gap_common, media_features as mf, media_scoring, topic_gaps, topics, train_common, train_image_quality,
    train_memorability, train_video_quality,
)
from app.models.gap import Gap


def _posts(role, cid, name, plan, n=30, followers=2000):
    out = []
    for i in range(n):
        caption, tags, fmt, likes, url = plan(i)
        out.append({
            "id": f"{role}{i}", "role": role, "competitor_id": cid, "source_id": f"s{role}{i}",
            "post_url": f"https://instagram.com/p/{role}{i}/", "media_url": url,
            "profile_url": f"https://instagram.com/{name}/", "submitted_url": f"https://instagram.com/{name}/",
            "profile_username": name, "caption": f"{caption} {tags}".strip(),
            "posted_at": f"2023-0{1 + i // 10}-{1 + i % 28:02d}T10:00:00+00:00", "media_type": fmt,
            "like_count": likes, "comment_count": 5,
            "profile_stats": {"followers_count": followers, "following_count": 300, "posts_count": 200,
                              "biography": "Shop", "external_url": "https://shop.pk", "highlights_count": 3},
            "scraped_at": "2023-09-15T00:00:00+00:00",
        })
    return out


ORDER = "New arrivals this week! Order now, available in all sizes, measurements on request"
CHAT = "just a regular day at the studio, you know how it goes"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "_model", None)
    monkeypatch.setattr(engine, "MODEL_PATH", engine.MODEL_PATH.with_name("no_such_model.joblib"))
    (tmp_path / "models").mkdir()
    monkeypatch.setattr(media_scoring, "MODELS", tmp_path / "models")
    monkeypatch.setattr(train_common, "MODELS", tmp_path / "models")
    media_scoring.reset_cache()
    yield
    media_scoring.reset_cache()


# ------------------------------------------------------------------ the correction for testing many things
def test_benjamini_hochberg_keeps_clear_wins_and_drops_lucky_ones():
    assert gap_common.bh_accept({"a": 0.001, "b": 0.5, "c": 0.9}) == {"a"}
    assert gap_common.bh_accept({"a": 0.04, "b": 0.045, "c": 0.9, "d": 0.8, "e": 0.7}) == set()   # four "p < 0.05" lucky hits
    assert gap_common.bh_accept({}) == set()


# ------------------------------------------------------------------ topics (off by default; these tests switch them on)
@pytest.fixture
def topics_on(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv("INSTAGRAM_TOPICS", "true")
    get_settings.cache_clear()              # settings are cached: read them again with topics on
    yield
    monkeypatch.delenv("INSTAGRAM_TOPICS")
    get_settings.cache_clear()


def test_topics_are_off_by_default_and_say_why():
    comp = _posts("competitor", "c1", "rival", lambda i: (ORDER, "#bridal", "Image", 300, "") if i < 12 else (CHAT, "", "Image", 110, ""))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    found, _, summary = engine.analyze_project("proj", mine + comp)
    assert not [g for g in found if g["details"]["kind"] == "topic"]
    t = summary["competitors"][0]["topics"]
    assert t["status"] == "off" and "English" in t["reason"]
    assert [g for g in found if g["details"]["kind"] == "hashtag"]             # hashtags still run


def test_the_topic_model_reads_english_and_admits_when_it_cannot_read_a_caption():
    got = topics.assign([ORDER, "aaj ka din bohat acha tha", ""])
    assert topics.info(got[0])["name"] == "Orders and availability"
    assert got[1] is None and got[2] is None


def test_a_theme_the_competitor_uses_and_wins_with_becomes_a_plain_gap(topics_on):
    comp = _posts("competitor", "c1", "rival", lambda i: (ORDER, "#bridal", "Image", 300, "") if i < 12 else (CHAT, "", "Image", 110, ""))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    found, _, summary = engine.analyze_project("proj", mine + comp)
    topic = [g for g in found if g["details"]["kind"] == "topic"]
    assert topic and "Orders and availability" in topic[0]["title"] and "12 of their" in topic[0]["description"]
    assert topic[0]["details"]["examples"] and Gap.model_validate(topic[0])
    tags = [g for g in found if g["details"]["kind"] == "hashtag"]
    assert tags and "#bridal" in tags[0]["title"]
    assert summary["competitors"][0]["topics"]["status"] == "ran"


def test_unread_captions_make_no_topic_gaps_and_the_coverage_is_reported(topics_on):
    roman = lambda i: ("aaj ka din bohat acha tha", "", "Image", 300 if i < 12 else 110, "")  # noqa: E731
    found, _, summary = engine.analyze_project("proj", _posts("own", None, "a", roman) + _posts("competitor", "c1", "b", roman))
    assert not [g for g in found if g["details"]["kind"] == "topic"]
    assert summary["competitors"][0]["topics"]["coverage"]["user"].startswith("0 of")


def test_your_best_theme_is_listed_as_a_strength_not_a_gap(topics_on):
    mine = _posts("own", None, "myshop", lambda i: (ORDER, "", "Image", 400, "") if i < 10 else (CHAT, "", "Image", 80, ""))
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 100, ""))
    found, _, summary = engine.analyze_project("proj", mine + comp)
    works = summary["competitors"][0]["report"]["works_for_you"]
    assert any("Orders and availability" in s["label"] for s in works)


# ------------------------------------------------------------------ pictures and videos
def _picture(blur: float, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:120, 0:160]
    base = np.zeros((120, 160, 3))
    base[..., 0], base[..., 1], base[..., 2] = np.sin(xx / 9) * .3 + .5, np.cos(yy / 7) * .3 + .5, ((xx // 20 + yy // 20) % 2) * .5
    im = Image.fromarray((np.clip(base, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im, float) / 255 + rng.normal(0, 0.01, (120, 160, 3))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))


@pytest.fixture
def trained_models(tmp_path):
    rng = np.random.default_rng(1)
    d = tmp_path / "train"; d.mkdir(); rows = []
    for i in range(160):
        blur = float(rng.uniform(0, 4)); _picture(blur, i).save(d / f"{i}.jpg", quality=95)
        rows.append({"image_name": f"{i}.jpg", "MOS": float(np.clip(4.7 - 0.6 * blur, 1, 5))})
    pd.DataFrame(rows).to_csv(tmp_path / "scores.csv", index=False)
    train_image_quality.main(str(d), str(tmp_path / "scores.csv"), None, 1, features="handcrafted")
    (tmp_path / "lamem.txt").write_text("\n".join(f"{r['image_name']} {r['MOS'] / 5:.3f}" for r in rows))
    train_memorability.main(str(d), str(tmp_path / "lamem.txt"), None, 1, features="handcrafted")
    media_scoring.reset_cache()


def test_the_training_scripts_save_models_the_scorer_can_load(trained_models):
    st = media_scoring.status()
    assert st["image_quality"]["available"] and st["memorability"]["available"] and not st["video_quality"]["available"]
    assert st["image_quality"]["srcc"] > 0.8 and st["image_quality"]["trained_on"] == "KonIQ-10k"


def test_sharper_pictures_score_higher(trained_models, tmp_path):
    sharp, blurry = tmp_path / "s.jpg", tmp_path / "b.jpg"
    _picture(0).save(sharp); _picture(4).save(blurry)
    df = pd.DataFrame({"media_type": ["Image", "Image"], "media_url": [str(sharp), str(blurry)], "when": pd.to_datetime(["2023-01-01"] * 2, utc=True)})
    media_scoring._download = lambda url, limit: Path(url).read_bytes()
    scores, stats = media_scoring.score_posts(df)
    assert scores.loc[0, "image_quality"] > scores.loc[1, "image_quality"] and stats["scored"] == 2


def test_reels_are_scored_frame_by_frame_with_the_picture_model(trained_models, tmp_path, monkeypatch):
    import cv2
    paths = {}
    for name, blur in (("sharp", 0.0), ("blurry", 4.0)):
        p = str(tmp_path / f"{name}.mp4")
        w = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
        for f in range(16):
            w.write(cv2.cvtColor(np.asarray(_picture(blur, f)), cv2.COLOR_RGB2BGR))
        w.release()
        paths[name] = p
    monkeypatch.setattr(media_scoring, "_download", lambda url, limit: Path(url).read_bytes())
    sharp, blurry = (media_scoring._score_one("video", paths[n]) for n in ("sharp", "blurry"))
    assert sharp["video_quality"] is None                        # no video model is trained ...
    assert sharp["reel_quality"] > blurry["reel_quality"]         # ... but the reel's frames are scored
    st = media_scoring.status()["reel_quality"]
    assert st["available"] and st["trained_on"] == "KonIQ-10k"


def test_media_gaps_compare_you_with_the_competitor_and_link_looks_to_results(trained_models, tmp_path, monkeypatch):
    for i in range(30):
        _picture(0.0, i).save(tmp_path / f"c{i}.jpg")                    # the competitor's pictures are sharp
        _picture(4.0 * (1 - i / 29), 100 + i).save(tmp_path / f"u{i}.jpg")   # yours get sharper over time ...
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 200, str(tmp_path / f"c{i}.jpg")))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 60 + 4 * i, str(tmp_path / f"u{i}.jpg")))  # ... and so do your likes
    monkeypatch.setattr(media_scoring, "_download", lambda url, limit: Path(url).read_bytes())
    found, warnings, summary = engine.analyze_project("proj", mine + comp)
    media = [g for g in found if g["details"]["kind"] == "media"]
    vs_rival = [g for g in media if g["details"]["who"] == "rival"]
    own_link = [g for g in media if g["details"]["who"] == "myshop"]
    assert any("photos look better made" in g["title"] for g in vs_rival)
    assert any("lower-quality photos get fewer likes" in g["title"] for g in own_link)
    info = summary["competitors"][0]["media"]
    assert info["status"] == "ran" and info["scored"]["user"]["scored"] == 30 and info["models"]["image_quality"]["available"]
    for g in media:
        Gap.model_validate(g)
        assert "rated by people" in " ".join(g["details"]["technical"])          # says what the score is based on
    report = summary["competitors"][0]["report"]
    assert any("lower-quality" in w["title"] for w in report["weak_spots"])


def test_without_trained_models_the_media_layer_says_so_and_does_not_guess():
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 200, "https://x/c.jpg"))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, "https://x/u.jpg"))
    found, _, summary = engine.analyze_project("proj", mine + comp)
    assert summary["competitors"][0]["media"]["status"] == "not_trained"
    assert "train_image_quality" in summary["competitors"][0]["media"]["reason"]
    assert not [g for g in found if g["details"]["kind"] == "media"]


def test_the_video_feature_reader_handles_unreadable_files(tmp_path):
    bad = tmp_path / "bad.mp4"; bad.write_bytes(b"not a video")
    assert mf.video_features(str(bad)) is None


# ------------------------------------------------------------------ one broken layer must not lose the others
def test_a_failing_layer_is_reported_and_the_rest_still_run(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("model file corrupt")
    monkeypatch.setattr(topic_gaps, "analyze", boom)
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Sidecar", 300, "") if i < 12 else (CHAT, "", "Image", 110, ""))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    found, warnings, _ = engine.analyze_project("proj", mine + comp)
    assert any("topic and hashtag layer failed" in w for w in warnings)
    assert any(g["details"]["kind"] == "format" for g in found)


# ------------------------------------------------------------------ habits must earn their place from the data
def test_only_habits_that_go_with_engagement_among_similar_accounts_can_be_gaps():
    from app.analysis.instagram import peer

    related = {m for m in ("feat_posts_per_week", "feat_avg_hashtags", "feat_avg_caption_length", "feat_gap_std_days",
                           "feat_pct_captions_with_cta", "feat_pct_captions_with_question", "feat_has_website", "feat_bio_has_cta")
               if peer.association(m)["significant"]}
    assert related == {"feat_posts_per_week", "feat_gap_std_days", "feat_pct_captions_with_cta"}


def test_habits_are_a_comparison_table_never_a_gap():
    import datetime as dt
    base = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc)
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 150, ""))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    for i, r in enumerate(comp):
        r["posted_at"] = (base + dt.timedelta(days=40 * i)).isoformat()      # one post every ~6 weeks
    for i, r in enumerate(mine):
        r["posted_at"] = (base + dt.timedelta(days=i)).isoformat()           # one post a day
    found, _, summary = engine.analyze_project("proj", mine + comp)
    assert not [g for g in found if g["details"]["kind"] == "habit"]             # no "post less often" advice
    h = summary["competitors"][0]["habits"]
    assert h["related"] == 3 and h["gaps"] == 0
    rate = next(r for r in h["table"] if r["label"] == "Posting rate")
    assert "posts a week" in rate["you"] and "posts a week" in rate["competitor"] and rate["typical"]


def test_a_habit_with_no_link_to_engagement_is_never_a_habit_gap():
    many = _posts("competitor", "c1", "rival", lambda i: (CHAT, "#a #b #c #d #e #f #g #h #i #j #k #l #m #n #o", "Image", 150, ""))
    none = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    found, _, _ = engine.analyze_project("proj", none + many)
    assert not [g for g in found if g["details"]["kind"] == "habit" and "hashtags" in g["title"].lower()]


# ------------------------------------------------------------------ the vision-network path
# (the network is built WITHOUT its pre-trained weights here, because they download from the internet on first use;
#  these tests check the plumbing, not how well a real pre-trained network scores)
needs_torch = pytest.mark.skipif(not cnn_features.available(), reason="PyTorch is not installed")


@needs_torch
def test_a_model_on_vision_network_features_trains_saves_and_scores(tmp_path, monkeypatch):
    rng = np.random.default_rng(2)
    d = tmp_path / "train"; d.mkdir(); rows = []
    for i in range(70):
        blur = float(rng.uniform(0, 4)); _picture(blur, i).save(d / f"{i}.jpg", quality=95)
        rows.append({"image_name": f"{i}.jpg", "MOS": float(np.clip(4.7 - 0.6 * blur, 1, 5))})
    pd.DataFrame(rows).to_csv(tmp_path / "scores.csv", index=False)
    monkeypatch.setattr(train_common, "extract", train_common.extract)
    orig = train_common.train_and_save
    monkeypatch.setattr(train_image_quality, "train_and_save", lambda *a, **k: orig(*a, force="ridge_on_network_features", **k))
    report = train_image_quality.main(str(d), str(tmp_path / "scores.csv"), None, 1, features="cnn", backbone="resnet18",
                                      max_side=96, pretrained=False, cache=str(tmp_path / "f.npz"))
    assert report["head"] == "ridge_on_network_features" and "baseline_measurements_only_srcc" in report
    assert (tmp_path / "f.npz").exists()                                   # features are saved, so retraining is instant
    media_scoring.reset_cache()
    st = media_scoring.status()["image_quality"]
    assert st["available"] and "vision network" in st["description"] and "ridge regression" in st["description"]
    sharp, blurry = tmp_path / "s.jpg", tmp_path / "b.jpg"
    _picture(0).save(sharp); _picture(4).save(blurry)
    monkeypatch.setattr(media_scoring, "_download", lambda url, limit: Path(url).read_bytes())
    got = [media_scoring._score_one("image", str(p))["image_quality"] for p in (sharp, blurry)]
    assert all(g is not None and np.isfinite(g) for g in got)


@needs_torch
def test_a_video_model_reads_frames_through_the_network(tmp_path, monkeypatch):
    import cv2
    rng = np.random.default_rng(3)
    vd = tmp_path / "vid" / "yfcc-batch1"; vd.mkdir(parents=True); lab = []
    for i in range(40):
        blur = float(rng.uniform(0, 3)); p = str(vd / f"{i}.mp4")
        w = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
        for f in range(16):
            w.write(cv2.cvtColor(np.asarray(_picture(blur, f).rotate(f * 2)), cv2.COLOR_RGB2BGR))
        w.release(); lab.append(f"yfcc-batch1/{i}.mp4, -1, -1, {np.clip(85 - 14 * blur, 0, 100):.2f}")
    (tmp_path / "labels.txt").write_text("\n".join(lab))
    orig = train_common.train_and_save
    monkeypatch.setattr(train_video_quality, "train_and_save", lambda *a, **k: orig(*a, force="ridge_on_network_features", **k))
    rep = train_video_quality.main(str(tmp_path / "vid"), [str(tmp_path / "labels.txt")], None, 1, features="cnn",
                                   backbone="resnet18", max_side=64, pretrained=False)
    assert rep["head"] == "ridge_on_network_features"
    media_scoring.reset_cache()
    monkeypatch.setattr(media_scoring, "_download", lambda url, limit: Path(url).read_bytes())
    res = media_scoring._score_one("video", str(vd / "0.mp4"))
    assert res["video_quality"] is not None and np.isfinite(res["video_quality"])


def test_a_network_model_without_pytorch_is_reported_not_used(tmp_path, monkeypatch):
    import joblib
    joblib.dump({"model": object(), "feature_set": "cnn", "backbone": "resnet50", "head": "ridge_on_network_features", "hand_features": [],
                 "report": {"n_train": 5, "srcc": 0.5}, "trained_on": "KonIQ-10k"}, tmp_path / "models" / "image_quality.joblib")
    monkeypatch.setattr(cnn_features, "available", lambda: False)
    media_scoring.reset_cache()
    assert not media_scoring.any_available()
    assert "PyTorch" in media_scoring.unavailable_reason()
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 200, "https://x/c.jpg"))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, "https://x/u.jpg"))
    _, _, summary = engine.analyze_project("proj", mine + comp)
    assert summary["competitors"][0]["media"]["status"] == "not_trained" and "PyTorch" in summary["competitors"][0]["media"]["reason"]


# ------------------------------------------------------------------ the training choices: split, weights, layers
def test_the_split_keeps_the_same_mix_of_scores_in_every_part():
    rng = np.random.default_rng(4)
    y = np.concatenate([rng.normal(3.3, 0.3, 900), rng.normal(1.5, 0.2, 100)])   # few low scores, like KonIQ
    tr, va, te, groups = train_common.stratified_split(y)
    assert groups == 10 and len(set(tr) | set(va) | set(te)) == len(y) and not (set(tr) & set(te))
    low = np.quantile(y, 0.1)
    shares = [float((y[part] <= low).mean()) for part in (tr, va, te)]
    assert max(shares) - min(shares) < 0.02                 # each part has about 10% of the lowest scores


def test_a_tiny_dataset_falls_back_to_fewer_groups():
    y = np.linspace(1, 5, 30)
    tr, va, te, groups = train_common.stratified_split(y)
    assert 0 <= groups < 10 and len(tr) + len(va) + len(te) == 30


def test_rare_scores_count_more_and_the_mean_weight_is_one():
    y = np.array([3.0] * 95 + [1.2] * 5)
    for scheme in ("sqrt_inverse", "inverse"):
        w = train_common.sample_weights(y, scheme)
        assert abs(w.mean() - 1) < 1e-9 and w[-1] > w[0]
    assert train_common.sample_weights(y, "none") is None
    assert train_common.sample_weights(y, "inverse")[-1] > train_common.sample_weights(y, "sqrt_inverse")[-1]


def test_error_by_score_group_counts_every_test_item():
    y = np.array([1.0, 1.5, 3.0, 3.1, 4.9]); p = y + 0.2
    g = train_common.group_errors(y, p, 1.0, 5.0)
    assert sum(r["n"] for r in g) == 5 and all(r["mae"] is None or abs(r["mae"] - 0.2) < 1e-9 for r in g)


def test_layer_columns_pick_the_right_part_of_the_vector():
    cols = cnn_features.columns("resnet18", cnn_features.ALL_LAYERS, ("layer4",))
    assert len(cols) == 2 * 512 and cols[0] == 2 * (64 + 128 + 256)
    full = cnn_features.image_dim("resnet18", cnn_features.ALL_LAYERS)
    vid = cnn_features.columns("resnet18", cnn_features.ALL_LAYERS, ("layer4",), video=True)
    assert len(vid) == 2 * len(cols) and vid[len(cols)] == cols[0] + full
    assert cnn_features.image_dim("resnet50") == 7168          # layers 2-4: (512 + 1024 + 2048) x 2


@needs_torch
def test_the_chosen_layers_are_saved_and_used_when_scoring(tmp_path, monkeypatch):
    rng = np.random.default_rng(5)
    d = tmp_path / "train"; d.mkdir(); rows = []
    for i in range(60):
        blur = float(rng.uniform(0, 4)); _picture(blur, i).save(d / f"{i}.jpg", quality=95)
        rows.append({"image_name": f"{i}.jpg", "MOS": float(np.clip(4.7 - 0.6 * blur, 1, 5))})
    pd.DataFrame(rows).to_csv(tmp_path / "scores.csv", index=False)
    orig = train_common.train_and_save
    monkeypatch.setattr(train_image_quality, "train_and_save", lambda *a, **k: orig(*a, force="ridge_on_network_features", **k))
    rep = train_image_quality.main(str(d), str(tmp_path / "scores.csv"), None, 1, features="cnn", backbone="resnet18",
                                   max_side=64, pretrained=False)
    assert len(rep["ablation_network_and_layers"]) == len(cnn_features.LAYER_SETS)
    assert (train_common.MODELS / "image_quality_report.json").exists()
    media_scoring.reset_cache()
    m = media_scoring.load("image_quality")
    ext = media_scoring._extractor(m)
    assert ext.layers == tuple(m["layers"]) and m["model"].n_features_in_ == ext.dim + len(mf.IMAGE_FEATURES)


# ------------------------------------------------------------------ guards against inputs and scores off the scale
def test_focus_on_centre_stays_between_0_and_1_even_with_a_flat_border():
    a = np.full((200, 200, 3), 128, dtype="uint8")
    a[50:150, 50:150] = (np.random.default_rng(6).random((100, 100, 3)) * 255).astype("uint8")   # detail only in the centre
    f = mf.image_features(Image.fromarray(a))["focus_centre"]
    assert 0.0 <= f <= 1.0 and f > 0.9
    assert mf.image_features(Image.fromarray(np.full((50, 50, 3), 128, dtype="uint8")))["focus_centre"] == 0.5


def test_an_extreme_input_cannot_push_a_score_off_the_scale():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(200, 5)); y = 3 + X[:, 0] * 0.5
    m = train_common._make("ridge_on_network_features", 5, 200, 0).fit(X, y)
    wild = np.array([[40000.0, 0, 0, 0, 0]])                 # like the flat-border picture: 40,000 standard deviations
    assert y.min() <= m.predict(wild)[0] <= y.max()
    w = train_common.sample_weights(y, "sqrt_inverse")
    assert np.isfinite(train_common._make("svr_on_network_features", 5, 200, 0).fit(X, y, sample_weight=w).predict(X)).all()


# ------------------------------------------------------------------ honest output for big accounts and few posts
def test_accounts_bigger_than_the_reference_data_are_not_given_a_percentile():
    comp = _posts("competitor", "c1", "shein", lambda i: (CHAT, "", "Image", 2000, ""), n=12, followers=30_000_000)
    mine = _posts("own", None, "temu", lambda i: (CHAT, "", "Video", 1500, ""), n=12, followers=3_000_000)
    _, _, summary = engine.analyze_project("proj", mine + comp)
    part = summary["competitors"][0]
    assert part["results"]["status"] == "skipped" and "3,000,000 followers" in part["results"]["reason"]
    assert "not possible" in part["results"]["reason"]
    assert all(row["typical"] is None for row in part["habits"]["table"])     # no "accounts your size" column either


def test_a_weak_format_difference_is_not_shown_at_all():
    # 3 of 12 carousels for them (doing well), none for you: Fisher p ~ 0.11 even before any correction, so it could
    # easily be chance. It is not shown, not even as "worth testing".
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Sidecar", 300, "") if i < 3 else (CHAT, "", "Video", 100, ""), n=12)
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Video", 100, ""), n=12)
    found, _, _ = engine.analyze_project("proj", mine + comp)
    assert not [g for g in found if g["details"]["kind"] == "format"]


def test_one_or_two_posts_of_a_format_never_make_a_gap():
    # they have a single photo (with lots of likes) and you have none: one post says nothing
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 900, "") if i == 0 else (CHAT, "", "Video", 100, ""), n=30)
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Video", 100, ""), n=30)
    found, _, _ = engine.analyze_project("proj", mine + comp)
    assert not [g for g in found if g["details"]["kind"] == "format"]


def test_the_habit_table_leaves_out_the_rows_a_seller_cannot_read():
    comp = _posts("competitor", "c1", "rival", lambda i: (CHAT, "", "Image", 150, ""))
    mine = _posts("own", None, "myshop", lambda i: (CHAT, "", "Image", 100, ""))
    _, _, summary = engine.analyze_project("proj", mine + comp)
    labels = {r["label"] for r in summary["competitors"][0]["habits"]["table"]}
    assert "Posting rate" in labels and "Time since the last post" not in labels and "Regular posting" not in labels
    assert all(" and " not in (r["typical"] or "") for r in summary["competitors"][0]["habits"]["table"])


def test_when_results_could_not_be_compared_the_gaps_do_not_claim_equal_results():
    s = gap_common._context_sentence("unknown", "rival")
    assert "could not compare" in s and "equally" not in s
    assert "equally well" in gap_common._context_sentence("even", "rival")
