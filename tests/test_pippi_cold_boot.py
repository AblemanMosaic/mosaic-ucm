from __future__ import annotations

import hashlib, importlib.util, json
from pathlib import Path
import tempfile, unittest, zipfile

from ucm.release_certification import build_embedded_metadata


ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


builder=load("pippi_cold_boot_builder",ROOT/"tools/build_pippi_cold_boot.py")
verifier=load("pippi_cold_boot_verifier",ROOT/"tools/verify_pippi_cold_boot.py")


class PippiColdBootTests(unittest.TestCase):
    def runtime(self,path:Path):
        raw=b"runtime\n";payload={"README.md":raw}
        payload.update(build_embedded_metadata(payload_rows=sorted(payload.items()),
            artifact="UCM_RUNTIME",completeness="COMPLETE_RUNTIME",version="v0.1",
            engineering_revision="r027",source_manifest_root="1"*64,
            release_identity_root="2"*64))
        members=[{"path":name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
                 for name,data in sorted(payload.items())]
        body={"schema":"mosaic.ucm.artifact-manifest.v0.1","artifact":"UCM_RUNTIME",
              "version":"v0.1","engineering_revision":"r027","completeness":"COMPLETE_RUNTIME",
              "members":members,"member_count":len(members),"logical_bytes":sum(row["bytes"] for row in members),
              "standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
        manifest={**body,"root":hashlib.sha256(verifier.canonical(body)).hexdigest()}
        with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for name,data in [("MANIFEST.json",verifier.canonical(manifest)+b"\n"),*sorted(payload.items())]:
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,data)

    def test_deterministic_cold_boot_and_nested_runtime_verification(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);runtime=folder/"runtime.zip";self.runtime(runtime)
            first,second=folder/"a.zip",folder/"b.zip"
            builder.build(runtime,first);builder.build(runtime,second)
            self.assertEqual(first.read_bytes(),second.read_bytes())
            self.assertEqual(verifier.verify(first.read_bytes())["status"],"PASS")
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.read("PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json"),
                    (ROOT/"spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json").read_bytes())
                self.assertEqual(
                    archive.read("PIPPI/PIPPI-CAPABILITY-SURFACE-REGISTRY.json"),
                    (ROOT/"spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json").read_bytes())
                self.assertEqual(
                    archive.read("PIPPI/PIPPI-MEDIATION-LIBRARY.json"),
                    (ROOT/"spec/PIPPI-MEDIATION-LIBRARY.json").read_bytes())
            tampered=bytearray(first.read_bytes());tampered[-5]^=1
            with self.assertRaises((ValueError,zipfile.BadZipFile)):
                verifier.verify(bytes(tampered))


if __name__=="__main__":unittest.main()
