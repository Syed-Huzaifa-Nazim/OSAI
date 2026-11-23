# Agent Execution Prompt: OptiStratixAI — Alibaba Product Gap-Analysis ML Pipeline (`Alibaba_Model/`)

## 0. Mandatory Guardrails & Rules of Engagement (READ FIRST)

1. **Strict Workspace Isolation (`Final_Development-Repository/Alibaba_Model/` ONLY for Writes/Deletes):**
   - Repository root: `Final_Development-Repository/`.
   - Sibling directories in the repo: `Alibaba_Model/`, `backend/`, `Daraz_Model/`, `docs/`, `frontend/`.
   - **ALL file creation, modification, dataset downloads, and deletions MUST happen strictly inside `Alibaba_Model/`.**
   - **NEVER** modify, delete, install packages into, or overwrite anything in `backend/` (including `backend/.venv` and `backend/requirements.txt`), `Daraz_Model/`, `docs/`, or `frontend/`.
   - **Read-Only Reference Allowed:** You **ARE encouraged to READ** (read-only) existing project files so our inference schema and documentation match the codebase 100%:
     - `backend/app/models/ecommerce.py` and `backend/app/models/gap.py` (exact Pydantic models)
     - `backend/app/scrapers/` (exact Alibaba scraper output keys in `text_fields` and `raw_metadata`)
     - `backend/app/analysis/` (how the backend consumes gap outputs)
     - `Daraz_Model/Models_detail.md` (team documentation convention so we match or exceed it in `Alibaba_Model/Models_detail.md`)
   - **Cleanup Step First:** Delete all old/legacy items inside `Alibaba_Model/` ONLY (`__pycache__/`, `prepare_dataset.py`, `README.md`, old `.gitignore`), preserving `alibaba_reviews_validation.csv` and `alibaba_products_validation.csv` if the user already placed them inside `Alibaba_Model/`.
   - **Python Environment Isolation:** Do NOT touch `backend/.venv`. Use a dedicated `Alibaba_Model/.venv` (or Google Colab runtime) for ML dependencies (`torch`, `transformers`, `datasets`, `scikit-learn`, `gradio`).
2. **Strict Git & GitHub Restriction:**
   - **DO NOT** run `git add`, `git commit`, `git push`, `git reset`, `git checkout`, or create/modify branches or PRs until the user explicitly instructs you to do so.
   - Include a clean `Alibaba_Model/.gitignore` so `__pycache__/`, `.venv/`, `data/raw/`, and large temporary checkpoints are ignored when the user later decides to commit.
3. **Human-in-the-Loop Decision Gate (No Unapproved Major Decisions):**
   - **DO NOT** make any large architectural or scope decision without asking the user first.
   - Before starting Step 2 (dataset download) or changing any core design choice, pause and confirm the 4 items listed in **Section 5 (Pre-Execution Confirmation Checklist)** if the user has not already specified them.
4. **Compute & Training Permission:**
   - You have full permission to train locally if a CUDA/MPS GPU is available, **OR** use **Google Colab (T4 GPU)** — whatever executes cleanly and produces verified saved model weights in `Alibaba_Model/artifacts/model/`.
   - If training runs on Google Colab, generate a 100% self-contained, zero-manual-edit notebook (`Alibaba_Model/notebooks/train_colab_t4.ipynb`) and ensure the resulting weights/metrics are saved into `Alibaba_Model/artifacts/model/` and `Alibaba_Model/artifacts/reports/`.

---

## 1. Project Context & Exact OptiStratixAI Schema Alignment

### Why Cross-Domain Transfer Learning?
OptiStratixAI compares a user's **Alibaba listing (`role = 'own'`)** against one or more **competitor Alibaba listings (`role = 'competitor'`)** scraped by our existing Alibaba scraping engine in `backend/app/scrapers/`.
- Public Alibaba datasets (e.g., Bright Data's 1,000-row sample `Alibaba.csv`) suffer from severe data sparsity and class imbalance: after cleaning, only **210 reviews** survive, **93.81% (197)** are 5-star, only **6 reviews (2.86%)** are 1–3 star, and 100% of `description` fields are auto-generated SEO boilerplate.
- Therefore, we use **Cross-Domain Transfer Learning**:
  1. **Train** on a large, clean, strictly balanced subset of **`McAuley-Lab/Amazon-Reviews-2023`** (downloaded automatically via Hugging Face `datasets` in streaming mode).
  2. **Validate Cross-Domain** on our cleaned real scraped Alibaba validation files (`alibaba_reviews_validation.csv` — 210 rows, and `alibaba_products_validation.csv` — 903 rows).
  3. **Run Inference** on live scraped Alibaba records conforming to our Supabase Postgres schema (`backend/app/db/schema.sql` + migrations `0001`–`0004`) and Pydantic models (`backend/app/models/ecommerce.py`, `backend/app/models/gap.py`).

### Exact Database Contract (Input Tables → Output Table)

#### Input Tables (Scraped Alibaba Listings)
Verify exact field names by reading `backend/app/models/ecommerce.py` and `backend/app/scrapers/` first, aligning with these Supabase tables:

1. **`public.ecommerce_products` (`platform = 'alibaba'`, `role IN ('own', 'competitor')`)**:
   - Core columns: `id`, `project_id`, `competitor_id`, `source_id`, `url`, `product_name`, `brand`, `price` (`numeric(14,4)`), `max_price` (`numeric(14,4)`), `original_price`, `discount_percent`, `currency`, `rating` (`0–5`), `review_count`, `image_count`, `seller_name`, `seller_rating`, `stock_status`, `category`, `content_completeness_score`, `moq`, `moq_unit`, `lead_time_days`.
   - JSONB columns:
     - `text_fields`: keyed by field type (`title`, `description`, `specs`, `review`, `promo_tags`, `policy_text`, `category`).
     - `raw_metadata`: complete scraper output dictionary.
2. **`public.ecommerce_product_price_tiers`**:
   - `position`, `min_quantity`, `max_quantity`, `price`, `currency`, `unit`.
3. **`public.ecommerce_product_suppliers`**:
   - `name`, `country_code`, `country_name`, `years_on_platform`, `gold_supplier`, `verified`, `trade_assurance`, `transaction_level`, `response_rate` (`0–100`), `historic_order_count`, `historic_gmv_label`, `main_products`.
4. **`public.ecommerce_product_images`**:
   - `position`, `url`, `is_primary`, `source`.

#### CRITICAL FEATURE-COMPATIBILITY RULE
Because the trained NLP model runs inference on **Alibaba listings** (not Amazon), the ML model **MUST ONLY use platform-independent input features**:
- `review_text` (required)
- Optional context prefix: `category` and `product_title`
- **NEVER** include Amazon-only columns (`helpful_vote`, `verified_purchase`, `asin`, `user_id`) as model inputs.

#### Output Table Contract (`public.gaps_opportunities` / `backend/app/models/gap.py`)
Every gap record emitted by the inference/comparison engine MUST strictly satisfy `backend/app/models/gap.py` and all Postgres `CHECK` constraints in `public.gaps_opportunities`:
```json
{
  "title": "Short, specific gap headline",
  "description": "Clear root-cause explanation backed by model predictions and/or B2B metric deltas",
  "category": "content | seo | social_engagement | positioning | audience | conversion | pricing",
  "priority": "critical | high | medium | low",
  "confidence": 0.875,
  "evidence": [
    {
      "source_id": "src_or_item_id",
      "source_url": "https://www.alibaba.com/...",
      "source_title": "Scraped listing title",
      "quote": "Exact review excerpt or scraped B2B metric comparison",
      "relevance": "Why this quote/metric proves the gap"
    }
  ],
  "opportunity": "Concrete, actionable fix the user should apply to their Alibaba listing"
}
```
- `category` MUST be one of: `'content'`, `'seo'`, `'social_engagement'`, `'positioning'`, `'audience'`, `'conversion'`, `'pricing'`.
- `priority` MUST be one of: `'critical'`, `'high'`, `'medium'`, `'low'`.
- `confidence` MUST be a float rounded to 3 decimal places strictly in `[0.000, 1.000]`.
- `evidence` MUST contain **at least 1** grounded evidence object (no ungrounded claims).

---

## 2. Target Folder Structure (`Final_Development-Repository/Alibaba_Model/`)

Mirroring the repository's top-level model folder layout (sibling to `Daraz_Model/` and `backend/`), clear all legacy files inside `Alibaba_Model/` and build this exact clean structure:

```text
Final_Development-Repository/
├── backend/                               # READ-ONLY reference (models/, scrapers/, analysis/, db/)
├── Daraz_Model/                           # READ-ONLY reference (Models_detail.md convention)
├── docs/                                  # DO NOT TOUCH
├── frontend/                              # DO NOT TOUCH
└── Alibaba_Model/                         # ALL WORK HAPPENS EXCLUSIVELY HERE
    ├── .gitignore                         # Ignore __pycache__/, .venv/, data/raw/, temp checkpoints
    ├── README.md                          # Quickstart, architecture, and how to run pipeline/demo
    ├── Models_detail.md                   # Detailed model card & EDA/metrics doc (matches Daraz_Model/ convention)
    ├── requirements.txt                   # Isolated ML dependencies (does NOT touch backend/requirements.txt)
    ├── config.yaml                        # Hyperparameters, category list, paths, label mappings
    ├── data/
    │   ├── raw/                           # Streamed Amazon Reviews 2023 raw sample + metadata
    │   ├── processed/                     # Cleaned, deduplicated, balanced train/val/test CSVs
    │   └── alibaba_validation/            # User-provided real Alibaba validation CSVs:
    │       ├── alibaba_reviews_validation.csv  # (210 clean real Alibaba reviews)
    │       └── alibaba_products_validation.csv # (903 clean real Alibaba product listings)
    ├── eda/
    │   ├── eda_report.md                  # Pre-training stats, spread, IQR outliers, balance audit
    │   ├── eda_stats.json                 # Machine-readable before/after metrics
    │   ├── eda_class_balance.png          # Class balance bar chart (Amazon balanced vs Alibaba skew)
    │   ├── eda_spread_outliers.png        # Price & review length boxplots + IQR outlier summary
    │   └── eda_category_distribution.png  # Category coverage chart
    ├── src/
    │   ├── 01_download_amazon.py          # Automated HF streaming download + metadata join
    │   ├── 02_eda_and_preprocess.py       # Full EDA, outlier handling, deduplication, balancing, splits
    │   ├── 03_train_model.py              # Transformer fine-tuning + test evaluation + artifact export
    │   ├── 04_validate_alibaba.py         # Cross-domain validation on real scraped Alibaba reviews
    │   ├── 05_gap_inference.py            # Schema-aligned AlibabaGapAnalyzer (own vs competitor -> gaps_opportunities JSON)
    │   ├── 06_demo_app.py                 # Lightweight Gradio/CLI live demo for presentation
    │   └── run_pipeline.py                # Single-command end-to-end orchestrator
    ├── notebooks/
    │   └── train_colab_t4.ipynb           # Self-contained Colab T4 GPU notebook (if training on Colab)
    └── artifacts/
        ├── model/                         # Saved fine-tuned model, tokenizer, label_map.json
        └── reports/
            ├── training_metrics.json      # Accuracy, Macro F1, Per-class P/R/F1, epochs
            ├── confusion_matrix.png       # Held-out Amazon test set confusion matrix
            ├── alibaba_validation_report.md   # Cross-domain Alibaba accuracy, recall on 1-3★ gaps, error table
            ├── alibaba_predictions.csv    # Row-by-row model predictions on the 210 Alibaba reviews
            └── sample_comparison_output.json  # End-to-end own vs competitor output matching gaps_opportunities
```

---

## 3. End-to-End Execution Steps (Run as One Cohesive Workflow)

### Step 0: Read-Only Repo Discovery (2 mins)
Before writing any code, **read (do not modify)**:
1. `backend/app/models/ecommerce.py` and `backend/app/models/gap.py` to verify exact Pydantic field names and types.
2. `backend/app/scrapers/` (Alibaba scraper & metrics modules) to confirm exact keys inside `text_fields` and `raw_metadata` (especially how scraped reviews are stored).
3. `Daraz_Model/Models_detail.md` so `Alibaba_Model/Models_detail.md` aligns cleanly with the team's existing model documentation style.

### Step 1: Clean `Alibaba_Model/` & Verify Validation Files
1. Check if `alibaba_reviews_validation.csv` and `alibaba_products_validation.csv` already exist inside `Alibaba_Model/` — if so, temporarily preserve them.
2. Delete all legacy files/folders inside `Alibaba_Model/` ONLY (`__pycache__/`, `prepare_dataset.py`, `README.md`, old `.gitignore`).
3. Create the full directory structure from Section 2 + fresh `Alibaba_Model/.gitignore`.
4. Place/verify `alibaba_reviews_validation.csv` and `alibaba_products_validation.csv` inside `Alibaba_Model/data/alibaba_validation/`. If missing, notify the user to drop them there before Step 5 runs (Steps 2–4 can proceed immediately).

### Step 2: Automated Dataset Download (`src/01_download_amazon.py`)
1. Stream from Hugging Face **`McAuley-Lab/Amazon-Reviews-2023`** (`streaming=True`) so we never download massive multi-GB archives.
   - *Fallback:* If `load_dataset` dataset-script loading fails on newer `datasets` versions, stream directly from the official JSONL/Parquet URLs on `McAuley-Lab/Amazon-Reviews-2023` (`raw/review_categories/<Category>.jsonl` and `raw/meta_categories/meta_<Category>.jsonl`).
2. Pull a **stratified multi-category sample** (or user-approved single category — recommended default: balanced 3-category e-commerce mix covering top Alibaba verticals: `Electronics`, `Home_and_Kitchen`, and `Clothing_Shoes_and_Jewelry`).
3. Map star ratings to our **3-Class Gap Severity Target**:
   - `1–2 stars` → **`High Gap`** (label `2`)
   - `3 stars` → **`Moderate Gap`** (label `1`)
   - `4–5 stars` → **`No Gap`** (label `0`)
4. Collect at least **4,500 raw reviews per class (13,500 total raw reviews)** so that after strict deduplication, noise filtering, and outlier trimming, we retain **9,000–12,000 clean, strictly balanced training rows**.
5. Join each review with its product metadata (`parent_asin`) to attach `product_title`, `main_category`, `sub_category`, `price`, and `features` (remember: keep ML inputs strictly platform-independent).
6. Save to `Alibaba_Model/data/raw/amazon_raw_sample.parquet` (or `.csv`).

### Step 3: Collaborator-Proof EDA, Outlier Audit & Preprocessing (`src/02_eda_and_preprocess.py`)
**Must execute and save full diagnostics BEFORE any model training begins:**
1. **Text Cleaning & Deduplication:**
   - Decode HTML entities (`html.unescape`), strip URLs/control chars, normalize whitespace.
   - Drop rows with null `review_text`, null `rating`, or `< 5 words` (removes noisy 1-word reviews like `"ok"`, `"good"` that carry zero gap signal).
   - Remove exact duplicate `(normalized_review_text, product_title)` pairs and duplicate `review_text` strings.
2. **Statistical Spread & IQR Outlier Analysis (Before & After):**
   - Compute `count`, `mean`, `median`, `std`, `min`, `Q1`, `Q3`, `max`, `IQR`, and `1.5×IQR outlier count & %` for `review_word_count`, `review_char_count`, and `price` (where available).
   - Handle extreme review-length outliers cleanly (e.g., filter `> 99th percentile` and cap tokenizer length at `256` tokens, logging exact rows removed vs. retained).
   - Include a side-by-side EDA audit of `alibaba_reviews_validation.csv` and `alibaba_products_validation.csv` inside `eda_report.md` proving statistically why training directly on Alibaba's 210 reviews (93.81% 5-star, only 6 negative/neutral rows) was invalid.
3. **Strict Class Balancing & Leakage-Free Stratified Splitting:**
   - Undersample larger classes down to the smallest clean class (target: **3,000+ clean rows per class = 9,000+ total clean rows**, exact **33.3% / 33.3% / 33.3%** balance).
   - Perform stratified **80% Train / 10% Validation / 10% Test** split grouped by `parent_asin` (zero product leakage between splits!).
   - Save `train.csv`, `val.csv`, and `test.csv` into `Alibaba_Model/data/processed/`.
4. **Save Visuals & Reports:**
   - `eda/eda_report.md`, `eda/eda_stats.json`
   - `eda/eda_class_balance.png`, `eda/eda_spread_outliers.png`, `eda/eda_category_distribution.png`

### Step 4: Model Training & Held-Out Evaluation (`src/03_train_model.py` + `notebooks/train_colab_t4.ipynb`)
1. **Platform-Independent Input Format:**
   - `"Category: {category} | Product: {product_title} | Review: {review_text}"` (`max_length=256`).
   - Verify zero dependency on Amazon-only columns.
2. **Architecture & Training Config:**
   - Fine-tune `distilbert-base-uncased` (or user-approved backbone) with `AutoModelForSequenceClassification(num_labels=3)`.
   - Hyperparameters: `lr=2e-5`, `batch_size=16` (or `32` with `fp16=True` on GPU), `epochs=3–4`, `weight_decay=0.01`, linear warmup (`10%`), `EarlyStoppingCallback(patience=1)` monitoring validation **Macro F1**, seed `42`.
3. **Evaluation on Held-Out Amazon Test Set:**
   - Report overall **Accuracy**, **Macro F1**, **Weighted F1**, and per-class **Precision / Recall / F1** (`No Gap`, `Moderate Gap`, `High Gap`).
   - Save `artifacts/reports/confusion_matrix.png` and `artifacts/reports/training_metrics.json`.
   - Save best checkpoint + tokenizer + `label_map.json` to `Alibaba_Model/artifacts/model/`.
4. **Colab Execution / Fallback:**
   - Auto-detect GPU (`torch.cuda.is_available()`).
   - If local GPU is unavailable, generate and run (or provide ready-to-run) `Alibaba_Model/notebooks/train_colab_t4.ipynb` on Colab T4 GPU (~10–15 mins) and bring trained artifacts back into `Alibaba_Model/artifacts/model/` and `Alibaba_Model/artifacts/reports/`.

### Step 5: Cross-Domain Validation on Real Scraped Alibaba Data (`src/04_validate_alibaba.py`)
1. Load saved model from `Alibaba_Model/artifacts/model/`.
2. Load `Alibaba_Model/data/alibaba_validation/alibaba_reviews_validation.csv` (210 real Alibaba reviews).
3. Format using the identical platform-independent prompt template (`Category: {top_category} | Product: {title} | Review: {review_text}`).
4. Evaluate against ground-truth `gap_severity_label` (`High Gap` [1–2★], `Moderate Gap` [3★], `No Gap` [4–5★]):
   - Overall accuracy, Macro F1, and **Binary Gap Recall** (how many of the 6 real Alibaba 1–3★ gap reviews are flagged as `High Gap` or `Moderate Gap`).
   - Mean confidence on correct vs. incorrect predictions.
   - Qualitative Error & Gap Inspection Table printing all 6 real Alibaba 1–3★ reviews with predicted label, confidence score, and extracted pain-point phrases.
5. Save `artifacts/reports/alibaba_validation_report.md` and `artifacts/reports/alibaba_predictions.csv`.

### Step 6: Schema-Aligned Gap Analysis & Competitor Comparison Engine (`src/05_gap_inference.py`)
Build a production-ready `AlibabaGapAnalyzer` aligned with `backend/app/models/ecommerce.py` and `backend/app/models/gap.py`:

1. **ML Layer — Review Gap Classification + Pain-Point Extraction (Meaningful Reasoning):**
   - Score every review in `text_fields["review"]` (or the exact key verified in Step 0 from `backend/app/scrapers/`) for both `own` and `competitor`.
   - For reviews predicted as `High Gap` or `Moderate Gap`, extract specific **customer pain-point keyphrases** (TF-IDF bigrams/trigrams + curated e-commerce/B2B aspect taxonomy: `quality/durability`, `battery/performance`, `sizing/wrong_item`, `shipping/delivery`, `packaging`, `supplier_communication`, `pricing/value`, `listing_mismatch`).
   - Emit both:
     - **Own Weaknesses:** Recurring complaints in `own` reviews → mapped to valid `category`, `priority`, calibrated `confidence`, grounded review `quote` in `evidence`, and actionable `opportunity`.
     - **Competitor Exploitation Gaps:** Recurring complaints in `competitor` reviews that `own` can exploit in listing positioning and copy.
2. **B2B Comparative Layer — Deterministic Alibaba Schema Metrics:**
   - Compare `own` vs. `competitor` directly on Alibaba B2B columns (`0004_alibaba_platform.sql`):
     - **Pricing & Tiers (`pricing`):** `price`, `max_price`, and `ecommerce_product_price_tiers`.
     - **B2B Order Friction (`conversion`):** `moq` and `lead_time_days`.
     - **Listing Content & Media (`content` / `seo`):** `image_count`, `content_completeness_score`, and description quality.
     - **Supplier Trust (`positioning`):** `verified`, `gold_supplier`, `trade_assurance`, `response_rate`, `years_on_platform`, `rating`, `review_count`.
3. **Strict Schema Validation & End-to-End Smoke Test:**
   - Validate every generated gap dict with Pydantic against `public.gaps_opportunities` constraints.
   - Pair two real Alibaba products from `alibaba_products_validation.csv` + `alibaba_reviews_validation.csv` into exact `ecommerce_products` payloads, run `AlibabaGapAnalyzer.compare(own, competitor)`, and save to `Alibaba_Model/artifacts/reports/sample_comparison_output.json`.

### Step 7: Orchestrator, Model Card & Presentation Demo (`src/run_pipeline.py`, `src/06_demo_app.py`, `Models_detail.md`)
1. `src/run_pipeline.py`: Single-command runner for Steps 2 → 6 (`--skip-download`, `--skip-train`, `--device auto`).
2. `src/06_demo_app.py`: Lightweight Gradio live demo for the presentation (paste `own` vs `competitor` Alibaba listing + reviews → live Gap Severity, extracted pain points, and `gaps_opportunities` JSON).
3. `Alibaba_Model/Models_detail.md`: Complete documentation matching the `Daraz_Model/Models_detail.md` convention (problem statement, why Alibaba raw data failed EDA, cross-domain transfer learning methodology, training metrics, Alibaba validation results, and integration guide for `backend/app/analysis/`).

---

## 4. Verification & Acceptance Criteria (Definition of Done)

Before reporting completion to the user, verify every item:
- [ ] All created/modified files live strictly inside `Alibaba_Model/`; old legacy files (`__pycache__/`, `prepare_dataset.py`, old `README.md`) are cleaned; **zero** files inside `backend/`, `Daraz_Model/`, `docs/`, or `frontend/` were modified.
- [ ] Zero git write commands (`add`/`commit`/`push`) were executed.
- [ ] `eda/eda_report.md` and all 3 EDA PNG plots exist and clearly document before/after row counts, spread (`mean/median/std/IQR`), outlier counts, and exact 33.3% / 33.3% / 33.3% class balance across `>= 9,000` clean rows.
- [ ] Trained model weights exist in `Alibaba_Model/artifacts/model/` with held-out Amazon test **Macro F1 >= 0.72** (target `0.75–0.82`) and `confusion_matrix.png` saved.
- [ ] Cross-domain validation report (`alibaba_validation_report.md`) exists with predictions and qualitative inspection across all 210 real Alibaba reviews (including all 6 real 1–3★ gap reviews).
- [ ] `sample_comparison_output.json` passes strict Pydantic validation matching `public.gaps_opportunities` & `backend/app/models/gap.py`.
- [ ] `Alibaba_Model/Models_detail.md` is complete and presentation-ready.
- [ ] Report a concise summary table of EDA stats, training metrics, Alibaba validation results, and await user approval before any backend integration or git operations.

---

## 5. Pre-Execution Confirmation Checklist (Ask User Before Running If Unspecified)

Before starting Step 2, confirm these 4 choices with the user (use Recommended Defaults only after user approval):
1. **Amazon Training Categories:** 3-category mix (`Electronics` + `Home_and_Kitchen` + `Clothing_Shoes_and_Jewelry`) *(Recommended — covers Alibaba's top verticals)* OR a single category?
2. **Model Backbone:** `distilbert-base-uncased` *(Recommended — fast, 10–15 mins on Colab T4, lightweight for FastAPI)* OR `roberta-base`?
3. **Training Compute:** Local GPU (if detected) OR Google Colab T4 GPU?
4. **Hybrid B2B Layer:** Include both the trained NLP review model AND the deterministic B2B schema comparator (`moq`, `price_tiers`, `lead_time_days`, `supplier trust`) + competitor pain-point exploitation in `05_gap_inference.py` *(Recommended)*?
