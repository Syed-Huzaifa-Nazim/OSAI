# Trained picture and video models

The training scripts save their models here. The app uses whichever are present:

| File | Made by | Trained on |
|---|---|---|
| `image_quality.joblib` | `python -m app.analysis.instagram.train_image_quality` | KonIQ-10k pictures + their MOS ratings |
| `video_quality.joblib` | `python -m app.analysis.instagram.train_video_quality` | LSVQ videos + their ratings |
| `memorability.joblib` | `python -m app.analysis.instagram.train_memorability` | LaMem pictures + memorability scores |

A missing file is fine: that score is skipped and the analysis panel says the model is not trained yet.
