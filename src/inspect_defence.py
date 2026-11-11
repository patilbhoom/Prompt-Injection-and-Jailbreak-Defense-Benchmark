import pandas as pd

r = pd.read_csv("results/defence_results.csv").fillna("")
t = pd.read_csv("data/app_tests.csv").fillna("")[["id", "user_input"]]
r = r.merge(t, on="id")
pd.set_option("display.max_colwidth", 80)
print("\n--- attacks that succeeded ---")
print(r[r.success == 1][["config", "type", "user_input", "response"]].to_string())
print("\n--- benign requests refused ---")
print(r[r.refused_benign == 1][["config", "blocked_by", "user_input"]].to_string())