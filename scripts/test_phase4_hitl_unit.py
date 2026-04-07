from __future__ import annotations

import subprocess
import sys


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_services/test_human_review.py",
        "-q",
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
