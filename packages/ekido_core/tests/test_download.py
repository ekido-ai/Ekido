import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from ekido_core.download import save_checkpoint_blob


class Download(unittest.TestCase):
    def test_only_exact_matching_content_replaces_the_target(self):
        expected = b"checkpoint-data"
        digest = hashlib.sha256(expected).hexdigest()
        for body, claimed, advertised, success in (
            (expected, digest, len(expected), True),
            (expected[:-1], digest, len(expected), False),
            (expected + b"x", digest, len(expected), False),
            (expected, "0" * 64, len(expected), False),
            (expected, digest, 0, False),
        ):
            with self.subTest(body=body, advertised=advertised, success=success), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "checkpoint"
                target.write_bytes(b"old")
                if success:
                    save_checkpoint_blob(io.BytesIO(body), target, claimed, advertised)
                    self.assertEqual(target.read_bytes(), expected)
                else:
                    with self.assertRaises(ValueError):
                        save_checkpoint_blob(io.BytesIO(body), target, claimed, advertised)
                    self.assertEqual(target.read_bytes(), b"old")
                self.assertEqual([p.name for p in Path(tmp).iterdir()], ["checkpoint"])
