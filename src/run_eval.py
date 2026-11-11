import os
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from detectors import KeywordDetector, ContextAwareDetector

df = pd.read_csv("data/dataset.csv")
os.makedirs("results", exist_ok=True)


def outcome(r):
    if r["pred"] == 1:
        return "TP" if r["label"] == 1 else "FP"
    return "FN" if r["label"] == 1 else "TN"


summary, per_cat = [], {}
for det in [KeywordDetector(), ContextAwareDetector()]:
    outs = [det.predict(t, c) for t, c in zip(df["text"], df["context"])]
    res = pd.concat([df, pd.DataFrame(outs)], axis=1)
    res["correct"] = res["label"] == res["pred"]
    res["outcome"] = res.apply(outcome, axis=1)
    res.to_csv(f"results/predictions_{det.name}.csv", index=False)

    p, r, f1, _ = precision_recall_fscore_support(
        res["label"], res["pred"], average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(res["label"], res["pred"], labels=[0, 1]).ravel()
    paired = res.dropna(subset=["pair_id"]).groupby("pair_id")["correct"].all().mean()

    summary.append({"detector": det.name, "precision": p, "recall": r, "f1": f1,
                    "false_positive_rate": fp / (fp + tn),
                    "paired_context_accuracy": paired, "TP": tp, "FP": fp, "FN": fn, "TN": tn})
    per_cat[det.name] = res.groupby("category")["correct"].mean()

summary = pd.DataFrame(summary).round(3)
print("\n=== OVERALL ===")
print(summary.to_string(index=False))
print("\n=== ACCURACY PER CATEGORY ===")
print(pd.DataFrame(per_cat).round(2))
summary.to_csv("results/summary.csv", index=False)