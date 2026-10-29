from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ".env"), extra="ignore")

    # LLM: primary provider, then the other one if its key is set, then deterministic fallback.
    llm_provider: str = "anthropic"          # anthropic | sarvam | none
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    anthropic_chat_model: str = ""           # live conversation turns; empty = anthropic_model
    anthropic_chat_effort: str = "low"       # low = fastest replies (Opus 5.5 thinking can't be disabled)
    anthropic_eval_effort: str = "medium"    # end-of-session evaluation, learning plans
    llm_timeout_s: float = 6.0
    llm_hints: bool = False                  # LLM-rewritten hints (adds latency on live calls)

    database_url: str = "postgresql://guru:guru@localhost:54322/guruline"
    supabase_url: str = ""
    supabase_service_key: str = ""

    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    graph_name: str = "guruline"

    bolna_api_key: str = ""
    bolna_agent_id: str = ""
    bolna_agent_id_en: str = ""      # same agent, English speech recognition
    # the phone conversation's brain inside Bolna: "openai" (Bolna's own gpt-5.4-mini) or "custom" (a model you
    # registered in Bolna > Providers, e.g. Qwen on Groq; Bolna keeps that key, it never touches this server)
    bolna_llm: str = "openai"
    bolna_llm_model: str = "gpt-5.4-mini"
    bolna_llm_base_url: str = ""
    bolna_llm_family: str = ""
    bolna_from_number: str = ""
    bolna_ip_allowlist: bool = False
    webhook_secret: str = "change-me"
    public_base_url: str = ""

    # Sarvam AI: fallback voice channel (browser call) + optional LLM.
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v4"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "priya"
    sarvam_tts_pace: float = 1.0
    sarvam_llm_model: str = "sarvam-105b-conversations"

    # Voice routing: auto = Bolna first, Sarvam web call when Bolna is out of credit / rate-limited / down.
    voice_provider: str = "auto"             # auto | bolna | sarvam
    bolna_cooldown_minutes: int = 60         # how long to skip Bolna after a limit error
    web_call_link_minutes: int = 60          # validity of a Sarvam web-call link

    admin_key: str = "change-me-admin"
    demo_mode: bool = True
    demo_student_phone: str = ""
    timezone: str = "Asia/Kolkata"
    enable_scheduler: bool = False


settings = Settings()
