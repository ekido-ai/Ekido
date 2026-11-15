"""Worker-side transfers: direct links when the coordinator offers them, the coordinator's own routes otherwise."""
import hashlib
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ekido_core.transfer import download_blob, upload_blob


class Server:
    """One process playing both the coordinator and the object store."""

    def __init__(self, direct: bool):
        self.direct = direct
        self.store: dict[str, bytes] = {}
        self.seen: list[tuple[str, str, str | None]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, code, body=b"", kind="application/json"):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                return self.rfile.read(int(self.headers.get("Content-Length", 0)))

            def do_POST(self):
                outer.seen.append(("POST", self.path, self.headers.get("Authorization")))
                digest = self.path.split("/")[2]
                self._body()
                if not outer.direct:
                    self._reply(404, b'{"detail":"off"}')
                elif digest in outer.store:
                    self._reply(200, b'{"exists": true}')
                else:
                    offer = {"url": f"{outer.base}/s3/{digest}", "headers": {"x-amz-checksum-sha256": "c"}}
                    self._reply(200, json.dumps(offer).encode())

            def do_PUT(self):
                outer.seen.append(("PUT", self.path, self.headers.get("Authorization")))
                outer.store[self.path.rsplit("/", 1)[1]] = self._body()
                self._reply(201, b"{}")

            def do_GET(self):
                outer.seen.append(("GET", self.path, self.headers.get("Authorization")))
                digest = self.path.split("/")[2]
                if not self.path.endswith("/download-url"):
                    self._reply(200, outer.store[digest], "application/octet-stream")
                elif not outer.direct:
                    self._reply(404, b'{"detail":"off"}')
                else:
                    self._reply(200, json.dumps({"url": f"{outer.base}/s3/{digest}"}).encode())

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TransferTests(unittest.TestCase):
    def roundtrip(self, direct: bool) -> Server:
        server = Server(direct)
        self.addCleanup(server.close)
        data = b"weights" * 5000
        digest = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "in.bin")
            source.write_bytes(data)
            upload_blob(server.base, "tok", source, digest, timeout=10)
            download_blob(server.base, "tok", digest, Path(tmp, "out.bin"), len(data), timeout=10)
            self.assertEqual(Path(tmp, "out.bin").read_bytes(), data)
        return server

    def test_direct_links_skip_the_coordinator_and_never_carry_its_token(self):
        server = self.roundtrip(direct=True)
        storage = [s for s in server.seen if s[1].startswith("/s3/")]
        self.assertEqual([s[0] for s in storage], ["PUT", "GET"])
        self.assertTrue(all(auth is None for _, _, auth in storage))

    def test_falls_back_to_the_coordinator_routes(self):
        server = self.roundtrip(direct=False)
        self.assertIn(("PUT", f"/artifacts/{hashlib.sha256(b'weights' * 5000).hexdigest()}", "Bearer tok"), server.seen)
        self.assertFalse(any(s[1].startswith("/s3/") for s in server.seen))

    def test_existing_blob_is_not_sent_again(self):
        server = Server(direct=True)
        self.addCleanup(server.close)
        data = b"same"
        digest = hashlib.sha256(data).hexdigest()
        server.store[digest] = data
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "f").write_bytes(data)
            upload_blob(server.base, "tok", Path(tmp, "f"), digest, timeout=10)
        self.assertFalse(any(method == "PUT" for method, _, _ in server.seen))

    def test_a_tampered_download_is_refused(self):
        server = Server(direct=True)
        self.addCleanup(server.close)
        digest = hashlib.sha256(b"real").hexdigest()
        server.store[digest] = b"fake"
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            download_blob(server.base, "tok", digest, Path(tmp, "out"), 4, timeout=10)


if __name__ == "__main__":
    unittest.main()
