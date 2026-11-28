import pytest

from agi import disk_guard


def test_disk_guard_raises_when_full(monkeypatch, tmp_path):
    monkeypatch.setattr(disk_guard, "free_gb", lambda path="C:\\": 0.1)
    monkeypatch.setattr(disk_guard, "cleanup_snapshots", lambda: [])
    monkeypatch.setattr(disk_guard, "cleanup_temp", lambda hours=24: 0)
    with pytest.raises(disk_guard.DiskFullError):
        disk_guard.ensure_free(1.0, tmp_path)
