from __future__ import annotations

import subprocess
import sys


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_core/test_hybrid_equation.py",
        "tests/test_vectordb/test_sparse_index.py",
        "-q",
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())