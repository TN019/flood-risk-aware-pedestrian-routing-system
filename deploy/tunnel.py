"""Share this copy of the app through a temporary public link (a Cloudflare quick tunnel).

Run it with ./deploy/share.sh (macOS, Linux) or deploy\\share.bat (Windows). Each run builds the
web client from the working copy, starts the API on a free local port, opens the tunnel and prints
the public address, with a QR code of it in the terminal and in deploy/share.png; Ctrl+C stops both
and deletes the image. The address is public (anyone who has it can open the app),
changes on every run, and works only while this computer is on and the script is running.

Needs uv, Node.js (npm), cloudflared, and the processed data (see Getting started in README.md).
"""

from __future__ import annotations

import argparse
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SHARE_PNG = Path(__file__).resolve().parent / "share.png"  # QR code of the link, only while it works
TUNNEL_URL = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com")
INSTALL = {
    "npm": "Node.js 20 from https://nodejs.org",
    "cloudflared": "it with 'brew install cloudflared' (macOS), "
    "'winget install --id Cloudflare.cloudflared' (Windows) "
    "or from https://github.com/cloudflare/cloudflared/releases",
}
API_TIMEOUT_S = 180  # loading the network and the flood scenarios takes a while
TUNNEL_TIMEOUT_S = 60
# A new address takes a minute or more to resolve, and every lookup made before that is cached as
# "not found" for 60 s, so the link is checked sparingly: first after 10 s, then every 10 s.
LINK_FIRST_CHECK_S = 10
LINK_CHECK_EVERY_S = 10
LINK_TIMEOUT_S = 180


def step(text: str) -> None:
    print(f"\n==> {text}", flush=True)


def fail(text: str) -> None:
    sys.exit(f"\nError: {text}")


def require(tool: str) -> str:
    path = shutil.which(tool)
    if path is None:
        fail(f"{tool} not found. Install {INSTALL[tool]}.")
    return path


def free_port(preferred: int) -> int:
    """The preferred port if nothing uses it, otherwise the next free one."""
    for port in range(preferred, preferred + 50):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                continue  # something is listening
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    fail(f"no free port between {preferred} and {preferred + 49}.")


def check_data() -> None:
    from floodroute import config

    if not any(config.PROCESSED_DIR.glob("*.gpkg")):
        fail(
            f"no processed data in {config.PROCESSED_DIR}. Download and build it first (Getting started in README.md)."
        )


def build_client(npm: str) -> None:
    if not (FRONTEND / "node_modules").exists():
        step("Installing the web client's dependencies")
        if subprocess.run([npm, "ci"], cwd=FRONTEND).returncode != 0:
            fail("npm ci failed; see its messages above.")
    step("Building the web client from this working copy")
    if subprocess.run([npm, "run", "build"], cwd=FRONTEND).returncode != 0:
        fail("the web client did not build; see its messages above.")


def responds(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status == 200
    except OSError:
        return False


def wait_until(ready, process: subprocess.Popen, timeout_s: float, every_s: float = 1) -> bool:
    """Wait until ready() is true; False if the process exits or the time runs out first."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        if ready():
            return True
        time.sleep(every_s)
    return False


def start_api(port: int) -> subprocess.Popen:
    step(f"Starting the API on port {port}")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "floodroute.api.app:app", "--port", str(port), "--log-level", "warning"],
        cwd=BACKEND,
    )


def start_tunnel(cloudflared: str, port: int) -> tuple[subprocess.Popen, list[str], deque[str]]:
    """Start the quick tunnel; its address appears in the returned list once cloudflared prints it."""
    step("Opening the Cloudflare tunnel")
    process = subprocess.Popen(
        [cloudflared, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    address: list[str] = []
    log: deque[str] = deque(maxlen=20)

    def read() -> None:
        for line in process.stdout:
            log.append(line.rstrip())
            match = TUNNEL_URL.search(line)
            if match and not address:
                address.append(match.group())

    threading.Thread(target=read, daemon=True).start()
    return process, address, log


def show_qr(link: str) -> None:
    """Print a QR code of the link and save it as deploy/share.png."""
    qr = segno.make(link, error="m")
    qr.save(str(SHARE_PNG), scale=10, border=4)
    try:
        qr.terminal(compact=True)
    except UnicodeEncodeError:  # a console without block characters
        qr.terminal()


# Signals that end the run like Ctrl+C. SIGBREAK is how Windows reports Ctrl+Break and a closed
# console window; SIGHUP a closed terminal elsewhere.
STOP_SIGNALS = [getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGBREAK") if hasattr(signal, name)]


def interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def stop(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8010, help="local port for the API (the next free one if taken)")
    args = parser.parse_args()

    SHARE_PNG.unlink(missing_ok=True)  # left over if an earlier run was killed
    for stop_signal in STOP_SIGNALS:
        signal.signal(stop_signal, interrupt)
    npm = require("npm")
    cloudflared = require("cloudflared")
    check_data()
    build_client(npm)

    port = free_port(args.port)
    local = f"http://127.0.0.1:{port}"
    api = tunnel = None
    try:
        api = start_api(port)
        if not wait_until(lambda: responds(f"{local}/api/options"), api, API_TIMEOUT_S):
            fail("the API did not start; see its messages above.")

        tunnel, address, log = start_tunnel(cloudflared, port)
        if not wait_until(lambda: bool(address), tunnel, TUNNEL_TIMEOUT_S):
            fail("cloudflared gave no address. Its last messages:\n  " + "\n  ".join(log))
        public = address[0]
        print("    waiting for the new address to work (usually one to two minutes)...", flush=True)
        time.sleep(LINK_FIRST_CHECK_S)
        reachable = wait_until(
            lambda: responds(f"{public}/api/options"), tunnel, LINK_TIMEOUT_S, every_s=LINK_CHECK_EVERY_S
        )

        print(f"\n  Public link   {public}")
        print(f"  This computer {local}")
        if not reachable:
            print("  The link did not answer from this computer yet; it may need another minute.")
        print()
        show_qr(public)
        print(f"  The QR code is also in {SHARE_PNG.relative_to(ROOT)} until this stops.")
        print("\n  Anyone with the link can open the app while this runs. Press Ctrl+C to stop.\n", flush=True)

        while api.poll() is None and tunnel.poll() is None:
            time.sleep(1)
        which = "API" if api.poll() is not None else "tunnel"
        fail(f"the {which} stopped, so the link no longer works.")
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        for stop_signal in STOP_SIGNALS:  # let the clean-up finish
            signal.signal(stop_signal, signal.SIG_IGN)
        stop(tunnel)
        stop(api)
        SHARE_PNG.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
