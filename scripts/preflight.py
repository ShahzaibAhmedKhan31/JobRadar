#!/usr/bin/env python
"""JobRadar environment doctor.

Answers the question "why is my UI showing errors?" with concrete checks and
copy-pasteable fixes. Runs on Windows, macOS and Linux with the backend's
virtualenv Python:

    Windows:  .\\.venv\\Scripts\\python.exe scripts\\preflight.py
    macOS:    ./.venv/bin/python scripts/preflight.py

Exit code is 0 when everything needed for `npm run dev` + `uvicorn` is in place,
1 otherwise. It never modifies anything.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

OK = "ok"
WARN = "warn"
FAIL = "fail"
SYMBOLS = {OK: "PASS", WARN: "WARN", FAIL: "FAIL"}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    hint: str = ""


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.5)
        return sock.connect_ex((host, port)) == 0


def _http_json(url: str, timeout: float = 3.0) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            import json

            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def _mask(url: str) -> str:
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    credentials, _, host = rest.partition("@")
    user, _, _ = credentials.partition(":")
    return f"{scheme}://{user}:***@{host}"


def check_python() -> Check:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info < (3, 11):
        return Check(
            "Python version",
            FAIL,
            f"{version} — JobRadar needs 3.11+",
            "Install Python 3.12 and recreate the virtualenv.",
        )
    return Check("Python version", OK, f"{version} ({sys.executable})")


def check_backend_deps() -> list[Check]:
    checks: list[Check] = []
    missing = [
        module
        for module in ("fastapi", "sqlalchemy", "alembic", "psycopg", "pydantic_settings", "uvicorn")
        if importlib.util.find_spec(module) is None
    ]
    if missing:
        checks.append(
            Check(
                "Backend dependencies",
                FAIL,
                f"missing: {', '.join(missing)}",
                "Activate the backend virtualenv, then run: "
                "pip install -r backend\\requirements-dev.txt",
            )
        )
    else:
        checks.append(Check("Backend dependencies", OK, "fastapi, sqlalchemy, alembic, psycopg, uvicorn"))
    return checks


def check_env_files() -> list[Check]:
    checks: list[Check] = []
    pairs = [
        (REPO_ROOT / ".env", REPO_ROOT / ".env.example", "PostgreSQL container credentials"),
        (BACKEND_DIR / ".env", BACKEND_DIR / ".env.example", "DATABASE_URL and app settings"),
    ]
    for target, example, purpose in pairs:
        if target.exists():
            checks.append(Check(f"{target.relative_to(REPO_ROOT)}", OK, purpose))
        elif example.exists():
            checks.append(
                Check(
                    f"{target.relative_to(REPO_ROOT)}",
                    WARN,
                    f"missing ({purpose}) — defaults will be used",
                    f"Copy-Item {example.relative_to(REPO_ROOT)} {target.relative_to(REPO_ROOT)}",
                )
            )
        else:
            checks.append(Check(f"{target.relative_to(REPO_ROOT)}", WARN, "missing"))
    frontend_env = FRONTEND_DIR / ".env.local"
    checks.append(
        Check(
            "frontend/.env.local",
            OK if frontend_env.exists() else WARN,
            "present" if frontend_env.exists() else "missing — defaults to http://127.0.0.1:8000",
            "" if frontend_env.exists() else "Optional. Copy frontend\\.env.example if the API is not on port 8000.",
        )
    )
    return checks


def load_settings():
    """Import the app settings exactly the way uvicorn does (cwd = backend/)."""
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.core.config import Settings

    return Settings()


def check_database(settings) -> Check:
    from sqlalchemy import create_engine, text

    url = settings.database_url
    if settings.is_sqlite:
        return Check("Database", WARN, f"SQLite configured: {_mask(url)}", "PostgreSQL is the supported target.")
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 4})
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar_one()
        engine.dispose()
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        message = str(exc).strip().splitlines()[0][:180]
        return Check(
            "Database",
            FAIL,
            f"cannot connect to {_mask(url)} — {message}",
            "Is PostgreSQL running? From the repo root: docker compose up -d postgres "
            "(then `docker compose ps` should show healthy). If it is up, try 127.0.0.1 "
            "instead of localhost in DATABASE_URL.",
        )
    short = version.split(" on ")[0]
    return Check("Database", OK, f"{short} at {_mask(url)}")


def check_migrations(settings) -> Check:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, text

    if settings.is_sqlite:
        return Check("Migrations", WARN, "skipped for SQLite")
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        head = ScriptDirectory.from_config(config).get_current_head()
        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 4})
        with engine.connect() as connection:
            current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        engine.dispose()
    except Exception as exc:  # noqa: BLE001
        return Check(
            "Migrations",
            FAIL,
            f"could not read schema version — {str(exc).strip().splitlines()[0][:160]}",
            "cd backend; alembic upgrade head",
        )
    if current is None:
        return Check("Migrations", FAIL, "no alembic_version row — schema not created", "cd backend; alembic upgrade head")
    if current != head:
        return Check("Migrations", FAIL, f"database at {current}, code expects {head}", "cd backend; alembic upgrade head")
    return Check("Migrations", OK, f"at head ({head})")


def check_api(port: int) -> Check:
    health = _http_json(f"http://127.0.0.1:{port}/health")
    if health is not None:
        return Check(
            "FastAPI on port %d" % port,
            OK,
            f"responding — version {health.get('version')}, database {health.get('database')}",
        )
    if _port_open("127.0.0.1", port):
        return Check(
            f"FastAPI on port {port}",
            FAIL,
            "something is listening but /health did not answer",
            "Check the uvicorn terminal for a traceback; another app may be using the port. "
            f"netstat -ano | findstr :{port}",
        )
    return Check(
        f"FastAPI on port {port}",
        FAIL,
        "nothing is listening — the frontend proxy cannot reach it",
        "Start it in a second terminal: cd backend; "
        f"uvicorn app.main:app --reload --port {port}",
    )


def check_web(port: int) -> Check:
    if _port_open("127.0.0.1", port):
        return Check(f"Next.js on port {port}", OK, "listening")
    return Check(
        f"Next.js on port {port}",
        WARN,
        "not running yet (expected if you only started the backend)",
        f"cd frontend; npm run dev   # then open http://localhost:{port}",
    )


def check_frontend_deps() -> list[Check]:
    checks: list[Check] = []
    if shutil.which("node") is None:
        checks.append(Check("Node.js", FAIL, "not on PATH", "Install Node 20+ from https://nodejs.org"))
    else:
        checks.append(Check("Node.js", OK, shutil.which("node") or ""))
    if (FRONTEND_DIR / "node_modules").exists():
        checks.append(Check("Frontend dependencies", OK, "frontend/node_modules present"))
    else:
        checks.append(Check("Frontend dependencies", FAIL, "frontend/node_modules is missing", "cd frontend; npm install"))
    return checks


def check_scraping(settings) -> Check:
    installed = importlib.util.find_spec("jobspy") is not None
    sites = ", ".join(settings.jobspy_sites) or "none"
    if not settings.jobspy_enabled:
        return Check("Scraping (jobspy)", WARN, "disabled by JOBSPY_ENABLED=false", "Manual import and the sample feed still work.")
    if not installed:
        return Check(
            "Scraping (jobspy)",
            WARN,
            "python-jobspy is not installed — LinkedIn/Indeed cannot be scraped",
            "pip install -r backend\\requirements-scraping.txt",
        )
    return Check("Scraping (jobspy)", OK, f"installed · sites: {sites} · enabled")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose a local JobRadar setup.")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3000)
    args = parser.parse_args()

    checks: list[Check] = [check_python()]
    checks.extend(check_backend_deps())
    checks.extend(check_env_files())

    settings = None
    try:
        settings = load_settings()
    except Exception as exc:  # noqa: BLE001
        checks.append(
            Check(
                "Backend settings",
                FAIL,
                f"could not load app.core.config — {exc}",
                "Run this script with the backend virtualenv Python.",
            )
        )
    if settings is not None:
        checks.append(check_database(settings))
        checks.append(check_migrations(settings))

    checks.extend(check_frontend_deps())
    checks.append(check_api(args.api_port))
    checks.append(check_web(args.web_port))
    if settings is not None:
        checks.append(check_scraping(settings))

    width = max(len(check.name) for check in checks)
    print()
    print("JobRadar preflight")
    print("=" * (width + 8))
    for check in checks:
        print(f"[{SYMBOLS[check.status]}] {check.name.ljust(width)}  {check.detail}")
        if check.hint and check.status != OK:
            print(f"       {' ' * width}  -> {check.hint}")
    print()

    failures = [check for check in checks if check.status == FAIL]
    warnings = [check for check in checks if check.status == WARN]
    if failures:
        print(f"{len(failures)} check(s) failed. Fix them top-to-bottom, then re-run this script.")
        return 1
    if warnings:
        print(f"Everything required is ready ({len(warnings)} optional warning(s)).")
    else:
        print("Everything is ready. Start the API and the frontend, then open http://localhost:3000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
