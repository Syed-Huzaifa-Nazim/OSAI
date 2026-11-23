# Alibaba model: method and results

## 1. Task

Classify a review as **No Gap** (4–5 stars), **Moderate Gap** (3 stars), or **High Gap** (1–2 stars). Use recurring classified complaints and observable Alibaba B2B differences to generate evidence-backed opportunities for the user's listing.

## 2. Why transfer learning

The local Alibaba review sample has 210 rows: 197 five-star, 7 four-star, 2 three-star, 1 two-star, and 3 one-star. This maps to 204 No Gap, 2 Moderate Gap, and 4 High Gap. Review length has median 9 words and 17 IQR outliers (8.10%). The 903 product records have median price USD 16, with 141 IQR outliers (15.61%). All 903 descriptions contain the scraper's “Find Complete Details about” boilerplate. `eda/eda_report.md` records the full before/after Amazon audit once preprocessing runs. Alibaba product descriptions are not training labels.

## 3. Data and leakage control

The downloader streams official Amazon Reviews 2023 category JSONL archives, samples Electronics, Home_and_Kitchen, and Clothing_Shoes_and_Jewelry, and joins metadata on `parent_asin`. Cleaning removes empty and short text, exact review duplicates, and the longest one percent. Classes are undersampled equally. Splits use `parent_asin` groups, so the same product cannot occur in train, validation, and test. The model input is only category, product title and review text.

## 4. Model and evaluation

DistilBERT, maximum 256 tokens, learning rate 2e-5, batch size 16, up to four epochs, 10% warmup, and early stopping on validation macro F1. Temperature scaling is fitted on Amazon validation logits and applied to inference probabilities. The held-out Amazon metrics and confusion matrix are written to `artifacts/reports/training_metrics.json` and `confusion_matrix.png` by the training stage. The untouched Alibaba results, including all low-star reviews, are written to `artifacts/reports/alibaba_validation_report.md` and `alibaba_predictions.csv`. No performance claims are made before these files are generated.

## 5. Inference and integration

`src/05_gap_inference.py` accepts two `ecommerce_products` payloads with attached `supplier` and `price_tiers`. It produces complete `Gap` records with ID, project ID, timestamp, category, priority, numeric confidence and grounded evidence. B2B comparisons only emit a gap when both values are observed. Review scoring is skipped when reviews are absent; the current Alibaba scraper does not collect reviews. A future backend integration should pass user-authorized review data explicitly and persist the validated records using the existing gap service.

Review probabilities use validation-fitted temperature scaling. B2B rule confidence is a bounded heuristic based on observed deltas; it is not an empirical probability of business impact.

## 6. Limits

Star ratings are a noisy proxy for gap severity, review language may shift from Amazon to Alibaba, and supplier credentials should be verified before making claims. Missing B2B fields are not interpreted as poor performance. The recorded Alibaba binary gap recall is particularly important because the sample has very few low-star reviews.
