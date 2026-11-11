import os
import sys
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from detectors import KeywordDetector, ContextAwareDetector

args = [a for a in sys.argv[1:] if not a.startswith("--")]
use_llm = "--llm" in sys.argv
data_path = args[0] if args else "data/dataset.csv"
suffix = "_heldout" if "heldout" in data_path else ""

df = pd.read_csv(data_path)
os.makedirs("results", exist_ok=True)

detectors = [KeywordDetector(), ContextAwareDetector()]
if use_llm:
    from llm_detector import LLMDetector
    detectors.append(LLMDetector())


def outcome(r):
    if r["pred"] == 1:
        return "TP" if r["label"] == 1 else "FP"
    return "FN" if r["label"] == 1 else "TN"


summary, per_cat = [], {}
for det in detectors:
    outs = [det.predict(t, c) for t, c in zip(df["text"], df["context"])]
    res = pd.concat([df, pd.DataFrame(outs)], axis=1)
    res["correct"] = res["label"] == res["pred"]
    res["outcome"] = res.apply(outcome, axis=1)
    res.to_csv(f"results/predictions_{det.name}{suffix}.csv", index=False)

    p, r, f1, _ = precision_recall_fscore_support(
        res["label"], res["pred"], average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(res["label"], res["pred"], labels=[0, 1]).ravel()
    pairs = res.dropna(subset=["pair_id"])
    paired = pairs.groupby("pair_id")["correct"].all().mean() if len(pairs) else float("nan")

    summary.append({"detector": det.name, "precision": p, "recall": r, "f1": f1,
                    "false_positive_rate": fp / (fp + tn),
                    "paired_context_accuracy": paired, "TP": tp, "FP": fp, "FN": fn, "TN": tn})
    per_cat[det.name] = res.groupby("category")["correct"].mean()

summary = pd.DataFrame(summary).round(3)
print("\n=== OVERALL ===")
print(summary.to_string(index=False))
print("\n=== ACCURACY PER CATEGORY ===")
print(pd.DataFrame(per_cat).round(2))
summary.to_csv(f"results/summary{suffix}.csv", index=False)
