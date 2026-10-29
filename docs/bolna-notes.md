# Bolna — verified facts (read from official docs on 2026-10-28)

Docs moved: `docs.bolna.ai` → `https://www.bolna.ai/docs/...` (full dump: `https://www.bolna.ai/docs/llms-full.txt`).

## Custom function tools (`tool-calling/custom-function-schema`, `custom-function-examples`)
- Required: `name`, `description`, `key: "custom_task"`, `value.method`.
- `value`: `method`, `url`, `param` (Python-style placeholders `%(name)s` / `%(name)i` / `%(name)f`),
  optional `api_token` (sent as `Authorization` value, include `Bearer `), optional `headers` (any extra headers → we send `X-Webhook-Secret`).
- POST → JSON body (example sets `Content-Type: application/json` in headers). GET → query string.
- `properties` names must equal `param` names (case-sensitive).
- Endpoint response is handed to the LLM. `pre_call_message` is spoken while waiting.
- In the agent API: `tools_config.api_tools.tools[]` = `{key,name,description,parameters,pre_call_message}`;
  `tools_config.api_tools.tools_params.<name>` = `{url, method, param, headers}`.

## Variables (`prompting/using-context`, `tool-calling/custom-function-variables`)
- Every key in `user_data` (outbound call) is available as `{student_id}` in prompt/welcome message.
- System vars: `agent_id, execution_id, call_sid, from_number, to_number, current_date, current_time, timezone`.
- Variables referenced in the prompt are auto-substituted into tool params (LLM won't ask the caller). So the
  prompt must contain `student_id: {student_id}` and `call_id: {execution_id}`.

## Outbound call (`api-reference/calls/make`)
`POST https://api.bolna.ai/call`, `Authorization: Bearer <API_KEY>`
Body: `agent_id`, `recipient_phone_number` (E.164) required; optional `from_phone_number`, `scheduled_at`
(ISO 8601 with numeric offset, no `Z`), `user_data`, `retry_config`.
Response: `{"message":"done","status":"queued","execution_id":"..."}`.

## Post-call webhook (`post-call/polling-call-status-webhooks`, `execution-payload`)
- `agent_config.webhook_url`; custom headers can be added in the dashboard ("Add headers" JSON toggle).
- POST on every status change (same `id` repeated) → handler must be idempotent. Final data at `status == "completed"`.
- Payload = `GET https://api.bolna.ai/executions/{id}`: `id, agent_id, status, transcript ("assistant:"/"user:" lines),
  conversation_duration, telephony_data{...}, context_details{recipient_phone_number, recipient_data}, ...`.
- Return 200 fast; retried on non-2xx/timeout.

## Security (`concepts/security`)
- No HMAC signature on tool calls or webhooks. Bolna egress IPs: `13.203.39.153`, `13.126.9.249`, `13.202.133.53`.
- Our layers: `X-Webhook-Secret` custom header + optional IP allowlist (`BOLNA_IP_ALLOWLIST=true`).

## Inbound (`api-reference/inbound/agent`, `customizations/identify-incoming-callers`)
- `POST /inbound/setup {agent_id, phone_number_id}`.
- Caller identification: Bolna GETs your URL `?contact_number=+91...&agent_id=...&execution_id=...` (Bearer token);
  top-level keys of the JSON response become prompt variables. **Must answer within 3 s.** Option to only accept known numbers.

## Voices / STT
- Sarvam TTS: `bulbul:v4-flash` (recommended, voice ids like `<persona>_hi_<usecase>`) or `bulbul:v3`
  (voices: shubh, ratan, ashutosh, amit, rahul, sumit, manan, priya, ritu, kavya, simran, pooja, ishita, shreya, shruti, suhani).
  `provider_config` needs both `voice` and `voice_id`.
- Sarvam STT: `{"provider":"sarvam","model":"saaras:v4","language":"hi","stream":true,"endpointing":500}` (`"hi"`, not `"hi-IN"`).
- Deepgram Hindi: `nova-2`, `"language":"hi"`.

## Not documented
- Tool-call webhook timeout and retry behaviour → keep tool responses < ~1.5 s, set `pre_call_message`.
