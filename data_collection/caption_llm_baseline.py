"""Model C's LLM baselines: the app's own LLM (Groq, backend/.env) labels the captions with no training.

  ../backend/.venv/bin/python caption_llm_baseline.py [zero|few] [model]

zero = the label guide only. few = the guide + 2 labelled examples per label (FEW_SHOT_IDS, taken from captions the
person did not check; they are left out of every method's score). Captions are public Instagram posts; only the caption
text is sent. Writes reports/caption_llm_<mode>.csv (resumable: captions already answered are skipped).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.core.config import get_settings  # noqa: E402

LABELS = ["offer", "new_arrival", "price", "call_to_order", "product_details", "review", "behind_the_scenes",
          "event_season", "other"]
GUIDE = """Label Instagram captions from Pakistani jewellery shops. A caption can have SEVERAL labels.
Label what the caption SAYS, not the picture.
- offer: announces a discount, sale, deal, bundle or free delivery
- new_arrival: presents something new, a new collection, a restock
- price: states a price (Rs 2,499 / PKR 1500 / 999/-)
- call_to_order: tells the customer how to order or contact (DM to order, WhatsApp number, link in bio, COD available)
- product_details: describes the product: material, size, colours, finish, care
- review: customer feedback, a delivered order, a happy customer
- behind_the_scenes: making, packing, the shop or the team
- event_season: ties the post to an event or season (Eid, wedding season, Valentine's)
- other: none of the above (only a greeting, a quote, emojis or hashtags)"""
BATCH = 20


def few_shot_ids(l: pd.DataFrame) -> list[str]:
    """2 single-label-rich examples per label from captions the person did not check (fixed seed).
    Once chosen they are saved and reused, so adding captions later never changes the examples."""
    saved = HERE / "reports" / "caption_few_shot_ids.txt"
    if saved.exists():
        return saved.read_text().split()
    pool = l[~l["checked_by_person"]]
    ids = []
    for lab in LABELS:
        has = pool[pool["labels_draft"].str.split("|").apply(lambda x: lab in x) & ~pool["caption_id"].isin(ids)]
        ids += has.sample(min(2, len(has)), random_state=1)["caption_id"].tolist()
    return ids


def ask(client, model: str, system: str, batch: pd.DataFrame) -> dict:
    items = "\n".join(f'{r.caption_id}: {json.dumps(str(r.caption)[:700], ensure_ascii=False)}' for r in batch.itertuples())
    user = ("Label each caption. Reply with JSON only: {\"<id>\": [\"label\", ...], ...} using only these labels: "
            + ", ".join(LABELS) + "\n\n" + items)
    for attempt in range(6):
        try:
            r = client.chat.completions.create(model=model, temperature=0, response_format={"type": "json_object"},
                                               messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            return json.loads(r.choices[0].message.content)
        except Exception as exc:  # noqa: BLE001 - rate limits and the odd malformed reply: wait and retry
            wait = 20 * (attempt + 1)
            print(f"  retry in {wait}s: {str(exc)[:120]}", flush=True)
            time.sleep(wait)
    return {}


def main(mode: str = "zero", model: str | None = None) -> None:
    from groq import Groq

    s = get_settings()
    model = model or s.groq_model
    client = Groq(api_key=s.groq_api_key)
    l = pd.read_csv(HERE / "labels" / "captions_labels.csv")
    shots = few_shot_ids(l)
    (HERE / "reports" / "caption_few_shot_ids.txt").write_text("\n".join(shots))   # left out of every score
    system = GUIDE
    if mode == "few":
        ex = l[l["caption_id"].isin(shots)]
        system += "\n\nExamples:\n" + "\n".join(f'{json.dumps(str(r.caption)[:300], ensure_ascii=False)} -> {r.labels_draft.replace("|", ", ")}'
                                                for r in ex.itertuples())
    out = HERE / "reports" / f"caption_llm_{mode}.csv"
    done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["caption_id", "labels_llm"])
    todo = l[~l["caption_id"].isin(set(done["caption_id"]) | set(shots))]
    print(f"{mode}-shot with {model}: {len(done)} done, {len(todo)} to do", flush=True)
    for i in range(0, len(todo), BATCH):
        batch = todo.iloc[i:i + BATCH]
        ans = ask(client, model, system, batch)
        rows = [{"caption_id": c, "labels_llm": "|".join(sorted(x for x in ans.get(c, []) if x in LABELS)), "model": model}
                for c in batch["caption_id"] if c in ans]
        done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
        done.to_csv(out, index=False)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)} (answered {len(rows)}/{len(batch)})", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "zero", sys.argv[2] if len(sys.argv) > 2 else None)
