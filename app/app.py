import os, socket
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def root():
    return jsonify({
        "ok": True,
        "cloud": os.environ.get("CLOUD", "local"),
        "host": socket.gethostname(),
        "message": "hello from the multicloud app!"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
