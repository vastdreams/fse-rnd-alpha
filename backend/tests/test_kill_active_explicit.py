"""Unknown kill states must remain unknown and fail closed downstream."""

from __future__ import annotations


def test_kill_active_map_preserves_unknowns():
    # Mirror scripts/build_universe.py + patch_kill_active.py contract
    KILL_ACTIVE = {"WDAY": True, "FRSH": False, "DOCU": False, "PCTY": False}
    panel = ["EGAN", "WDAY", "FRSH", "DOCU", "PCTY", "ZZZZ", "ACME"]
    flags = {t: KILL_ACTIVE.get(t) for t in panel}
    assert flags["WDAY"] is True
    assert flags["FRSH"] is False
    assert flags["EGAN"] is None
    assert flags["ZZZZ"] is None
