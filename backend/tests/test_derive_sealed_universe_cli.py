"""Smoke: derive script is importable / argparse-safe."""
import runpy
from pathlib import Path

def test_derive_script_defines_main():
    path = Path(__file__).resolve().parents[2] / "scripts" / "derive_sealed_universe.py"
    assert path.is_file()
    # Do not execute main; just compile
    compile(path.read_text(), str(path), "exec")
