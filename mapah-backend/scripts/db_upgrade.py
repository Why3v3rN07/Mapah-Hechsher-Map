"""
Run Alembic upgrades safely from Python.

Usage:
  python scripts/db_upgrade.py
  python scripts/db_upgrade.py --seed
  python scripts/db_upgrade.py --seed --wipe
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    print(f"$ {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=str(cwd), env=env)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def required_tables_exist(backend_dir: Path, env: dict[str, str]) -> bool:
    check_code = """
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    insp = db.inspect(db.engine)
    required = {
        'users', 'places', 'hechshers', 'hechsher_aliases',
        'place_tags', 'place_hechshers', 'place_aliases', 'submissions',
        'user_preferred_hechshers', 'refresh_token_families',
        'refresh_tokens', 'revoked_tokens'
    }
    existing = set(insp.get_table_names())
    missing = sorted(required - existing)
    if missing:
        print('MISSING_TABLES:' + ','.join(missing))
        raise SystemExit(2)
"""
    completed = subprocess.run([sys.executable, "-c", check_code], cwd=str(backend_dir), env=env)
    return completed.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run database migrations and optional seed.")
    parser.add_argument("--seed", action="store_true", help="Run seed.py after migration upgrade")
    parser.add_argument("--wipe", action="store_true", help="When used with --seed, wipe seedable tables first")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.setdefault("FLASK_APP", "run.py")

    run([sys.executable, "-m", "flask", "db", "upgrade"], backend_dir, env)

    # Recovery path: if DB was previously stamped incorrectly, reapply from base.
    if not required_tables_exist(backend_dir, env):
        print("Schema check failed after upgrade; stamping base and reapplying migration...")
        run([sys.executable, "-m", "flask", "db", "stamp", "base"], backend_dir, env)
        run([sys.executable, "-m", "flask", "db", "upgrade"], backend_dir, env)
        if not required_tables_exist(backend_dir, env):
            raise SystemExit("Database schema check failed after recovery attempt.")

    if args.seed:
        seed_cmd = [sys.executable, "seed.py"]
        if args.wipe:
            seed_cmd.append("--wipe")
        run(seed_cmd, backend_dir, env)

    print("Database upgrade complete.")


if __name__ == "__main__":
    main()
