"""Spoken-answer normaliser for Hinglish / Hindi / English STT output.
"minus paanch" -> -5, "seventeen" -> 17, "सात" -> 7, "saade chaar" -> 4.5, "plus 3 toh 10" -> 10 (last number wins)."""
from __future__ import annotations

import re

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

EN_UNITS = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
EN_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
           "eighty": 80, "ninety": 90}

# Hindi number words are (mostly) atomic. Romanised spellings vary a lot in STT output.
HI = {
    0: "shunya shoonya sunya शून्य",
    1: "ek एक", 2: "do दो", 3: "teen tin तीन", 4: "char chaar चार", 5: "paanch panch panc पांच पाँच",
    6: "chhe che chhah chah chheh छह छः छे", 7: "saat sat सात", 8: "aath ath आठ", 9: "nau no नौ",
    10: "das dus दस", 11: "gyarah gyaarah gyara ग्यारह", 12: "barah baarah bara बारह",
    13: "terah tera तेरह", 14: "chaudah chauda चौदह", 15: "pandrah pandra पंद्रह पन्द्रह",
    16: "solah sola सोलह", 17: "satrah satra सत्रह", 18: "atharah athara अठारह",
    19: "unnis unees उन्नीस", 20: "bees bis बीस", 21: "ikkis ikkees इक्कीस", 22: "bais baees बाईस",
    23: "teis teyis तेईस", 24: "chaubis chaubees चौबीस", 25: "pachis pachchis pachees पच्चीस",
    26: "chhabbis chabbis छब्बीस", 27: "sattais sattaees सत्ताईस", 28: "athais atthais अट्ठाईस",
    29: "untis unatis उनतीस", 30: "tees tis तीस", 32: "battis बत्तीस", 35: "paintis पैंतीस",
    36: "chhattis chattis छत्तीस", 40: "chalis chaalis चालीस", 42: "bayalis byalis बयालीस",
    50: "pachas pachaas पचास", 100: "sau सौ",
}
HI_WORDS = {w: n for n, ws in HI.items() for w in ws.split()}
# "do" (2) and "no"/"nau" (9) collide with English filler; only accept them when they stand alone
# or next to a sign word, see _ambiguous().
AMBIGUOUS = {"do", "no", "sat", "tin", "ek"}

FRACTION_PREFIX = {"saade": 0.5, "sade": 0.5, "साढ़े": 0.5}
FRACTION_WORDS = {"dedh": 1.5, "dhai": 2.5, "dhaai": 2.5, "डेढ़": 1.5, "ढाई": 2.5}
NEG_WORDS = {"minus", "maainas", "mainus", "negative", "nagetive", "माइनस", "ऋण", "−", "-"}
DONT_KNOW = re.compile(r"(pata\s*nahi|nahi\s*pata|nahin\s*pata|malum\s*nahi|don'?t\s*know|no\s*idea|"
                       r"पता\s*नहीं|नहीं\s*पता|maloom\s*nahi)", re.I)

# Devanagari letters + matras, excluding the danda punctuation U+0964/U+0965 ("सात।" -> "सात").
_DEV = f"{chr(0x900)}-{chr(0x963)}{chr(0x966)}-{chr(0x97F)}"
_TOKEN = re.compile(rf"[−-]?\d+(?:\.\d+)?|[{_DEV}]+|[^\W\d_]+|[−-]", re.UNICODE)

# Sarvam STT in hi-IN writes English words in Devanagari: "सेवन" = seven, "प्लस" = plus.
DEV_EN = {w: en for en, ws in {
    "one": "वन", "two": "टू", "three": "थ्री", "four": "फोर फ़ोर", "five": "फाइव फ़ाइव", "six": "सिक्स",
    "seven": "सेवन", "eight": "एट एइट", "nine": "नाइन", "ten": "टेन", "eleven": "इलेवन", "twelve": "ट्वेल्व",
    "thirteen": "थर्टीन", "fourteen": "फोर्टीन फ़ोर्टीन", "fifteen": "फिफ्टीन फ़िफ़्टीन", "sixteen": "सिक्सटीन",
    "seventeen": "सेवनटीन सेवेंटीन सेवेनटीन", "eighteen": "एटीन", "nineteen": "नाइनटीन", "twenty": "ट्वेंटी",
    "thirty": "थर्टी", "forty": "फोर्टी फ़ोर्टी", "fifty": "फिफ्टी फ़िफ़्टी", "hundred": "हंड्रेड",
    "point": "पॉइंट पॉइन्ट", "minus": "मायनस", "negative": "नेगेटिव",
}.items() for w in ws.split()}


def _tokens(text: str) -> list[str]:
    t = (text or "").translate(_DEV_DIGITS).lower().replace("–", "-")
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
    return [DEV_EN.get(tok, tok) for tok in _TOKEN.findall(t)]


def numbers(text: str) -> list[float]:
    """Every number mentioned, in order, with spoken signs applied."""
    toks = _tokens(text)
    out: list[float] = []
    neg = False
    frac = 0.0
    i = 0
    while i < len(toks):
        w = toks[i]
        val: float | None = None
        if w in NEG_WORDS:
            neg = True
            i += 1
            continue
        if w in FRACTION_PREFIX:
            frac = FRACTION_PREFIX[w]
            i += 1
            continue
        if re.fullmatch(r"[−-]?\d+(?:\.\d+)?", w):
            if w[0] in "−-":
                neg, w = True, w[1:]
            val = float(w)
            # "4 point 5"
            if i + 2 < len(toks) and toks[i + 1] == "point" and toks[i + 2].isdigit():
                val = float(f"{int(val)}.{toks[i + 2]}")
                i += 2
        elif w in FRACTION_WORDS:
            val = FRACTION_WORDS[w]
        elif w in EN_TENS or w in EN_UNITS or w == "hundred":
            val, i = _english(toks, i)
            out.append(-(val + frac) if neg else val + frac)
            neg, frac = False, 0.0
            continue
        elif w in HI_WORDS:
            if w in AMBIGUOUS and not _standalone(toks, i, neg):
                i += 1
                continue
            val = float(HI_WORDS[w])
        if val is not None:
            out.append(-(val + frac) if neg else val + frac)
            neg, frac = False, 0.0
        else:  # a sign word only applies to the number right after it ("minus ho jata hai... 7" -> 7)
            neg, frac = False, 0.0
        i += 1
    return out


def _standalone(toks: list[str], i: int, neg: bool) -> bool:
    return neg or len(toks) <= 2 or (i > 0 and toks[i - 1] in FRACTION_PREFIX)


def _english(toks: list[str], i: int) -> tuple[float, int]:
    """Greedy English number phrase starting at i: 'one hundred twelve', 'twenty three', 'four point five'."""
    total, cur = 0, 0
    while i < len(toks):
        w = toks[i]
        if w in EN_UNITS:
            cur += EN_UNITS[w]
        elif w in EN_TENS:
            cur += EN_TENS[w]
        elif w == "hundred":
            cur = max(cur, 1) * 100
        elif w == "and" and total + cur and i + 1 < len(toks) and toks[i + 1] in {**EN_UNITS, **EN_TENS}:
            pass
        else:
            break
        i += 1
    val = float(total + cur)
    if i + 1 < len(toks) and toks[i] == "point" and toks[i + 1] in EN_UNITS:
        val += EN_UNITS[toks[i + 1]] / 10
        i += 2
    return val, i


def final_number(text: str) -> float | None:
    """The student's answer = the last number they said ('minus ho jata hai... 7' -> 7)."""
    ns = numbers(text)
    return ns[-1] if ns else None


def to_float(s: str) -> float | None:
    try:
        return float(str(s).strip().replace("−", "-"))
    except ValueError:
        return None


def same(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) < 1e-6


def says_dont_know(text: str) -> bool:
    return bool(DONT_KNOW.search(text or ""))


YES = re.compile(r"\b(haan|haa|ha|han|yes|yeah|yep|ok|okay|theek|thik|chalo|shuru|ready|sure|bilkul|ji)\b|हाँ|हां|ठीक|चलो|शुरू|जी", re.I)
NO = re.compile(r"\b(nahi|nahin|nai|no|nope|not now|baad mein|later)\b|नहीं|नही|बाद में", re.I)


def yes_no(text: str) -> bool | None:
    y, n = bool(YES.search(text or "")), bool(NO.search(text or ""))
    if n and not y:
        return False
    if y and not n:
        return True
    return None


def confidence_value(text: str) -> int | None:
    n = final_number(text)
    if n is None or n != int(n):
        return None
    n = int(abs(n))
    return n if 1 <= n <= 10 else None
