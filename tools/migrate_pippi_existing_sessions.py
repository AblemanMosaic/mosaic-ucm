"""Discover and reference exact P/PPI campaigns without rewriting their history."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from uclop.canonical import canonical_bytes
from ucm.pippi_global import PippiHub
from ucm.pippi_portfolio import PortfolioStore, discover_campaigns


def source_envelope(path:Path)->dict[str,str]:
    rows={}
    for name in ("PIPPI-CONTEXT.json","journal/EVENTS.jsonl","journal/HEAD.json"):
        member=path/name
        if member.is_file():rows[name]=hashlib.sha256(member.read_bytes()).hexdigest()
    return rows


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="Reference verified P/PPI campaigns from a sovereign local hub")
    parser.add_argument("--data-root",type=Path,required=True)
    parser.add_argument("--map",action="append",default=[],metavar="PROJECT_ID=SEARCH_ROOT",required=True)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    hub=PippiHub(args.data_root);store=PortfolioStore(hub);imports=[];refusals=[]
    for mapping in args.map:
        if "=" not in mapping:raise SystemExit("PIPPI_MIGRATION_MAP_INVALID")
        project_id,raw=mapping.split("=",1);search=Path(raw).resolve();hub.get_project(project_id)
        discovered=discover_campaigns([search])
        for record in discovered:
            if record.get("discovery_status")!="VERIFIED":refusals.append({"project_id":project_id,**record});continue
            source=Path(record["source_path"]);before=source_envelope(source)
            imported=store.import_session(record,project_id=project_id);after=source_envelope(source)
            if before!=after:raise SystemExit("PIPPI_MIGRATION_SOURCE_CHANGED")
            imports.append({"project_id":project_id,"session_reference_root":imported["session_reference_root"],
                            "source_path":imported["source_path"],"source_envelope":before})
    body={"schema":"mosaic.ucm.pippi-session-migration.v0.1","mode":"REFERENCE_ONLY_NO_REWRITE",
          "imports":imports,"refusals":refusals,"status":"PASS","standing":"INFORMATION_ONLY",
          "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(canonical_bytes(body)+b"\n")
    print(json.dumps(body,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
