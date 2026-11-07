from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal
from ucm.subject import bind_subject, verify_subject_binding


class SubjectBindingTests(unittest.TestCase):
    def test_directory_binding_is_exact_and_self_verifying(self):
        with tempfile.TemporaryDirectory() as directory:
            subject = Path(directory)
            (subject / "app.txt").write_text("one", encoding="utf-8")
            policy = {"schema": "mosaic.ucm.subject-binding-policy.v0.1",
                      "subject_id": "APP.ONE", "mode": "IMMUTABLE_SNAPSHOT",
                      "include": ["**/*"], "exclude": [], "allow_symlinks": False,
                      "git_observation": "NONE"}
            first = verify_subject_binding(bind_subject(subject, policy))
            (subject / "app.txt").write_text("two", encoding="utf-8")
            second = verify_subject_binding(bind_subject(subject, policy))
            self.assertNotEqual(first["source_root"], second["source_root"])

    def test_tampered_manifest_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            subject = Path(directory)
            (subject / "app.txt").write_text("one", encoding="utf-8")
            value = bind_subject(subject, {"schema": "mosaic.ucm.subject-binding-policy.v0.1",
                "subject_id": "APP.ONE", "mode": "IMMUTABLE_SNAPSHOT",
                "include": ["**/*"], "exclude": [], "allow_symlinks": False,
                "git_observation": "NONE"})
            value["manifest"]["files"][0]["bytes"] += 1
            with self.assertRaises(Refusal):
                verify_subject_binding(value)


if __name__ == "__main__":
    unittest.main()
