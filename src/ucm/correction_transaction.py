"""AMCAS bounded correction transaction: begin, patch, seal, restore, verify."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile,time,zipfile
from pathlib import Path,PurePosixPath
INFO={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
TXS="mosaic.ucm.correction-transaction.v0.1";PS="mosaic.ucm.correction-patch.v0.1";RS="mosaic.ucm.correction-receipt.v0.1";ZERO="0"*64
class Refusal(RuntimeError):
 def __init__(self,code,detail=""):self.code,self.detail=code,detail;super().__init__(code+(":"+detail if detail else ""))
def cb(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def rt(v):return hashlib.sha256(cb(v)).hexdigest()
def sh(b):return hashlib.sha256(b).hexdigest()
def rj(p):
 try:return json.loads(Path(p).read_text("utf-8"),parse_constant=lambda x:(_ for _ in()).throw(ValueError(x)))
 except FileNotFoundError as e:raise Refusal("CORRECTION_RECORD_MISSING",Path(p).name) from e
 except Exception as e:raise Refusal("CORRECTION_RECORD_INVALID",Path(p).name) from e
def ad(p):
 if os.name=="nt":return
 f=os.open(p,os.O_RDONLY)
 try:os.fsync(f)
 finally:os.close(f)
def wb(p,b,replace=True):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);fd,n=tempfile.mkstemp(prefix="."+p.name+".",suffix=".tmp",dir=p.parent);t=Path(n)
 try:
  with os.fdopen(fd,"wb") as f:f.write(b);f.flush();os.fsync(f.fileno())
  if not replace and p.exists():raise Refusal("CORRECTION_IMMUTABLE_RECORD_EXISTS",p.name)
  os.replace(t,p);ad(p.parent)
 finally:
  if t.exists():t.unlink()
def wj(p,v,replace=True):wb(p,cb(v)+b"\n",replace)
def safe(s):
 if not s or "\\" in s:raise Refusal("CORRECTION_PATH_INVALID",str(s))
 p=PurePosixPath(s)
 if p.is_absolute() or any(x in ("",".","..") for x in p.parts):raise Refusal("CORRECTION_PATH_INVALID",s)
 return p.as_posix()
def tgt(base,rel):
 rel=safe(rel);p=(Path(base)/Path(*PurePosixPath(rel).parts)).resolve()
 try:p.relative_to(Path(base).resolve())
 except ValueError as e:raise Refusal("CORRECTION_PATH_ESCAPES_ROOT",rel) from e
 return p
def inv(base,ex=()):
 base=Path(base).resolve();xs=sorted({safe(x.rstrip("/")) for x in ex})
 if not base.is_dir():raise Refusal("CORRECTION_SOURCE_NOT_DIRECTORY",str(base))
 rows=[]
 all_paths=list(base.rglob("*"))
 if any(x.is_symlink() for x in all_paths):raise Refusal("CORRECTION_SYMLINK_UNSUPPORTED")
 for p in sorted((x for x in all_paths if x.is_file()),key=lambda x:x.relative_to(base).as_posix()):
  q=p.relative_to(base).as_posix()
  if any(q==x or q.startswith(x+"/") for x in xs):continue
  b=p.read_bytes();rows.append({"path":q,"sha256":sh(b),"bytes":len(b)})
 return {"schema":"mosaic.ucm.source-envelope.v0.1","files":rows,"file_count":len(rows),"source_root":rt(rows),"excludes":xs}
def mp(e):return {x["path"]:dict(x) for x in e["files"]}
def dif(a,b):
 x,y=mp(a),mp(b);return {k for k in set(x)|set(y) if x.get(k)!=y.get(k)}
class Progress:
 def __init__(self,tx):
  self.tx=Path(tx);self.log=self.tx/"PROGRESS.jsonl";self.status=self.tx/"STATUS.json";self.n=0
  if self.log.exists():
   try:self.n=json.loads(self.log.read_text("utf-8").splitlines()[-1])["sequence"]
   except Exception:pass
 def emit(self,phase,state,**kw):
  self.n+=1;e={"schema":"mosaic.ucm.nonsemantic-progress.v0.1","sequence":self.n,"phase":phase,"state":state,"nonsemantic":True,"time_unix_ns":time.time_ns(),**kw};self.tx.mkdir(parents=True,exist_ok=True)
  with self.log.open("ab") as f:f.write(cb(e)+b"\n");f.flush();os.fsync(f.fileno())
  wj(self.status,{"schema":"mosaic.ucm.correction-status-projection.v0.1","nonsemantic":True,"sequence":self.n,"phase":phase,"state":state,"time_unix_ns":e["time_unix_ns"],"transaction_state":kw.get("transaction_state"),"refusal_code":kw.get("refusal_code")})
  print(json.dumps(e,sort_keys=True,separators=(",",":")),flush=True)
def st(tx):
 v=rj(Path(tx)/"TRANSACTION.json")
 if v.get("schema")!=TXS:raise Refusal("CORRECTION_TRANSACTION_SCHEMA_INVALID")
 return v
def ss(tx,v):wj(Path(tx)/"TRANSACTION.json",v)
def hd(tx):
 p=Path(tx)/"HEAD.json"
 if not p.exists():return 0,ZERO
 h=rj(p);return h["sequence"],h["receipt_root"]
def rec(tx,kind,body):
 tx=Path(tx);n,prev=hd(tx);c={"schema":RS,"sequence":n+1,"kind":kind,"previous_receipt_root":prev,**INFO,**body};r={**c,"receipt_root":rt(c)}
 with (tx/"RECEIPTS.jsonl").open("ab") as f:f.write(cb(r)+b"\n");f.flush();os.fsync(f.fileno())
 ad(tx)
 wj(tx/"HEAD.json",{"sequence":r["sequence"],"receipt_root":r["receipt_root"]});return r
def chain(tx):
 prev=ZERO;n=0
 for raw in (Path(tx)/"RECEIPTS.jsonl").read_bytes().splitlines():
  r=json.loads(raw);n+=1;c={k:v for k,v in r.items() if k!="receipt_root"}
  if r["sequence"]!=n or r["previous_receipt_root"]!=prev or r["receipt_root"]!=rt(c):raise Refusal("CORRECTION_RECEIPT_CHAIN_INVALID")
  prev=r["receipt_root"]
 if hd(tx)!=(n,prev):raise Refusal("CORRECTION_RECEIPT_HEAD_MISMATCH")
 return prev
def begin(source,tx,transaction_id,ex=()):
 src,tx=Path(source).resolve(),Path(tx).resolve()
 try:tx.relative_to(src);raise Refusal("CORRECTION_TRANSACTION_OVERLAPS_SOURCE")
 except ValueError:pass
 if tx.exists() and any(tx.iterdir()):raise Refusal("CORRECTION_TRANSACTION_NOT_EMPTY")
 tx.mkdir(parents=True,exist_ok=True);p=Progress(tx);p.emit("inventory","start",transaction_state="BEGINNING");e=inv(src,ex);p.emit("inventory","complete",files=e["file_count"],source_root=e["source_root"]);(tx/"objects").mkdir();p.emit("snapshot","start",total=e["file_count"])
 for i,row in enumerate(e["files"],1):
  b=tgt(src,row["path"]).read_bytes()
  if sh(b)!=row["sha256"]:raise Refusal("CORRECTION_SOURCE_CHANGED_DURING_SNAPSHOT",row["path"])
  o=tx/"objects"/row["sha256"]
  if not o.exists():wb(o,b,False)
  if i==1 or i==e["file_count"] or i%100==0:p.emit("snapshot","progress",completed=i,total=e["file_count"])
 wj(tx/"PREIMAGE.json",e,False);p.emit("precondition_verification","start")
 if inv(src,e["excludes"])!=e:raise Refusal("CORRECTION_SOURCE_CHANGED_DURING_BEGIN")
 c={"schema":"mosaic.ucm.correction-begin-receipt.v0.1","transaction_id":transaction_id,"source_path":str(src),"pre_source_root":e["source_root"],"pre_file_count":e["file_count"],"excludes":e["excludes"],**INFO};br={**c,"begin_root":rt(c)};wj(tx/"BEGIN-RECEIPT.json",br,False);r=rec(tx,"BEGIN",{"transaction_id":transaction_id,"begin_root":br["begin_root"],"pre_source_root":e["source_root"]});ss(tx,{"schema":TXS,"transaction_id":transaction_id,"source_path":str(src),"state":"BEGUN","pre_source_root":e["source_root"],"post_source_root":None,"patch_root":None,"changed_paths":[],"head_receipt_root":r["receipt_root"]});p.emit("precondition_verification","complete",transaction_state="BEGUN",source_root=e["source_root"]);return br
def zw(path,members):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);t=path.with_name("."+path.name+".tmp")
 try:
  with zipfile.ZipFile(t,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for n in sorted(members):
    i=zipfile.ZipInfo(n,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,members[n])
  os.replace(t,path);ad(path.parent)
 finally:
  if t.exists():t.unlink()
def build_patch(tx,out,replacements,deletions=()):
 tx=Path(tx).resolve();s=st(tx)
 if s["state"]!="BEGUN":raise Refusal("CORRECTION_PATCH_BUILD_STATE_INVALID",s["state"])
 p=Progress(tx);p.emit("patch_construction","start",transaction_state=s["state"]);pre=rj(tx/"PREIMAGE.json");src=Path(s["source_path"])
 if inv(src,pre["excludes"])!=pre:raise Refusal("CORRECTION_PRECONDITION_ROOT_MISMATCH")
 reps={}
 for rel,sp in replacements:
  rel=safe(rel);q=Path(sp)
  if rel in reps or not q.is_file():raise Refusal("CORRECTION_PATCH_INPUT_INVALID",rel)
  reps[rel]=q.read_bytes()
 ds={safe(x) for x in deletions}
 if ds&set(reps):raise Refusal("CORRECTION_PATCH_PATH_CONFLICT")
 old=mp(pre);new={k:dict(v) for k,v in old.items()};changes=[];objs={}
 for rel,b in sorted(reps.items()):
  a=sh(b);z=old.get(rel,{}).get("sha256")
  if z==a:raise Refusal("CORRECTION_PATCH_NOOP",rel)
  changes.append({"path":rel,"operation":"replace" if z else "add","before_sha256":z,"after_sha256":a,"bytes":len(b)});new[rel]={"path":rel,"sha256":a,"bytes":len(b)};objs["objects/"+a]=b
 for rel in sorted(ds):
  if rel not in old:raise Refusal("CORRECTION_DELETE_TARGET_MISSING",rel)
  changes.append({"path":rel,"operation":"delete","before_sha256":old[rel]["sha256"],"after_sha256":None,"bytes":0});del new[rel]
 if not changes:raise Refusal("CORRECTION_PATCH_EMPTY")
 rows=[new[k] for k in sorted(new)];c={"schema":PS,"transaction_id":s["transaction_id"],"pre_source_root":pre["source_root"],"post_source_root":rt(rows),"pre_file_count":pre["file_count"],"post_file_count":len(rows),"excludes":pre["excludes"],"changes":changes,"post_manifest":rows,**INFO};patch={**c,"patch_root":rt(c)};zw(Path(out).resolve(),{"PATCH.json":cb(patch)+b"\n",**objs});p.emit("patch_construction","complete",changes=len(changes),patch_root=patch["patch_root"]);return patch
def lp(path):
 try:
  with zipfile.ZipFile(path) as z:
   names=z.namelist()
   if len(names)!=len(set(names)) or "PATCH.json" not in names:raise Refusal("CORRECTION_PATCH_ARCHIVE_INVALID")
   raw={n:z.read(n) for n in names}
 except (FileNotFoundError,zipfile.BadZipFile) as e:raise Refusal("CORRECTION_PATCH_ARCHIVE_INVALID") from e
 patch=json.loads(raw.pop("PATCH.json"));c={k:v for k,v in patch.items() if k!="patch_root"};expected={"objects/"+x["after_sha256"] for x in patch["changes"] if x["after_sha256"]}
 if patch.get("schema")!=PS or patch.get("patch_root")!=rt(c) or set(raw)!=expected or any(sh(b)!=n.split("/",1)[1] for n,b in raw.items()):raise Refusal("CORRECTION_PATCH_INVALID")
 return patch,raw
def seal(tx,archive):
 tx=Path(tx).resolve();s=st(tx)
 if s["state"]!="BEGUN":raise Refusal("CORRECTION_SEAL_STATE_INVALID",s["state"])
 p=Progress(tx);p.emit("precondition_verification","start",transaction_state="BEGUN");pre=rj(tx/"PREIMAGE.json");src=Path(s["source_path"]);patch,objs=lp(Path(archive).resolve())
 if patch["transaction_id"]!=s["transaction_id"] or patch["pre_source_root"]!=s["pre_source_root"] or inv(src,pre["excludes"])!=pre:raise Refusal("CORRECTION_PATCH_BINDING_OR_PRECONDITION_MISMATCH")
 changed=[x["path"] for x in patch["changes"]];bound=tx/"PATCH.zip";shutil.copyfile(Path(archive).resolve(),bound)
 with bound.open("r+b") as f:f.flush();os.fsync(f.fileno())
 ad(tx)
 r=rec(tx,"PATCH_BOUND",{"transaction_id":s["transaction_id"],"patch_root":patch["patch_root"],"patch_archive_sha256":sh(bound.read_bytes()),"pre_source_root":pre["source_root"],"declared_changed_paths":changed});s.update({"state":"PATCH_BOUND","patch_root":patch["patch_root"],"post_source_root":patch["post_source_root"],"changed_paths":changed,"head_receipt_root":r["receipt_root"]});ss(tx,s);p.emit("precondition_verification","complete",transaction_state="PATCH_BOUND")
 try:
  p.emit("patch_application","start",total=len(changed))
  for i,row in enumerate(patch["changes"],1):
   q=tgt(src,row["path"])
   if row["operation"]=="delete":
    if q.exists():q.unlink();ad(q.parent)
   else:wb(q,objs["objects/"+row["after_sha256"]])
   p.emit("patch_application","progress",completed=i,total=len(changed),path=row["path"])
  p.emit("post_apply_verification","start");post=inv(src,pre["excludes"]);expect={**pre,"files":patch["post_manifest"],"file_count":patch["post_file_count"],"source_root":patch["post_source_root"]}
  if post!=expect:
   extra=sorted(dif(post,expect)-set(changed))
   if extra:raise Refusal("CORRECTION_UNDECLARED_CHANGE",",".join(extra))
   raise Refusal("CORRECTION_POST_ROOT_MISMATCH")
  r=rec(tx,"SEALED",{"transaction_id":s["transaction_id"],"patch_root":patch["patch_root"],"pre_source_root":pre["source_root"],"post_source_root":patch["post_source_root"],"declared_changed_paths":changed});s.update({"state":"SEALED","head_receipt_root":r["receipt_root"]});ss(tx,s);p.emit("post_apply_verification","complete",transaction_state="SEALED",source_root=post["source_root"]);return r
 except Exception as e:
  s["state"]="RECOVERY_REQUIRED";ss(tx,s);p.emit("patch_application","refused",transaction_state="RECOVERY_REQUIRED",refusal_code=e.code if isinstance(e,Refusal) else "CORRECTION_INTERNAL_ERROR");raise
def restore(tx):
 tx=Path(tx).resolve();s=st(tx)
 if s["state"] not in ("PATCH_BOUND","SEALED","RECOVERY_REQUIRED"):raise Refusal("CORRECTION_RESTORE_STATE_INVALID",s["state"])
 p=Progress(tx);p.emit("rollback","start",transaction_state=s["state"]);pre=rj(tx/"PREIMAGE.json");patch,_=lp(tx/"PATCH.zip");src=Path(s["source_path"]);changed=set(s["changed_paths"]);bad=sorted(dif(inv(src,pre["excludes"]),pre)-changed)
 if bad:raise Refusal("CORRECTION_UNDECLARED_CHANGE",",".join(bad))
 old=mp(pre);p.emit("member_restoration","start",total=len(changed))
 for i,rel in enumerate(sorted(changed),1):
  q=tgt(src,rel)
  if rel in old:
   h=old[rel]["sha256"];b=(tx/"objects"/h).read_bytes()
   if sh(b)!=h:raise Refusal("CORRECTION_PREIMAGE_OBJECT_HASH_MISMATCH",rel)
   wb(q,b)
  elif q.exists():q.unlink();ad(q.parent)
  p.emit("member_restoration","progress",completed=i,total=len(changed),path=rel)
 p.emit("whole_root_proof","start");got=inv(src,pre["excludes"])
 if got!=pre:raise Refusal("CORRECTION_ROLLBACK_ROOT_MISMATCH")
 r=rec(tx,"RESTORED",{"transaction_id":s["transaction_id"],"patch_root":patch["patch_root"],"recovered_source_root":got["source_root"],"declared_changed_paths":sorted(changed)});s.update({"state":"RESTORED","head_receipt_root":r["receipt_root"]});ss(tx,s);p.emit("whole_root_proof","complete",transaction_state="RESTORED",source_root=got["source_root"]);return r
def verify(tx):
 tx=Path(tx).resolve();s=st(tx);p=Progress(tx);p.emit("verification","start",transaction_state=s["state"]);pre=rj(tx/"PREIMAGE.json");src=Path(s["source_path"])
 for row in pre["files"]:
  q=tx/"objects"/row["sha256"]
  if not q.is_file() or sh(q.read_bytes())!=row["sha256"]:raise Refusal("CORRECTION_PREIMAGE_OBJECT_INVALID",row["path"])
 expected=lp(tx/"PATCH.zip")[0]["post_source_root"] if s["state"]=="SEALED" else pre["source_root"]
 if s["state"] not in ("BEGUN","SEALED","RESTORED","VERIFIED"):raise Refusal("CORRECTION_VERIFY_STATE_INVALID",s["state"])
 got=inv(src,pre["excludes"])
 if got["source_root"]!=expected:raise Refusal("CORRECTION_VERIFY_SOURCE_ROOT_MISMATCH")
 h=chain(tx)
 if s["state"]!="VERIFIED":
  prior=s["state"];r=rec(tx,"VERIFIED",{"transaction_id":s["transaction_id"],"transaction_state":prior,"observed_source_root":got["source_root"],"verified_receipt_head":h});s.update({"state":"VERIFIED","verified_from_state":prior,"head_receipt_root":r["receipt_root"]});ss(tx,s)
 else:r={"kind":"VERIFIED","receipt_root":s["head_receipt_root"]}
 p.emit("verification","complete",transaction_state="VERIFIED",source_root=got["source_root"]);return r
def status(tx):
 tx=Path(tx).resolve();return {"transaction":st(tx),"progress_projection":rj(tx/"STATUS.json"),"receipt_head":rj(tx/"HEAD.json")}
inventory=inv
def parser():
 p=argparse.ArgumentParser(prog="ucm-correction");s=p.add_subparsers(dest="cmd",required=True);q=s.add_parser("begin");q.add_argument("source");q.add_argument("transaction");q.add_argument("--transaction-id",required=True);q.add_argument("--exclude",action="append",default=[]);q=s.add_parser("build-patch");q.add_argument("transaction");q.add_argument("output");q.add_argument("--replace",action="append",default=[]);q.add_argument("--delete",action="append",default=[]);q=s.add_parser("seal");q.add_argument("transaction");q.add_argument("patch")
 for n in ("restore","verify","status"):q=s.add_parser(n);q.add_argument("transaction")
 return p
def main(argv=None):
 a=parser().parse_args(argv)
 try:
  if a.cmd=="begin":r=begin(a.source,a.transaction,a.transaction_id,a.exclude)
  elif a.cmd=="build-patch":
   pairs=[]
   for v in a.replace:
    if "=" not in v:raise Refusal("CORRECTION_REPLACEMENT_ARGUMENT_INVALID",v)
    pairs.append(tuple(v.split("=",1)))
   r=build_patch(a.transaction,a.output,pairs,a.delete)
  elif a.cmd=="seal":r=seal(a.transaction,a.patch)
  elif a.cmd=="restore":r=restore(a.transaction)
  elif a.cmd=="verify":r=verify(a.transaction)
  else:r=status(a.transaction)
  print(json.dumps({"status":"PASS","result":r},sort_keys=True,separators=(",",":")));return 0
 except Refusal as e:print(json.dumps({"status":"REFUSED","reason_code":e.code,"detail":e.detail},sort_keys=True,separators=(",",":")),file=sys.stderr);return 20
if __name__=="__main__":raise SystemExit(main())
