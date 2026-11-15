import unittest

from ekido_core.checkpoint_files import checkpoint_files


def manifest():
    return {"files": {name: {"sha256": "a" * 64, "bytes": 8} for name in ("trainable.safetensors", "optimizer.safetensors")}}


class CheckpointFiles(unittest.TestCase):
    def test_accepts_the_two_checkpoint_blobs(self):
        body = manifest()
        self.assertEqual(checkpoint_files(body), body["files"])

    def test_missing_or_extra_files_are_refused(self):
        for body in ({}, {"files": []}, {"files": {}}, {"files": {**manifest()["files"], "../escaped.py": {}}}):
            with self.subTest(body=body), self.assertRaises(ValueError):
                checkpoint_files(body)

    def test_invalid_hashes_and_sizes_are_refused(self):
        for field, values in (("sha256", (None, "a" * 63, "a" * 64 + "\n", "A" * 64, "../file")), ("bytes", (None, True, 0, -1, 1.5, 512 * 1024**2 + 1))):
            for value in values:
                body = manifest()
                body["files"]["trainable.safetensors"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    checkpoint_files(body)
