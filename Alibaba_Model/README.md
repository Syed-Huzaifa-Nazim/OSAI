# Alibaba product gap model

This folder trains a three-class review severity model on product-disjoint Amazon Reviews 2023 data and compares Alibaba listings using observed B2B fields. A review label is a proxy for complaint severity, not a verified business gap.

## Setup

Use Python 3.11 or 3.12 in a dedicated environment:

```powershell
cd Alibaba_Model
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\run_pipeline.py --device auto
```

The pipeline streams a bounded sample from the official UCSD Amazon Reviews 2023 category archives. Metadata is joined by `parent_asin`. It writes EDA, split files, model weights, held-out metrics, Alibaba validation predictions, and a sample comparison. The dataset download can take substantial time because metadata archives must be scanned. No backend files are written.

If raw data already exists, pass `--skip-download`; if fine-tuned weights already exist, also pass `--skip-train`. `--device cpu` works but training is slow. For Colab, run `python src/package_colab.py`, then open `notebooks/train_colab_t4.ipynb` on a T4 runtime and upload the generated ZIP when prompted. No notebook edits are needed. Download its results ZIP and extract it into this folder.

## Demo

```powershell
.venv\Scripts\python src\06_demo_app.py
.venv\Scripts\python src\06_demo_app.py --cli --own own.json --competitor competitor.json
```

Inputs must use `platform=alibaba`, `role=own` or `role=competitor`, and match `backend/app/models/ecommerce.py`. Attach review text in `text_fields.review` (one review per line) or `raw_metadata.reviews` (a list). The current live Alibaba scraper exposes `title`, `specs`, `promo_tags`, `order_terms`, and `supplier` text, but **does not scrape reviews**. Review predictions are therefore available only for explicitly attached reviews; B2B comparisons still work without them. Output records are validated against `backend/app/models/gap.py`, including numeric evidence relevance.

## Data sources

- [Official Amazon Reviews 2023 dataset](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
- Local Alibaba validation CSVs in `data/alibaba_validation/`; these are reserved for cross-domain evaluation.

