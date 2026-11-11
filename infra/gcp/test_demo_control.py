import http.client
import json
import threading
import unittest
from unittest.mock import patch

import demo_control as control


class DemoControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        control.ThreadingHTTPServer.allow_reuse_address = True
        cls.server = control.ThreadingHTTPServer(("127.0.0.1", 0), control.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        control.last_start, control.starting, control.owned_job, control.kill_used = 0, False, None, False

    def post(self, path, data, origin=control.ORIGIN):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        conn.request("POST", path, json.dumps(data), {"Content-Type": "application/json", "Origin": origin})
        response = conn.getresponse()
        result = (response.status, json.loads(response.read()))
        conn.close()
        return result

    def test_rejects_untrusted_origin_without_reaching_backend(self):
        with patch.object(control, "local_demo_ready") as ready:
            self.assertEqual(self.post("/start-job", {}, "https://attacker.example")[0], 403)
            ready.assert_not_called()

    def test_start_is_single_and_rate_limited(self):
        with patch.object(control, "local_demo_ready", return_value=True), patch.object(control, "newest", return_value=None), patch.object(control, "request", return_value={}), patch.object(control, "track_job"):
            self.assertEqual(self.post("/start-job", {})[0], 202)
            self.assertEqual(self.post("/start-job", {})[0], 409)
            control.starting = False
            self.assertEqual(self.post("/start-job", {})[0], 429)

    def test_kill_only_own_current_job_once(self):
        control.owned_job = "our-job"
        with patch.object(control, "local_demo_ready", return_value=True), patch.object(control, "newest", return_value={"job_id": "our-job", "state": "RUNNING"}), patch.object(control, "request", return_value={"delivered": True}) as request:
            self.assertEqual(self.post("/kill", {"job_id": "other-job"})[0], 409)
            request.assert_not_called()
            self.assertEqual(self.post("/kill", {"job_id": "our-job"})[0], 200)
            self.assertEqual(self.post("/kill", {"job_id": "our-job"})[0], 409)
            self.assertEqual(request.call_count, 1)

    def test_fails_closed_if_demo_is_not_local(self):
        with patch.object(control, "local_demo_ready", return_value=False), patch.object(control, "request") as request:
            self.assertEqual(self.post("/start-job", {})[0], 503)
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
