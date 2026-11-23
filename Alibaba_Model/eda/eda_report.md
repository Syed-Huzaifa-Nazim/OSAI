# EDA status

The local Alibaba validation audit is complete. Amazon before/after processing, class-balance figures, and product-disjoint split sizes are generated here by `src/02_eda_and_preprocess.py` after the official Amazon sample finishes streaming. No Amazon training metrics are available yet.

| Alibaba measure | Observed value |
|---|---:|
| Review rows | 210 |
| Product rows | 903 |
| 1-star / 2-star / 3-star / 4-star / 5-star reviews | 3 / 1 / 2 / 7 / 197 |
| No Gap / Moderate Gap / High Gap | 204 / 2 / 4 |
| Review word count mean / median / std | 13.30 / 9.00 / 15.60 |
| Review word count Q1 / Q3 / IQR | 3 / 17 / 14 |
| Review word count min / max / IQR outliers | 1 / 98 / 17 (8.10%) |
| Product price USD mean / median / std | 449.72 / 16.00 / 4620.75 |
| Product price USD Q1 / Q3 / IQR | 4.20 / 65.00 / 60.80 |
| Product price USD min / max / IQR outliers | 0.02 / 98000 / 141 (15.61%) |
| Products with “Find Complete Details about” description boilerplate | 903 (100%) |

The skewed severity labels and boilerplate descriptions rule out using this small sample as the training source. It remains an untouched cross-domain validation set.
