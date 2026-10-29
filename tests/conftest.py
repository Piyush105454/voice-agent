import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

# Tests never call paid APIs, including from background threads that outlive a test's monkeypatch.
# (Unit tests that exercise a client set a fake key explicitly and stub the HTTP call.)
from config import settings  # noqa: E402

settings.anthropic_api_key = ""
settings.sarvam_api_key = ""
settings.bolna_api_key = ""
