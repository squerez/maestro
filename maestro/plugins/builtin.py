from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from maestro.plugins.plugin import plugin


def _read_csv_from_zip(zip_path: Path, csv_name: str, sep: str) -> Any:
    import fnmatch

    import polars as pl

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        match = next((n for n in names if fnmatch.fnmatch(Path(n).name, csv_name)), None)
        if match is None:
            raise FileNotFoundError(
                f"{csv_name!r} not found in {zip_path}. Available: {[Path(n).name for n in names[:20]]}"
            )
        with zf.open(match) as f:
            return pl.read_csv(f, separator=sep, infer_schema_length=10_000).lazy()


@plugin(kind="source", name="http_csv")
class HttpCsvSourcePlugin:
    """Downloads a CSV from a URL and returns a Polars LazyFrame."""

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import polars as pl
        import requests

        url = params["url"]
        sep = params.get("separator", ",")
        resp = requests.get(url, timeout=params.get("timeout", 30))
        resp.raise_for_status()
        return pl.read_csv(io.StringIO(resp.text), separator=sep).lazy()


@plugin(kind="source", name="http_ndjson")
class HttpNdJsonSourcePlugin:
    """Downloads newline-delimited JSON from a URL and returns a Polars LazyFrame."""

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import polars as pl
        import requests

        url = params["url"]
        resp = requests.get(url, timeout=params.get("timeout", 30))
        resp.raise_for_status()
        return pl.read_ndjson(io.StringIO(resp.text)).lazy()


@plugin(kind="source", name="http_json")
class HttpJsonSourcePlugin:
    """Fetches a JSON API endpoint and returns a Polars LazyFrame from a list at a key path.

    params:
      url          – API URL (query params can be embedded or passed via query_params)
      query_params – dict of query parameters to append (optional)
      list_key     – dot-separated path to the list in the response, e.g. "events" or "data.items"
      headers      – dict of extra request headers (optional)
      timeout      – request timeout seconds (default 60)
    """

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import polars as pl
        import requests

        url: str = params["url"]
        list_key: str = params.get("list_key", "")
        query_params: dict = params.get("query_params", {})
        headers: dict = params.get("headers", {})
        timeout: int = params.get("timeout", 60)

        resp = requests.get(url, params=query_params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()

        # traverse dot-separated key path
        node = payload
        if list_key:
            for key in list_key.split("."):
                node = node[key]

        if not isinstance(node, list):
            raise ValueError(f"Expected a list at '{list_key}', got {type(node).__name__}")

        return pl.DataFrame(node, strict=False).lazy()


@plugin(kind="source", name="local_zip_csv")
class LocalZipCsvSourcePlugin:
    """Reads a CSV from inside a local zip archive and returns a Polars LazyFrame.

    params:
      path      – local path to the .zip file
      csv_name  – name of the CSV file inside the zip (supports fnmatch globs)
      separator – field delimiter (default ,)
    """

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        zip_path = Path(params["path"]).expanduser()
        csv_name: str = params["csv_name"]
        sep: str = params.get("separator", ",")
        return _read_csv_from_zip(zip_path, csv_name, sep)


@plugin(kind="source", name="kaggle_zip_csv")
class KaggleZipCsvSourcePlugin:
    """Downloads a Kaggle dataset zip (if not already cached) and reads a CSV from it.

    params:
      dataset   – e.g. "jessicali9530/celeba-dataset"
      csv_name  – name of the CSV inside the zip (fnmatch glob ok)
      cache_dir – where to store the zip (default ~/.maestro/kaggle_cache)
      separator – field delimiter (default ,)

    Credentials are read from ~/.kaggle/kaggle.json (KAGGLE_USERNAME /
    KAGGLE_KEY env vars also work).
    """

    def __init__(self, runtime: Any = None) -> None:
        pass

    def _credentials(self) -> tuple[str, str]:
        import os

        username = os.environ.get("KAGGLE_USERNAME")
        key = os.environ.get("KAGGLE_KEY")
        if username and key:
            return username, key
        cred_path = Path("~/.kaggle/kaggle.json").expanduser()
        if cred_path.exists():
            creds = json.loads(cred_path.read_text())
            return creds["username"], creds["key"]
        raise RuntimeError(
            "Kaggle credentials not found. Set KAGGLE_USERNAME/KAGGLE_KEY env vars "
            "or create ~/.kaggle/kaggle.json via kaggle.com/settings → API."
        )

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import requests

        dataset: str = params["dataset"]
        csv_name: str = params["csv_name"]
        sep: str = params.get("separator", ",")
        cache_dir = Path(params.get("cache_dir", "~/.maestro/kaggle_cache")).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)

        slug = dataset.replace("/", "_")
        zip_path = cache_dir / f"{slug}.zip"

        if not zip_path.exists():
            username, key = self._credentials()
            url = f"https://www.kaggle.com/api/v1/datasets/download/{dataset}"
            from loguru import logger

            logger.info(f"Downloading Kaggle dataset {dataset} → {zip_path}")
            with requests.get(url, auth=(username, key), stream=True, timeout=300) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            logger.debug(f"  {downloaded / total:.0%} ({downloaded >> 20} MB)")
            logger.info(f"Download complete: {zip_path.stat().st_size >> 20} MB")

        return _read_csv_from_zip(zip_path, csv_name, sep)


@plugin(kind="sink", name="parquet")
class LocalParquetSinkPlugin:
    """Writes a Polars DataFrame/LazyFrame to a local Parquet file."""

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import polars as pl

        path = params["path"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df = data.collect() if isinstance(data, pl.LazyFrame) else data
        df.write_parquet(path, compression=params.get("compression", "snappy"))
        return df.lazy() if isinstance(data, pl.LazyFrame) else df


@plugin(kind="sink", name="csv")
class LocalCsvSinkPlugin:
    """Writes a Polars DataFrame/LazyFrame to a local CSV file."""

    def __init__(self, runtime: Any = None) -> None:
        pass

    def run(self, data: Any, params: Dict[str, Any]) -> Any:
        import polars as pl

        path = params["path"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df = data.collect() if isinstance(data, pl.LazyFrame) else data
        df.write_csv(path, separator=params.get("separator", ","))
        return df.lazy() if isinstance(data, pl.LazyFrame) else df
