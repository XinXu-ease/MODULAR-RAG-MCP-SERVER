from __future__ import annotations

import subprocess
import sys


def main() -> int:
    command = [sys.executable, "-m", "streamlit", "run", "src/observability/dashboard/app.py"]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
