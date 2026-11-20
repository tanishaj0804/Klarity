"""Run dbt with your .env settings loaded (dbt does not read .env by itself).

    python scripts/run_dbt.py debug
    python scripts/run_dbt.py build                      # run models and tests
    python scripts/run_dbt.py build --select silver
    python scripts/run_dbt.py build --vars "{use_geolocation: true}"

Any arguments are passed to dbt. dbt lives in its own environment (requirements-dbt.txt).
"""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "dbt" / "klarity"


def main(argv):
    env_file = os.environ.get("KLARITY_ENV_FILE")
    load_dotenv(env_file or REPO / ".env")
    missing = [k for k in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing in your .env file: {', '.join(missing)}")
    cmd = ["dbt", *argv, "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
