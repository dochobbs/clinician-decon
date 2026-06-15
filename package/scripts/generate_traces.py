"""Generate persona-driven synthetic decon traces from a source checkout."""

from __future__ import annotations

from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PACKAGE_DIR / "src"
if str(SRC_DIR) not in sys.path:
  sys.path.insert(0, str(SRC_DIR))

from decon.persona_trace_generator import main  # noqa: E402


if __name__ == "__main__":
  raise SystemExit(main())
