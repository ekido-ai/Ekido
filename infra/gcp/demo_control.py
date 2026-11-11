"""EXPERIMENTAL, NOT DEPLOYED: bounded controls for a synthetic local-chain demo.

Piyush wants Base Sepolia, so this is not the requested testnet solution. Do not
expose this service without reviewing abuse protection and the trust boundary.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ORIGIN = "https://gpuchain.duckdns.org"
API = "http://127.0.0.1:8000"
HELPER = "http://127.0.0.1:8001"
RPC = "http://127.0.0.1:8545"
COOLDOWN = 90
lock = threading.Lock()
last_start = 0.0
owned_job = None
starting = False
kill_used = False


def request(url, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    with urlopen(req, timeout=6) as response:
        raw = response.read(1_000_000)
        return json.loads(raw) if raw else {}


def local_demo_ready():
    info_file = Path("/opt/GPUchain/experiments/demo_stack_info.json")
    stack = json.loads(info_file.read_text(encoding="utf-8"))
    if stack.get("testnet") is not False or stack.get("mode") != "SYNTHETIC CPU" or stack.get("api") != API or stack.get("chain", {}).get("chain_id") != 31337 or stack.get("chain", {}).get("rpc") != RPC:
        return False
    info = request(API + "/healthz")
    rpc = request(RPC, {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, {"Content-Type": "application/json"})
    return info.get("demo_mode") is True and rpc.get("result") == "0x7a69"


def newest():
    jobs = request(API + "/jobs?limit=1")
    return jobs[0] if jobs else None


def track_job(previous):
    global starting, owned_job
    try:
        for _ in range(30):
            time.sleep(1)
            job = newest()
            if job and job.get("job_id") != previous:
                with lock:
                    owned_job = job["job_id"]
                return
    finally:
        with lock:
            starting = False


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        global last_start, starting, owned_job, kill_used
        if self.headers.get("Origin") != ORIGIN or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.reply(403, {"error": "Request origin is not allowed."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 512 or length < 0:
                return self.reply(413, {"error": "Request is too large."})
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("invalid body")
            with lock:
                if not local_demo_ready():
                    return self.reply(503, {"error": "The local synthetic demo is unavailable."})
                if self.path == "/start-job":
                    if body:
                        return self.reply(400, {"error": "Unexpected request data."})
                    job = newest()
                    if starting or (job and job.get("state") not in ("SETTLED", "COMPLETED", "DISPUTED", "CANCELLED", "FAILED", "ABORTED")):
                        return self.reply(409, {"error": "A demo job is already running or starting."})
                    if time.monotonic() - last_start < COOLDOWN:
                        return self.reply(429, {"error": "Please wait before starting another demo."})
                    previous = job.get("job_id") if job else None
                    request(HELPER + "/start-job", {}, {"Origin": "http://localhost:3100", "Content-Type": "application/json"})
                    last_start = time.monotonic()
                    starting, owned_job, kill_used = True, None, False
                    threading.Thread(target=track_job, args=(previous,), daemon=True).start()
                    return self.reply(202, {"status": "starting"})
                if self.path == "/kill":
                    job = newest()
                    if set(body) != {"job_id"} or not owned_job or body["job_id"] != owned_job or not job or job.get("job_id") != owned_job or job.get("state") != "RUNNING" or kill_used:
                        return self.reply(409, {"error": "This demo cannot be stopped now."})
                    kill_used = True
                    result = request(API + "/demo/faults", {"job_id": owned_job, "kind": "KILL_CONTAINER"}, {"Content-Type": "application/json"})
                    return self.reply(200 if result.get("delivered") else 409, {"delivered": bool(result.get("delivered")), "error": None if result.get("delivered") else "The provider was no longer running."})
                return self.reply(404, {"error": "Not found."})
        except (ValueError, TypeError, OSError, HTTPError):
            return self.reply(503, {"error": "The demo is unavailable. Please try again later."})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8002), Handler).serve_forever()
