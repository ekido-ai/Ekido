"""The invoice audit must work after a Windows CRLF checkout."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RECIPES = Path(__file__).resolve().parents[1] / 'recipes'


class InvoiceCheckoutTest(unittest.TestCase):
    def test_reproducibility_with_crlf_in_quoted_invoice_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'experiments' / 'recipes'
            target = root / 'invoice-fields'
            target.mkdir(parents=True)
            for name in ('generate_invoice_fields.py', 'audit_invoice_fields.py'):
                shutil.copy2(RECIPES / name, root / name)
            for name in ('train.csv', 'test.csv'):
                data = (RECIPES / 'invoice-fields' / name).read_bytes().replace(b'\r\n', b'\n')
                (target / name).write_bytes(data.replace(b'\n', b'\r\n'))
            run = subprocess.run([sys.executable, '-I', str(root / 'audit_invoice_fields.py')],
                                 cwd=tmp, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('"reproduced_from_generator": true', run.stdout)


if __name__ == '__main__':
    unittest.main()
