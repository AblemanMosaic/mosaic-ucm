#!/usr/bin/env python3
"""Create a disposable, effect-free native P/PPI dashboard review capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
for candidate in (ROOT / "vendor" / "mosaic-native", ROOT / "src"):
    if str(candidate) not in sys.path:sys.path.insert(0,str(candidate))

from ucm.pippi_dashboard import Dashboard
from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_portfolio import (PortfolioStore, build_project_profile,
                                 build_session_reference)
from mosaic_ui.native_capture import capture_client


R = "1" * 64


def _profile(project, workspace: Path, *, subject: str | None, verified: str | None,
             holds: list[str], gaps: list[str], archive: str, courthouse: str):
    return build_project_profile(
        project=project,
        workspaces=[{"workspace_id":"working","path":str(workspace),"role":"WORKING","status":"ACTIVE"}],
        canonical_store={"kind":"FILESYSTEM","path":str(workspace.parent / (workspace.name + "-canonical")),
                         "active_revision":project["revision"],"revision_root":subject},
        current_subject_root=subject,last_material_activity_ns=1793920000000000000,
        last_verified_ns=1793919000000000000 if verified else None,verified_subject_root=verified,
        proof_level="TARGETED",operational_maturity="CONSTRUCTION",execution_holds=holds,
        release_blockers=[],qualification_gaps=gaps,archive_status=archive,courthouse_status=courthouse)


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    parser.add_argument("--data-root",type=Path,default=Path(".test-tmp/pippi-dashboard-preview"))
    args=parser.parse_args();data_root=args.data_root.resolve()
    if data_root.exists():shutil.rmtree(data_root)
    data_root.parent.mkdir(parents=True,exist_ok=True)
    hub=PippiHub(data_root);hub.initialize(build_onboarding(governor_label="preview-governor",mosaic_id=None,
        dkn_public_key=None,github_account=None,github_credential_reference=None))
    store=PortfolioStore(hub)
    definitions=(
        ("mosaic-ucm","Universal Constitutional Machine","r016",R,R,[],[],"CUSTODY_CONFIRMED","BINDING_PREPARED"),
        ("memory-vault","Mosaic Memory Vault","r021","2"*64,"2"*64,["PUBLICATION_RECEIPT_PENDING"],[],"CUSTODY_CONFIRMED","NO_WORK_PENDING"),
        ("world-engine","Mosaic World Engine","r009","3"*64,None,[],["CURRENT_SUBJECT_ROOT_UNVERIFIED"],"UNVERIFIED","NO_WORK_PENDING"),
    )
    projects=[]
    for project_id,title,revision,subject,verified,holds,gaps,archive,courthouse in definitions:
        workspace=data_root / "preview-workspaces" / project_id;workspace.mkdir(parents=True)
        project=hub.add_project(build_project(project_id=project_id,title=title,workspace=str(workspace),
            github_url=f"https://github.com/AblemanMosaic/{project_id}",application_command=["APP"],
            verification_command=["VERIFY"],readme="README.md",docs=["docs/START.md"],revision=revision))
        store.save_profile(_profile(project,workspace,subject=subject,verified=verified,holds=holds,gaps=gaps,
                                    archive=archive,courthouse=courthouse));projects.append(project)
    session=build_session_reference(session_id="codex:ucm-interface",project_id=None,
        source_path=str(data_root / "preview-workspaces" / "mosaic-ucm"),source_kind="PIPPI_CAMPAIGN",
        context_root="4"*64,subject_root=R,journal_head="5"*64,event_count=37,
        last_activity_ns=1793920100000000000,status="ACTIVE",integration_mode="SIDECAR_PARTIAL",
        mediated_channels=["MODEL_INPUT","MODEL_DRAFT","VISIBLE_OUTPUT","JOURNAL_WRITE"],
        source_manifest_root="6"*64,discovery_status="VERIFIED")
    store.import_session(session,project_id="mosaic-ucm")
    dashboard=Dashboard(hub);observed={}
    def capture() -> None:
        try:
            dashboard.window.relayout();dashboard.window.redraw()
            observed.update(capture_client(dashboard.window,args.output.resolve()))
        finally:dashboard.window.close()
    dashboard.window.set_timer(500,capture)
    code=dashboard.run()
    if code!=0 or not args.output.is_file():raise SystemExit("PIPPI_DASHBOARD_CAPTURE_FAILED")
    result={"status":"PASS","capture":str(args.output.resolve()),"sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),
            "width":observed["width"],"height":observed["height"],"desktop_input":False,
            "standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
    print(json.dumps(result,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
