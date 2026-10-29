"""Pure unit tests: no Postgres / FalkorDB / network needed."""
import httpx
import pytest

import answers
import bolna
import mastery
import safety
import sarvam
import tutor


@pytest.mark.parametrize("text,expected", [
    ("17", 17), ("minus 5", -5), ("-5", -5), ("minus paanch", -5), ("seventeen", 17), ("twenty three", 23),
    ("सात", 7), ("माइनस पांच", -5), ("७", 7), ("saade chaar", 4.5), ("4.5", 4.5), ("four point five", 4.5),
    ("minus ho jata hai... 7", 7), ("plus 3 toh 10", 10), ("left... minus 5", -5), ("x equals 7", 7),
    ("mera answer barah hai", 12), ("one hundred twelve", 112), ("do", 2), ("hmm", None),
    # real Sarvam saaras:v4 hi-IN output shapes (Devanagari, danda punctuation, English words transliterated)
    ("माइनस पाँच।", -5), ("मेरा जवाब सात है।", 7), ("सेवनटीन", 17), ("ट्वेंटी थ्री।", 23), ("माइनस सेवन", -7),
])
def test_final_number(text, expected):
    assert answers.final_number(text) == expected


def test_yes_no_and_confidence():
    assert answers.yes_no("haan chalo") is True
    assert answers.yes_no("nahi abhi nahi") is False
    assert answers.yes_no("hmm") is None
    assert answers.confidence_value("shayad 3") == 3
    assert answers.confidence_value("15") is None
    assert answers.says_dont_know("mujhe pata nahi")


Q17 = {"id": "q_017", "text": "x + 5 = 12, x kya hoga?", "answer": "7",
       "wrong_answer_map": {"17": "adds_instead_of_inverse"}}


def test_judge_deterministic(monkeypatch):
    monkeypatch.setattr(tutor, "llm", lambda *a, **k: None)
    assert tutor.judge(Q17, "saat", {})["correct"] is True
    j = tutor.judge(Q17, "seventeen", {})
    assert j["correct"] is False and j["misconception"] == "adds_instead_of_inverse"
    assert tutor.judge(Q17, "pata nahi", {})["source"] == "no_answer"
    assert tutor.judge(Q17, "9", {})["misconception"] is None


def test_hint_ladder_never_reveals_before_level_3(monkeypatch):
    for mis in list(tutor._T):
        for lvl in (1, 2):
            for lang in ("hi-en", "en"):
                h = tutor.hint(Q17, mis, lvl, lang)
                assert not tutor.reveals_answer(h, "7"), (mis, lvl, h)
        assert tutor.reveals_answer(tutor.hint(Q17, mis, 3), "7")
    # an LLM hint that leaks the answer is rejected
    monkeypatch.setattr(tutor.settings, "llm_hints", True)
    monkeypatch.setattr(tutor, "llm", lambda *a, **k: "x toh 7 hoga na")
    assert not tutor.reveals_answer(tutor.hint(Q17, "adds_instead_of_inverse", 1), "7")


def test_decide_action():
    assert tutor.decide_action(False, 0) == {"action": "hint", "hint_level": 1}
    assert tutor.decide_action(False, 1)["action"] == "explain_step"
    assert tutor.decide_action(False, 2)["action"] == "reveal"
    assert tutor.decide_action(False, 3)["action"] == "reveal"
    assert tutor.decide_action(True, 2)["action"] == "praise_next"


def test_bkt():
    p = 0.3
    assert mastery.bkt_update(p, True) > p
    assert mastery.bkt_update(p, False) < p + mastery.P_LEARN
    assert mastery.bkt_update(p, True, hints_used=2) < mastery.bkt_update(p, True)


def test_safety():
    assert safety.scan("papa beats me every day")
    assert safety.scan("main marna chahta hoon")
    assert safety.scan("मुझे मारते हैं")
    assert not safety.scan("x + 5 = 12 toh 7")
    assert not safety.scan("minus 5")


@pytest.mark.parametrize("status,body,limit", [
    (402, "Payment required", True), (429, "Too many requests", True),
    (400, '{"message":"Insufficient wallet balance"}', True), (403, "Your plan call limit is exhausted", True),
    (400, "recipient_phone_number invalid", False), (500, "internal", False),
])
def test_bolna_classify(status, body, limit):
    assert bolna.classify(status, body).limit is limit


def test_sarvam_error_parsing(monkeypatch):
    monkeypatch.setattr(sarvam.settings, "sarvam_api_key", "k")
    def fake_post(url, **kw):
        return httpx.Response(402, json={"error": {"code": "insufficient_quota_error", "message": "No credits available"}},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(sarvam.httpx, "post", fake_post)
    with pytest.raises(sarvam.SarvamError) as e:
        sarvam.tts("namaste")
    assert e.value.out_of_credit and not e.value.retryable


def test_web_call_token_roundtrip():
    import voice_router
    t = voice_router.make_token("11111111-1111-4111-8111-111111111111")
    assert voice_router.read_token(t) == "11111111-1111-4111-8111-111111111111"
    with pytest.raises(voice_router.VoiceError):
        voice_router.read_token(t[:-2] + "xx")
    with pytest.raises(voice_router.VoiceError):
        voice_router.read_token(voice_router.make_token("abc", minutes=-1))


def test_router_falls_back_to_sarvam_when_bolna_limit(monkeypatch):
    import voice_router
    voice_router.reset_bolna()
    monkeypatch.setattr(voice_router.db, "student", lambda sid: {"phone_e164": "+919800000021", "first_name": "R"})
    monkeypatch.setattr(voice_router.db, "has_consent", lambda sid: True)
    monkeypatch.setattr(voice_router.db, "audit", lambda *a: None)
    monkeypatch.setattr(voice_router.events, "emit", lambda *a, **k: None)
    monkeypatch.setattr(voice_router.bolna, "enabled", lambda: True)
    monkeypatch.setattr(voice_router.sarvam, "enabled", lambda: True)
    # the session is made before dialling (its id + Guru's memory travel with the call)
    import phone
    monkeypatch.setattr(voice_router.db, "create_session", lambda *a, **k: {"id": "sess-1", "existing": False})
    monkeypatch.setattr(voice_router.db, "run", lambda *a, **k: None)
    monkeypatch.setattr(voice_router.db, "bind_call", lambda *a: None)
    monkeypatch.setattr(phone, "call_variables", lambda sid, sess=None: {"student_id": sid, "session_id": sess})
    calls = []
    def out_of_credit(*a, **k):
        calls.append(1)
        raise bolna.BolnaError(402, "insufficient balance", limit=True)
    monkeypatch.setattr(voice_router.bolna, "trigger_call", out_of_credit)

    r = voice_router.start_call("sid-1")
    assert r["provider"] == "sarvam_web" and "/call?t=" in r["url"] and "limit reached" in r["fallback_reason"]
    assert voice_router.status()["bolna"]["blocked"]
    r2 = voice_router.start_call("sid-1")          # benched: no second Bolna request
    assert r2["provider"] == "sarvam_web" and len(calls) == 1

    voice_router.reset_bolna()                      # after a top-up
    monkeypatch.setattr(voice_router.bolna, "trigger_call", lambda *a, **k: {"execution_id": "e1", "status": "queued"})
    assert voice_router.start_call("sid-1")["provider"] == "bolna"


def test_misconception_update_rule():
    s = mastery.misconception_update(None, "error")
    assert 0.3 < s < 1                                       # new edge starts at 0.3, error pushes it up
    assert mastery.misconception_update(0.99, "error") <= 1.0   # saturates, never exceeds 1
    assert mastery.misconception_update(0.8, "correct") < mastery.misconception_update(0.8, "guided_correct") < 0.8
    assert mastery.misconception_update(0.0, "correct") == 0.0


def test_bolna_trial_unverified_number_is_not_an_outage():
    e = bolna.classify(400, '{"message":"Trial accounts can only make calls to verified phone numbers."}')
    assert e.recipient and not e.limit
