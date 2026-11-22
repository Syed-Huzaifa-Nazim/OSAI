"""Trains the topic model: what are Instagram business posts about?

    python -m app.analysis.instagram.train_topics --profiles Instagram_dataset_snowflake_profile.csv

Unsupervised (there are no labelled topics for posts): it reads the captions of the public
business profiles the grader was trained on and groups words that appear together (NMF on
TF-IDF). It learns from the English-language captions only, because most of the others are in
languages this vocabulary cannot read; the app shows how many of an account's posts a topic
could be found for. The number of topics is chosen by a coherence score (NPMI), not by hand.
Writes topic_model.joblib and topic_candidates.json (names are in topic_names.json).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

HERE = Path(__file__).parent
COMMON = set("the and to of in is for you your with this that we our it are on at be have from as by new all".split())
TOKEN = r"#?[A-Za-z]{3,}"


def clean(text: str) -> str:
    return re.sub(r"https?://\S+|@\w+", " ", text or "")


def looks_english(text: str) -> bool:
    words = re.findall(r"[a-z']+", (text or "").lower())
    return len(words) >= 4 and sum(w in COMMON for w in words) / len(words) > 0.18


def load_captions(profiles_csv: str) -> list[str]:
    out = []
    for _, a in pd.read_csv(profiles_csv, low_memory=False).iterrows():
        try:
            posts = json.loads(a.POSTS)
        except Exception:  # noqa: BLE001
            continue
        out += [p.get("caption") or "" for p in posts]
    return out


def npmi_coherence(components: np.ndarray, terms: np.ndarray, X_bin, top: int = 10) -> float:
    """Average NPMI of the top words of each topic: higher = the words really appear together."""
    n_docs = X_bin.shape[0]
    index = {t: i for i, t in enumerate(terms)}
    col = {i: X_bin[:, i].toarray().ravel().astype(bool) for i in range(X_bin.shape[1])}
    scores = []
    for comp in components:
        idx = comp.argsort()[::-1][:top]
        pair_scores = []
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                da, db = col[idx[a]], col[idx[b]]
                pa, pb, pab = da.mean(), db.mean(), (da & db).mean()
                if pab == 0:
                    pair_scores.append(-1.0)
                else:
                    pair_scores.append(np.log(pab / (pa * pb)) / -np.log(pab))
        scores.append(np.mean(pair_scores))
    return float(np.mean(scores))


def main(profiles: str, k_values=range(8, 31, 2), seed: int = 0) -> None:
    caps = [clean(c) for c in load_captions(profiles)]
    docs = [c for c in caps if looks_english(c)]
    print(f"{len(caps)} captions, {len(docs)} read as English and used for training")
    vec = TfidfVectorizer(min_df=8, max_df=0.3, stop_words=list(ENGLISH_STOP_WORDS),
                          token_pattern=TOKEN, sublinear_tf=True)
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    from sklearn.feature_extraction.text import CountVectorizer
    Xb = CountVectorizer(vocabulary=vec.vocabulary_, binary=True, token_pattern=TOKEN, lowercase=True).fit_transform(docs)
    table, best = [], None
    for k in k_values:
        nmf = NMF(n_components=k, init="nndsvda", random_state=seed, max_iter=500).fit(X)
        score = npmi_coherence(nmf.components_, terms, Xb)
        table.append({"k": k, "npmi_coherence": round(score, 4), "reconstruction_error": round(float(nmf.reconstruction_err_), 3)})
        print(f"k={k:2d}  coherence={score:.4f}")
        if best is None or score > best[0]:
            best = (score, k, nmf)
    _, k, nmf = best
    print("chosen k =", k)
    topics = {str(i): {"terms": [str(t) for t in terms[c.argsort()[::-1][:10]]]} for i, c in enumerate(nmf.components_)}
    joblib.dump({"vectorizer": vec, "nmf": nmf, "k": k, "n_train_docs": len(docs), "n_captions": len(caps)}, HERE / "topic_model.joblib")
    (HERE / "topic_candidates.json").write_text(json.dumps({"coherence_by_k": table, "chosen_k": k, "topics": topics}, indent=1))
    print("wrote topic_model.joblib and topic_candidates.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True)
    main(ap.parse_args().profiles)
