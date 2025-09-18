#!/bin/bash
set -euxo pipefail
exec > >(tee -a /var/log/startup-script.log | logger -t startup-script -s 2>/dev/console) 2>&1

apt-get update -y
apt-get install -y docker.io
systemctl enable --now docker
docker --version

# app on the VM
mkdir -p /opt/hello
cat >/opt/hello/app.py <<'PY'
from flask import Flask, jsonify
import socket, os
app = Flask(__name__)

@app.get("/")
def r():
    return jsonify({
        "ok": True,
        "message": "hello from GCP (docker)",
        "hostname": socket.gethostname(),
        "cloud": os.getenv("CLOUD", "gcp")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
PY

#  Python container and mount the app
docker run -d --restart unless-stopped --name hello-api \
  -p 8080:8080 -e CLOUD=gcp \
  -v /opt/hello:/app -w /app \
  python:3.11-slim bash -lc "pip install flask && python app.py"

# logging
docker ps -a || true
ss -ltnp || true
