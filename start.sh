#!/bin/bash
# API on a private port; the dashboard owns the public $PORT (Render sets it; 10000 by default).
# One API worker: in-process state (Bolna cooldown, browser-call sessions) lives in memory.
cd /app/api
uvicorn main:app --host 127.0.0.1 --port 8765 --workers 1 --proxy-headers --forwarded-allow-ips '*' &
cd /app/web
HOSTNAME=0.0.0.0 PORT="${PORT:-10000}" node server.js &
# if either process dies, stop the container so the platform restarts it
wait -n
exit $?
