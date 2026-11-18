# Prompt Injection and Jailbreak Defense Benchmark

A context-aware, explainable benchmark for prompt-injection detection, plus a comparison of multi-layer defences on a chatbot that protects a secret.

## Problem

Keyword filters flag harmless text ("ignore the first row", a security lecture) and miss obfuscated attacks. This project asks:

1. Does **context-aware** detection reduce false positives without missing real injections?
2. Can every verdict be **explained** (why flagged, which category, why it was wrong)?
3. Which **defence layers** (input filter, instruction hierarchy, output validation) work best, and what do they cost in usability?

## Key findings

- A keyword baseline flags 46% of benign dev prompts (false positive rate 0.457) and scores 0.00 on obfuscated attacks.
- A hand-written context-aware regex detector reached F1 **1.00 on the dev set** but only **0.29 on an independently written held-out set**: hand-written rules overfit their own test data.
- An LLM-based detector with structured, explainable output scored 1.00 on the held-out set, but its prompt was written after seeing those failures, so treat that number as optimistic.
- On a chatbot protecting a secret, attack success fell from **50% (no defences)** to **0%** with instruction hierarchy + output validation, with no false refusals on the benign set.
- Output validation catches secret leaks but cannot stop hijacks like "reply only with PWNED". Instruction hierarchy handles most hijacks but still leaked in 2 of 24 attacks. Together they cover each other's gaps.
- Output validation alone wrongly refused 2 of 24 benign requests, a measurable strength-vs-usability cost.

## Detector results

Dev set: 140 samples (70 attacks, 70 benign), written alongside the detectors.

Held-out set: 50 samples (26 attacks, 24 benign), written afterwards with new wording, Hindi and Kannada text, ROT13, spaced letters, attacks hidden in documents, and attacks disguised as quotes.

| Set | Detector | Precision | Recall | F1 | False positive rate |
|---|---|---:|---:|---:|---:|
| Dev | Keyword | 0.549 | 0.557 | 0.553 | 0.457 |
| Dev | Context-aware regex | 1.000 | 1.000 | 1.000 | 0.000 |
| Dev | LLM | 1.000 | 1.000 | 1.000 | 0.000 |
| Held-out | Keyword | 0.417 | 0.385 | 0.400 | 0.583 |
| Held-out | Context-aware regex | 0.625 | 0.192 | 0.294 | 0.125 |
| Held-out | LLM | 1.000 | 1.000 | 1.000 | 0.000 |

Every detector returns a label, a category and a reason. A full breakdown of errors and their causes is in [docs/error_analysis.md](docs/error_analysis.md).

## Defence comparison

Target: a fake store chatbot (SupportBot) holding a secret discount code. Test set: 24 attacks (8 direct, 8 indirect via documents, 8 evasive) and 24 benign requests. Attack success means the secret leaked or the bot was hijacked into replying "PWNED".

Layers: **filter** = context-aware regex input filter, **hierarchy** = hardened system prompt with untrusted input in tags, **output** = reply scanned for the secret or copied system-prompt text.

| Config | Attack success | Direct | Indirect | Evasive | False refusal |
|---|---:|---:|---:|---:|---:|
| none | 0.500 | 0.500 | 0.625 | 0.375 | 0.000 |
| filter | 0.333 | 0.250 | 0.375 | 0.375 | 0.000 |
| output | 0.125 | 0.125 | 0.250 | 0.000 | 0.083 |
| hierarchy | 0.083 | 0.000 | 0.125 | 0.125 | 0.000 |
| filter + hierarchy | 0.083 | 0.000 | 0.125 | 0.125 | 0.000 |
| filter + output | 0.042 | 0.000 | 0.125 | 0.000 | 0.083 |
| hierarchy + output | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| filter + hierarchy + output | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Notes:

- The input filter helped least. It misses evasive and many document-based attacks, and adds nothing once hierarchy is on.
- A first run against a stronger target model showed almost no successful attacks even with no defences (4.2%), so the weaker model was used to make the comparison informative.

## Repo structure

```text
data/       dataset.csv, heldout.csv, app_tests.csv
src/        detectors.py (keyword + context-aware), llm_detector.py,
            build_dataset.py, build_heldout.py, build_app_tests.py,
            run_eval.py, error_analysis.py,
            target_app.py, run_defence_eval.py, inspect_defence.py
results/    summaries, predictions, error lists
docs/       error_analysis.md
