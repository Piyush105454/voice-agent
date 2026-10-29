"""Expose the local API (http://localhost:8000) through a free Cloudflare quick tunnel, then point Bolna at it.
    python scripts/dev_tunnel.py
1. starts `cloudflared tunnel --url http://localhost:8000` (.tools/cloudflared/cloudflared.exe or PATH)
2. writes the https://*.trycloudflare.com URL to PUBLIC_BASE_URL in .env
3. runs scripts/bolna_sync_agent.py (creates the agent the first time, updates its URLs afterwards)
Keep this running while testing calls; Ctrl+C stops the tunnel. Restart the API after the URL changes so
Sarvam web-call links use the new URL."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".tools" / "cloudflared" / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
URL_RX = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def set_env(key: str, value: str) -> None:
    env = ROOT / ".env"
    s = env.read_text(encoding="utf-8")
    s = re.sub(rf"(?m)^{key}=.*$", f"{key}={value}", s) if re.search(rf"(?m)^{key}=", s) else s + f"\n{key}={value}\n"
    env.write_text(s, encoding="utf-8")


def main() -> None:
    exe = str(LOCAL) if LOCAL.exists() else shutil.which("cloudflared")
    if not exe:
        sys.exit("cloudflared not found: download it to .tools/cloudflared/")
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", "http://localhost:8000"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    url = None
    try:
        for line in proc.stdout:
            if url is None and (m := URL_RX.search(line)):
                url = m.group(0)
                set_env("PUBLIC_BASE_URL", url)
                print(f"\nTunnel: {url}  (saved to .env as PUBLIC_BASE_URL)", flush=True)
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / "bolna_sync_agent.py")], cwd=ROOT)
                print("Bolna agent synced." if r.returncode == 0 else "Bolna sync FAILED (see above).", flush=True)
                print("Tunnel running. Ctrl+C to stop.\n", flush=True)
            elif "ERR" in line:
                print(line.rstrip(), flush=True)
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
