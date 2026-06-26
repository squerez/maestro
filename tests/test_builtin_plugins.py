import io
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import polars as pl

from maestro.plugins.builtin import (
    HttpCsvSourcePlugin,
    HttpJsonSourcePlugin,
    HttpNdJsonSourcePlugin,
    LocalParquetSinkPlugin,
    LocalCsvSinkPlugin,
    LocalZipCsvSourcePlugin,
)


# ── HTTP CSV ─────────────────────────────────────────────────────────────────

def test_http_csv_returns_lazy_frame():
    csv_text = "id,name\n1,Alice\n2,Bob\n"
    mock_resp = MagicMock()
    mock_resp.text = csv_text
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = HttpCsvSourcePlugin().run(None, {"url": "http://example.com/data.csv"})

    mock_get.assert_called_once()
    assert isinstance(result, pl.LazyFrame)
    df = result.collect()
    assert df.shape == (2, 2)
    assert df["name"].to_list() == ["Alice", "Bob"]


def test_http_csv_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(Exception, match="404"):
            HttpCsvSourcePlugin().run(None, {"url": "http://example.com/missing.csv"})


def test_http_csv_custom_separator():
    tsv_text = "id\tname\n1\tAlice\n"
    mock_resp = MagicMock()
    mock_resp.text = tsv_text
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = HttpCsvSourcePlugin().run(None, {"url": "http://x.com/d.tsv", "separator": "\t"})

    assert result.collect()["name"].to_list() == ["Alice"]


# ── HTTP JSON ─────────────────────────────────────────────────────────────────

def test_http_json_extracts_list():
    payload = {"events": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = HttpJsonSourcePlugin().run(None, {"url": "http://api.x.com/", "list_key": "events"})

    df = result.collect()
    assert df.shape == (2, 2)
    assert df["title"].to_list() == ["A", "B"]


def test_http_json_nested_key():
    payload = {"data": {"items": [{"x": 1}, {"x": 2}]}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = HttpJsonSourcePlugin().run(None, {"url": "http://x.com", "list_key": "data.items"})

    assert result.collect()["x"].to_list() == [1, 2]


def test_http_json_raises_when_not_list():
    payload = {"result": {"not": "a list"}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="Expected a list"):
            HttpJsonSourcePlugin().run(None, {"url": "http://x.com", "list_key": "result"})


# ── HTTP NDJSON ───────────────────────────────────────────────────────────────

def test_http_ndjson_returns_lazy_frame():
    ndjson = '{"id":1,"v":"a"}\n{"id":2,"v":"b"}\n'
    mock_resp = MagicMock()
    mock_resp.text = ndjson
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = HttpNdJsonSourcePlugin().run(None, {"url": "http://x.com/nd.json"})

    df = result.collect()
    assert df.shape == (2, 2)
    assert df["v"].to_list() == ["a", "b"]


# ── Parquet sink ──────────────────────────────────────────────────────────────

def test_parquet_sink_writes_file(tmp_path):
    df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    out = tmp_path / "out.parquet"
    result = LocalParquetSinkPlugin().run(df, {"path": str(out)})
    assert out.exists()
    loaded = pl.read_parquet(out)
    assert loaded.shape == (3, 2)


def test_parquet_sink_creates_parent_dirs(tmp_path):
    df = pl.DataFrame({"x": [1]})
    out = tmp_path / "deep" / "nested" / "out.parquet"
    LocalParquetSinkPlugin().run(df, {"path": str(out)})
    assert out.exists()


def test_parquet_sink_preserves_lazy_frame_type(tmp_path):
    lf = pl.DataFrame({"x": [1, 2]}).lazy()
    out = tmp_path / "out.parquet"
    result = LocalParquetSinkPlugin().run(lf, {"path": str(out)})
    assert isinstance(result, pl.LazyFrame)


# ── CSV sink ─────────────────────────────────────────────────────────────────

def test_csv_sink_writes_file(tmp_path):
    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    out = tmp_path / "out.csv"
    LocalCsvSinkPlugin().run(df, {"path": str(out)})
    assert out.exists()
    content = out.read_text()
    assert "a,b" in content
    assert "1,x" in content


def test_csv_sink_custom_separator(tmp_path):
    df = pl.DataFrame({"a": [1], "b": ["x"]})
    out = tmp_path / "out.tsv"
    LocalCsvSinkPlugin().run(df, {"path": str(out), "separator": "\t"})
    content = out.read_text()
    assert "\t" in content


# ── Local zip CSV ─────────────────────────────────────────────────────────────

def test_local_zip_csv_reads_csv(tmp_path):
    import zipfile

    zip_path = tmp_path / "data.zip"
    csv_content = b"id,name\n1,Alice\n2,Bob\n"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("data.csv", csv_content)

    result = LocalZipCsvSourcePlugin().run(None, {"path": str(zip_path), "csv_name": "data.csv"})
    df = result.collect()
    assert df.shape == (2, 2)
    assert df["name"].to_list() == ["Alice", "Bob"]


def test_local_zip_csv_missing_file_raises(tmp_path):
    import zipfile

    zip_path = tmp_path / "data.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("other.csv", b"x,y\n1,2\n")

    with pytest.raises(FileNotFoundError, match="missing.csv"):
        LocalZipCsvSourcePlugin().run(None, {"path": str(zip_path), "csv_name": "missing.csv"})
