#!/usr/bin/env bash
# relay for the helper when it runs on a rented pod: ams1's 0.0.0.0:$PORT is forwarded over ssh to the pod's
# 127.0.0.1:$PORT, so callers keep the ams1 address and the pod needs no public port. reconnects if the link drops.
set -uo pipefail

PORT=${PORT:-8300}
POD_HOST=${POD_HOST:?pod ip}
POD_SSH_PORT=${POD_SSH_PORT:?pod ssh port}
KEY=${KEY:-$HOME/.ssh/id_ed25519}

while true; do
  echo "relay up $(date -u +%FT%TZ)"
  ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
    -i "$KEY" -p "$POD_SSH_PORT" -L "0.0.0.0:$PORT:127.0.0.1:$PORT" "root@$POD_HOST"
  echo "relay down $(date -u +%FT%TZ), retrying in 10 s"
  sleep 10
done
