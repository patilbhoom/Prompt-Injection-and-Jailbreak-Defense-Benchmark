import sys
import pandas as pd

suffix = "_heldout" if "heldout" in sys.argv[1:] else ""
names = ["keyword", "context_aware"] + (["llm"] if "--llm" in sys.argv else [])

lines = []
for name in names:
    res = pd.read_csv(f"results/predictions_{name}{suffix}.csv").astype(object).fillna("")
    errs = res[res["outcome"].isin(["FP", "FN"])]
    lines.append(f"\n=== {name}: {len(errs)} errors ===")
    for r in errs.itertuples():
        lines.append(f"[{r.outcome}] ({r.context} / {r.category}) {r.text[:90]}")
        lines.append(f"      why: {r.reasons}\n")

out_path = f"results/errors{suffix}.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Wrote {out_path}")
