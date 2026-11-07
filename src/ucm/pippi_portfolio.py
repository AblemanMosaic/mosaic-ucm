"""P/PPI portfolio projections, session migration, timelines, and user layout.

All imported sessions remain authoritative at their source paths.  The central
hub stores verified references and roots; it does not rewrite their journals.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from uclop.canonical import canonical_bytes, root, strict_loads

from .pippi_global import BOUNDARY, HubRefusal, PippiHub, validate_project
from .pippi import validate_pippi_context
from .pippi_runtime import validate_pippi_campaign_workspace


PROFILE_SCHEMA="mosaic.ucm.pippi-project-profile.v0.1"
SESSION_SCHEMA="mosaic.ucm.pippi-session-reference.v0.1"
PREFERENCES_SCHEMA="mosaic.ucm.pippi-dashboard-preferences.v0.1"
TIMELINE_SCHEMA="mosaic.ucm.pippi-project-timeline.v0.1"
PROJECT_BRIEF_SCHEMA="mosaic.ucm.pippi-project-brief.v0.1"
ADHERENCE={"PASS","ADVISORY","HELD","STALE","UNVERIFIED"}
SESSION_STATES={"ACTIVE","WAITING","NEEDS_ATTENTION","COMPLETED","IMPORTED","REFUSED"}
ARCHIVE_EVENTS={"ARCHIVE_PREPARED","ARCHIVE_SUBMITTED","ARCHIVE_CUSTODY_CONFIRMED",
 "ARCHIVE_RECONSTRUCTION_VERIFIED","ARCHIVE_SUPERSEDED","ARCHIVE_RESTORED","ARCHIVE_CUSTODY_FAILED"}
COURTHOUSE_EVENTS={"COURTHOUSE_WORK_ORDER_DRAFTED","COURTHOUSE_PREFLIGHT_PASSED","COURTHOUSE_SUBMITTED",
 "COURTHOUSE_CUSTODY_ACCEPTED","COURTHOUSE_ROUTED","COURTHOUSE_REVIEW_UNDERWAY",
 "COURTHOUSE_CLARIFICATION_REQUESTED","COURTHOUSE_RESULT_RETURNED","COURTHOUSE_RESULT_IMPORTED",
 "COURTHOUSE_DISPOSITION_RECORDED","COURTHOUSE_CLOSED","COURTHOUSE_HELD","COURTHOUSE_SUPERSEDED"}
REVIEW_EVENTS={"REVIEW_ENVELOPE_REGISTERED","REVIEW_LOCAL_RUN_COMPLETED"}


def _atomic(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);pending=path.with_name(path.name+".pending")
 with pending.open("wb") as stream:stream.write(canonical_bytes(value)+b"\n");stream.flush();os.fsync(stream.fileno())
 os.replace(pending,path)


def _path_record(raw:dict[str,Any],code:str)->dict[str,Any]:
 if set(raw)!={"workspace_id","path","role","status"}:raise HubRefusal(code)
 path=str(Path(raw["path"]).resolve())
 if raw["role"] not in {"WORKING","BUILD","REVIEW","RUNTIME"} or raw["status"] not in {"ACTIVE","INACTIVE","MISSING"}:
  raise HubRefusal(code)
 return {"workspace_id":raw["workspace_id"],"path":path,"role":raw["role"],"status":raw["status"]}


def build_project_profile(*,project:dict[str,Any],workspaces:list[dict[str,Any]],canonical_store:dict[str,Any],
 current_subject_root:str|None,last_material_activity_ns:int|None,last_verified_ns:int|None,
 verified_subject_root:str|None,proof_level:str,operational_maturity:str,
 execution_holds:list[str],release_blockers:list[str],qualification_gaps:list[str],
 archive_status:str,courthouse_status:str)->dict[str,Any]:
 project=validate_project(project)
 paths=[_path_record(row,"PIPPI_WORKSPACE_RECORD_INVALID") for row in workspaces]
 if paths!=sorted(paths,key=lambda row:row["workspace_id"]) or len({row["workspace_id"] for row in paths})!=len(paths):
  raise HubRefusal("PIPPI_WORKSPACES_INVALID")
 if set(canonical_store)!={"kind","path","active_revision","revision_root"} or canonical_store["kind"] not in {
  "FILESYSTEM","MEMORY_VAULT","GIT","UNBOUND"}:raise HubRefusal("PIPPI_CANONICAL_STORE_INVALID")
 canonical=deepcopy(canonical_store)
 if canonical["path"] is not None:canonical["path"]=str(Path(canonical["path"]).resolve())
 if canonical["path"] is not None and canonical["path"] in {row["path"] for row in paths}:
  raise HubRefusal("PIPPI_CANONICAL_STORE_COLLIDES_WITH_WORKSPACE")
 for value in (current_subject_root,verified_subject_root,canonical["revision_root"]):
  if value is not None and (not isinstance(value,str) or len(value)!=64):raise HubRefusal("PIPPI_SUBJECT_ROOT_INVALID")
 for values,code in ((execution_holds,"PIPPI_EXECUTION_HOLDS_INVALID"),(release_blockers,"PIPPI_RELEASE_BLOCKERS_INVALID"),
                     (qualification_gaps,"PIPPI_QUALIFICATION_GAPS_INVALID")):
  if values!=sorted(set(values)):raise HubRefusal(code)
 adherence="HELD" if execution_holds else "UNVERIFIED" if last_verified_ns is None else \
  "STALE" if current_subject_root!=verified_subject_root else "ADVISORY" if qualification_gaps else "PASS"
 body={"schema":PROFILE_SCHEMA,"project_id":project["project_id"],"base_project_root":project["project_root"],
  "workspaces":paths,"canonical_store":canonical,"current_subject_root":current_subject_root,
  "last_material_activity_ns":last_material_activity_ns,"last_verified_ns":last_verified_ns,
  "verified_subject_root":verified_subject_root,"adherence_status":adherence,"proof_level":proof_level,
  "operational_maturity":operational_maturity,"execution_holds":execution_holds,
  "release_blockers":release_blockers,"qualification_gaps":qualification_gaps,
  "archive_status":archive_status,"courthouse_status":courthouse_status,**BOUNDARY}
 return {**body,"profile_root":root(body)}


def validate_project_profile(value:Any)->dict[str,Any]:
 if not isinstance(value,dict) or value.get("schema")!=PROFILE_SCHEMA:raise HubRefusal("PIPPI_PROJECT_PROFILE_INVALID")
 body={k:deepcopy(v) for k,v in value.items() if k!="profile_root"}
 if value.get("profile_root")!=root(body) or value.get("adherence_status") not in ADHERENCE:raise HubRefusal("PIPPI_PROJECT_PROFILE_INVALID")
 return deepcopy(value)


def build_project_brief(*,project:dict[str,Any],profile:dict[str,Any],
                        sessions:list[dict[str,Any]],reviews:list[dict[str,Any]],
                        gateway_status:str)->dict[str,Any]:
 """Project the most important current fact and one safe next navigation step.

 The brief is a read-only, rooted projection.  Its recommendation selects a
 dashboard context; it never dispatches an application or creates authority.
 """
 project=validate_project(project);profile=validate_project_profile(profile)
 if profile["project_id"]!=project["project_id"]:raise HubRefusal("PIPPI_BRIEF_PROJECT_MISMATCH")
 if gateway_status not in {"BUILT_IN","BOUND_EXTERNAL","DECLARED_UNBOUND","UNAVAILABLE"}:
  raise HubRefusal("PIPPI_BRIEF_GATEWAY_STATUS_INVALID")
 project_sessions=[row for row in sessions if row.get("project_id")==project["project_id"]]
 project_reviews=[row for row in reviews if row.get("project_id")==project["project_id"]]
 attention_sessions=[row for row in project_sessions if row.get("status") in {"NEEDS_ATTENTION","REFUSED"}]
 returned_reviews=[row for row in project_reviews if row.get("status") in {"RETURNED","PUBLICATION_PROPOSED"}]
 if profile["execution_holds"]:
  state,tone="HELD","refused";headline="Execution is held"
  reason=profile["execution_holds"][0];label,tab="Inspect the hold","EVIDENCE"
 elif attention_sessions:
  state,tone="ATTENTION","pending";headline="A session needs attention"
  reason=attention_sessions[0]["session_id"];label,tab="Open session state","SESSIONS"
 elif profile["adherence_status"]=="STALE":
  state,tone="STALE","pending";headline="Verification is behind the current subject"
  reason="Current and verified subject roots differ";label,tab="Inspect verification evidence","EVIDENCE"
 elif profile["adherence_status"]=="UNVERIFIED":
  state,tone="UNVERIFIED","info";headline="Current project state is not yet verified"
  reason=(profile["qualification_gaps"][0] if profile["qualification_gaps"]
          else "No current verification receipt is bound")
  label,tab="Inspect verification requirements","EVIDENCE"
 elif returned_reviews:
  state,tone="REVIEW_RETURNED","accent";headline="A review return is ready"
  reason=returned_reviews[0]["review_id"];label,tab="Open review return","REVIEWS"
 elif profile["release_blockers"]:
  state,tone="BLOCKED","pending";headline="Release preparation has an open blocker"
  reason=profile["release_blockers"][0];label,tab="Inspect release blockers","EVIDENCE"
 elif profile["qualification_gaps"]:
  state,tone="ADVISORY","pending";headline="Qualified operation has a documented gap"
  reason=profile["qualification_gaps"][0];label,tab="Inspect qualification gaps","EVIDENCE"
 else:
  state,tone="READY","accent";headline="Project state is current"
  reason="Continue against the next explicit acceptance case";label,tab="Continue governed work","OVERVIEW"
 reason_display=(reason.replace("_"," ").strip().capitalize()
                 if reason and reason.upper()==reason else reason)
 body={"schema":PROJECT_BRIEF_SCHEMA,"project_id":project["project_id"],
  "project_root":project["project_root"],"profile_root":profile["profile_root"],
  "state":state,"tone":tone,"headline":headline,"reason":reason,"reason_display":reason_display,
  "recommended_action":{"label":label,"workspace_tab":tab,
   "effect":"READ_ONLY_NAVIGATION","dispatch_authorized":False},
  "metrics":{"sessions":len(project_sessions),"sessions_needing_attention":len(attention_sessions),
   "reviews":len(project_reviews),"returned_reviews":len(returned_reviews),
   "execution_holds":len(profile["execution_holds"]),
   "release_blockers":len(profile["release_blockers"]),
   "qualification_gaps":len(profile["qualification_gaps"])},
  "verification":{"adherence_status":profile["adherence_status"],
   "current_subject_root":profile["current_subject_root"],
   "verified_subject_root":profile["verified_subject_root"],
   "last_verified_ns":profile["last_verified_ns"]},
  "gateway_status":gateway_status,"projection_only":True,**BOUNDARY}
 return {**body,"project_brief_root":root(body)}


def build_preferences(*,session_navigation:str="LEFT",theme:str="signature-dark",density:str="comfortable",
 default_tab:str="OVERVIEW",hash_display:str="ABBREVIATED",pinned_projects:list[str]|None=None,
 pinned_sessions:list[str]|None=None,visible_project_fields:list[str]|None=None)->dict[str,Any]:
 if session_navigation not in {"LEFT","TOP"} or theme not in {"signature-dark","high-contrast-dark","signature-light"}:
  raise HubRefusal("PIPPI_LAYOUT_INVALID")
 if density not in {"comfortable","compact"} or default_tab not in {"OVERVIEW","SESSIONS","TIMELINE","EVIDENCE","REVIEWS","CONSTITUTION"}:
  raise HubRefusal("PIPPI_LAYOUT_INVALID")
 if hash_display not in {"ABBREVIATED","FULL"}:raise HubRefusal("PIPPI_LAYOUT_INVALID")
 def values(rows):return sorted(set(rows or []))
 fields=values(visible_project_fields or ["VERSION_REVISION","LAST_ACTIVITY","VERIFICATION_FRESHNESS","ADHERENCE",
  "BLOCKERS","ACTIVE_SESSIONS","ARCHIVE_STATUS","COURTHOUSE_STATUS"])
 body={"schema":PREFERENCES_SCHEMA,"session_navigation":session_navigation,"theme":theme,"density":density,
  "default_tab":default_tab,"hash_display":hash_display,"pinned_projects":values(pinned_projects),
  "pinned_sessions":values(pinned_sessions),"visible_project_fields":fields,**BOUNDARY}
 return {**body,"preferences_root":root(body)}


def validate_preferences(value:Any)->dict[str,Any]:
 if not isinstance(value,dict) or value.get("schema")!=PREFERENCES_SCHEMA:raise HubRefusal("PIPPI_PREFERENCES_INVALID")
 expected=build_preferences(session_navigation=value.get("session_navigation"),theme=value.get("theme"),density=value.get("density"),
  default_tab=value.get("default_tab"),hash_display=value.get("hash_display"),pinned_projects=value.get("pinned_projects"),
  pinned_sessions=value.get("pinned_sessions"),visible_project_fields=value.get("visible_project_fields"))
 if value!=expected:raise HubRefusal("PIPPI_PREFERENCES_INVALID")
 return deepcopy(value)


def _file_root(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_campaigns(search_roots:Iterable[Path],*,max_contexts:int=256)->list[dict[str,Any]]:
 found=[];seen=set()
 for search_root in sorted(Path(p).resolve() for p in search_roots):
  if not search_root.is_dir():continue
  for context_path in sorted(search_root.rglob("PIPPI-CONTEXT.json"),
                             key=lambda item: item.relative_to(search_root).as_posix()):
   workspace=context_path.parent.resolve()
   if workspace in seen:continue
   seen.add(workspace)
   if len(found)>=max_contexts:raise HubRefusal("PIPPI_DISCOVERY_LIMIT_EXCEEDED")
   try:
    context=validate_pippi_context(strict_loads(context_path.read_bytes()))
    from .pippi import effective_integration_mode
    verification=validate_pippi_campaign_workspace(workspace)
    head_path=workspace/"journal"/"HEAD.json";head=strict_loads(head_path.read_bytes())
    record=build_session_reference(session_id=f"import:{hashlib.sha256(str(workspace).encode()).hexdigest()[:16]}",
     project_id=None,source_path=str(workspace),source_kind="PIPPI_CAMPAIGN",context_root=context["context_root"],
     subject_root=context["subject_root"],journal_head=verification["journal_head"],event_count=verification["event_count"],
     last_activity_ns=max(context_path.stat().st_mtime_ns,head_path.stat().st_mtime_ns),status="IMPORTED",
     integration_mode=effective_integration_mode(context),mediated_channels=context["mediated_channels"],
     source_manifest_root=_file_root(context_path),discovery_status="VERIFIED")
   except Exception as exc:
    record={"schema":"mosaic.ucm.pippi-session-discovery-refusal.v0.1","source_path":str(workspace),
     "code":getattr(exc,"code",type(exc).__name__),"detail":str(exc),"discovery_status":"REFUSED",**BOUNDARY}
    record["discovery_root"]=root(record)
   found.append(record)
 return found


def build_session_reference(*,session_id:str,project_id:str|None,source_path:str,source_kind:str,
 context_root:str,subject_root:str,journal_head:str,event_count:int,last_activity_ns:int,status:str,
 integration_mode:str,mediated_channels:list[str],source_manifest_root:str,discovery_status:str)->dict[str,Any]:
 for value in (context_root,subject_root,journal_head,source_manifest_root):
  if not isinstance(value,str) or len(value)!=64:raise HubRefusal("PIPPI_SESSION_ROOT_INVALID")
 if status not in SESSION_STATES or discovery_status!="VERIFIED":raise HubRefusal("PIPPI_SESSION_STATUS_INVALID")
 body={"schema":SESSION_SCHEMA,"session_id":session_id,"project_id":project_id,"source_path":str(Path(source_path).resolve()),
  "source_kind":source_kind,"context_root":context_root,"subject_root":subject_root,"journal_head":journal_head,
  "event_count":event_count,"last_activity_ns":last_activity_ns,"status":status,"integration_mode":integration_mode,
  "mediated_channels":sorted(set(mediated_channels)),"source_manifest_root":source_manifest_root,
  "discovery_status":discovery_status,"migration_mode":"REFERENCE_ONLY_NO_REWRITE",**BOUNDARY}
 return {**body,"session_reference_root":root(body)}


def validate_session_reference(value:Any)->dict[str,Any]:
 if not isinstance(value,dict) or value.get("schema")!=SESSION_SCHEMA:raise HubRefusal("PIPPI_SESSION_REFERENCE_INVALID")
 body={k:deepcopy(v) for k,v in value.items() if k!="session_reference_root"}
 if value.get("session_reference_root")!=root(body):raise HubRefusal("PIPPI_SESSION_REFERENCE_INVALID")
 return deepcopy(value)


def build_timeline(*,project_id:str,hub_events:list[dict[str,Any]],sessions:list[dict[str,Any]])->dict[str,Any]:
 rows=[];represented_sessions=set()
 for event in hub_events:
  payload=event.get("payload",{})
  if payload.get("project_id")!=project_id:continue
  kind=event["event_type"]
  if kind=="SESSION_REFERENCE_IMPORTED":represented_sessions.add(payload.get("session_id"))
  lane="ARCHIVE" if kind in ARCHIVE_EVENTS else "COURTHOUSE" if kind in COURTHOUSE_EVENTS else \
   "REVIEW" if kind in REVIEW_EVENTS else "SESSION" if kind.startswith("SESSION_") else "OPERATION"
  rows.append({"sequence":event["sequence"],"observed_unix_ns":event["observed_unix_ns"],"lane":lane,
   "kind":kind,"receipt_root":payload.get("session_reference_root",event["event_root"])})
 for session in sessions:
  if session.get("project_id")==project_id and session.get("session_id") not in represented_sessions:
   rows.append({"sequence":None,"observed_unix_ns":session["last_activity_ns"],"lane":"SESSION",
    "kind":"SESSION_REFERENCE_IMPORTED","receipt_root":session["session_reference_root"]})
 rows.sort(key=lambda row:(row["observed_unix_ns"],row["lane"],row["kind"]))
 body={"schema":TIMELINE_SCHEMA,"project_id":project_id,"events":rows,**BOUNDARY}
 return {**body,"timeline_root":root(body)}


class PortfolioStore:
 def __init__(self,hub:PippiHub):
  self.hub=hub;self.root=hub.root/"portfolio";self.profiles=self.root/"projects";self.sessions=self.root/"sessions"
  self.preferences_path=self.root/"PREFERENCES.json"
 def preferences(self)->dict[str,Any]:
  if not self.preferences_path.is_file():return build_preferences()
  return validate_preferences(strict_loads(self.preferences_path.read_bytes()))
 def save_preferences(self,value:dict[str,Any])->dict[str,Any]:
  value=validate_preferences(value);_atomic(self.preferences_path,value);self.hub.append("DASHBOARD_PREFERENCES_UPDATED",{
   "preferences_root":value["preferences_root"]});return value
 def profile(self,project:dict[str,Any])->dict[str,Any]:
  path=self.profiles/f"{project['project_id']}.json"
  if path.is_file():return validate_project_profile(strict_loads(path.read_bytes()))
  return build_project_profile(project=project,workspaces=[{"workspace_id":"primary","path":project["workspace"],"role":"WORKING",
   "status":"ACTIVE" if Path(project["workspace"]).is_dir() else "MISSING"}],canonical_store={"kind":"UNBOUND","path":None,
   "active_revision":project["revision"],"revision_root":None},current_subject_root=None,last_material_activity_ns=None,
   last_verified_ns=None,verified_subject_root=None,proof_level="UNVERIFIED",operational_maturity="REGISTERED",
   execution_holds=[],release_blockers=["CANONICAL_STORE_UNBOUND"],qualification_gaps=["CURRENT_SUBJECT_ROOT_UNBOUND"],
   archive_status="UNVERIFIED",courthouse_status="NO_WORK_PENDING")
 def save_profile(self,value:dict[str,Any])->dict[str,Any]:
  value=validate_project_profile(value);_atomic(self.profiles/f"{value['project_id']}.json",value);self.hub.append(
   "PROJECT_PROFILE_UPDATED",{"project_id":value["project_id"],"profile_root":value["profile_root"]});return value
 def list_sessions(self,project_id:str|None=None)->list[dict[str,Any]]:
  rows=[validate_session_reference(strict_loads(path.read_bytes()))
        for path in sorted(self.sessions.glob("*.json"), key=lambda item: item.name)]
  return [row for row in rows if project_id is None or row["project_id"]==project_id]
 def import_session(self,value:dict[str,Any],*,project_id:str)->dict[str,Any]:
  value=validate_session_reference(value);project=self.hub.get_project(project_id)
  body={k:deepcopy(v) for k,v in value.items() if k!="session_reference_root"};body["project_id"]=project_id
  value={**body,"session_reference_root":root(body)};path=self.sessions/f"{value['session_id'].replace(':','_')}.json"
  if path.exists() and strict_loads(path.read_bytes())!=value:raise HubRefusal("PIPPI_SESSION_IMPORT_CONFLICT")
  _atomic(path,value);self.hub.append("SESSION_REFERENCE_IMPORTED",{"project_id":project_id,"session_id":value["session_id"],
   "session_reference_root":value["session_reference_root"],"source_path":value["source_path"]});return value

