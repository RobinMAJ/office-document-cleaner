"""Start/status the independent public static origin; never change Funnel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path("/config/workspace/office-document-cleaner")
RELEASE = Path(__file__).resolve().parents[1]
STATE = ROOT / "var/origin"
PORT = 18815
HOST = "office-document-cleaner.tailee7aa5.ts.net"
ARGV = [sys.executable, str(RELEASE / "deploy/static_server.py"), "--port", str(PORT)]


def no_symlinks(path):
    for item in (path,) + tuple(path.parents):
        if item.is_symlink():
            raise RuntimeError("Symlinked path is not supported")


def private_write(path, text):
    no_symlinks(path)
    temporary = path.with_name(path.name + "." + str(os.getpid()) + ".incoming")
    fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temporary), str(path))


def verify_environment():
    if os.getuid() == 0 or RELEASE.parent != ROOT / "deployment":
        raise RuntimeError("Run as the existing NAS owner from its deployment release")
    for path in (ROOT, RELEASE):
        no_symlinks(path)
        info = path.stat()
        if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError("Release is not controlled by the NAS owner")
    manifest = json.loads((RELEASE / "MANIFEST.json").read_text())
    for name, expected in {**manifest["deployment_files"], **{"site/"+k:v for k,v in manifest["public_files"].items()}}.items():
        path = RELEASE / name
        no_symlinks(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Deployment release hash mismatch")


def process_matches(pid):
    proc = Path("/proc") / str(pid)
    try:
        return (proc.stat().st_uid == os.getuid() and (proc / "cwd").resolve() == RELEASE
                and (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0") == [arg.encode() for arg in ARGV])
    except OSError:
        return False


def readiness():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    paths = [("/", 200), ("/assets/app.css", 200), ("/assets/app.js", 200),
             ("/assets/", 404), ("/README.md", 404), ("/MANIFEST.json", 404),
             ("/.git/config", 404), ("/../deploy/static_server.py", 404), ("/%2e%2e/deploy/static_server.py", 404)]
    for path, expected in paths:
        request = urllib.request.Request("http://127.0.0.1:" + str(PORT) + path, headers={"Host": HOST})
        try:
            response = opener.open(request, timeout=2)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            if response.status != expected:
                raise RuntimeError("Static origin route check failed: " + path)
            if path == "/" and b"Office" not in response.read():
                raise RuntimeError("Static origin returned unexpected page")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["probe", "start", "status"])
    args = parser.parse_args()
    os.umask(0o077)
    verify_environment()
    no_symlinks(STATE)
    with socket.socket() as probe:
        occupied = probe.connect_ex(("127.0.0.1", PORT)) == 0
    if args.mode == "probe":
        print(json.dumps({"bind": "127.0.0.1:" + str(PORT), "occupied": occupied,
                          "release_verified": True, "public_route_enabled_by_this_script": False}))
        return
    if STATE.exists():
        info = STATE.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise RuntimeError("Origin state must be private owner-controlled storage")
    elif args.mode == "start":
        STATE.mkdir(parents=True, mode=0o700)
        os.chmod(str(STATE), 0o700)
    else:
        raise RuntimeError("Origin is not initialized; status does not start it")
    pidfile = STATE / "origin.pid"
    no_symlinks(pidfile)
    pid = int(pidfile.read_text()) if pidfile.exists() else None
    if pidfile.exists() and (pidfile.stat().st_uid != os.getuid() or stat.S_IMODE(pidfile.stat().st_mode) != 0o600):
        raise RuntimeError("Origin PID file is not private")
    if occupied:
        if not pid or not process_matches(pid):
            raise RuntimeError("Origin port is occupied by an unrecognized process")
        readiness()
    elif args.mode == "status":
        raise RuntimeError("Origin is not running; no automatic start from status")
    else:
        if pidfile.exists():
            raise RuntimeError("Recorded origin stopped; preserve evidence and review before restart")
        logpath = STATE / "origin.log"
        no_symlinks(logpath)
        fd = os.open(str(logpath), os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "ab") as log:
            process = subprocess.Popen(ARGV, cwd=str(RELEASE), stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        pid = process.pid
        private_write(pidfile, str(pid) + "\n")
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Static origin exited; inspect its private log")
            try:
                readiness()
                break
            except (OSError, RuntimeError):
                time.sleep(0.25)
        else:
            raise RuntimeError("Static origin readiness timed out")
    receipt = {"running": True, "pid": pid, "bind": "127.0.0.1:" + str(PORT),
               "release": str(RELEASE), "public_url": "https://" + HOST + "/",
               "public_route_enabled_by_this_script": False}
    private_write(STATE / "origin.json", json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
