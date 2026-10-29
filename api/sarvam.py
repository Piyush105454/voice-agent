"""Sarvam AI REST client: speech-to-text, text-to-speech, chat. Docs: https://docs.sarvam.ai/api-reference
Auth header is `api-subscription-key`. Errors are JSON {"error": {"code","message"}}; 402
`insufficient_quota_error` means the org is out of credits (never retry it)."""
from __future__ import annotations

import base64
import io
import wave
from array import array
import re
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

import httpx

from config import settings

BASE = "https://api.sarvam.ai"
TTS_MAX_CHARS = 2500  # bulbul:v3 / v4-flash
# mp3 measured ~2.7 s vs ~6.8 s for wav on the same text, at a third of the size.
TTS_CODEC, TTS_MIME, TTS_RATE = "mp3", "audio/mpeg", 22050
_TTS_CACHE: OrderedDict[tuple, bytes] = OrderedDict()   # fixed phrases (greetings, questions, hints) repeat a lot
_TTS_CACHE_MAX = 400


class SarvamError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"sarvam {status} {code}: {message}")
        self.status, self.code, self.message = status, code, message

    @property
    def out_of_credit(self) -> bool:
        return self.status == 402 or self.code in ("insufficient_quota_error", "seat_budget_exhausted_error")

    @property
    def retryable(self) -> bool:
        return self.status in (429, 500, 502, 503) and not self.out_of_credit


def enabled() -> bool:
    return bool(settings.sarvam_api_key)


def _headers() -> dict:
    return {"api-subscription-key": settings.sarvam_api_key}


def _check(r: httpx.Response) -> dict:
    if r.status_code < 400:
        return r.json()
    code, msg = "unknown", r.text[:300]
    try:
        err = r.json().get("error") or {}
        code, msg = err.get("code") or code, err.get("message") or msg
    except Exception:
        pass
    raise SarvamError(r.status_code, code, msg)


def lang_code(student_language: str | None) -> str:
    """Our students.language (hi | en | hi-en) -> Sarvam BCP-47 code."""
    return "en-IN" if (student_language or "").lower() == "en" else "hi-IN"


def stt(audio: bytes, filename: str = "audio.webm", content_type: str = "audio/webm",
        language: str | None = None, keyterms: list[str] | None = None, timeout: float = 15,
        mode: str | None = None) -> dict:
    """Short utterance (< 30 s) -> {"transcript", "language_code"}.
    mode (saaras:v3 only): "translit" = Latin script for English AND Hinglish ("Haan, AI bahut kuch kar sakta hai"),
    measured as the cleanest input for the coach; v4 in hi-IN writes English words in Devanagari."""
    # Sarvam matches the bare MIME type ("audio/webm;codecs=opus" is rejected even where audio/webm isn't)
    content_type = (content_type or "audio/wav").split(";")[0].strip()
    model = "saaras:v3" if mode else settings.sarvam_stt_model
    data = {"model": model, "language_code": language or "unknown"}
    if mode:
        data["mode"] = mode
    if keyterms and model == "saaras:v4":
        import json
        data["keyterms"] = json.dumps(keyterms[:50])
    r = httpx.post(f"{BASE}/speech-to-text", headers=_headers(), data=data,
                   files={"file": (filename, audio, content_type)}, timeout=timeout)
    out = _check(r)
    return {"transcript": (out.get("transcript") or "").strip(), "language_code": out.get("language_code")}


def tts(text: str, language: str = "hi-IN", speaker: str | None = None, timeout: float = 15) -> bytes:
    """Text -> audio bytes (TTS_MIME). Cached per (text, language, voice, model)."""
    speaker = speaker or settings.sarvam_tts_speaker
    key = (text, language, speaker, settings.sarvam_tts_model, settings.sarvam_tts_pace, TTS_CODEC)
    if key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(key)
        return _TTS_CACHE[key]
    body = {"text": text[:TTS_MAX_CHARS], "language_code": language, "model": settings.sarvam_tts_model,
            "speaker": speaker, "pace": settings.sarvam_tts_pace,
            "output_audio_codec": TTS_CODEC, "speech_sample_rate": TTS_RATE}
    r = httpx.post(f"{BASE}/text-to-speech", headers={**_headers(), "Content-Type": "application/json"},
                   json=body, timeout=timeout)
    audios = _check(r).get("audios") or []
    if not audios:
        raise SarvamError(200, "empty_audio", "no audio returned")
    audio = base64.b64decode(audios[0])
    _TTS_CACHE[key] = audio
    while len(_TTS_CACHE) > _TTS_CACHE_MAX:
        _TTS_CACHE.popitem(last=False)
    return audio


# ---------------------------------------------------------------- fast STT for long utterances
# Measured: REST STT time grows with audio length (a 14.7 s answer took 7-19 s) and students' recordings include
# silence before they start and after they stop. So: trim silence, split at natural pauses into <= ~6 s pieces,
# transcribe the pieces in parallel, join. Latency ~ the longest piece instead of the whole recording.

def _pcm16_mono(audio: bytes) -> tuple[array, int] | None:
    """16-bit PCM WAV (what our browsers send) -> samples, rate. None for anything else (sent as-is)."""
    try:
        w = wave.open(io.BytesIO(audio))
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            return None
        pcm = array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
        return pcm, w.getframerate()
    except Exception:
        return None


def _wav(pcm: array, rate: int) -> bytes:
    out = io.BytesIO()
    w = wave.open(out, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(pcm.tobytes())
    w.close()
    return out.getvalue()


def _mp3(pcm: array, rate: int) -> bytes:
    """16-bit mono PCM -> 32 kbps MP3 (falls back to WAV if the encoder isn't installed)."""
    try:
        import lameenc
    except ImportError:
        return _wav(pcm, rate)
    enc = lameenc.Encoder()
    enc.set_bit_rate(32)
    enc.set_in_sample_rate(rate)
    enc.set_channels(1)
    enc.set_quality(5)
    return bytes(enc.encode(pcm.tobytes()) + enc.flush())


def speech_chunks(pcm: array, rate: int, max_s: float = 6.0, min_s: float = 1.5) -> list[tuple[int, int]]:
    """Voiced regions (trimmed) split at the quietest pauses so every piece is <= max_s seconds."""
    hop = rate // 50                                   # 20 ms frames
    rms = [(sum(x * x for x in pcm[i:i + hop]) / hop) ** 0.5 for i in range(0, len(pcm) - hop + 1, hop)]
    if not rms:
        return []
    floor = sorted(rms)[len(rms) // 10]                # quietest 10% = background noise
    thr = max(300.0, floor * 3)
    voiced = [i for i, v in enumerate(rms) if v > thr]
    if not voiced:
        return []
    pad = 10                                           # keep 200 ms around speech
    start, end = max(0, voiced[0] - pad), min(len(rms), voiced[-1] + pad + 1)
    cuts, seg_start = [], start
    max_f, min_f = int(max_s * 50), int(min_s * 50)
    while end - seg_start > max_f:
        lo, hi = seg_start + min_f, seg_start + max_f  # cut at the quietest frame inside the allowed window
        cut = min(range(lo, hi), key=lambda i: rms[i])
        cuts.append((seg_start, cut))
        seg_start = cut
    cuts.append((seg_start, end))
    return [(a * hop, b * hop) for a, b in cuts]


def stt_fast(audio: bytes, filename: str = "audio.wav", content_type: str = "audio/wav", language: str | None = None,
             keyterms: list[str] | None = None, mode: str | None = None) -> dict:
    """Trim + split + parallel STT. mode="translit" uses saaras:v3 (Latin script for English and Hinglish)."""
    decoded = _pcm16_mono(audio)
    if decoded is None:
        return stt(audio, filename, content_type, language, keyterms, mode=mode)
    pcm, rate = decoded
    pieces = speech_chunks(pcm, rate)
    if not pieces:
        return {"transcript": "", "language_code": None, "pieces": 0}
    # MP3 at 32 kbps is ~8x smaller than 16-bit WAV: measured uplink here is 11-24 KB/s, so upload time dominated.
    clips = [_mp3(pcm[a:b], rate) for a, b in pieces]
    outs = list(_tts_pool.map(lambda c: stt(c, "a.mp3", "audio/mpeg", language, keyterms, mode=mode), clips))
    text = " ".join(o["transcript"] for o in outs if o["transcript"]).strip()
    return {"transcript": text, "language_code": outs[0]["language_code"], "pieces": len(clips),
            "speech_s": round(sum(b - a for a, b in pieces) / rate, 1)}


_SENTENCE = re.compile(r"(?<=[.!?।])\s+")
_tts_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="tts")


def split_sentences(text: str, min_chars: int = 12) -> list[str]:
    """Sentence chunks for parallel synthesis; very short sentences are merged into their neighbour."""
    parts, buf = [], ""
    for s in _SENTENCE.split(text.strip()):
        buf = f"{buf} {s}".strip() if buf else s
        if len(buf) >= min_chars:
            parts.append(buf)
            buf = ""
    if buf:
        if parts and len(buf) < min_chars:
            parts[-1] = f"{parts[-1]} {buf}"
        else:
            parts.append(buf)
    return parts or [text]


def tts_parts(text: str, language: str = "hi-IN", speaker: str | None = None) -> list[bytes]:
    """Synthesise each sentence in parallel: latency ~ the longest sentence, not the sum (measured TTS time grows
    with text length). The browser plays the clips back to back."""
    chunks = split_sentences(text)
    if len(chunks) == 1:
        return [tts(chunks[0], language, speaker)]
    return list(_tts_pool.map(lambda c: tts(c, language, speaker), chunks))


_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def has_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text or ""))


def transliterate(text: str, source: str = "hi-IN", target: str = "en-IN", timeout: float = 10) -> str:
    """Devanagari -> Roman (e.g. phone STT writes English speech as "यस, मैं ठीक हूँ" -> "yes, main theek hoon")."""
    r = httpx.post(f"{BASE}/transliterate", headers={**_headers(), "Content-Type": "application/json"},
                   json={"input": text, "source_language_code": source, "target_language_code": target},
                   timeout=timeout)
    return (_check(r).get("transliterated_text") or text).strip()


def chat(system: str, user: str | None = None, max_tokens: int = 800, timeout: float = 8, json_mode: bool = False,
         messages: list[dict] | None = None) -> str:
    convo = messages if messages is not None else [{"role": "user", "content": user or ""}]
    body = {"model": settings.sarvam_llm_model, "max_tokens": max_tokens, "temperature": 0.2,
            "reasoning_effort": None,  # documented way to turn reasoning off (lower latency)
            "messages": ([{"role": "system", "content": system}] if system else [])  # API rejects empty system
                        + convo}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(f"{BASE}/v1/chat/completions",
                   headers={**_headers(), "Authorization": f"Bearer {settings.sarvam_api_key}"},
                   json=body, timeout=timeout)
    out = _check(r)
    return (out["choices"][0]["message"].get("content") or "").strip()
