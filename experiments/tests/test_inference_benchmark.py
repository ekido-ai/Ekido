"""Exercise the local-engine measurement without recording prompt contents."""
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'inference' / 'benchmark_local.py'
spec = importlib.util.spec_from_file_location('benchmark_local', SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert self.path == '/v1/chat/completions'
        response = json.dumps({'choices': [{'message': {'content': 'ok'}}],
                               'usage': {'prompt_tokens': 2, 'completion_tokens': 1}}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_):
        pass


class LocalBenchmark(unittest.TestCase):
    def test_only_loopback_origins_are_accepted(self):
        for value in ('https://localhost', 'http://example.org', 'http://127.0.0.1/x',
                      'http://user:pass@localhost', 'http://localhost?token=secret'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                benchmark.endpoint(value)

    def test_records_latency_without_prompts_or_responses(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / 'test.csv'
            dataset.write_text('text,label\nsecret-synthetic-input,other\nsecond,order\n', encoding='utf-8')
            result = benchmark.run(f'http://127.0.0.1:{server.server_port}', 'fake', dataset, 2, 8, 3)
        self.assertEqual(result['successful'], 2)
        self.assertEqual(result['p95_ms'], max(row['latency_ms'] for row in result['records']))
        self.assertNotIn('secret-synthetic-input', json.dumps(result))
        self.assertNotIn('"content"', json.dumps(result))

    def test_stops_on_first_connection_failure(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        port = server.server_port
        server.server_close()
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / 'test.csv'
            dataset.write_text('text\none\ntwo\n', encoding='utf-8')
            result = benchmark.run(f'http://127.0.0.1:{port}', 'fake', dataset, 2, 8, 2)
        self.assertEqual(result['attempted'], 1)
        self.assertEqual(result['successful'], 0)
        self.assertIsNone(result['p95_ms'])

    def test_does_not_follow_engine_redirects(self):
        class Redirect(Handler):
            calls = 0

            def do_POST(self):
                type(self).calls += 1
                self.send_response(307)
                self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/elsewhere')
                self.end_headers()

        server = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / 'test.csv'
            dataset.write_text('text\none\n', encoding='utf-8')
            result = benchmark.run(f'http://127.0.0.1:{server.server_port}', 'fake', dataset, 1, 8, 3)
        self.assertEqual(result['successful'], 0)
        self.assertEqual(Redirect.calls, 1)


if __name__ == '__main__':
    unittest.main()
