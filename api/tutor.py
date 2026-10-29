"""Grading, hint ladder and next action. Deterministic first; LLM only for answers we cannot match."""
from __future__ import annotations

import answers
from config import settings
from llm import llm, prompt

HINT_LADDER = ["nudge", "hint", "worked_step", "reveal"]
ACTIONS = {1: "hint", 2: "explain_step", 3: "reveal"}


def decide_action(correct: bool, hint_level: int) -> dict:
    """hint_level = highest level already given for this question in this session."""
    if correct:
        return {"action": "praise_next", "hint_level": hint_level}
    nxt = min(hint_level + 1, 3)
    return {"action": ACTIONS[nxt], "hint_level": nxt}


# ---------------------------------------------------------------- grading


def judge(question: dict, student_text: str, misconceptions: dict[str, str]) -> dict:
    """question: {id,text,answer,wrong_answer_map}; misconceptions: id -> description (all known)."""
    text = (student_text or "").strip()
    if not text or answers.says_dont_know(text):
        return {"correct": False, "misconception": None, "source": "no_answer", "parsed": None}

    correct_val = answers.to_float(question["answer"])
    val = answers.final_number(text)
    if val is not None and correct_val is not None:
        if answers.same(val, correct_val):
            return {"correct": True, "misconception": None, "source": "deterministic", "parsed": val}
        for wrong, mis in (question.get("wrong_answer_map") or {}).items():
            if answers.same(val, answers.to_float(wrong)):
                return {"correct": False, "misconception": mis, "source": "wrong_answer_map", "parsed": val}

    # Unmatched: ask the LLM (time-boxed). Without one, a wrong number is wrong with no tag.
    out = llm("", _fill(prompt("judge_answer.md"), question_text=question["text"],
                        correct_answer=question["answer"],
                        misconception_list="; ".join(f"{k}: {v}" for k, v in misconceptions.items()),
                        student_answer_text=text),
              json_mode=True, max_tokens=200, timeout=2.5)
    if isinstance(out, dict) and "correct" in out:
        mis = out.get("misconception")
        mis = mis if mis in misconceptions else None
        correct = bool(out["correct"])
        # Trust the number over the LLM when we parsed one.
        if val is not None and correct_val is not None:
            correct = answers.same(val, correct_val)
        return {"correct": correct, "misconception": None if correct else mis, "source": "llm", "parsed": val}
    return {"correct": False, "misconception": None, "source": "unmatched", "parsed": val}


# ---------------------------------------------------------------- hints

_T = {  # misconception -> level -> (hinglish, english). Level 3 may contain {answer}; 1-2 never do.
    "adds_instead_of_inverse": {
        1: ("Chalo check karte hain. x ke saath jo number juda hai, use hatane ke liye ulta kaam kya hoga?",
            "Let's check. To remove the number attached to x, what is the opposite operation?"),
        2: ("Ek step saath karte hain: plus ko hatane ke liye dono taraf se wahi number ghatao. Ab dusri taraf kya bacha?",
            "Let's do one step together: take the same number away from both sides. What is left on the other side?"),
        3: ("Answer {answer} hai. Plus ko hatane ke liye minus karte hain, guna ko hatane ke liye divide.",
            "The answer is {answer}. To undo plus we subtract, to undo times we divide."),
    },
    "sign_not_flipped": {
        1: ("Chalo check karte hain. Jab number equal ke dusri taraf jaata hai, toh uske sign ka kya hota hai?",
            "Let's check. When a number moves to the other side of equals, what happens to its sign?"),
        2: ("Minus wala number dusri taraf jaakar plus ban jaata hai. Ab dono numbers ko jodo, kya aaya?",
            "A minus number becomes plus on the other side. Now add the two numbers, what do you get?"),
        3: ("Answer {answer} hai. Sign badal kar dusri taraf le gaye aur jod diya.",
            "The answer is {answer}. We flipped the sign while moving it across and added."),
    },
    "coefficient_ignored": {
        1: ("Chalo check karte hain. x ke aage wale number ka matlab hai 'itne guna x'. x akela kaise hoga?",
            "Let's check. The number in front of x means 'that many times x'. How do we get x alone?"),
        2: ("Dono taraf ko x ke aage wale number se divide karo. Ab kya bacha?",
            "Divide both sides by the number in front of x. What is left?"),
        3: ("Answer {answer} hai. x ke aage wale number se divide karna tha.",
            "The answer is {answer}. We needed to divide by the number in front of x."),
    },
    "neg_number_confusion": {
        1: ("Chalo number line socho. Pehle number se shuru karke kis taraf jaoge, left ya right?",
            "Picture a number line. Starting from the first number, which way do you move, left or right?"),
        2: ("Minus ka matlab left jaana, plus ka matlab right jaana. Ek ek kadam gino, kahan pahunche?",
            "Minus means move left, plus means move right. Count the steps one by one, where do you land?"),
        3: ("Answer {answer} hai. Number line par kadam gin kar yahi aata hai.",
            "The answer is {answer}. Counting the steps on the number line gives exactly that."),
    },
    "distributes_partially": {
        1: ("Chalo check karte hain. Bracket ke bahar wala number andar kis kis se multiply hota hai?",
            "Let's check. The number outside the bracket multiplies which terms inside?"),
        2: ("Bahar wala number bracket ke har term se multiply hota hai, dono se. Ab dobara jodo.",
            "The outside number multiplies every term in the bracket, both of them. Add them again."),
        3: ("Answer {answer} hai. Bahar wala number dono terms se multiply hua.",
            "The answer is {answer}. The outside number multiplied both terms."),
    },
    "equals_as_answer": {
        1: ("Chalo check karte hain. Equal ka matlab hai dono taraf barabar. Left side kitna hai?",
            "Let's check. Equals means both sides are the same. What is the left side?"),
        2: ("Left side ka total nikalo, phir socho right side mein kya jodne se wahi total banega.",
            "Find the left side total, then think what makes the right side the same total."),
        3: ("Answer {answer} hai, kyunki tab dono taraf barabar ho jaate hain.",
            "The answer is {answer}, because then both sides are equal."),
    },
    None: {
        1: ("Chalo check karte hain. Sawaal ko dhyaan se dobara socho, pehla step kya hoga?",
            "Let's check. Think about the question again, what would the first step be?"),
        2: ("Ek step saath karte hain. Pehla step bolo, main saath mein check karta hoon.",
            "Let's go one step at a time. Tell me your first step and we will check it together."),
        3: ("Answer {answer} hai. Koi baat nahi, isko step by step dekhte hain.",
            "The answer is {answer}. No problem, let's look at it step by step."),
    },
}


def _fill(tpl: str, **kw) -> str:
    for k, v in kw.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def reveals_answer(text: str, answer: str) -> bool:
    a = answers.to_float(answer)
    return any(answers.same(n, a) for n in answers.numbers(text))


def hint(question: dict, misconception: str | None, level: int, language: str = "hi-en",
         strategy: str = "step_by_step", misconception_desc: str = "") -> str:
    lvl = max(1, min(level, 3))
    lang_i = 1 if language == "en" else 0
    template = _fill(_T.get(misconception, _T[None])[lvl][lang_i], answer=question["answer"])
    if not settings.llm_hints:
        return template
    out = llm("", _fill(prompt("hint_writer.md"), hint_level=lvl, question_text=question["text"],
                        misconception_desc=misconception_desc or "unknown", strategy=strategy),
              max_tokens=120, timeout=2.5)
    if not out or len(out) > 220:
        return template
    if lvl < 3 and reveals_answer(out, question["answer"]):  # hard guarantee: no reveal before level 3
        return template
    return out.strip().strip('"')
