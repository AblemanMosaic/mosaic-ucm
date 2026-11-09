"""Create review-only sample data for native P/PPI UI capture."""
from __future__ import annotations

import argparse
from pathlib import Path

from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_portfolio import PortfolioStore, build_preferences
from ucm.pippi_reviews import (ReviewStore, SPEC_SCHEMA, build_review_envelope,
                               build_review_return_archive)


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--data-root",type=Path,required=True)
    args=parser.parse_args();root=args.data_root.resolve()
    if root.exists():raise SystemExit("fixture root already exists")
    source=root.parent/(root.name+"-source");source.mkdir(parents=True,exist_ok=True)
    (source/"candidate.txt").write_text("P/PPI r003 review candidate\n",encoding="utf-8",newline="\n")
    (source/"runner.py").write_text(
        "import argparse,json,pathlib\n"
        "p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()\n"
        "o=pathlib.Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)\n"
        "(o/'REPORT.json').write_text(json.dumps({'status':'PASS'},sort_keys=True,separators=(',',':'))+'\\n',encoding='utf-8')\n",
        encoding="utf-8",newline="\n")
    hub=PippiHub(root);hub.initialize(build_onboarding(governor_label="Local-Governor",mosaic_id=None,
        dkn_public_key=None,github_account="AblemanMosaic",github_credential_reference=None))
    project=hub.add_project(build_project(project_id="pippi",title="P/PPI",workspace=str(source),
        github_url="https://github.com/AblemanMosaic/mosaic-ucm",application_command=None,
        verification_command=None,readme="README.md",revision="r003"))
    spec={"schema":SPEC_SCHEMA,"review_id":"pippi-r003-independent-review",
        "review_class":"INDEPENDENT_RELEASE_REVIEW","subject_role":"PIPPI_RELEASE_CANDIDATE",
        "declared_subject_root":None,
        "members":[{"source":"runner.py","path":"runner/RUN-REVIEW.py","role":"REVIEW_RUNNER"},
                   {"source":"candidate.txt","path":"subject/PIPPI-r003.txt","role":"SUBJECT"}],
        "runner":{"command":["{PYTHON}","runner/RUN-REVIEW.py","--output-dir","{OUTPUT_DIR}"],
                  "required_paths":["runner/RUN-REVIEW.py","subject/PIPPI-r003.txt"],
                  "expected_outputs":["REPORT.json"],"timeout_seconds":60},
        "limitations":["TIER1_REQUIRES_INDEPENDENT_OPERATOR"],"independent_review_required":True}
    envelope=source/"PIPPI-r003-REVIEW.zip"
    built=build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=envelope)
    store=ReviewStore(hub);store.register(project_id="pippi",envelope_path=envelope)
    store.prepare_courthouse(project_id="pippi",review_id=spec["review_id"],destination_jurisdiction="aok:courthouse")
    evidence=source/"review-return";evidence.mkdir();(evidence/"REPORT.md").write_text(
        "# Review\n\nQualified recommendation; independent Tier 1 remains.\n",encoding="utf-8",newline="\n")
    returned=source/"PIPPI-r003-REVIEW-RETURN.zip"
    build_review_return_archive(review_id=spec["review_id"],envelope_sha256=built["archive_sha256"],
        reviewer_identity_root="a"*64,reported_outcome="QUALIFIED_RECOMMENDATION_ONLY",findings=[],
        limitations=["INDEPENDENT_TIER1_NOT_PERFORMED"],
        evidence_members=[{"source":"REPORT.md","path":"evidence/REPORT.md"}],source_dir=evidence,output_path=returned)
    store.import_return(project_id="pippi",review_id=spec["review_id"],return_path=returned)
    PortfolioStore(hub).save_preferences(build_preferences(default_tab="REVIEWS"))
    print(root)
    return 0


if __name__=="__main__":raise SystemExit(main())
