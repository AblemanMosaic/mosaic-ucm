"""Authenticated loopback service for cross-session P/PPI coordination."""
from __future__ import annotations

import json
from multiprocessing.connection import Client, Listener
import os
from pathlib import Path
import secrets
from typing import Any

from .pippi_global import PippiHub, default_data_root
from .pippi_portfolio import (PortfolioStore, build_project_brief, build_timeline,
                              discover_campaigns)
from .pippi_reviews import ReviewStore
from .pippi_security import protect_private_file, verify_private_file


def dispatch_read(hub:PippiHub,request:dict[str,Any])->Any:
    """Return authenticated hub projections without executing project effects."""
    portfolio=PortfolioStore(hub);command=request.get("command")
    if command=="verify":return hub.verify()
    if command=="projects":return hub.list_projects()
    if command=="project":return hub.get_project(request["project_id"])
    if command=="profile":return portfolio.profile(hub.get_project(request["project_id"]))
    if command=="project-brief":
        project=hub.get_project(request["project_id"])
        return build_project_brief(project=project,profile=portfolio.profile(project),
            sessions=portfolio.list_sessions(project["project_id"]),
            reviews=ReviewStore(hub).list(project["project_id"]),
            gateway_status=hub.integration("UCM_OPERATIONAL_GATEWAY")["status"])
    if command=="sessions":return portfolio.list_sessions(request.get("project_id"))
    if command=="turns":
        from .pippi_turn_workflow import project_turn_history, turn_continuation_context
        return {"history":project_turn_history(hub,request["project_id"]),
                "continuation":turn_continuation_context(hub,request["project_id"])}
    if command=="preferences":return portfolio.preferences()
    if command=="timeline":
        project_id=request["project_id"];hub.get_project(project_id)
        return build_timeline(project_id=project_id,hub_events=hub._events(),
                              sessions=portfolio.list_sessions(project_id))
    if command=="reviews":return ReviewStore(hub).list(request.get("project_id"))
    return {"status":"REFUSED","code":"PIPPI_IPC_COMMAND_REFUSED"}


def _key(root: Path, create: bool = False) -> bytes:
    path=root/"IPC.key"
    if create and not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(secrets.token_bytes(32));stream.flush();os.fsync(stream.fileno())
            protect_private_file(path)
        except Exception:
            path.unlink(missing_ok=True)
            raise
    verify_private_file(path)
    return path.read_bytes()


def serve(data_root: Path | None = None) -> int:
    root=Path(data_root or default_data_root()).resolve(); hub=PippiHub(root)
    pid_path=root/"IPC-SERVICE.pid"
    if pid_path.exists():
        try:
            os.kill(int(pid_path.read_text(encoding="ascii").strip()),0)
        except (OSError,ValueError): pid_path.unlink(missing_ok=True)
        else: raise RuntimeError("PIPPI_SERVICE_ALREADY_RUNNING")
    pid_path.write_text(str(os.getpid()),encoding="ascii")
    listener=Listener(("127.0.0.1",0),authkey=_key(root,True))
    address={"host":listener.address[0],"port":listener.address[1]}
    (root/"IPC-ENDPOINT.json").write_text(json.dumps(address,sort_keys=True)+"\n",encoding="utf-8")
    hub.append("HUB_SERVICE_STARTED",{"transport":"AUTHENTICATED_LOOPBACK","port":address["port"]})
    try:
        while True:
            connection=listener.accept()
            try:
                request=connection.recv()
                command=request.get("command") if isinstance(request,dict) else None
                if command=="stop":
                    hub.append("HUB_SERVICE_STOPPED",{});connection.send({"status":"PASS"});break
                else: result=dispatch_read(hub,request)
                connection.send(result)
            finally: connection.close()
    finally:
        listener.close();pid_path.unlink(missing_ok=True)
    return 0


def request(command: str, payload: dict[str,Any] | None=None, data_root: Path | None=None) -> Any:
    root=Path(data_root or default_data_root()).resolve()
    endpoint=json.loads((root/"IPC-ENDPOINT.json").read_text(encoding="utf-8"))
    connection=Client((endpoint["host"],endpoint["port"]),authkey=_key(root))
    try:
        connection.send({"command":command,**(payload or {})});return connection.recv()
    finally: connection.close()

