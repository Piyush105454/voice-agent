from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


# 1) proxy: a stale kept-alive socket makes the first fetch fail instantly; GETs are safe to retry once
edit("web/app/api/gl/[...path]/route.ts", [
    ('''  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    return Response.json({ error: "API unreachable. Is the backend running on " + API + "?" }, { status: 502 });
  }''', '''  let upstream: Response | undefined;
  for (let attempt = 0; attempt < 2 && !upstream; attempt++) {
    try {
      upstream = await fetch(url, init);
    } catch {
      if (!["GET", "HEAD"].includes(req.method)) break;   // never replay a POST/DELETE
    }
  }
  if (!upstream) {
    return Response.json({ error: "API unreachable. Is the backend running on " + API + "?" }, { status: 502 });
  }'''),
])

# 2) API process: keep idle connections longer than the proxy's pool does
edit("start.sh", [
    ("--workers 1 --proxy-headers --forwarded-allow-ips '*' &", "--workers 1 --timeout-keep-alive 75 --proxy-headers --forwarded-allow-ips '*' &"),
])
edit("api/Dockerfile", [
    ("--workers 1 --proxy-headers", "--workers 1 --timeout-keep-alive 75 --proxy-headers"),
])

# 3) page: if the student's overview did not load, try again instead of keeping placeholder data
edit("web/app/live/page.tsx", [
    ('''  const load = useCallback(async (sid: string, sessionId?: string) => {''',
     '''  const load = useCallback(async (sid: string, sessionId?: string, attempt = 0) => {'''),
    ('''      setProgress(p);
    } catch {''', '''      setProgress(p);
      if (!o && attempt < 3) {   // overview failed (network blip): retry rather than showing placeholder data forever
        setTimeout(() => { if (sid === wantedRef.current) load(sid, sessionId, attempt + 1); }, 2500 * (attempt + 1));
      }
    } catch {'''),
])
print("ok")
