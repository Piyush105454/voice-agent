"""Harm / abuse / severe-distress phrase detection. Keyword-based on purpose: predictable, fast, no LLM.
It never diagnoses; a hit stops the lesson and notifies the teacher."""
from __future__ import annotations

import re

_PATTERNS = [
    # English
    r"\bkill (my ?self|myself|him|her|them)\b", r"\bsuicid", r"\bwant to die\b", r"\bend my life\b",
    r"\bhurt (my ?self|myself)\b", r"\bself[- ]harm", r"\bcut(ting)? myself\b",
    r"\b(he|she|they|someone|papa|mummy|uncle|teacher) (hits|beats|touches|touched|hurts) me\b",
    r"\bbeat(s|ing)? me\b", r"\babus(e|ed|ing)\b", r"\bnot safe\b", r"\bunsafe at home\b",
    r"\bscared to go home\b",
    # Hinglish (romanised)
    r"\bmar(na)? jaana? chahta\b", r"\bmarna chahti\b", r"\bmarna chahta\b", r"\bkhud ko (maar|nuksan|hurt)",
    r"\bjaan de (dunga|dungi|du)\b", r"\bmujhe maar(te|ti)\b", r"\bmaarta hai\b", r"\bmaarti hai\b",
    r"\bpitai\b", r"\bgalat tarike se chhu", r"\bdar lagta hai ghar\b", r"\bsurakshit nahi\b",
    # Devanagari
    r"मरना चाहत", r"आत्महत्या", r"खुद को (मार|नुकसान)", r"मुझे मारत", r"पिटाई", r"गलत तरीके से छु",
    r"सुरक्षित नहीं",
]
_RX = re.compile("|".join(_PATTERNS), re.I)

SAFE_REPLY = {
    "hi": ("Aapne mujhe yeh bataya, yeh bahut himmat ki baat hai. Aap kisi musibat mein nahi ho. "
           "Abhi apne kisi bharosemand bade ya teacher se baat karo. Main aapke teacher ko bata dunga. "
           "Aaj ki class yahin rokte hain. Take care."),
    "en": ("Thank you for telling me, that was brave. You are not in trouble. Please talk to a trusted "
           "adult or your teacher right now. I will let your teacher know. Let's stop the lesson here. Take care."),
}


def scan(text: str | None) -> bool:
    return bool(text and _RX.search(text))


def reply(language: str | None) -> str:
    return SAFE_REPLY["en" if (language or "") == "en" else "hi"]
