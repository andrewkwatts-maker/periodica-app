"""Tier B: the GL capability spike (docs/dev/gl-spike.md) passes on this machine.

Runs ``tools/gl_spike.py --quick`` in a subprocess: the spike creates its own
hidden window and may pick a different GL backend, which must not leak into
the test process.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SPIKE = Path(__file__).resolve().parents[1] / "tools" / "gl_spike.py"


@pytest.mark.gpu
def test_gl_spike_has_no_failing_capability(tmp_path):
    out = tmp_path / "spike.json"
    proc = subprocess.run(
        [sys.executable, str(SPIKE), "--quick", "--json", str(out)],
        capture_output=True, text=True, timeout=300,
    )
    assert out.exists(), proc.stdout[-4000:] + proc.stderr[-4000:]
    checks = json.loads(out.read_text(encoding="utf-8"))["checks"]
    assert {c["key"] for c in checks} == set("abcdefg")
    failing = {c["key"]: c["notes"] for c in checks if c["status"] == "FAIL"}
    assert not failing, failing
    assert proc.returncode == 0
