"""Each detector exposes predict(text, context) -> dict(pred, pred_category, score, reasons)."""
import base64
import re

# ---------------- Detector 1: naive keyword baseline ----------------
KEYWORD_RX = re.compile(
    r"\b(ignore|disregard|forget|override|bypass|jailbreak|reveal|system prompt|"
    r"secret|password|admin|you are now|act as|dan|unfiltered|no restrictions)\b",
    re.I,
)


class KeywordDetector:
    name = "keyword"

    def predict(self, text, context="general_chat"):
        hits = sorted({m.group(0).lower() for m in KEYWORD_RX.finditer(text)})
        if hits:
            return {"pred": 1, "pred_category": "instruction_override",
                    "score": len(hits),
                    "reasons": "matched keyword(s): " + ", ".join(hits)}
        return {"pred": 0, "pred_category": "benign_plain", "score": 0,
                "reasons": "no suspicious keyword"}


# ---------------- Detector 2: context-aware + explainable ----------------
UNLEET = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o",
                        "5": "s", "7": "t"})
B64_RX = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
QUOTE_RX = re.compile(r'"[^"]{6,}"|“[^”]{6,}”|(?<!\w)\'[^\']{8,}\'(?!\w)')
COMMENT_RX = re.compile(r"<!--.*?-->", re.S)
CUE_RX = re.compile(
    r"\b(the paper|the authors|researchers?|attackers? (?:often|sometimes|typically|usually)|"
    r"red[- ]team|detection rule|course report|security course|how does the attack work|"
    r"explains? why|chapter \d+|bulletin|for example|known attack)\b", re.I)

# feature name -> (regex, weight, category)
FEATURES = {
    "override": (re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass|disable)\b[^.!?\n]{0,25}?"
        r"\b(?:all|any|every\w*|your|the|previous|prior|earlier)\b[^.!?\n]{0,25}?"
        r"\b(?:instructions?|rules|guidelines|prompts?|above|restrictions|safety|programming)\b",
        re.I), 2.0, "instruction_override"),
    "leak": (re.compile(
        r"\b(?:reveal|show|print|display|output|repeat|leak|share|disclose|expose|tell|write|give)\w*\b"
        r"[^.!?\n]{0,30}?\b(?:the|your)\s+(?:full\s+|complete\s+)?"
        r"(?:initial|original|hidden|system|secret|admin|master)\s+"
        r"(?:instructions?|prompts?|rules|message|key|password|token)\b"
        r"|\brepeat\b[^.!?\n]{0,20}?\b(?:text|words|everything|content)\s+(?:above|before)\b",
        re.I), 2.0, "prompt_leak"),
    "roleplay": (re.compile(
        r"\b(?:you are|act as|pretend to be|behave as)\s+(?:now\s+)?dan\b"
        r"|\b(?:unfiltered|uncensored|unrestricted|jailbroken)\b"
        r"|\b(?:no|without(?: any)?)\s+(?:rules|restrictions|limits|filters)\b",
        re.I), 2.0, "role_play"),
    "exfil": (re.compile(
        r"\bsend\b[^.!?\n]{0,40}?\b(?:to|at)\s+[\w.+-]+@[\w-]+\.[\w.]+", re.I),
        2.0, "instruction_override"),
    "authority": (re.compile(
        r"\b(?:system message|new system instructions|end of user input|"
        r"note to the (?:ai|assistant)|for (?:the )?ai (?:assistants?|summari[sz]ers?)|"
        r"i authori[sz]e you|as the (?:developer|admin|administrator|owner))\b",
        re.I), 1.5, "instruction_override"),
    "multilingual": (re.compile(
        r"instrucciones anteriores|mensaje del sistema|ignorez (?:toutes )?les instructions",
        re.I), 2.0, "obfuscation"),
}


def _try_b64(blob):
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True)
        s = raw.decode("utf-8")
        return s if s.isprintable() else None
    except Exception:
        return None


class ContextAwareDetector:
    name = "context_aware"
    THRESHOLD = 1.5

    def predict(self, text, context="general_chat"):
        # 1) look at the raw text, a leetspeak-normalised copy, and decoded base64
        variants = {"raw": text, "leet": text.lower().translate(UNLEET)}
        for blob in B64_RX.findall(text):
            decoded = _try_b64(blob)
            if decoded:
                variants["base64"] = decoded

        quotes = [m.span() for m in QUOTE_RX.finditer(text)]
        hits = {}
        for vname, s in variants.items():
            for fname, (rx, w, cat) in FEATURES.items():
                if fname in hits:
                    continue
                m = rx.search(s)
                if m:
                    hits[fname] = {"w": w, "cat": cat, "ev": m.group(0),
                                   "variant": vname, "span": m.span()}

        reasons = [f'{f}: "{h["ev"][:60]}" (seen in {h["variant"]} text)'
                   for f, h in hits.items()]
        attack = sum(h["w"] for h in hits.values())

        if any(h["variant"] != "raw" for h in hits.values()):
            attack += 2.0
            reasons.append("obfuscation: attack phrase only visible after decoding/normalising")
        if attack and COMMENT_RX.search(text):
            attack += 1.0
            reasons.append("instruction hidden inside an HTML comment")

        # 2) context: is the phrase USED as a command or only MENTIONED?
        mention = 0.0
        if hits:
            raw_hits = [h for h in hits.values() if h["variant"] == "raw"]
            if raw_hits and all(
                any(a <= h["span"][0] and h["span"][1] <= b for a, b in quotes)
                for h in raw_hits
            ):
                mention += 2.5
                reasons.append("attack phrase is quoted -> mentioned, not issued as a command")
            cues = {m.group(0).lower() for m in CUE_RX.finditer(text)}
            if cues:
                mention += min(len(cues), 2) * 1.0
                reasons.append("discussion cues: " + ", ".join(sorted(cues)))
            if context == "retrieved_document" and mention == 0:
                attack += 1.0
                reasons.append("retrieved documents should not contain commands for the AI")

        net = attack - mention
        pred = int(net >= self.THRESHOLD)

        if pred:
            cat = max(hits.values(), key=lambda h: h["w"])["cat"]
            if context == "retrieved_document":
                cat = "indirect_injection"
            elif any(h["variant"] != "raw" for h in hits.values()):
                cat = "obfuscation"
        else:
            cat = "benign_discussion" if hits else "benign_plain"

        if not reasons:
            reasons = ["no attack pattern found"]
        return {"pred": pred, "pred_category": cat, "score": round(net, 2),
                "reasons": " | ".join(reasons)}