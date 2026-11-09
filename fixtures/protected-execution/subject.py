from __future__ import annotations

import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys


mode = sys.argv[1]
output_root = Path(os.environ["DAR_OUTPUT_ROOT"])
if mode == "BENIGN":
    (output_root / "result.txt").write_text("DISPOSABLE_ONLY\n", encoding="utf-8", newline="\n")
elif mode == "NETWORK":
    socket.socket().connect(("127.0.0.1", 9))
elif mode == "SENDTO":
    socket.socket().sendto(b"x", ("127.0.0.1", 9))
elif mode == "OUTSIDE_WRITE":
    Path(os.environ["DAR_ATTACK_TARGET"]).write_text("forbidden\n", encoding="utf-8")
elif mode == "SUBPROCESS":
    subprocess.run([sys.executable, "-c", "pass"], check=True)
elif mode == "SPAWNV":
    os.spawnv(os.P_WAIT, sys.executable, [sys.executable, "-c", "pass"])
elif mode == "SQLITE_OUTSIDE":
    sqlite3.connect(os.environ["DAR_ATTACK_TARGET"] + ".sqlite").execute("create table t(x)")
elif mode == "SQLITE_ATTACH":
    connection = sqlite3.connect(output_root / "inside.sqlite")
    connection.execute("attach database ? as outside", (os.environ["DAR_ATTACK_TARGET"] + ".attached.sqlite",))
elif mode == "SQLITE_CLEAR_AUTHORIZER":
    connection = sqlite3.connect(output_root / "inside.sqlite")
    connection.set_authorizer(None)
elif mode == "SQLITE_INTERNAL_ESCAPE":
    connection = sqlite3.connect(output_root / "inside.sqlite")
    connection._connection.set_authorizer(None)
elif mode == "SQLITE_RAW_METHOD_ESCAPE":
    connection = sqlite3.connect(output_root / "inside.sqlite")
    connection._raw().execute("attach database ? as outside", (os.environ["DAR_ATTACK_TARGET"] + ".raw.sqlite",))
elif mode == "SQLITE_OBJECT_GETATTRIBUTE_ESCAPE":
    connection = sqlite3.connect(output_root / "inside.sqlite")
    raw = object.__getattribute__(connection, "_GuardedConnection__connection")
    raw.execute("attach database ? as outside", (os.environ["DAR_ATTACK_TARGET"] + ".object.sqlite",))
elif mode == "SQLITE_CONNECTION_CONSTRUCTOR_OUTSIDE":
    sqlite3.Connection(os.environ["DAR_ATTACK_TARGET"] + ".constructor.sqlite").execute("create table t(x)")
elif mode == "SQLITE_C_MODULE_OUTSIDE":
    import _sqlite3
    _sqlite3.connect(os.environ["DAR_ATTACK_TARGET"] + ".c-module.sqlite").execute("create table t(x)")
elif mode == "SQLITE_DBAPI2_OUTSIDE":
    sqlite3.dbapi2.connect(os.environ["DAR_ATTACK_TARGET"] + ".dbapi2.sqlite").execute("create table t(x)")
elif mode == "MKFIFO_OUTSIDE":
    target = os.environ["DAR_ATTACK_TARGET"] + ".fifo"
    if hasattr(os, "mkfifo"):
        os.mkfifo(target)
    else:
        sys.audit("os.mkfifo", target)
elif mode == "POSIX_MKFIFO_OUTSIDE":
    target = os.environ["DAR_ATTACK_TARGET"] + ".posix-fifo"
    try:
        import posix
    except ImportError:
        sys.audit("os.mkfifo", target)
    else:
        posix.mkfifo(target)
elif mode == "MKNOD_OUTSIDE":
    target = os.environ["DAR_ATTACK_TARGET"] + ".node"
    if hasattr(os, "mknod"):
        os.mknod(target)
    else:
        sys.audit("os.mknod", target)
elif mode == "MKFIFO_DIRFD_OUTSIDE":
    if os.name == "posix":
        directory = os.open(str(output_root.parent), os.O_RDONLY)
        try:
            os.mkfifo("outside-dirfd.fifo", dir_fd=directory)
        finally:
            os.close(directory)
    else:
        target = str(output_root.parent / "outside-dirfd.fifo")
        if hasattr(os, "mkfifo"):
            os.mkfifo(target)
        else:
            sys.audit("os.mkfifo", target)
elif mode == "OPEN_DIRFD_OUTSIDE":
    if os.name == "posix":
        directory = os.open(str(output_root.parent), os.O_RDONLY)
        try:
            descriptor = os.open("outside-dirfd.txt", os.O_CREAT | os.O_WRONLY, 0o600, dir_fd=directory)
            os.close(descriptor)
        finally:
            os.close(directory)
    else:
        descriptor = os.open(str(output_root.parent / "outside-dirfd.txt"), os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(descriptor)
elif mode in {"POSIX_OPEN_DIRFD_OUTSIDE", "RENAME_DIRFD_OUTSIDE", "MKDIR_DIRFD_OUTSIDE", "SYMLINK_DIRFD_OUTSIDE", "CHMOD_DIRFD_OUTSIDE"}:
    if os.name == "posix":
        import posix
        directory = os.open(str(output_root.parent), os.O_RDONLY)
        try:
            if mode == "POSIX_OPEN_DIRFD_OUTSIDE":
                descriptor = posix.open("outside-posix-open.txt", os.O_CREAT | os.O_WRONLY, 0o600, dir_fd=directory); os.close(descriptor)
            elif mode == "RENAME_DIRFD_OUTSIDE":
                (output_root / "rename-source.txt").write_text("x", encoding="utf-8")
                os.rename(str(output_root / "rename-source.txt"), "outside-renamed.txt", dst_dir_fd=directory)
            elif mode == "MKDIR_DIRFD_OUTSIDE":
                os.mkdir("outside-directory", dir_fd=directory)
            elif mode == "SYMLINK_DIRFD_OUTSIDE":
                os.symlink(str(output_root / "result.txt"), "outside-link", dir_fd=directory)
            else:
                target = output_root.parent / "outside-chmod.txt"; target.write_text("x", encoding="utf-8")
                os.chmod("outside-chmod.txt", 0o600, dir_fd=directory)
        finally:
            os.close(directory)
    else:
        outside = output_root.parent
        if mode == "POSIX_OPEN_DIRFD_OUTSIDE":
            descriptor = os.open(str(outside / "outside-posix-open.txt"), os.O_CREAT | os.O_WRONLY, 0o600); os.close(descriptor)
        elif mode == "RENAME_DIRFD_OUTSIDE":
            source = output_root / "rename-source.txt"; source.write_text("x", encoding="utf-8"); os.rename(source, outside / "outside-renamed.txt")
        elif mode == "MKDIR_DIRFD_OUTSIDE":
            os.mkdir(outside / "outside-directory")
        elif mode == "SYMLINK_DIRFD_OUTSIDE":
            os.symlink(output_root / "result.txt", outside / "outside-link")
        else:
            target = outside / "outside-chmod.txt"; target.write_text("x", encoding="utf-8"); os.chmod(target, 0o600)
elif mode == "SETXATTR_OUTSIDE":
    if hasattr(os, "setxattr"):
        os.setxattr(os.environ["DAR_ATTACK_TARGET"], "user.ucl_test", b"x")
    else:
        sys.audit("os.setxattr", os.environ["DAR_ATTACK_TARGET"], "user.ucl_test", b"x")
elif mode == "KILL_EVENT":
    os.kill(os.getpid(), 0)
elif mode == "CTYPES_NATIVE":
    import ctypes
    ctypes.CDLL(None)
elif mode == "UTIME_OUTSIDE":
    target = Path(os.environ["DAR_ATTACK_TARGET"])
    target.touch()
    os.utime(target, None)
else:
    raise RuntimeError("UNKNOWN_MODE")
