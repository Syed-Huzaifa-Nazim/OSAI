# The Story of the Model (in simple words)

## 1. What was the job?
The model had to learn two jobs:

- **Job A (sentiment):** read a review and say whether it is Positive, Negative or Neutral.
- **Job B (reasons):** read a review and say what it is about (Delivery, Quality, Price...) and whether that part is good or bad.

A separate model was chosen for each job.

## 2. Which models were tried, and why
We tried 9 models so that the final choice is based on numbers, not guesses.

| Model | What it is (simple) | Why we tried it |
|---|---|---|
| Naive Bayes | Counts words. The simplest one | Easiest comparison |
| Logistic Regression | Gives a score based on the words used | Popular for text, fast |
| Linear SVM | Like Logistic Regression, often a bit better | Works well on text |
| Random Forest | Many "yes/no" decision trees | You asked for it |
| XGBoost | A faster, stronger version of trees | You asked for it |
| DistilBERT, mBERT | Smaller "smart" AI models that read the whole sentence | To understand context |
| XLM-RoBERTa | A big smart model that has already read text in about 100 languages (Urdu, English...) | Good for Roman Urdu + English mix |
| MuRIL | A model built for languages of the Indian subcontinent | For Roman Urdu |

In the first run, all 9 models were trained. In the second run, only the 4 most promising ones (LR, SVM, XLM-R, mBERT) were trained again, and this time the reasons job got more training time.

## 3. How to read the numbers
We did **not** use accuracy (how many answers are right) as the main number. Reason: 61% of reviews are Positive, so a model that says "Positive" for everything would already be 61% "accurate" and still be useless. So we used **macro-F1**, which treats Positive, Negative and Neutral equally. 1.0 is perfect and 0 is the worst.

**What is the test set?** About 15% of the data (about 5,100 reviews) that the model never saw during training. It is the real exam.

## 4. Result: Sentiment (Positive / Negative / Neutral)
**Winner: XLM-RoBERTa**

| Model | macro-F1 (test) | Accuracy |
|---|---|---|
| **XLM-RoBERTa** | **0.766** | 80.8% |
| mBERT | 0.753 | 79.7% |
| SVM | 0.729 | 81.2% |
| Logistic Regression | 0.728 | 78.8% |
| (first run) MuRIL / DistilBERT | 0.757 / 0.749 | 79.7% / 78.7% |
| (first run) Random Forest / XGBoost | 0.711 / 0.720 | 79.7% / 79.9% |
| (first run) Naive Bayes | 0.689 | 77.4% |

**What this means:** XLM-R is fairly good, but not perfect. Score for each class:
- Negative: 0.81 (good)
- Positive: 0.88 (good)
- Neutral: 0.60 (weak)

**On Roman Urdu data (similar to Pakistani Daraz): 0.85. On the English part: 0.69.** Your project will run on Pakistani Daraz, so this is good news.

**Why Neutral is weak:** many "neutral" reviews are really mixed ("good quality but late delivery"). Even people do not agree on one answer for them. This is more a limit of the data than a mistake of the model.

**Error in the percentages:** on the test set the model said Neutral was 24.8% when the true value was 18.8%, and it said Positive was 55.7% when the true value was 61.3%. So the percentages can be off by **about 5-6 points**. Mention this as a limitation in the report.

## 5. Result: Reasons (Delivery, Quality, Price...)
**Winner: XLM-RoBERTa**

| Model | macro-F1 (test) |
|---|---|
| **XLM-RoBERTa** | **0.50** |
| mBERT | 0.49 |
| SVM | 0.47 |
| Logistic Regression | 0.44 |

**Good news:** in the first run XLM-R scored 0.41 (3 epochs of training). With 8 epochs in the second run it reached **0.50**. So it simply needed more training time.

**What this really means (the most important part):**
- The model only shows reasons when it is **very sure** (confidence threshold 0.95).
- Of the reasons it shows, about **76% are correct**.
- But it finds only about **25%** of all the real reasons, which is **1 in 4**.
- In short: what it shows is mostly right, but many reasons will be missed. The list of reasons is **not complete**, it only contains the **clear** ones.

**Another reason the score looks low:** in Dataset 1, a label of "0" often means the annotator did not write that reason down, not that the reason was absent. So the measured score is lower than the real quality.
