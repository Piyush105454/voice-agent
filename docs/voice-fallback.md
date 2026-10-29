# Voice channels: Bolna first, Sarvam web call as fallback

## How routing works (`api/voice_router.py`)

`POST /voice/call {"student_id": "..."}` (admin key) starts a tutoring call:

1. **Bolna phone call**, used when `BOLNA_API_KEY` + `BOLNA_AGENT_ID` are set, the student has a phone number, and Bolna is not benched.
2. If Bolna replies with a **limit error**, Bolna is benched for `BOLNA_COOLDOWN_MINUTES` (default 60). A limit error is HTTP 402/429, or a 4xx whose message mentions credit, balance, wallet, quota, limit, concurrency and so on. Bolna doesn't document its exact out-of-credit error. If Bolna is unreachable or returns a 5xx, it's benched for 5 minutes.
3. While Bolna is benched, every call goes straight to **Sarvam**. The response holds a signed link `/call?t=...` that expires after `WEB_CALL_LINK_MINUTES`. Send it to the student by WhatsApp or SMS.

`GET /voice/status` shows the active channel and when Bolna will be retried. `POST /voice/reset_bolna` switches back to Bolna immediately after a top-up.

`VOICE_PROVIDER=bolna|sarvam` forces a single channel. A per-call `"provider"` field overrides it.

## The Sarvam web call (`api/webcall.py`, `api/static/call.html`)

- The student taps **Start** once and allows the microphone. After that it's hands-free: the page detects when they stop talking, sends the clip and plays the reply.
- Each turn goes **browser audio → Sarvam STT `saaras:v4` → tutor core → Sarvam TTS `bulbul:v3` → browser**.
- The tutor core is the same one the Bolna tools use (`api/service.py`). Sessions, mastery, misconceptions, live dashboard events, summaries and plans are identical. Sessions are stored with `channel='web'`.
- The call flow is deterministic and mirrors the Bolna prompt: consent greeting → confidence before → 3 questions with the hint ladder → confidence after → close with tomorrow's plan. The safety check runs on every turn.
- If Sarvam fails, including when it's out of credit (402 `insufficient_quota_error`), the page falls back to the browser's own voice for replies and shows a text box for answers. The call never dead-ends.
- Call state is held in memory in the API process. Run **one** uvicorn worker. If the API restarts, the student has to reload the page.
- **Latency, measured on 2026-10-28:** about 1.5 s for STT, about 3 s for TTS (MP3; WAV took about 6.8 s), and about 1.3 s extra when an answer needs the LLM grader. Server time per turn is 3–6 s. TTS audio is cached, so repeated phrases (greetings, questions, hints) cost 0 s and no credits. The free Cloudflare tunnel adds about 3–4 s for moving the audio; a real server removes most of that. The response's `timing` field and the API log show the per-stage split.
- Sarvam STT in `hi-IN` returns Devanagari ("माइनस पाँच।", and "सेवन" for "seven"). `api/answers.py` handles both.

## LLM fallback (`api/llm.py`)

`LLM_PROVIDER` is tried first. If it fails, the other provider is tried, provided its key is set: Anthropic ↔ Sarvam `sarvam-105b-conversations`, with reasoning off for low latency. If both fail, the deterministic templates are used.

## Setup

1. Get a key at https://dashboard.sarvam.ai and set `SARVAM_API_KEY` in `.env`.
2. Set `PUBLIC_BASE_URL` to the public HTTPS API. Links and Bolna webhooks need it.
3. Run `python scripts/bolna_agent_config.py > bolna_agent.json`. It produces the prompt, the 4 tools, the webhook and the voice settings for the Bolna agent.
4. Try the fallback without spending Bolna credit: `POST /voice/call {"student_id": "1111...", "provider": "sarvam"}` → open the `url`.
