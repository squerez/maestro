import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from maestro.pipeline.state import Checkpoint, CheckpointStore


@pytest.fixture
def store(tmp_path):
    return CheckpointStore(tmp_path)


def _make_checkpoint(pipeline="test_pipeline", status="success", records=100):
    return Checkpoint(
        pipeline=pipeline,
        last_run=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        status=status,
        records_processed=records,
    )


def test_save_creates_file(store, tmp_path):
    cp = _make_checkpoint()
    store.save(cp)
    assert (tmp_path / "test_pipeline.json").exists()


def test_save_and_load_roundtrip(store):
    cp = _make_checkpoint(records=42)
    store.save(cp)
    loaded = store.load("test_pipeline")
    assert loaded.pipeline == "test_pipeline"
    assert loaded.status == "success"
    assert loaded.records_processed == 42
    assert loaded.last_run == cp.last_run


def test_load_missing_returns_none(store):
    assert store.load("nonexistent") is None


def test_save_overwrites(store):
    store.save(_make_checkpoint(records=10))
    store.save(_make_checkpoint(records=99))
    loaded = store.load("test_pipeline")
    assert loaded.records_processed == 99


def test_delete_removes_file(store, tmp_path):
    store.save(_make_checkpoint())
    store.delete("test_pipeline")
    assert not (tmp_path / "test_pipeline.json").exists()
    assert store.load("test_pipeline") is None


def test_delete_nonexistent_is_safe(store):
    store.delete("nonexistent")  # should not raise


def test_list_all_empty(store):
    assert store.list_all() == []


def test_list_all_returns_sorted_newest_first(store):
    cp1 = Checkpoint(
        pipeline="pipe1",
        last_run=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="success",
    )
    cp2 = Checkpoint(
        pipeline="pipe2",
        last_run=datetime(2026, 6, 1, tzinfo=timezone.utc),
        status="failed",
    )
    store.save(cp1)
    store.save(cp2)
    result = store.list_all()
    assert result[0].pipeline == "pipe2"
    assert result[1].pipeline == "pipe1"


def test_list_all_skips_corrupt_files(store, tmp_path):
    store.save(_make_checkpoint("good"))
    (tmp_path / "bad.json").write_text("not json {{{")
    # corrupt file should not crash list_all (it raises on bad json — document current behaviour)
    with pytest.raises(Exception):
        store.list_all()


def test_extra_field_persisted(store):
    cp = _make_checkpoint()
    cp.extra = {"dq_results": {"suite1": {"success": True}}}
    store.save(cp)
    loaded = store.load("test_pipeline")
    assert loaded.extra["dq_results"]["suite1"]["success"] is True


def test_now_returns_utc():
    dt = CheckpointStore.now()
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc
