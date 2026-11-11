import itertools
import pandas as pd
from target_app import respond, attack_succeeded

tests = pd.read_csv("data/app_tests.csv").fillna("")
rows = []

for f, h, o in itertools.product([0, 1], repeat=3):
    parts = [n for n, on in [("filter", f), ("hierarchy", h), ("output", o)] if on]
    name = "+".join(parts) or "none"
    for t in tests.itertuples():
        resp, blocked = respond(t.user_input, t.doc, f, h, o)
        rows.append({
            "config": name, "id": t.id, "label": t.label, "type": t.type,
            "blocked_by": blocked,
            "success": int(t.label == "attack" and attack_succeeded(resp)),
            "refused_benign": int(t.label == "benign" and blocked != ""),
            "response": resp[:200].replace("\n", " "),
        })
    print("done:", name)

res = pd.DataFrame(rows)
res.to_csv("results/defence_results.csv", index=False, encoding="utf-8")

atk = res[res.label == "attack"]
ben = res[res.label == "benign"]
summ = pd.DataFrame({
    "attack_success_rate": atk.groupby("config")["success"].mean(),
    "false_refusal_rate": ben.groupby("config")["refused_benign"].mean(),
})
for ty in ["direct", "indirect", "evasive"]:
    summ[f"ASR_{ty}"] = atk[atk.type == ty].groupby("config")["success"].mean()
summ = summ.round(3).sort_values("attack_success_rate")

print("\n=== DEFENCE COMPARISON ===")
print(summ.to_string())
print("\n=== WHO BLOCKED WHAT ===")
print(res.groupby(["config", "blocked_by"]).size().unstack(fill_value=0))
print("\nLLM errors:", int((res.response == "[LLM_ERROR]").sum()))
summ.to_csv("results/defence_summary.csv")