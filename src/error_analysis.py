import pandas as pd

for name in ["keyword", "context_aware"]:
    res = pd.read_csv(f"results/predictions_{name}.csv").fillna("")
    errs = res[res["outcome"].isin(["FP", "FN"])]
    print(f"\n=== {name}: {len(errs)} errors ===")
    for r in errs.itertuples():
        print(f"[{r.outcome}] ({r.context} / {r.category}) {r.text[:90]}")
        print(f"      why: {r.reasons}\n")