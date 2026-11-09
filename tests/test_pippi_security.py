from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from ucm.pippi_security import protect_private_file, verify_private_file
from ucm.pippi_service import _key


class PippiSecurityTests(unittest.TestCase):
    def test_private_file_protection_is_verified_on_this_platform(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/"private.bin";path.write_bytes(b"private")
            protected=protect_private_file(path)
            verified=verify_private_file(path)
            self.assertEqual(protected["status"],"PASS")
            self.assertEqual(verified["status"],"PASS")
            self.assertEqual(protected["security_model"],verified["security_model"])
            if os.name=="nt":
                self.assertEqual(verified["security_model"],"WINDOWS_PROTECTED_USER_DACL")
                self.assertEqual(verified["principal_binding"],"CURRENT_USER_SID")
                self.assertEqual(verified["access_rule_count"],1)
                self.assertFalse(verified["inherited"])
            else:
                self.assertEqual(verified["mode"],"0600")

    def test_ipc_key_private_permissions(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            created=_key(root,True);reread=_key(root)
            self.assertEqual(len(created),32);self.assertEqual(created,reread)
            self.assertEqual(verify_private_file(root/"IPC.key")["status"],"PASS")


if __name__=="__main__":unittest.main()
