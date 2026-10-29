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
    r"\bscared to go home\b", r"\bno reason to live\b", r"\bbetter off dead\b", r"\bgive up on life\b",
    # Hinglish (romanised)
    r"\bmar(na)? jaana? chahta\b", r"\bmarna chahti\b", r"\bmarna chahta\b", r"\bkhud ko (maar|nuksan|hurt)",
    r"\bjaan de (dunga|dungi|du)\b", r"\bmujhe maar(te|ti)\b", r"\bmaarta hai\b", r"\bmaarti hai\b",
    r"\bpitai\b", r"\bgalat tarike se chhu", r"\bdar lagta hai ghar\b", r"\bsurakshit nahi\b",
    # Devanagari
    r"मरना चाहत", r"आत्महत्या", r"खुद को (मार|नुकसान)", r"मुझे मारत", r"पिटाई", r"गलत तरीके से छु",
    r"सुरक्षित नहीं", r"जीने का मन नहीं", r"जान दे (दूंगा|दूँगा|दूंगी|दूँगी)", r"जीना नहीं चाहत",
    r"jeene ka mann nahi", r"jeena nahi chahta",
]
_RX = re.compile("|".join(_PATTERNS), re.I)

SAFE_REPLY = {
    "hi": ("Aapne mujhe yeh bataya, yeh bahut himmat ki baat hai. Aap akele nahi ho aur kisi musibat mein nahi ho. "
           "Abhi apne kisi bharosemand insaan se baat karo. Free helpline Tele MANAS, ek chaar chaar ek chhe, "
           "chaubees ghante khula hai, aur emergency mein ek ek do. Main aapke teacher ko bhi bata dunga. Take care."),
    "en": ("Thank you for telling me, that was brave. You are not alone and you are not in trouble. Please talk to "
           "someone you trust right now. The free Tele MANAS helpline is one four four one six, open all day and "
           "night, or call one one two in an emergency. I will let your teacher know too. Take care."),
}


def scan(text: str | None) -> bool:
    return bool(text and _RX.search(text))


def reply(language: str | None) -> str:
    return SAFE_REPLY["en" if (language or "") == "en" else "hi"]
