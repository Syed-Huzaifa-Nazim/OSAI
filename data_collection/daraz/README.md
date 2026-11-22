# Daraz jewellery dataset

Builds the data behind the Daraz Gap Engine (`backend/app/analysis/daraz/`). Run from this folder with the
backend's Python: `../../backend/.venv/bin/python <script>`.

| Step | Script | What it does | Output |
|---|---|---|---|
| 1 | `collect_search.py` | 25 jewellery search words × top 80 results, **with rank**, price, discount, sold, rating, reviews, badges, sponsored flag | `search_listings.csv`, `raw/search_*.json` |
| 2 | `collect_details.py` | each listing's page (photos, description, options, title) with the app's own Daraz parser + up to 40 reviews | `raw/details/<item_id>.json` (resumable) |
| 3 | `tag_photos.py` | main photo of every listing tagged with our Model D (worn / in hand / displayed, face) | `photo_tags.csv` |
| 4 | `build_datasets.py` | joins everything; separates RESULTS (rank, sold, reviews, rating) from LEVERS (what a seller can change) | `datasets/listings_dataset.csv`, `datasets/reviews_dataset.csv` |
| 5 | `analyse_reviews.py` | sentiment + reasons for every review with the team's review model; 150-review check sheet | `datasets/reviews_dataset.csv` (+ columns), `labels/review_check_150.csv` |
| 6 | `test_effects.py` | which levers go with a better rank / more sales: Spearman inside each search word → Wilcoxon across words → Benjamini-Hochberg | `reports/effects.csv`, `backend/app/analysis/daraz/models/daraz_evidence.json` |

Rules kept from the Instagram work:
- results (rank, sold, reviews, rating) are never gaps; only levers are;
- each search word is compared with itself (like each shop with itself on Instagram);
- every threshold is a convention (p < 0.05, BH, middle half of the top 20, majority) or comes from the data.

Limits:
- video, specifications, warranty and delivery time are loaded by Daraz with JavaScript, so the plain page read does not see them; they are not tested;
- "N sold" is shown by Daraz only from 5 sold up, so blank is counted as fewer than 5;
- the review model was trained mostly on electronics reviews; check `labels/review_check_150.csv` before trusting its reasons on jewellery.

## Trained models

| Model | Script | What it does | Test | Used in the app |
|---|---|---|---|---|
| **A. Jewellery review reasons** | `train_review_model.py` | 22 reasons (quality, colour fading, breakage, wrong/missing item, size, matches photos, comfort, design, value, delivery, packaging, seller; each + / -) | 5-fold GroupKFold by listing; compared with the team model as-is, keyword rules, TF-IDF, frozen XLM-R + LR, fine-tuned MiniLM (`--xlmr`: fine-tuned XLM-R) | yes: reasons in "What customers say" (sentiment stays with the team model) |
| **B. Rank / sales from levers** | `train_rank_model.py` | predicts rank score and log(sold) from the 14 levers only | GroupKFold by search word; baseline = average | report only (shows levers matter: sales order right in 25/25 unseen words) |

Labels for A: `labels/jewellery_review_labels.csv` (800 reviews, AI-drafted from the full text with `labels/REVIEW_LABEL_GUIDE.md`);
person check: `labels/review_labels_check_100.xlsx`. Results: `reports/model_a_*.csv`, `reports/model_b_*.csv`.
