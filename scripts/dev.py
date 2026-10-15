"""Start ARIA for local development and say exactly what is wrong if it cannot.

    python scripts/dev.py                 # SQLite file aria-dev.db, API :8000, web :3000
    python scripts/dev.py --api-port 8010 --web-port 3100

Checks, in order: both ports are free, migrations apply, the backend answers
/health, the frontend answers, and the backend allows the frontend's origin
(CORS) so the browser can actually reach it. DATABASE_URL in the environment
wins over the default SQLite file. Ctrl+C stops both servers.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fail(problem: str, fix: str) -> None:
    print(f"\n[problem] {problem}\n  fix: {fix}")
    raise SystemExit(1)


def port_in_use(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_for(url: str, proc: subprocess.Popen, seconds: int) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except urllib.error.HTTPError:
            return  # it answered; the status is checked separately
        except OSError:
            time.sleep(1)


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)  # status lines show even when output is piped to a log
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3000)
    args = parser.parse_args()
    api, web = f"http://localhost:{args.api_port}", f"http://localhost:{args.web_port}"

    for name, port in (("backend", args.api_port), ("frontend", args.web_port)):
        if port_in_use(port):
            fail(f"Port {port} for the {name} is already in use, possibly by an older ARIA server.",
                 f"Stop that process, or pick another port with --{'api' if name == 'backend' else 'web'}-port.")
    print(f"[ok] Ports {args.api_port} and {args.web_port} are free")

    env = {**os.environ, "PYTHONPATH": "backend", "ARIA_CORS_ORIGINS": web,
           "ARIA_SCHEDULER_ENABLED": os.environ.get("ARIA_SCHEDULER_ENABLED", "false")}
    env.setdefault("DATABASE_URL", "sqlite:///./aria-dev.db")

    migrate = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env,
                             capture_output=True, text=True)
    if migrate.returncode != 0:
        fail("Database migrations did not apply:\n  " + "\n  ".join(migrate.stderr.strip().splitlines()[-6:]),
             "Fix the error above (often a missing package: pip install -r requirements-dev.txt).")
    print(f"[ok] Database is up to date ({env['DATABASE_URL'].split('@')[-1]})")

    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(args.api_port)],
                               cwd=ROOT, env=env)
    frontend = None
    try:
        wait_for(f"{api}/health", backend, 60)
        if backend.poll() is not None:
            fail("The backend stopped while starting.", "Read the backend error printed above.")
        print(f"[ok] Backend answers at {api}")

        npm = "npm.cmd" if os.name == "nt" else "npm"
        frontend = subprocess.Popen([npm, "run", "dev", "--", "-p", str(args.web_port)], cwd=ROOT / "frontend-v2",
                                    env={**os.environ, "NEXT_PUBLIC_API_URL": api})
        wait_for(web, frontend, 120)
        if frontend.poll() is not None:
            fail("The frontend stopped while starting.", "Read the frontend error printed above (try npm install).")
        print(f"[ok] Frontend answers at {web}")

        request = urllib.request.Request(f"{api}/health", headers={"Origin": web})
        allowed = urllib.request.urlopen(request, timeout=5).headers.get("Access-Control-Allow-Origin")
        if allowed not in (web, "*"):
            fail(f"The backend does not accept requests from {web}, so the app would show connection errors.",
                 "Check ARIA_CORS_ORIGINS; this script sets it, so another config may be overriding it.")
        print(f"[ok] The frontend can reach the backend\n\nARIA is running at {web}  (Ctrl+C to stop)")
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (frontend, backend):
            if proc and proc.poll() is None:
                if os.name == "nt":  # npm starts node as a child; stop the whole tree
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
                else:
                    proc.terminate()


if __name__ == "__main__":
    main()
